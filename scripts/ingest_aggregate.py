"""Aggregation + cross-check + write helpers for the ingest skill.

The main agent loads subagent outputs, passes them through these functions,
and (after user review) writes claims / financials. No LLM calls happen here
— this is plumbing only.

Public API:

- ``load_json_tolerant(raw)``: parse JSON even when wrapped in a markdown
  code fence or embedded in prose.
- ``normalize_claim(c)``: coerce subagent schema quirks (polarity synonyms,
  flat ``evidence_text``) into the canonical ``claim`` shape.
- ``normalize_period(p)``: ``FY2025 -> 2025A``, quarterly unchanged.
- ``aggregate(outputs)``: merge per-section subagent outputs into a single
  pre-write bundle.
- ``dedup_claims(claims)``: drop exact duplicates on (text-prefix, tag, tf).
- Cross-checks: ``check_revenue_consistency``, ``check_period_consistency``,
  ``check_empty_sections``, ``check_financials_required``. Each returns a
  list of human-readable issue strings; empty list = pass.
- ``build_claims_batch(...)``: produce the dict ``validate_batch`` expects
  (header fields flat at the top level — not nested under ``"header"``).
- ``write_financials(...)`` / ``write_claims(...)``: perform the writes.
"""
from __future__ import annotations

import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

from app.io import claims as claims_io
from app.io import financials as fin_io

POLARITY_MAP = {
    "bull": "bull",
    "bear": "bear",
    "neutral": "neutral",
    "positive": "bull",
    "negative": "bear",
}

# Only claims that explicitly talk about TOTAL revenue get revenue-consistency
# checked against financials CSV. Segment/geography/channel sub-revenues are
# naturally smaller than total and would otherwise trigger false positives.
_TOTAL_REVENUE_KEYS = ("total revenue", "营业收入", "营业总收入", "总收入")
_SEGMENT_REVENUE_KEYS = (
    "segment",
    "united states revenue",
    "rest of world",
    "rest of the world",
    "wholesale revenue",
    "online revenue",
    "international revenue",
    "personalized",
    "hers brand",
)

_MONEY_RE = re.compile(
    r"\$([\d,]+(?:\.\d+)?)\s*(M|B|billion|million)\b", re.IGNORECASE
)


# ---------- Parsing ---------------------------------------------------------


