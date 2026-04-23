"""Watchlist (observation pool) routes."""
from datetime import date as date_cls

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import watchlist as wl

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    today = date_cls.today()
    sections = {s: wl.read_watchlist(s) for s in wl.STAGES}
    # Annotate researching rows with overdue status
    for row in sections["researching"]:
        row["_status"] = wl.researching_status(row, today=today)
    return templates.TemplateResponse(
        request,
        "watchlist/index.html",
        {
            "sections": sections,
            "columns": wl.COLUMNS,
            "stages": wl.STAGES,
            "source_types": wl.SOURCE_TYPES,
            "gate_questions": wl.GATE_QUESTIONS,
            "stale_days": wl.STALE_DAYS,
            "today": today.isoformat(),
        },
    )


@router.post("/add/{stage}")
async def add_entry(stage: str, request: Request):
    if stage not in wl.STAGES:
        raise HTTPException(status_code=404, detail="unknown stage")
    form = await request.form()
    entry = {k: str(form.get(k, "")) for k in wl.COLUMNS[stage]}
    # Default date_added to today if blank on prefilter
    if stage == "prefilter" and not entry.get("date_added"):
        entry["date_added"] = date_cls.today().isoformat()
    try:
        wl.append_watchlist(stage, entry)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url="/watchlist", status_code=303)


@router.post("/move")
async def move_entry(request: Request):
    form = await request.form()
    ticker = str(form.get("ticker", "")).strip()
    from_stage = str(form.get("from_stage", "")).strip()
    to_stage = str(form.get("to_stage", "")).strip()
    extra = {
        "started": str(form.get("started", "")),
        "gap_focus": str(form.get("gap_focus", "")),
        "target_finish": str(form.get("target_finish", "")),
        "set_on": str(form.get("set_on", "")),
        "first_entry_price": str(form.get("first_entry_price", "")),
        "add1_price": str(form.get("add1_price", "")),
        "add2_price": str(form.get("add2_price", "")),
        "v0_link": str(form.get("v0_link", "")),
    }
    extra = {k: v for k, v in extra.items() if v}

    gate_answers = {qid: str(form.get(qid, "")) for qid, _ in wl.GATE_QUESTIONS}
    gate_reasons = {
        qid: str(form.get(f"reason_{qid}", "")) for qid, _ in wl.GATE_QUESTIONS
    }

    try:
        wl.move_watchlist(
            ticker, from_stage, to_stage,
            extra=extra,
            gate_answers=gate_answers,
            gate_reasons=gate_reasons,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url="/watchlist", status_code=303)
