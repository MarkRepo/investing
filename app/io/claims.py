"""Claim (research atomic unit) jsonl I/O.

Claims are one JSON object per line. Two ingest paths:
  - Single-claim form (manual entry from the research workbench)
  - Batch import: paste LLM-extracted JSON, validate against the controlled
    vocabulary, then append. The LLM call happens outside this process — we
    only validate and write. See docs/prompts/claim-extraction.md for the
    prompt shape.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

from app import config as cfg

POLARITIES = ("bull", "bear", "neutral")
CLAIM_TYPES = ("quantitative", "qualitative")

REQUIRED_CLAIM_FIELDS = ("claim_text", "subject_tag", "polarity", "claim_type")


def _claims_path(ticker: str, market: str, base: Path | None) -> Path:
    root = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    return root / f"{market}_{ticker}" / "claims.jsonl"


def _sources_dir(ticker: str, market: str, base: Path | None) -> Path:
    root = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    return root / f"{market}_{ticker}" / "sources"


def load_subjects(base: Path | None = None) -> list[dict]:
    root = Path(base) / "controlled-vocab" if base else cfg.CONTROLLED_VOCAB_DIR
    path = root / "subjects.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("subjects") or []


def iter_all_claims(base: Path | None = None) -> list[dict]:
    """Walk every company's claims.jsonl and return enriched claim dicts.

    Each claim gets two derived fields: ``_market`` / ``_ticker`` so the
    audit sampler knows which company it came from.
    """
    companies_dir = (Path(base) / "companies") if base else cfg.COMPANIES_DIR
    if not companies_dir.exists():
        return []
    out: list[dict] = []
    for d in sorted(companies_dir.iterdir()):
        if not d.is_dir() or "_" not in d.name:
            continue
        market, ticker = d.name.split("_", 1)
        for c in read_claims(ticker, market, base=base):
            c2 = {**c, "_market": market, "_ticker": ticker}
            out.append(c2)
    return out


def audit_sample(
    month: str | None = None,
    pct: float = 0.10,
    seed: int | None = None,
    base: Path | None = None,
) -> dict:
    """Random-sample ``pct`` fraction of claims, optionally filtered to a month.

    ``month`` is "YYYY-MM"; matched against ``extracted_at`` prefix. If None,
    audits all claims.

    Returns ``{total, pool, sample, month, pct, seed_used}``.
    """
    import random

    if pct <= 0 or pct > 1:
        raise ValueError("pct must be in (0, 1]")
    all_claims = iter_all_claims(base=base)
    pool = all_claims
    if month:
        pool = [c for c in all_claims if str(c.get("extracted_at", "")).startswith(month)]
    if seed is None:
        # Deterministic per-month: same month always produces same sample
        import hashlib
        seed_key = (month or "all").encode("utf-8")
        seed = int(hashlib.sha256(seed_key).hexdigest()[:8], 16)
    rng = random.Random(seed)
    size = max(1, int(round(len(pool) * pct)))
    sample = rng.sample(pool, k=min(size, len(pool))) if pool else []
    return {
        "total": len(all_claims),
        "pool": len(pool),
        "sample": sample,
        "month": month,
        "pct": pct,
        "seed_used": seed,
    }


def read_claims(ticker: str, market: str, base: Path | None = None) -> list[dict]:
    path = _claims_path(ticker, market, base)
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def append_claim(
    ticker: str,
    market: str,
    claim: dict,
    base: Path | None = None,
) -> Path:
    if claim.get("polarity") not in POLARITIES:
        raise ValueError(f"polarity must be one of {POLARITIES}")
    if claim.get("claim_type") not in CLAIM_TYPES:
        raise ValueError(f"claim_type must be one of {CLAIM_TYPES}")
    if not claim.get("claim_text"):
        raise ValueError("claim_text required")
    if not claim.get("subject_tag"):
        raise ValueError("subject_tag required")

    path = _claims_path(ticker, market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Auto-assign id if absent
    if not claim.get("id"):
        existing = read_claims(ticker, market, base)
        claim["id"] = f"{ticker}-{len(existing) + 1:04d}"
    claim.setdefault("ticker", ticker)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(claim, ensure_ascii=False) + "\n")
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_claim(claim: dict, valid_subject_ids: set[str]) -> list[str]:
    """Return a list of error strings for a single claim, empty if valid."""
    errs: list[str] = []
    for f in REQUIRED_CLAIM_FIELDS:
        if not claim.get(f):
            errs.append(f"missing {f}")
    if claim.get("polarity") not in POLARITIES:
        errs.append(f"polarity must be one of {POLARITIES}, got {claim.get('polarity')!r}")
    if claim.get("claim_type") not in CLAIM_TYPES:
        errs.append(f"claim_type must be one of {CLAIM_TYPES}, got {claim.get('claim_type')!r}")
    if claim.get("subject_tag") and claim["subject_tag"] not in valid_subject_ids:
        errs.append(
            f"subject_tag {claim['subject_tag']!r} not in controlled-vocab "
            f"(add it to subjects.yaml first or change this value)"
        )
    return errs


def parse_batch_json(raw: str) -> tuple[dict, list[dict]]:
    """Decode LLM output.

    Accepts either:
      - A JSON object ``{"source_id": "...", "source_file": "...", "claims": [...]}``
      - A bare JSON array of claim objects

    Returns ``(header_metadata, claims_list)``. Raises ``ValueError`` if the
    input isn't parseable JSON or doesn't match either shape.
    """
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty input")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"not valid JSON: {e.msg} at line {e.lineno} col {e.colno}") from e

    if isinstance(data, list):
        return {}, data
    if isinstance(data, dict):
        claims = data.get("claims")
        if not isinstance(claims, list):
            raise ValueError("object form requires a 'claims' array")
        header = {k: v for k, v in data.items() if k != "claims"}
        return header, claims
    raise ValueError("top-level must be a JSON object or array")


def validate_batch(
    raw: str, subjects: list[dict] | None = None
) -> tuple[dict, list[dict], list[dict]]:
    """Parse + validate a batch payload.

    Returns ``(header, valid_claims, errors)`` where errors has
    ``{"index": int, "errors": [str], "claim": {...}}``.
    """
    header, raw_claims = parse_batch_json(raw)
    valid_ids = {s["id"] for s in (subjects or [])}
    valid: list[dict] = []
    errors: list[dict] = []
    for i, c in enumerate(raw_claims):
        if not isinstance(c, dict):
            errors.append({"index": i, "errors": ["not a JSON object"], "claim": c})
            continue
        errs = list(validate_claim(c, valid_ids))

        # Optional arena_refs: list[str] of arena slugs; default []
        arena_refs = c.get("arena_refs")
        if arena_refs is None:
            c["arena_refs"] = []
        elif not isinstance(arena_refs, list) or not all(isinstance(s, str) for s in arena_refs):
            errs.append("arena_refs must be list[str]")

        # Optional company_dimension_hint: must match COMPANY_DIMENSIONS if provided
        dim_hint = c.get("company_dimension_hint")
        if dim_hint is not None:
            if dim_hint not in cfg.COMPANY_DIMENSIONS:
                errs.append(
                    f"company_dimension_hint must be one of {cfg.COMPANY_DIMENSIONS} "
                    f"or null, got {dim_hint!r}"
                )

        if errs:
            errors.append({"index": i, "errors": errs, "claim": c})
        else:
            valid.append(c)
    return header, valid, errors


def append_batch(
    ticker: str,
    market: str,
    claims: list[dict],
    header: dict | None = None,
    base: Path | None = None,
) -> list[str]:
    """Append validated claims. Returns the list of assigned ids, in order.

    Header fields (``source_id``, ``source_file``, ``extracted_by``) are
    propagated into each claim if not already present on the claim itself.
    Claims must have been through ``validate_claim`` — this writer trusts
    its input and does not re-validate.
    """
    header = header or {}
    path = _claims_path(ticker, market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = read_claims(ticker, market, base)
    next_seq = len(existing) + 1
    ids: list[str] = []
    with path.open("a", encoding="utf-8") as f:
        for c in claims:
            claim: dict[str, Any] = {**c}
            for k in ("source_id", "source_file", "extracted_by"):
                if header.get(k) and not claim.get(k):
                    claim[k] = header[k]
            if not claim.get("id"):
                claim["id"] = f"{ticker}-{next_seq:04d}"
                next_seq += 1
            claim.setdefault("ticker", ticker)
            claim.setdefault("extracted_at", _now_iso())
            evidence_text = claim.pop("evidence_text", None)
            if evidence_text and not claim.get("evidence"):
                claim["evidence"] = [{"text": evidence_text, "type": "secondary"}]
            f.write(json.dumps(claim, ensure_ascii=False) + "\n")
            ids.append(claim["id"])
    return ids


def consensus_map(claims: Iterable[dict]) -> list[dict]:
    """Group by subject_tag and return polarity counts.

    Output: ``[{subject_tag, bull, bear, neutral, claims: [...]}, ...]``
    sorted by total claim count desc.
    """
    grouped: dict[str, list[dict]] = {}
    for c in claims:
        grouped.setdefault(c.get("subject_tag") or "(untagged)", []).append(c)

    out: list[dict] = []
    for tag, items in grouped.items():
        counts = Counter(c.get("polarity") for c in items)
        out.append(
            {
                "subject_tag": tag,
                "bull": counts.get("bull", 0),
                "bear": counts.get("bear", 0),
                "neutral": counts.get("neutral", 0),
                "claims": items,
            }
        )
    out.sort(key=lambda x: x["bull"] + x["bear"] + x["neutral"], reverse=True)
    return out


def save_source_markdown(
    ticker: str,
    market: str,
    filename: str,
    content: bytes,
    base: Path | None = None,
) -> Path:
    """Save an uploaded source file under ``sources/{filename}``."""
    safe = Path(filename).name  # strip any directory components
    if not safe:
        raise ValueError("empty filename")
    dest = _sources_dir(ticker, market, base) / safe
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)
    return dest


def list_sources(ticker: str, market: str, base: Path | None = None) -> list[dict]:
    d = _sources_dir(ticker, market, base)
    if not d.exists():
        return []
    out: list[dict] = []
    for p in sorted(d.iterdir()):
        if not p.is_file():
            continue
        out.append({"name": p.name, "size": p.stat().st_size, "path": str(p)})
    return out
