"""Extreme-risk pre-trigger checks (DESIGN §3.8).

Three rules, each returning a ``violation`` dict or ``None``. All reads are
best-effort — if the required data isn't present (no VIX history / no regime
snapshots / no prices), the check returns ``None`` silently. This is an
advisory layer: rules report, UI decides.

DESIGN §3.8 wording:
- VIX 持续一周 > 40 → 整体股票仓位自动降到 50% 以下
- 信用利差 OAS 单月扩大 > 100bp → 降仓
- 单一行业内头部公司一周内同步下跌 > 20% → 组合再平衡

None of these AUTO-mutate rules. They surface as violations on /portfolio.
"""
from __future__ import annotations

from datetime import date as date_cls, timedelta
from pathlib import Path

import yaml

from app import config as cfg
from app.io import financials as fin_io
from app.io import regime as regime_io

VIX_SYMBOL = "VIX"
VIX_SPIKE_THRESHOLD = 40.0
VIX_SUSTAIN_DAYS = 7

CREDIT_WIDENING_BPS = 100.0
SECTOR_CRASH_DROP_PCT = -20.0
SECTOR_CRASH_WINDOW_DAYS = 7
SECTOR_CRASH_MIN_TICKERS = 3


def _split_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    return yaml.safe_load(text[3:end].strip()) or {}


# --- VIX sustained spike ----------------------------------------------------


def check_vix_sustained(base: Path | None = None) -> dict | None:
    """Return violation if the last ``VIX_SUSTAIN_DAYS`` closes all exceed 40."""
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            """
            SELECT date, close FROM benchmark
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
            """,
            (VIX_SYMBOL, VIX_SUSTAIN_DAYS),
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < VIX_SUSTAIN_DAYS:
        return None
    closes = [float(r["close"]) for r in rows]
    if all(c > VIX_SPIKE_THRESHOLD for c in closes):
        return {
            "kind": "vix_sustained_spike",
            "entity": VIX_SYMBOL,
            "limit": VIX_SPIKE_THRESHOLD,
            "actual": min(closes),  # the lowest of the streak — still > 40
            "detail": (
                f"VIX closed > {VIX_SPIKE_THRESHOLD} for {VIX_SUSTAIN_DAYS} "
                f"consecutive sessions (min={min(closes):.1f}). "
                "DESIGN §3.8: 整体股票仓位自动降到 50% 以下。"
            ),
        }
    return None


# --- credit spread widening -------------------------------------------------


def check_credit_widening(base: Path | None = None) -> dict | None:
    """Compare the two most recent regime snapshots' credit_spread_bps."""
    quarters = regime_io.list_quarters(base=base)
    if len(quarters) < 2:
        return None
    latest = regime_io.read(quarters[0], base=base)
    prev = regime_io.read(quarters[1], base=base)
    if latest is None or prev is None:
        return None
    try:
        l = float(latest["frontmatter"].get("credit_spread_bps"))
        p = float(prev["frontmatter"].get("credit_spread_bps"))
    except (TypeError, ValueError):
        return None
    diff = l - p
    if diff > CREDIT_WIDENING_BPS:
        return {
            "kind": "credit_widening",
            "entity": f"{quarters[1]}→{quarters[0]}",
            "limit": CREDIT_WIDENING_BPS,
            "actual": diff,
            "detail": (
                f"Credit spread widened {diff:.0f} bps ({p:.0f} → {l:.0f}) "
                f"across most-recent quarters ({quarters[1]} → {quarters[0]}). "
                "DESIGN §3.8: 降仓。"
            ),
        }
    return None


# --- sector crash -----------------------------------------------------------


def _ticker_sectors(base: Path | None) -> dict[str, str]:
    """Map ``TICKER -> sector`` from each company's meta.md (upper-case ticker)."""
    companies_dir = (Path(base) / "companies") if base else cfg.COMPANIES_DIR
    out: dict[str, str] = {}
    if not companies_dir.exists():
        return out
    for d in companies_dir.iterdir():
        if not d.is_dir() or "_" not in d.name:
            continue
        _, ticker = d.name.split("_", 1)
        meta = d / "meta.md"
        if not meta.exists():
            continue
        fm = _split_frontmatter(meta.read_text(encoding="utf-8"))
        sector = fm.get("sector") or fm.get("industry_primary")
        if sector:
            out[ticker.upper()] = str(sector)
    return out


def _recent_drop_pct(
    conn, ticker: str, today: date_cls, window_days: int
) -> float | None:
    """Return pct change ((latest - ref) / ref * 100) over ``window_days`` or None."""
    rows = conn.execute(
        """
        SELECT date, close FROM prices
        WHERE ticker = ? AND date <= ?
        ORDER BY date DESC
        LIMIT 60
        """,
        (ticker, today.isoformat()),
    ).fetchall()
    if len(rows) < 2:
        return None
    latest_date = date_cls.fromisoformat(rows[0]["date"])
    latest_close = float(rows[0]["close"])
    cutoff = latest_date - timedelta(days=window_days)
    ref = None
    for r in rows[1:]:
        d = date_cls.fromisoformat(r["date"])
        if d <= cutoff:
            ref = float(r["close"])
            break
    if ref is None or ref <= 0:
        return None
    return (latest_close - ref) / ref * 100.0


def check_sector_crash(
    today: date_cls | None = None, base: Path | None = None
) -> list[dict]:
    """Return one violation per sector where ≥ ``MIN_TICKERS`` dropped ≥ 20% in 7d."""
    t = today or date_cls.today()
    sectors = _ticker_sectors(base)
    if not sectors:
        return []
    try:
        fin_io._ensure_schema(fin_io.connect(base=base)).close()  # type: ignore[attr-defined]
    except Exception:
        pass
    conn = fin_io.connect(base=base)
    try:
        by_sector: dict[str, list[tuple[str, float]]] = {}
        for ticker, sector in sectors.items():
            pct = _recent_drop_pct(conn, ticker, t, SECTOR_CRASH_WINDOW_DAYS)
            if pct is None or pct > SECTOR_CRASH_DROP_PCT:
                continue
            by_sector.setdefault(sector, []).append((ticker, pct))
    finally:
        conn.close()

    violations: list[dict] = []
    for sector, hits in by_sector.items():
        if len(hits) < SECTOR_CRASH_MIN_TICKERS:
            continue
        worst = min(hits, key=lambda x: x[1])
        violations.append({
            "kind": "sector_crash",
            "entity": sector,
            "limit": SECTOR_CRASH_DROP_PCT,
            "actual": worst[1],
            "detail": (
                f"{len(hits)} tickers in sector '{sector}' fell ≥ "
                f"{abs(SECTOR_CRASH_DROP_PCT):.0f}% in the last "
                f"{SECTOR_CRASH_WINDOW_DAYS} days "
                f"(worst: {worst[0]} {worst[1]:.1f}%). "
                "DESIGN §3.8: 组合再平衡。"
            ),
            "tickers": [t[0] for t in hits],
        })
    return violations


# --- aggregate --------------------------------------------------------------


def all_extreme_risks(
    today: date_cls | None = None, base: Path | None = None
) -> list[dict]:
    out: list[dict] = []
    v = check_vix_sustained(base=base)
    if v:
        out.append(v)
    v = check_credit_widening(base=base)
    if v:
        out.append(v)
    out.extend(check_sector_crash(today=today, base=base))
    return out
