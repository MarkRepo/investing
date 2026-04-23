"""Journal (decision log) routes."""
from datetime import date as date_cls
from datetime import datetime

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR, VALID_MARKETS
from app.io import journal

router = APIRouter(prefix="/journal", tags=["journal"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def list_page(request: Request):
    rows = journal.list_entries()
    return templates.TemplateResponse(
        request,
        "journal/list.html",
        {"rows": rows},
    )


@router.get("/new")
def new_form(request: Request, ticker: str = "", market: str = "US", action: str = "buy"):
    return templates.TemplateResponse(
        request,
        "journal/new.html",
        {
            "ticker": ticker.strip().upper(),
            "market": market,
            "action": action,
            "today": date_cls.today().isoformat(),
            "markets": VALID_MARKETS,
            "actions": journal.ACTIONS,
        },
    )


@router.post("/new")
def new_submit(
    ticker: str = Form(...),
    market: str = Form(...),
    action: str = Form(...),
    entry_date: str = Form(...),
    price: float = Form(0),
    position_change: float = Form(0),
):
    try:
        d = date_cls.fromisoformat(entry_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"bad date: {e}") from e

    rel, h, text = journal.read_v0_snapshot(ticker.strip().upper(), market)
    try:
        paths = journal.create_entry(
            d,
            ticker,
            market,
            action,
            price=price,
            position_change=position_change,
            v0_snapshot_path=rel,
            v0_snapshot_hash_=h,
            v0_body_preview=text,
        )
    except (ValueError, FileExistsError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url=f"/journal/{paths.entry_id}", status_code=303)


@router.get("/{entry_id}")
def detail(request: Request, entry_id: str):
    try:
        doc = journal.read_entry(entry_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    bias_answers, bias_reasons = _pull_bias(doc["frontmatter"], doc["sections"][4])
    flagged = journal.bias_warnings(bias_answers, bias_reasons)

    v0_stale = False
    fm = doc["frontmatter"]
    if fm.get("v0_snapshot_path") and fm.get("v0_snapshot_hash"):
        d, ticker, _ = journal.parse_entry_id(entry_id)
        _, h_now, _ = journal.read_v0_snapshot(ticker, fm.get("market", ""))
        v0_stale = bool(h_now) and h_now != fm["v0_snapshot_hash"]

    return templates.TemplateResponse(
        request,
        "journal/edit.html",
        {
            "entry_id": entry_id,
            "fm": fm,
            "sections": doc["sections"],
            "bias_questions": journal.BIAS_QUESTIONS,
            "bias_answers": bias_answers,
            "bias_reasons": bias_reasons,
            "bias_flagged": flagged,
            "v0_stale": v0_stale,
        },
    )


def _pull_bias(fm: dict, section4_text: str) -> tuple[dict, dict]:
    """Bias answers + reasons are stored in frontmatter as flat keys."""
    answers = {q[0]: str(fm.get(f"bias_{q[0]}", "") or "") for q in journal.BIAS_QUESTIONS}
    reasons = {q[0]: str(fm.get(f"bias_reason_{q[0]}", "") or "") for q in journal.BIAS_QUESTIONS}
    return answers, reasons


@router.post("/{entry_id}")
async def save(request: Request, entry_id: str):
    try:
        doc = journal.read_entry(entry_id)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    form = await request.form()
    fm = dict(doc["frontmatter"])

    # Update process score fields (1-5, int or null)
    for key in (
        "process_quality", "process_rigor",
        "process_rule_adherence", "process_emotional_control",
    ):
        raw = form.get(key, "")
        fm[key] = int(raw) if raw else None

    # Result score (always optional)
    for key in ("pnl_3m", "pnl_6m", "pnl_12m"):
        raw = form.get(key, "")
        fm[key] = float(raw) if raw else None
    for key in ("result_quality", "result_luck_factor"):
        raw = form.get(key, "")
        fm[key] = int(raw) if raw else None

    # Bias four-question answers live in frontmatter for quick aggregation
    for qid, _ in journal.BIAS_QUESTIONS:
        fm[f"bias_{qid}"] = str(form.get(f"bias_{qid}", "")) or None
        fm[f"bias_reason_{qid}"] = str(form.get(f"bias_reason_{qid}", "")) or None

    d, ticker, action = journal.parse_entry_id(entry_id)
    sections = {i: str(form.get(f"sec{i}", "")) for i in range(1, len(journal.SECTIONS) + 1)}
    body = journal.join_sections(sections, ticker, action, d.isoformat())
    journal.write_entry(entry_id, fm, body)
    return RedirectResponse(url=f"/journal/{entry_id}", status_code=303)
