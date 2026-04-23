"""Yearly competence map: where am I skilled vs not.

Aggregate journal entries by (year, sector) and compute:
- count of decisions
- mean process score
- mean result score
- process−result gap (high = "lucky despite poor process", dangerous)
- hit rate: fraction of buy/add entries with result_quality >= 4

Sector comes from each ticker's ``meta.md`` frontmatter (``sector`` or
``industry_primary``). Entries for companies with no meta are bucketed as
``(unclassified)`` — they show up at the bottom of the table so you can't
ignore the hole.
"""
from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path
from statistics import mean

from app import config as cfg
from app.io import journal as journal_io

_PROCESS_FIELDS = (
    "process_quality",
    "process_rigor",
    "process_rule_adherence",
    "process_emotional_control",
)
_RESULT_FIELDS = ("result_quality",)

UNCLASSIFIED = "(unclassified)"


def _as_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _avg(values: list[float | None]) -> float | None:
    nums = [v for v in values if v is not None]
    return mean(nums) if nums else None


def _process_score(fm: dict) -> float | None:
    return _avg([_as_float(fm.get(k)) for k in _PROCESS_FIELDS])


def _result_score(fm: dict) -> float | None:
    return _avg([_as_float(fm.get(k)) for k in _RESULT_FIELDS])


def _split_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    import yaml
    return yaml.safe_load(text[3:end].strip()) or {}


def _ticker_sectors(base: Path | None) -> dict[tuple[str, str], str]:
    """Map ``(market, ticker) -> sector`` by scanning each company's meta.md."""
    companies_dir = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    out: dict[tuple[str, str], str] = {}
    if not companies_dir.exists():
        return out
    for d in companies_dir.iterdir():
        if not d.is_dir() or "_" not in d.name:
            continue
        market, ticker = d.name.split("_", 1)
        meta = d / "meta.md"
        if not meta.exists():
            continue
        fm = _split_frontmatter(meta.read_text(encoding="utf-8"))
        sector = fm.get("sector") or fm.get("industry_primary") or None
        if sector:
            out[(market.upper(), ticker.upper())] = str(sector)
    return out


def yearly_map(year: int, base: Path | None = None) -> dict:
    """Aggregate journal entries filed in ``year`` by sector.

    Returns ``{year, total, by_sector: [{sector, count, avg_process, avg_result,
    gap, hit_rate}]}`` sorted by count desc.
    """
    sectors = _ticker_sectors(base)
    entries = journal_io.list_entries(base=base)
    buckets: dict[str, list[dict]] = {}
    total = 0
    for fm in entries:
        d = fm.get("date")
        if not d:
            continue
        try:
            if date_cls.fromisoformat(d).year != year:
                continue
        except ValueError:
            continue
        total += 1
        key = (str(fm.get("market", "")).upper(), str(fm.get("ticker", "")).upper())
        sector = sectors.get(key) or UNCLASSIFIED
        p = _process_score(fm)
        r = _result_score(fm)
        buckets.setdefault(sector, []).append({
            "id": fm.get("id"),
            "ticker": fm.get("ticker"),
            "market": fm.get("market"),
            "action": fm.get("action"),
            "process": p,
            "result": r,
        })

    by_sector = []
    for sector, rows in buckets.items():
        avg_p = _avg([r["process"] for r in rows])
        avg_r = _avg([r["result"] for r in rows])
        gap = None
        if avg_p is not None and avg_r is not None:
            gap = avg_r - avg_p
        buys = [r for r in rows if r["action"] in ("buy", "add")]
        hit = None
        if buys:
            scored = [r for r in buys if r["result"] is not None]
            if scored:
                hit = sum(1 for r in scored if r["result"] >= 4) / len(scored)
        by_sector.append({
            "sector": sector,
            "count": len(rows),
            "avg_process": avg_p,
            "avg_result": avg_r,
            "gap": gap,
            "hit_rate": hit,
            "entries": sorted(rows, key=lambda x: x.get("ticker") or ""),
        })
    by_sector.sort(key=lambda x: (x["sector"] == UNCLASSIFIED, -x["count"]))
    return {"year": year, "total": total, "by_sector": by_sector}


def available_years(base: Path | None = None) -> list[int]:
    years = set()
    for fm in journal_io.list_entries(base=base):
        d = fm.get("date")
        if not d:
            continue
        try:
            years.add(date_cls.fromisoformat(d).year)
        except ValueError:
            continue
    return sorted(years, reverse=True)
