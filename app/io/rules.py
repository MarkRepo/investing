"""Portfolio-level rules (``portfolio/rules.md``): structured limits + evaluator.

Schema: YAML frontmatter holds numeric limits; markdown body is free-form prose.

Supported limits (all optional, numeric):
- ``max_single_pct``: any single position's position_pct must be ≤ this
- ``max_sector_pct``: sum of position_pct per sector must be ≤ this
- ``min_cash_pct``: (100 − total position_pct) must be ≥ this

Sector lookup reads each company's ``meta.md`` (``sector`` or ``industry_primary``
field). Positions without meta bucket as ``(unclassified)`` — the rule still
applies to that bucket to force you to classify.

``evaluate`` returns a list of violation dicts:
``{kind, limit, actual, entity, severity: 'warn' | 'block'}``.

Severity is informational only — this module reports, the UI decides what to do.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app import config as cfg

NUMERIC_LIMITS = ("max_single_pct", "max_sector_pct", "min_cash_pct", "max_theme_pct")


def _path(base: Path | None) -> Path:
    root = (Path(base) / "portfolio") if base else cfg.PORTFOLIO_DIR
    return root / "rules.md"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    return fm, text[end + len("\n---") :].lstrip("\n")


def read(base: Path | None = None) -> dict:
    path = _path(base)
    if not path.exists():
        return {"limits": {}, "body": ""}
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    limits: dict = {}
    for k in NUMERIC_LIMITS:
        v = fm.get(k)
        if v is None or v == "":
            continue
        try:
            limits[k] = float(v)
        except (TypeError, ValueError):
            continue
    return {"limits": limits, "body": body, "raw_fm": fm}


def write(limits: dict, body: str, base: Path | None = None) -> Path:
    """Write the limits (only validated numeric keys) + body back. Overwrites."""
    cleaned: dict = {}
    for k in NUMERIC_LIMITS:
        v = limits.get(k)
        if v is None or v == "":
            continue
        try:
            cleaned[k] = float(v)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{k} must be numeric, got {v!r}") from e
        if cleaned[k] < 0 or cleaned[k] > 100:
            raise ValueError(f"{k} must be 0..100")
    path = _path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(cleaned, allow_unicode=True, sort_keys=False).rstrip() if cleaned else ""
    header = f"---\n{fm_text}\n---\n\n" if fm_text else ""
    path.write_text(header + body.lstrip() + ("\n" if not body.endswith("\n") else ""), encoding="utf-8")
    return path


def _ticker_sectors(base: Path | None) -> dict[tuple[str, str], str]:
    companies_dir = (Path(base) / "companies") if base else cfg.COMPANIES_DIR
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
        fm, _ = _split_frontmatter(meta.read_text(encoding="utf-8"))
        sector = fm.get("sector") or fm.get("industry_primary")
        if sector:
            out[(market.upper(), ticker.upper())] = str(sector)
    return out


def _ticker_themes(base: Path | None) -> dict[tuple[str, str], list[str]]:
    """Map ``(market, ticker) -> [themes]`` from each company's meta.md."""
    companies_dir = (Path(base) / "companies") if base else cfg.COMPANIES_DIR
    out: dict[tuple[str, str], list[str]] = {}
    if not companies_dir.exists():
        return out
    for d in companies_dir.iterdir():
        if not d.is_dir() or "_" not in d.name:
            continue
        market, ticker = d.name.split("_", 1)
        meta = d / "meta.md"
        if not meta.exists():
            continue
        fm, _ = _split_frontmatter(meta.read_text(encoding="utf-8"))
        themes = fm.get("themes") or []
        if isinstance(themes, str):
            themes = [t.strip() for t in themes.split(",") if t.strip()]
        if isinstance(themes, list):
            out[(market.upper(), ticker.upper())] = [str(t) for t in themes]
    return out


def evaluate(
    positions: list[dict],
    base: Path | None = None,
    include_macro: bool = True,
) -> dict:
    """Return ``{limits, violations, totals}``.

    - ``limits``: the active limits (from rules.md)
    - ``violations``: list of dicts, each ``{kind, limit, actual, entity}``
    - ``totals``: ``{total_pct, cash_pct, by_sector: {sector: pct}}``

    When ``include_macro`` is True (default), extreme-risk pre-triggers
    (VIX spike / credit widening / sector crash — DESIGN §3.8) are also run.
    """
    state = read(base=base)
    limits = state["limits"]

    sectors = _ticker_sectors(base=base)
    themes_map = _ticker_themes(base=base)
    total = 0.0
    by_sector: dict[str, float] = {}
    by_theme: dict[str, float] = {}
    per_position: list[tuple[str, float, str]] = []
    for p in positions:
        try:
            pct = float(p.get("position_pct") or 0)
        except (TypeError, ValueError):
            pct = 0.0
        total += pct
        ticker = str(p.get("ticker") or "").upper()
        market = str(p.get("market") or "").upper()
        sector = sectors.get((market, ticker)) or "(unclassified)"
        by_sector[sector] = by_sector.get(sector, 0.0) + pct
        for theme in themes_map.get((market, ticker), []):
            by_theme[theme] = by_theme.get(theme, 0.0) + pct
        per_position.append((f"{market}:{ticker}", pct, sector))
    cash_pct = max(0.0, 100.0 - total)

    violations: list[dict] = []
    max_single = limits.get("max_single_pct")
    if max_single is not None:
        for entity, pct, _ in per_position:
            if pct > max_single:
                violations.append({
                    "kind": "single_position",
                    "entity": entity,
                    "limit": max_single,
                    "actual": pct,
                })

    max_sector = limits.get("max_sector_pct")
    if max_sector is not None:
        for sector, pct in by_sector.items():
            if pct > max_sector:
                violations.append({
                    "kind": "sector_exposure",
                    "entity": sector,
                    "limit": max_sector,
                    "actual": pct,
                })

    min_cash = limits.get("min_cash_pct")
    if min_cash is not None and cash_pct < min_cash:
        violations.append({
            "kind": "cash_floor",
            "entity": "cash",
            "limit": min_cash,
            "actual": cash_pct,
        })

    max_theme = limits.get("max_theme_pct")
    if max_theme is not None:
        for theme, pct in by_theme.items():
            if pct > max_theme:
                violations.append({
                    "kind": "theme_exposure",
                    "entity": theme,
                    "limit": max_theme,
                    "actual": pct,
                })

    if include_macro:
        from app.io import macro_risks as mr
        violations.extend(mr.all_extreme_risks(base=base))

    return {
        "limits": limits,
        "violations": violations,
        "totals": {
            "total_pct": total,
            "cash_pct": cash_pct,
            "by_sector": by_sector,
            "by_theme": by_theme,
        },
        "body": state.get("body", ""),
    }
