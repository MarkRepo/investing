"""Financial data utility for Prism workflows.

Wraps the existing financials IO layer with freshness checks and
frequency-aware refresh logic. Reads from local DB; fetches from
akshare/yfinance if data is missing or stale.

Refresh logic (aggressive):
  - Uses the earliest reasonable disclosure window, not filing deadlines
  - Each quarter-end has a short grace period for reports to start appearing:
    FY (12/31):  Jan 20 (20 days)
    Q1 (3/31):   Apr 10 (10 days)
    H1 (6/30):   Jul 15 (15 days)
    Q3 (9/30):   Oct 10 (10 days)
  - If DB's latest report_date is before the most recent quarter-end
    (past its grace window), data is stale → fetch.
  - If no data at all → fetch.
  - A fetch returns ALL historical periods; subsequent checks within the
    same quarter will find fresh data.

Trade-off: during the ~2 weeks after each quarter-end, there may be
redundant fetches before reports actually appear. This is intentional —
the cost of a wasted API call is lower than missing a newly filed report.
"""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime
from typing import Any

from app.io import financials as fin_io
from prism.scripts.topic import read_topic


def _resolve_ticker(slug: str, variant: str) -> tuple[str, str] | None:
    """Read topic.yaml and return (ticker, market) or None."""
    try:
        topic = read_topic(slug, variant)
    except Exception:
        return None
    scope = topic.get("scope") or {}
    ticker = scope.get("ticker", "")
    if not ticker:
        return None
    if "_" in ticker:
        market, code = ticker.split("_", 1)
        return code, market
    market = scope.get("market", "")
    if market and ticker:
        return ticker, market
    return None




# Quarter-end → (month, day, grace_days_after)
# Grace = earliest reasonable disclosure window (NOT filing deadline).
# Aggressive: prefer fetching too early over missing a newly filed report.
# Q1/H1/Q3 typically start appearing 10-15 days after quarter-end;
# FY reports take 20-30 days for early filers.
_QUARTER_ENDS = [
    (3, 31, 10),    # Q1: earliest ~Apr 10
    (6, 30, 15),    # H1: earliest ~Jul 15
    (9, 30, 10),    # Q3: earliest ~Oct 10
    (12, 31, 20),   # FY: earliest ~Jan 20
]


def _latest_available_quarter_end(today: date_cls | None = None) -> date_cls:
    """Return the latest quarter-end date whose reports COULD be available by now.

    Uses aggressive grace periods (~10-20 days) instead of filing deadlines,
    so we catch newly filed reports as soon as early filers start disclosing.

    Example: on 2026-04-12, Q1 ended 2026-03-31 + 10-day grace = Apr 10
    has passed → returns 2026-03-31. DB will be checked against this.

    If no quarter-end has passed its grace window (e.g. Jan 5), returns
    the previous year's Q3 end (Sep 30).
    """
    today = today or date_cls.today()
    best: date_cls | None = None

    for month, day, grace in _QUARTER_ENDS:
        # Build quarter-end date in the appropriate year
        # For FY (12/31): if today is Jan-Apr, we're waiting on LAST year's FY
        if month == 12:
            if today.month <= 4:
                q_end = date_cls(today.year - 1, month, day)
            else:
                q_end = date_cls(today.year, month, day)
        else:
            q_end = date_cls(today.year, month, day)

        # Can also be from last year if we haven't reached this quarter yet
        if q_end > today:
            q_end = date_cls(today.year - 1, month, day)

        deadline = date_cls(q_end.year, q_end.month, q_end.day)
        # Add grace days (handle month/year rollover roughly)
        from datetime import timedelta
        deadline = deadline + timedelta(days=grace)

        # If the filing deadline has passed and this is the newest quarter
        if today >= deadline:
            if best is None or q_end > best:
                best = q_end

    return best or date_cls(today.year - 1, 9, 30)