def load_json_tolerant(raw: str) -> dict:
    """Decode JSON that may be wrapped in a ```json ... ``` fence or embedded
    in other prose. Falls back to the first ``{`` and last ``}``.
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty input")
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1)
    else:
        first, last = raw.find("{"), raw.rfind("}")
        if first >= 0 and last > first:
            raw = raw[first : last + 1]
    return json.loads(raw)


def load_subagent_json(path: str | Path) -> dict:
    """Read a subagent output file and parse it tolerantly."""
    return load_json_tolerant(Path(path).read_text(encoding="utf-8"))


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
    hold ``claims``, ``profile_fragments``, ``financial_rows``, ``meta_updates``,
    ``flags``.

    Merge rules:
      - ``claims``: normalized (``normalize_claim``) then concatenated.
      - ``profile_fragments``: merged by key; on duplicate, prefer the
        longer string (assumed to be more detailed).
      - ``financial_rows``: concatenated (cross-check handles conflicts).
      - ``meta_updates``: first writer wins (``setdefault``).
      - ``flags``: kept per-subagent for surfacing in the final report.
      - ``empty_subagents``: subagents that returned nothing meaningful.
    """
    merged: dict = {
        "claims": [],
        "profile_fragments": {},
        "financial_rows": [],
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

        merged["financial_rows"].extend(blob.get("financial_rows") or [])

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
            and not (blob.get("financial_rows") or [])
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


def route_key_facts(key_facts: list[dict]) -> dict[str, list[dict]]:
    """Split digest key_facts into per-layer buckets based on target_layer.

    cross-layer facts (e.g. share_by_player that reports a ticker's industry
    market share) go into BOTH industry and company buckets so the arena
    page / company page both see the fact. Malformed facts (no target_refs,
    unknown target_layer) are silently dropped.
    """
    out: dict[str, list[dict]] = {"industry": [], "arena": [], "company": []}
    for f in key_facts:
        layer = f.get("target_layer")
        refs = f.get("target_refs") or {}
        if not refs:
            continue
        if layer == "industry":
            if refs.get("industry_slug"):
                out["industry"].append(f)
        elif layer == "arena":
            if refs.get("arena_slug"):
                out["arena"].append(f)
        elif layer == "company":
            if refs.get("ticker") and refs.get("market"):
                out["company"].append(f)
        elif layer == "cross":
            # Cross-layer: append to industry (primary) and also company if
            # ticker present.
            if refs.get("industry_slug"):
                out["industry"].append(f)
            if refs.get("ticker") and refs.get("market"):
                out["company"].append(f)
        # else: unknown target_layer → drop
    return out


def fact_to_observation(
    fact: dict,
    source_meta: dict,
    *,
    extracted_by: str,
    extracted_at: str,
) -> dict:
    """Map a digest key_fact (target_layer=industry) to an observations.jsonl row
    matching spec §4.2 schema.
    """
    slug = (fact.get("target_refs") or {}).get("industry_slug", "")
    # ID: first 3 chars of slug after any "cn-"/"us-" prefix
    # For "cn-cmp-material", we want "cmp"
    slug_no_geo = re.sub(r"^(cn|us|uk|de|fr|jp|in|br)-", "", slug)
    first_segment = slug_no_geo.split("-")[0]
    prefix = re.sub(r"[^a-z]", "", first_segment)[:3] or "obs"
    # Use fact idx + source sha8 for deterministic local id.
    obs_id = f"{prefix}-{source_meta.get('sha8', '')}-{fact.get('idx', 0):04d}"
    return {
        "id": obs_id,
        "dimension": fact.get("dimension_hint"),
        "field": fact.get("field_hint"),
        "value": fact.get("value_numeric"),
        "unit": fact.get("unit"),
        "timeframe": fact.get("timeframe"),
        "time_type": fact.get("time_type", "actual"),
        "metric_type": fact.get("metric_type", "atomic"),
        "segment": fact.get("segment"),
        "arena_refs": fact.get("arena_refs") or [],
        "source_id": source_meta["source_id"],
        "source_file": source_meta.get("source_file"),
        "source_note": source_meta.get("source_note"),
        "confidence": fact.get("confidence", "medium"),
        "claim_text": fact.get("fact_text"),
        "evidence": fact.get("evidence_quote"),
        "extracted_by": extracted_by,
        "extracted_at": extracted_at,
    }


def write_industry_observations(
    facts: list[dict],
    source_meta: dict,
    *,
    extracted_by: str,
    extracted_at: str,
    base: Path | None = None,
) -> int:
    """Convert digest facts → observation rows, dedup, append per-slug.
    Returns total rows written across all slugs.
    """
    from app.io import industry as industry_io  # lazy: avoid circular

    by_slug: dict[str, list[dict]] = {}
    for f in facts:
        refs = f.get("target_refs") or {}
        slug = refs.get("industry_slug")
        if not slug:
            continue
        by_slug.setdefault(slug, []).append(fact_to_observation(
            f, source_meta, extracted_by=extracted_by, extracted_at=extracted_at,
        ))

    total = 0
    for slug, rows in by_slug.items():
        rows = industry_io.dedup_observations(rows)
        total += industry_io.append_observations(slug, rows, base=base)
    return total



def _extract_money_usd(text: str) -> float | None:
    """Pull ``$N M|B`` from claim_text, return dollars. ``None`` if absent."""
    m = _MONEY_RE.search(text)
    if not m:
        return None
    val = float(m.group(1).replace(",", ""))
    unit = m.group(2).lower()
    return val * (1e9 if unit in ("b", "billion") else 1e6)


def check_revenue_consistency(merged: dict, tol: float = 0.02) -> list[str]:
    """Only validates claims that explicitly talk about TOTAL revenue. Segment
    and channel sub-revenue claims are skipped (they're smaller than total by
    definition and must not trigger a pause).
    """
    issues: list[str] = []
    by_period = {r["period"]: r for r in merged.get("financial_rows", [])}
    for c in merged.get("claims", []):
        if c.get("claim_type") != "quantitative":
            continue
        ct = (c.get("claim_text") or "").lower()
        if not any(k in ct for k in _TOTAL_REVENUE_KEYS):
            continue
        if any(k in ct for k in _SEGMENT_REVENUE_KEYS):
            continue
        tf = c.get("timeframe") or ""
        row = by_period.get(tf) or by_period.get(normalize_period(tf))
        if not row or row.get("revenue") is None:
            continue
        usd = _extract_money_usd(c.get("claim_text") or "")
        if usd is None:
            continue
        csv_rev = float(row["revenue"])
        if csv_rev == 0:
            continue
        diff = abs(usd - csv_rev) / csv_rev
        if diff > tol:
            issues.append(
                f"claim '{c['claim_text'][:80]}' -> {usd:.0f} vs "
                f"financial_rows[{tf}].revenue={csv_rev:.0f} "
                f"(diff {diff * 100:.1f}%)"
            )
    return issues


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


def check_financials_required(merged: dict) -> list[str]:
    issues: list[str] = []
    for r in merged.get("financial_rows", []):
        if r.get("revenue") is None:
            issues.append(f"row {r.get('period')!r} missing revenue")
        if r.get("net_income") is None:
            issues.append(f"row {r.get('period')!r} missing net_income")
    return issues


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


def build_financials_csv(rows: list[dict]) -> str:
    """Produce a CSV string accepted by ``fin_io.import_financials_csv``.

    Period strings are normalized (``FY2025 -> 2025A``). Missing financial
    columns are emitted as empty strings (SQLite treats these as NULL).
    """
    cols = ["period", "period_type"] + list(fin_io.FINANCIAL_COLUMNS)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        r = {**r, "period": normalize_period(r["period"])}
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})
    return buf.getvalue()


