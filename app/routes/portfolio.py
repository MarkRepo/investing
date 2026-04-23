"""Portfolio routes."""
import markdown as md
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import config as cfg
from app.config import APP_TEMPLATES_DIR
from app.io import portfolio
from app.io import prices as prices_io
from app.io import regime as regime_io
from app.io import rules as rules_io
from app.io import triggers as triggers_io

router = APIRouter(prefix="/portfolio", tags=["portfolio"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    rows = portfolio.read_positions()
    total = portfolio.total_position_pct(rows)
    cash = max(0.0, 100.0 - total)

    price_map = prices_io.latest_prices_map()
    all_triggers = triggers_io.list_all()

    # Attach live info per row
    enriched: list[dict] = []
    for r in rows:
        ticker = r.get("ticker", "")
        latest = price_map.get(ticker)
        current_price = latest[1] if latest else None
        price_date = latest[0] if latest else None
        try:
            avg_cost = float(r.get("avg_cost") or 0)
        except (TypeError, ValueError):
            avg_cost = 0.0
        pnl_pct = None
        if current_price is not None and avg_cost > 0:
            pnl_pct = (current_price - avg_cost) / avg_cost
        t_rows = [t for t in all_triggers if t["ticker"] == ticker]
        fired = [t for t in t_rows if t["triggered_at"]]
        enriched.append({
            **r,
            "current_price": current_price,
            "price_date": price_date,
            "pnl_pct": pnl_pct,
            "trigger_count": len(t_rows),
            "fired_count": len(fired),
        })

    rules_eval = rules_io.evaluate(rows)
    rules_html = md.markdown(rules_eval.get("body", ""), extensions=["extra"]) if rules_eval.get("body") else ""

    regime_latest = regime_io.latest()
    regime_fm = regime_latest["frontmatter"] if regime_latest else {}

    return templates.TemplateResponse(
        request,
        "portfolio/index.html",
        {
            "rows": enriched,
            "total": total,
            "cash": cash,
            "rules_html": rules_html,
            "rules_eval": rules_eval,
            "regime_fm": regime_fm,
        },
    )


@router.get("/rules")
def rules_edit(request: Request):
    state = rules_io.read()
    return templates.TemplateResponse(
        request,
        "portfolio/rules.html",
        {
            "limits": state.get("limits", {}),
            "body": state.get("body", ""),
            "error": None,
        },
    )


@router.post("/rules")
def rules_save(
    request: Request,
    max_single_pct: str = Form(""),
    max_sector_pct: str = Form(""),
    min_cash_pct: str = Form(""),
    max_theme_pct: str = Form(""),
    body: str = Form(""),
):
    limits = {
        "max_single_pct": max_single_pct,
        "max_sector_pct": max_sector_pct,
        "min_cash_pct": min_cash_pct,
        "max_theme_pct": max_theme_pct,
    }
    try:
        rules_io.write(limits, body)
    except ValueError as e:
        return templates.TemplateResponse(
            request,
            "portfolio/rules.html",
            {
                "limits": limits,
                "body": body,
                "error": str(e),
            },
            status_code=400,
        )
    return RedirectResponse(url="/portfolio/rules", status_code=303)


@router.post("/position")
def upsert(
    ticker: str = Form(...),
    market: str = Form(...),
    entry_date: str = Form(""),
    avg_cost: str = Form(""),
    shares: str = Form(""),
    position_pct: str = Form("0"),
):
    ticker = ticker.strip().upper()
    v0_link = f"/companies/{market}_{ticker}/v0"
    portfolio.upsert_position(
        {
            "ticker": ticker,
            "market": market,
            "entry_date": entry_date,
            "avg_cost": avg_cost,
            "shares": shares,
            "position_pct": position_pct,
            "v0_link": v0_link,
        }
    )
    return RedirectResponse(url="/portfolio", status_code=303)