def _latest_db_report_date(conn: Any, ticker: str, market: str) -> str | None:
    """Return the latest report_date string (YYYYMMDD) from DB, or None."""
    if market in ("SSE", "SZSE", "BSE"):
        row = conn.execute(
            "SELECT report_date FROM financials_cn WHERE ticker=? ORDER BY report_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT report_date FROM financials_us WHERE ticker=? ORDER BY report_date DESC LIMIT 1",
            (ticker,),
        ).fetchone()
    return row["report_date"] if row else None


def _is_fresh(ticker: str, market: str) -> bool:
    """Check if financial data is fresh.

    Data is fresh if the latest report_date in DB covers the most recent
    quarter-end whose filing deadline has passed.
    """
    expected = _latest_available_quarter_end()
    expected_str = expected.strftime("%Y%m%d")

    conn = fin_io.connect()
    try:
        latest = _latest_db_report_date(conn, ticker, market)
    finally:
        conn.close()

    if not latest:
        return False

    return latest >= expected_str


def _fetch_and_store(ticker: str, market: str) -> int:
    """Fetch financial data from akshare/yfinance and store to DB."""
    if market in ("SSE", "SZSE", "BSE"):
        from scripts.fetch_financials_cn import run_for_ticker
        return run_for_ticker(ticker, market)
    else:
        from scripts.fetch_financials_us import run_for_ticker
        return run_for_ticker(ticker, market)


def ensure_financials(slug: str, variant: str) -> dict[str, Any]:
    """Ensure financial data exists in DB for a Prism company topic.

    Returns status dict. Fetches from source if DB is missing or stale.
    """
    resolved = _resolve_ticker(slug, variant)
    if not resolved:
        return {"error": "no ticker in topic scope"}

    ticker, market = resolved
    fetched = False

    if not _is_fresh(ticker, market):
        n = _fetch_and_store(ticker, market)
        fetched = n > 0

    return {
        "ticker": ticker,
        "market": market,
        "fetched": fetched,
        "fresh": True,
    }


def _compute_roic(
    oi: float | None,
    ni: float | None,
    pretax: float | None,
    ta: float | None,
    cl: float | None,
) -> tuple[float | None, bool]:
    """单期 ROIC = oi*(1-tax) / (total_assets - current_liab)，带金融业失真守卫。

    返回 (roic_pct | None, distorted)。
    金融业(券商/银行)客户资金并表 → 投入资本(总资产−流动负债)被净掉,残值极小致
    ROIC 爆表(如富途 2858%)。ic 占总资产 <10% 或 |roic|>500% 判失真 → roic=None、
    distorted=True,由 get_financial_context 切换到 ROE 口径。
    """
    if not (oi and pretax and pretax != 0 and ta and cl):
        return None, False
    tax_rate = 1 - (ni / pretax) if ni and pretax else 0.15
    ic = ta - (cl or 0)
    if ic <= 0:
        return None, False
    roic = round(oi * (1 - tax_rate) / ic * 100, 2)
    if (ic / ta) < 0.10 or abs(roic) > 500:
        return None, True
    return roic, False


def get_quality_screen_data(slug: str, variant: str) -> dict[str, Any]:
    """Return financial metrics needed by _company_case Step 0.5 质量红线门控（折自旧 03b）.

    Returns: roic_3y (list), fcf_3y (list), debt_ratio, goodwill_pct_equity,
    ocf_quality_3y (list), has_data (bool).
    """
    ensure_financials(slug, variant)
    resolved = _resolve_ticker(slug, variant)
    if not resolved:
        return {"error": "no ticker", "has_data": False}

    ticker, market = resolved
    return get_quality_data_by_ticker(ticker, market)


