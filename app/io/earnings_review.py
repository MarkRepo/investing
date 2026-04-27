"""Earnings-report comparison trigger (DESIGN §8.1.3).

Goal: make sure a new quarter's financials never sits unseen on a company whose
V0 thesis depends on specific trigger conditions. We don't auto-judge — we just
surface the gap so the user opens V0 §5/§6 next to the numbers and decides.

Rule: a company is "pending review" if its latest financials period is newer
than its V0's ``last_reviewed_period``. The comparison uses the period sort
key from financials (so 2024A > 2024Q4 > 2024Q3 > 2023A etc.).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.io import financials as fin_io
from app.io import v0 as v0_io


def _period_gt(a: str | None, b: str | None) -> bool:
    """True iff period ``a`` is strictly newer than period ``b``."""
    if not a:
        return False
    if not b:
        return True
    return fin_io._period_sort_key(a) > fin_io._period_sort_key(b)


def _scan(base: Path | None = None) -> list[dict[str, Any]]:
    """Return one summary row per company that has financials."""
    rows = v0_io.list_all_v0s(base=base)
    conn = fin_io.connect(base=base)
    try:
        out: list[dict[str, Any]] = []
        for r in rows:
            ticker = r.get("ticker")
            market = r.get("market")
            if not ticker or not market:
                continue
            if market == "US":
                fins = fin_io.list_financials_us(conn, ticker)
            elif market in ("SSE", "SZSE", "BSE"):
                fins = fin_io.list_financials_cn(conn, ticker)
            else:
                continue
            if not fins:
                continue
            latest = fins[0]["period"]
            v0 = v0_io.read_v0(ticker, market, base=base)
            reviewed = v0["frontmatter"].get("last_reviewed_period")
            out.append(
                {
                    "key": f"{market}_{ticker}",
                    "ticker": ticker,
                    "market": market,
                    "status": r.get("status"),
                    "position_size_pct": r.get("position_size_pct", 0),
                    "latest_period": latest,
                    "last_reviewed_period": reviewed,
                    "pending": _period_gt(latest, reviewed),
                }
            )
    finally:
        conn.close()
    return out


def pending_reviews(base: Path | None = None) -> list[dict[str, Any]]:
    """Companies with at least one financial period newer than last review.

    Sorted: active positions first, then larger latest periods first.
    """
    rows = [r for r in _scan(base=base) if r["pending"]]
    rows.sort(
        key=lambda r: (
            0 if r["status"] == "active" else 1,
            -fin_io._period_sort_key(r["latest_period"])[0],
        )
    )
    return rows


def mark_reviewed(
    ticker: str, market: str, period: str, base: Path | None = None
) -> Path:
    """Set ``last_reviewed_period`` on the V0 file. Trusts that ``period`` is valid."""
    doc = v0_io.read_v0(ticker, market, base=base)
    fm = {**doc["frontmatter"], "last_reviewed_period": period}
    return v0_io.write_v0(ticker, market, fm, doc["body"], base=base)


def company_summary(
    ticker: str, market: str, base: Path | None = None, limit: int = 4
) -> dict[str, Any]:
    """Gather everything the comparison page needs for one company."""
    doc = v0_io.read_v0(ticker, market, base=base)
    fm = doc["frontmatter"]
    body = doc["body"]
    sections = v0_io.split_sections(body)
    conn = fin_io.connect(base=base)
    try:
        rows = fin_io.list_periods_with_ratios(conn, ticker, market=market)[:limit]
    finally:
        conn.close()
    latest = rows[0]["period"] if rows else None
    reviewed = fm.get("last_reviewed_period")
    return {
        "ticker": ticker,
        "market": market,
        "v0_frontmatter": fm,
        "v0_section_5": sections.get(5, ""),   # 卖出触发
        "v0_section_6": sections.get(6, ""),   # 什么不算推翻
        "v0_section_7": sections.get(7, ""),   # 当前状态
        "financials": rows,
        "latest_period": latest,
        "last_reviewed_period": reviewed,
        "pending": _period_gt(latest, reviewed),
    }