# ---------- Writers ---------------------------------------------------------


def write_financials(
    ticker: str,
    rows: list[dict],
    *,
    source_file: str,
    base: Path | None = None,
) -> int:
    csv_text = build_financials_csv(rows)
    return fin_io.import_financials_csv(ticker, csv_text, source_file=source_file, base=base)


def write_claims(
    ticker: str,
    market: str,
    claims: list[dict],
    *,
    source_id: str,
    source_file: str,
    extracted_by: str,
    extracted_at: str,
    base: Path | None = None,
) -> tuple[int, list[dict]]:
    """Validate then append. Returns ``(n_written, errors)``. On any
    validation error returns ``(0, errors)`` and writes nothing.
    """
    batch = build_claims_batch(
        claims,
        source_id=source_id,
        source_file=source_file,
        extracted_by=extracted_by,
        extracted_at=extracted_at,
    )
    subjects = claims_io.load_subjects(base=base)
    try:
        header, valid, errors = claims_io.validate_batch(
            json.dumps(batch, ensure_ascii=False), subjects
        )
    except ValueError as e:
        return 0, [{"error": str(e)}]
    if errors:
        return 0, errors
    claims_io.append_batch(ticker, market, valid, header=header, base=base)
    return len(valid), []


# ---------- Three-layer narrative writers -----


def _is_blank_block(s) -> bool:
    return s is None or (isinstance(s, str) and not s.strip())