def get_quality_data_by_ticker(ticker: str, market: str) -> dict[str, Any]:
    """Ticker-level variant of get_quality_screen_data — no slug required.

    Use this for peer-matrix lookups where peers have only a ticker (no
    registered company topic yet). Auto-fetches if DB is missing/stale.
    """
    if not _is_fresh(ticker, market):
        _fetch_and_store(ticker, market)
    conn = fin_io.connect()
    try:
        if market in ("SSE", "SZSE", "BSE"):
            rows = fin_io.list_financials_cn(conn, ticker)
        else:
            rows = fin_io.list_financials_us(conn, ticker)

        if not rows:
            return {"has_data": False, "error": "no financial data in DB"}

        # Get ratios for computed metrics
        ratio_rows = conn.execute(
            "SELECT * FROM ratios WHERE ticker=? ORDER BY period DESC",
            (ticker,),
        ).fetchall()
        ratios_by_period = {r["period"]: dict(r) for r in ratio_rows} if ratio_rows else {}

        # Extract annual periods for multi-year metrics
        annuals = [r for r in rows if r.get("period_type") in ("annual", "年报", "合并期末")]
        if len(annuals) < 3:
            # Fallback: use Q4 periods
            annuals = [r for r in rows if "Q4" in r.get("period", "")]

        # 3-year ROIC: (operating_income * (1 - tax_rate)) / (total_assets - current_liab)
        roic_3y = []
        for r in annuals[:3]:
            period = r.get("period", "")
            oi = r.get("operating_income")
            ni = r.get("net_income_to_parent") or r.get("net_income")
            pretax = r.get("pretax_income")
            ta = r.get("total_assets")
            # CN schema → total_current_liab; US/HKEX (yfinance) schema → current_liabilities
            cl = r.get("total_current_liab") or r.get("current_liabilities")
            roic, distorted = _compute_roic(oi, ni, pretax, ta, cl)
            roic_3y.append({"period": period, "roic": roic, "distorted": distorted})

        # 3-year FCF
        fcf_3y = []
        for r in annuals[:3]:
            period = r.get("period", "")
            ratio = ratios_by_period.get(period, {})
            fcf = ratio.get("fcf")
            fcf_3y.append({"period": period, "fcf": fcf})

        # Latest period balance sheet ratios
        latest = annuals[0] if annuals else rows[0]
        latest_ratio = ratios_by_period.get(latest.get("period", ""), {})

        debt_ratio = latest_ratio.get("debt_to_equity")
        goodwill = latest.get("goodwill")
        equity = latest.get("total_equity") or latest.get("equity_to_parent")
        goodwill_pct = round(goodwill / equity * 100, 2) if goodwill and equity else None

        # 3-year OCF quality
        ocf_3y = []
        for r in annuals[:3]:
            period = r.get("period", "")
            ratio = ratios_by_period.get(period, {})
            ocf_3y.append({"period": period, "ocf_quality": ratio.get("ocf_quality")})

        # Latest period key metrics
        return {
            "has_data": True,
            "ticker": ticker,
            "market": market,
            "latest_period": latest.get("period"),
            "latest_revenue": latest.get("total_revenue"),
            "latest_net_income": latest.get("net_income_to_parent") or latest.get("net_income"),
            "latest_gross_margin": latest_ratio.get("gross_margin"),
            "latest_roe": latest_ratio.get("roe"),
            "latest_roa": latest_ratio.get("roa"),
            "debt_to_equity": debt_ratio,
            "goodwill_pct_equity": goodwill_pct,
            "fcf": latest_ratio.get("fcf"),
            "roic_3y": roic_3y,
            "roic_distorted": any(x.get("distorted") for x in roic_3y),
            "fcf_3y": fcf_3y,
            "ocf_quality_3y": ocf_3y,
            "total_periods": len(rows),
        }
    finally:
        conn.close()


def _peer_row_from_quality(data: dict[str, Any]) -> dict[str, Any]:
    if not data.get("has_data"):
        return {"error": data.get("error", "no data")}
    roic_vals = [r.get("roic") for r in data.get("roic_3y", []) if r.get("roic")]
    avg_roic = round(sum(roic_vals) / len(roic_vals), 2) if roic_vals else None
    return {
        "ticker": data.get("ticker"),
        "revenue": data.get("latest_revenue"),
        "gross_margin": data.get("latest_gross_margin"),
        "roic_3y_avg": avg_roic,
        "debt_to_equity": data.get("debt_to_equity"),
    }


