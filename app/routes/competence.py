"""Competence self-check routes."""
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR, VALID_SECTORS
from app.io import competence

router = APIRouter(prefix="/companies/{key}/competence", tags=["competence"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


@router.get("")
def edit_page(request: Request, key: str):
    market, ticker = _parse_key(key)
    try:
        doc = competence.read_competence(ticker, market)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="competence-check.md missing") from e

    sector = doc["sector"]
    if sector and sector not in VALID_SECTORS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown sector {sector!r} in meta.md; valid: {VALID_SECTORS}",
        )

    return templates.TemplateResponse(
        request,
        "competence/edit.html",
        {
            "key": key,
            "ticker": ticker,
            "market": market,
            "fm": doc["frontmatter"],
            "sector": sector,
            "universal_questions": doc["universal_questions"],
            "sector_questions": doc["sector_questions"],
            "answers": doc["answers"],
            "levels": competence.LEVELS,
        },
    )


@router.post("")
async def save(request: Request, key: str):
    market, ticker = _parse_key(key)
    doc = competence.read_competence(ticker, market)
    sector = doc["sector"]

    form = await request.form()
    answers: dict[str, dict] = {}
    for q in doc["universal_questions"] + doc["sector_questions"]:
        qid = q["id"]
        level = str(form.get(f"{qid}__level", "unanswered"))
        if level not in competence.LEVELS:
            level = "unanswered"
        text = str(form.get(f"{qid}__text", ""))
        answers[qid] = {"label": q["label"], "level": level, "text": text}

    competence.write_competence(
        ticker=ticker,
        market=market,
        sector=sector,
        check_date=date.today().isoformat(),
        answers=answers,
    )
    return RedirectResponse(url=f"/companies/{key}/competence", status_code=303)