def write_industry_narrative(
    narratives: dict[str, dict[str, str]],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    """narratives shape: {industry_slug: {dim: md_block, ...}, ...}.
    Appends one source block per non-empty (slug, dim). Returns count written."""
    from app.io import industry as industry_io

    count = 0
    for slug, by_dim in (narratives or {}).items():
        if not by_dim:
            continue
        for dim, block in by_dim.items():
            if _is_blank_block(block):
                continue
            industry_io.append_narrative_block(slug, dim, block, source_meta, base=base)
            count += 1
    return count


def write_arena_narrative(
    narratives: dict[str, dict[str, str]],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    """narratives shape: {arena_slug: {dim: md_block, ...}}."""
    from app.io import arenas as arenas_io

    count = 0
    for slug, by_dim in (narratives or {}).items():
        if not by_dim:
            continue
        for dim, block in by_dim.items():
            if _is_blank_block(block):
                continue
            arenas_io.append_narrative_block(slug, dim, block, source_meta, base=base)
            count += 1
    return count


def write_company_narrative(
    narratives: dict[str, dict[str, str]],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    """narratives shape: {company_key (MARKET_TICKER): {dim: md_block, ...}}."""
    from app.io import company as company_io

    count = 0
    for key, by_dim in (narratives or {}).items():
        if not by_dim or "_" not in key:
            continue
        market, ticker = key.split("_", 1)
        for dim, block in by_dim.items():
            if _is_blank_block(block):
                continue
            company_io.append_narrative_block(
                ticker, market, dim, block, source_meta, base=base,
            )
            count += 1
    return count


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


def facts_to_claims(facts: list[dict]) -> list[dict]:
    """Convert company-layer digest facts to claim dicts accepted by
    claims_io.validate_batch (and subsequently append_batch)."""
    out: list[dict] = []
    for f in facts:
        if f.get("target_layer") not in ("company", "cross"):
            continue
        refs = f.get("target_refs") or {}
        if not (refs.get("ticker") and refs.get("market")):
            continue
        out.append({
            "claim_text": f.get("fact_text"),
            "subject_tag": f.get("subject_tag_hint"),
            "polarity": f.get("polarity", "neutral"),
            "claim_type": (
                "quantitative" if f.get("value_numeric") is not None
                else "qualitative"
            ),
            "timeframe": f.get("timeframe"),
            "time_type": f.get("time_type", "actual"),
            "evidence": [{"text": f.get("evidence_quote") or "", "type": "primary"}],
            "confidence": f.get("confidence", "medium"),
            "arena_refs": f.get("arena_refs") or [],
            "company_dimension_hint": f.get("company_dimension_hint"),
        })
    return out


def group_company_facts(facts: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """Return {(ticker, market): [facts]} for every company-layer fact."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for f in facts:
        if f.get("target_layer") not in ("company", "cross"):
            continue
        refs = f.get("target_refs") or {}
        if not (refs.get("ticker") and refs.get("market")):
            continue
        groups.setdefault((refs["ticker"], refs["market"]), []).append(f)
    return groups


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

    Note: base param is treated as the companies directory itself (not project root).
    Internally we convert it to project root for create_company compatibility.
    """
    from app.io import company as company_io

    key = f"{market}_{ticker}"
    companies_dir = base if base else company_io.cfg.COMPANIES_DIR
    dir_path = companies_dir / key

    # Check if company already exists. Also check for the case where someone called
    # create_company(base=companies_dir) directly, which would create it at
    # companies_dir/companies/key due to create_company's internal logic.
    if dir_path.exists():
        return {"key": key, "autobuilt": False}
    if (companies_dir / "companies" / key).exists():
        return {"key": key, "autobuilt": False}

    # create_company expects base= as project root, but our caller passes companies_dir.
    # So we need to pass the parent directory to create_company.
    project_root = companies_dir.parent if base else None
    company_io.create_company(
        ticker=ticker, market=market, name=name,
        industry_slugs=industry_slugs or [],
        currency=currency, base=project_root,
    )
    return {"key": key, "autobuilt": True}


def propose_arena_bootstrap(proposed: list[dict]) -> list[dict]:
    """Normalize digest proposed_arenas to arena-create args for the main agent
    to surface to the user. Lower-cases slug; drops proposals without
    battleground_focus. Returns list of {slug, name, industry, battleground_focus,
    participants}.
    """
    out: list[dict] = []
    for p in proposed or []:
        slug_raw = (p.get("tentative_slug") or "").strip().lower()
        focus = (p.get("battleground_focus") or "").strip()
        industry = (p.get("parent_industry_slug") or "").strip()
        if not slug_raw or not focus or not industry:
            continue
        participants = p.get("tentative_participants") or []
        # Synthesize a display name from focus if absent
        out.append({
            "slug": slug_raw,
            "name": p.get("name") or focus[:40],
            "industry": industry,
            "battleground_focus": focus,
            "participants": participants,
        })
    return out


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