def get_peer_comparison_data(
    slug: str, variant: str, peer_slugs: list[str]
) -> dict[str, Any]:
    """Return comparison data for _peer_matrix_spec workflow (slug-based).

    For each peer slug, fetches: revenue, 3Y avg ROIC, gross_margin,
    debt_to_equity. Returns {slug: {metrics}} dict.
    """
    return {ps: _peer_row_from_quality(get_quality_screen_data(ps, variant)) for ps in peer_slugs}


def get_peer_comparison_data_by_tickers(peers: list[dict[str, str]]) -> dict[str, Any]:
    """Ticker-level peer comparison — no registered company topics required.

    peers: [{"key": "利元亨", "ticker": "688499", "market": "SSE"}, ...]
    Returns {key: {metrics}} where key = peers[i]["key"] (display name).

    `key` is only the output label (not used for fetching — ticker+market do
    that), so callers may pass "name" or omit it entirely; falls back
    name → ticker → "?".
    """
    out = {}
    for p in peers:
        key = p.get("key") or p.get("name") or p.get("ticker") or "?"
        ticker = p.get("ticker", "")
        market = p.get("market", "")
        if not ticker or not market:
            out[key] = {"error": "missing ticker/market"}
            continue
        out[key] = _peer_row_from_quality(get_quality_data_by_ticker(ticker, market))
    return out


def get_financial_context(slug: str, variant: str) -> str:
    """Return a markdown snippet with financial data for workflow injection.

    Designed for 决策链环②定价锚 and 03-extract-findings context.
    """
    data = get_quality_screen_data(slug, variant)
    if not data.get("has_data"):
        return f"*(财务数据不可用: {data.get('error', 'unknown')})*"

    lines = [
        "## 当前财务数据 (自动获取)",
        "",
        f"- **最新报告期**: {data['latest_period']}",
        f"- **营业收入**: {_fmt(data['latest_revenue'])}",
        f"- **归母净利润**: {_fmt(data['latest_net_income'])}",
        f"- **毛利率**: {_fmt_pct(data['latest_gross_margin'])}",
        f"- **ROE**: {_fmt_pct(data['latest_roe'])}",
        f"- **资产负债率**: {_fmt_pct(data['debt_to_equity'])}",
        f"- **自由现金流**: {_fmt(data['fcf'])}",
        f"- **商誉占净资产**: {_fmt_pct(data['goodwill_pct_equity'])}",
        "",
    ]
    lines.append("### 3年 ROIC")
    if data.get("roic_distorted"):
        lines.append(
            "- ⚠️ ROIC 因金融业客户资金并表致投入资本(总资产−流动负债)失真,已抑制"
            "——改以上方 **ROE** 衡量资本回报"
        )
    else:
        for r in data.get("roic_3y", []):
            lines.append(f"- {r['period']}: {_fmt_pct(r['roic'])}")
    lines.append("")
    lines.append("### 3年自由现金流")
    for r in data.get("fcf_3y", []):
        lines.append(f"- {r['period']}: {_fmt(r['fcf'])}")
    return "\n".join(lines)


def _fmt(v: Any) -> str:
    """Format number in 亿 for display."""
    if v is None:
        return "N/A"
    if abs(v) >= 1e8:
        return f"{v / 1e8:.2f} 亿"
    if abs(v) >= 1e4:
        return f"{v / 1e4:.2f} 万"
    return f"{v:,.2f}"


def _fmt_pct(v: Any) -> str:
    """Format ratio value as percentage. DB stores decimals (0.72 = 72%)."""
    if v is None:
        return "N/A"
    return f"{v * 100:.2f}%"