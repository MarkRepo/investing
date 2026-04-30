"""Aggregation + cross-check + write helpers for the ingest skill.

The main agent loads subagent outputs, passes them through these functions,
and (after user review) writes claims. No LLM calls happen here — this is
plumbing only. Financial line-items are no longer part of ingest; numbers
come from API (akshare / yfinance) via the financials page.

Public API:

- ``normalize_claim(c)``: coerce subagent schema quirks (polarity synonyms,
  flat ``evidence_text``) into the canonical ``claim`` shape.
- ``normalize_period(p)``: ``FY2025 -> 2025A``, quarterly unchanged.
- ``aggregate(outputs)``: merge per-section subagent outputs into a single
  pre-write bundle.
- ``dedup_claims(claims)``: drop exact duplicates on (text-prefix, tag, tf).
- Cross-checks: ``check_period_consistency``, ``check_empty_sections``.
  Each returns a list of human-readable issue strings; empty list = pass.
- ``build_claims_batch(...)``: produce the dict ``validate_batch`` expects
  (header fields flat at the top level — not nested under ``"header"``).
- ``write_figure_contexts_for_company(...)``: append figure contexts to a
  company's figure_contexts.jsonl.
- ``bootstrap_arena_from_candidate(...)``: create arena from a candidate dict
  using tentative_slug / name / parent_industry_slug / battleground_focus.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

POLARITY_MAP = {
    "bull": "bull",
    "bear": "bear",
    "neutral": "neutral",
    "positive": "bull",
    "negative": "bear",
}


# ---------- Normalization ---------------------------------------------------


def normalize_claim(c: dict) -> dict:
    """Coerce subagent schema quirks into the canonical claim shape.

    - ``polarity``: ``positive|negative`` → ``bull|bear``; unknowns → ``neutral``.
    - ``evidence``: if missing but ``evidence_text`` is present, wrap into
      a single-item ``[{"text": ..., "type": "primary"}]`` list.
    """
    out = dict(c)
    pol = out.get("polarity", "neutral")
    out["polarity"] = POLARITY_MAP.get(pol, "neutral")

    if "evidence" not in out:
        text = out.pop("evidence_text", None)
        out["evidence"] = [{"text": text, "type": "primary"}] if text else []
    return out


def normalize_period(p: str) -> str:
    """``FY2025`` → ``2025A``; ``2025Q1`` / ``2025A`` unchanged.

    The SQLite ``financials.period`` column is constrained to
    ``^(\\d{4})(Q[1-4]|A)$`` — this adapter lets subagents output the more
    natural ``FYxxxx`` string without hitting the CHECK constraint.
    """
    if not isinstance(p, str):
        raise TypeError(f"period must be str, got {type(p).__name__}")
    if p.startswith("FY") and p[2:].isdigit() and len(p) == 6:
        return p[2:] + "A"
    return p


def enrich_claim(
    c: dict,
    *,
    ticker: str,
    source_id: str,
    source_file: str,
    extracted_by: str,
    extracted_at: str,
) -> dict:
    """Attach ingest-level metadata to a claim. Does NOT override fields
    already present on the claim (so subagents can override if needed).
    """
    out = dict(c)
    out.setdefault("ticker", ticker)
    out.setdefault("source_id", source_id)
    out.setdefault("source_file", source_file)
    out.setdefault("extracted_by", extracted_by)
    out.setdefault("extracted_at", extracted_at)
    return out


# ---------- Aggregation -----------------------------------------------------


def aggregate(outputs: dict[str, dict]) -> dict:
    """Merge per-subagent outputs keyed by name into a single bundle.

    ``outputs`` is ``{subagent_name: raw_output_dict}``. Each raw output may
    hold ``claims``, ``profile_fragments``, ``meta_updates``, ``flags``.

    Merge rules:
      - ``claims``: normalized (``normalize_claim``) then concatenated.
      - ``profile_fragments``: merged by key; on duplicate, prefer the
        longer string (assumed to be more detailed).
      - ``meta_updates``: first writer wins (``setdefault``).
      - ``flags``: kept per-subagent for surfacing in the final report.
      - ``empty_subagents``: subagents that returned nothing meaningful.
    """
    merged: dict = {
        "claims": [],
        "profile_fragments": {},
        "meta_updates": {},
        "competence_findings": {"answered": [], "proposed_additions": []},
        "flags_by_subagent": {},
        "empty_subagents": [],
    }
    for name, blob in outputs.items():
        claims = [normalize_claim(c) for c in blob.get("claims") or []]
        merged["claims"].extend(claims)

        for k, v in (blob.get("profile_fragments") or {}).items():
            prev = merged["profile_fragments"].get(k)
            if prev is None or len(v) > len(prev):
                merged["profile_fragments"][k] = v

        for k, v in (blob.get("meta_updates") or {}).items():
            merged["meta_updates"].setdefault(k, v)

        cf = blob.get("competence_findings") or {}
        merged["competence_findings"]["answered"].extend(cf.get("answered") or [])
        merged["competence_findings"]["proposed_additions"].extend(
            cf.get("proposed_additions") or []
        )

        merged["flags_by_subagent"][name] = list(blob.get("flags") or [])

        if (
            not claims
            and not (blob.get("profile_fragments") or {})
            and not cf.get("answered")
            and not cf.get("proposed_additions")
        ):
            merged["empty_subagents"].append(name)

    return merged


def dedup_claims(claims: list[dict]) -> list[dict]:
    """Drop exact duplicates on (first 60 chars of text, subject_tag, timeframe).

    The 60-char prefix lets us catch cases where two subagents quote the
    same sentence with minor trailing variations.
    """
    seen: set[tuple] = set()
    out: list[dict] = []
    for c in claims:
        key = (c.get("claim_text", "")[:60], c.get("subject_tag"), c.get("timeframe"))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def check_period_consistency(merged: dict, expected: str) -> list[str]:
    """The dominant claim timeframe must match the report's fiscal period."""
    tfs = [c.get("timeframe") for c in merged.get("claims", []) if c.get("timeframe")]
    if not tfs:
        return ["no claim carries a timeframe"]
    top, top_n = Counter(tfs).most_common(1)[0]
    if top != expected:
        return [f"dominant timeframe is {top} ({top_n} claims), expected {expected}"]
    return []


