"""Daily price entry route.

Paste-friendly: one 'TICKER price' per line, whitespace or comma separated.
After write, evaluate triggers so any newly-crossed ones get marked fired.
"""
from datetime import date as date_cls

from fastapi import APIRouter, Form, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import prices as prices_io
from app.io import triggers as triggers_io

router = APIRouter(prefix="/prices", tags=["prices"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    latest = prices_io.latest_prices_map()
    latest_rows = sorted(
        [{"ticker": t, "date": d, "close": c} for t, (d, c) in latest.items()],
        key=lambda r: r["ticker"],
    )
    return templates.TemplateResponse(
        request,
        "prices/index.html",
        {
            "latest_rows": latest_rows,
            "today": date_cls.today().isoformat(),
            "new_triggers": [],
            "parse_errors": [],
            "written": 0,
        },
    )


@router.post("")
def submit(
    request: Request,
    date: str = Form(...),
    paste: str = Form(""),
):
    try:
        d = date_cls.fromisoformat(date.strip())
    except ValueError:
        d = date_cls.today()

    rows, parse_errors = prices_io.parse_freeform(paste)
    prices_io.upsert_closes(rows, d)

    fired = triggers_io.evaluate(prices_io.latest_prices_map(), today=d)

    latest = prices_io.latest_prices_map()
    latest_rows = sorted(
        [{"ticker": t, "date": pd, "close": c} for t, (pd, c) in latest.items()],
        key=lambda r: r["ticker"],
    )
    return templates.TemplateResponse(
        request,
        "prices/index.html",
        {
            "latest_rows": latest_rows,
            "today": d.isoformat(),
            "new_triggers": fired["new"],
            "parse_errors": parse_errors,
            "written": len(rows),
            "paste": paste,
        },
    )