def check_empty_sections(merged: dict) -> list[str]:
    return [f"empty output from subagent: {name}" for name in merged.get("empty_subagents", [])]


# ---------- Builders --------------------------------------------------------


def build_claims_batch(
    claims: list[dict],
    *,
    source_id: str,
    source_file: str,
    extracted_by: str,
    extracted_at: str,
) -> dict:
    """Shape expected by ``claims_io.parse_batch_json``: header fields are
    FLAT at the top level, NOT nested under a ``"header"`` key. The nested
    form silently discards metadata and was a real source of ``source_id =
    None`` rows in earlier runs.
    """
    return {
        "source_id": source_id,
        "source_file": source_file,
        "extracted_by": extracted_by,
        "extracted_at": extracted_at,
        "claims": claims,
    }


# ---------- Writers ---------------------------------------------------------


def write_figure_contexts(
    *,
    slug: str,
    contexts: list[dict],
    source_meta: dict,
    base: Path | None = None,
) -> int:
    """Stamp source_id on each preprocess figure_context and append to
    industries/{slug}/figure_contexts.jsonl."""
    from app.io import figure_contexts as fc_io

    enriched = []
    for c in contexts or []:
        enriched.append({**c, "source_id": source_meta["source_id"]})
    return fc_io.append_figure_contexts(slug, enriched, base=base)


def ensure_industry_exists(
    *, slug: str, name: str, scope: str = "", base: Path | None = None,
) -> dict:
    """If industry slug dir missing → create it via industry_io.create_industry.
    Returns {slug, autobuilt: bool}. Caller (main agent) can surface
    autobuilt=True to the user ('I just made a new industry slug for you').
    """
    from app.io import industry as industry_io

    try:
        industry_io.read_meta(slug, base=base)
        return {"slug": slug, "autobuilt": False}
    except FileNotFoundError:
        industry_io.create_industry(slug=slug, name=name, scope=scope, base=base)
        return {"slug": slug, "autobuilt": True}


def ensure_company_exists(
    *, ticker: str, market: str, name: str,
    industry_slugs: list[str] | None = None,
    currency: str = "USD",
    base: Path | None = None,
) -> dict:
    """If companies/{market}_{ticker}/ missing → create via
    company_io.create_company. Returns {key, autobuilt}.

    base is the project root (same convention as company_io / arenas_io /
    industry_io after Plan 4 T2).
    """
    from app.io import company as company_io

    key = f"{market}_{ticker}"
    companies_dir = (Path(base) / "companies") if base else company_io.cfg.COMPANIES_DIR
    if (companies_dir / key).exists():
        return {"key": key, "autobuilt": False}

    company_io.create_company(
        ticker=ticker, market=market, name=name,
        industry_slugs=industry_slugs or [],
        currency=currency, base=base,
    )
    return {"key": key, "autobuilt": True}


def bootstrap_arena(proposal: dict, *, base: Path | None = None) -> None:
    """After user approves, actually create the arena (definition + 5 dim
    narrative skeletons). Wrapper around arenas_io.write_definition."""
    from app.io import arenas as arenas_io

    arenas_io.write_definition(
        slug=proposal["slug"],
        name=proposal["name"],
        definition_text=proposal["battleground_focus"],
        industry=proposal["industry"],
        battleground_focus=proposal["battleground_focus"],
        base=base,
    )


def write_figure_contexts_for_company(
    market_ticker: str,
    contexts: list[dict],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    """Append figure contexts to companies/{market_ticker}/figure_contexts.jsonl.

    Each row is the original context dict plus source_id, source_title, and
    source_date taken from source_meta. Returns count of rows written.
    """
    from app import config as cfg

    companies_dir = (Path(base) / "companies") if base else cfg.COMPANIES_DIR
    out_path = companies_dir / market_ticker / "figure_contexts.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for c in contexts or []:
        row = dict(c)
        row["source_id"] = source_meta.get("source_id")
        row["source_title"] = source_meta.get("source_title")
        row["source_date"] = source_meta.get("source_date")
        rows.append(row)
    with out_path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def bootstrap_arena_from_candidate(
    candidate: dict,
    *,
    base: Path | None = None,
) -> None:
    """Create an arena from a candidate dict using tentative_slug / name /
    parent_industry_slug / battleground_focus fields.

    Adapts the candidate shape into the proposal shape expected by
    bootstrap_arena and delegates to it.
    """
    proposal = {
        "slug": (candidate.get("tentative_slug") or "").strip().lower(),
        "name": (candidate.get("name") or "").strip(),
        "industry": (candidate.get("parent_industry_slug") or "").strip(),
        "battleground_focus": (candidate.get("battleground_focus") or "").strip(),
    }
    bootstrap_arena(proposal, base=base)
