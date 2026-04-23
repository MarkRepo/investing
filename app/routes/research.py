"""Research workbench routes (V1 simplified: no LLM, all manual)."""
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import claims as claims_io

router = APIRouter(prefix="/research/{key}", tags=["research"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


@router.get("")
def index(request: Request, key: str):
    market, ticker = _parse_key(key)
    all_claims = claims_io.read_claims(ticker, market)
    consensus = claims_io.consensus_map(all_claims)
    sources = claims_io.list_sources(ticker, market)
    subjects = claims_io.load_subjects()
    return templates.TemplateResponse(
        request,
        "research/index.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "claims": all_claims,
            "consensus": consensus,
            "sources": sources,
            "subjects": subjects,
            "polarities": claims_io.POLARITIES,
            "claim_types": claims_io.CLAIM_TYPES,
        },
    )


@router.post("/claim")
def add_claim(
    key: str,
    claim_text: str = Form(...),
    subject_tag: str = Form(...),
    polarity: str = Form(...),
    claim_type: str = Form(...),
    timeframe: str = Form(""),
    source_id: str = Form(""),
    evidence_text: str = Form(""),
):
    market, ticker = _parse_key(key)
    claim = {
        "claim_text": claim_text,
        "subject_tag": subject_tag,
        "polarity": polarity,
        "claim_type": claim_type,
        "timeframe": timeframe or None,
        "source_id": source_id or None,
        "extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if evidence_text:
        claim["evidence"] = [{"text": evidence_text, "type": "secondary"}]

    try:
        claims_io.append_claim(ticker, market, claim)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return RedirectResponse(url=f"/research/{key}", status_code=303)


@router.post("/batch-import")
def batch_import(request: Request, key: str, claims_json: str = Form(...)):
    """Validate an LLM-produced claim batch and append atomically.

    If any row fails validation, reject the whole batch and re-render the
    research page with errors (no partial imports — makes audit sane).
    """
    market, ticker = _parse_key(key)
    subjects = claims_io.load_subjects()

    try:
        header, valid, errors = claims_io.validate_batch(claims_json, subjects)
    except ValueError as e:
        return _render_with_batch_error(
            request, key, ticker, market, claims_json, str(e), [], subjects
        )

    if errors:
        return _render_with_batch_error(
            request, key, ticker, market, claims_json,
            f"{len(errors)} 条 claim 未通过校验，全部拒绝。修正后重试。",
            errors, subjects,
        )

    claims_io.append_batch(ticker, market, valid, header=header)
    return RedirectResponse(url=f"/research/{key}", status_code=303)


def _render_with_batch_error(
    request, key, ticker, market, claims_json, message, errors, subjects
):
    return templates.TemplateResponse(
        request,
        "research/index.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "claims": claims_io.read_claims(ticker, market),
            "consensus": claims_io.consensus_map(claims_io.read_claims(ticker, market)),
            "sources": claims_io.list_sources(ticker, market),
            "subjects": subjects,
            "polarities": claims_io.POLARITIES,
            "claim_types": claims_io.CLAIM_TYPES,
            "batch_json": claims_json,
            "batch_error_message": message,
            "batch_errors": errors,
        },
        status_code=400,
    )


@router.post("/source")
async def upload_source(key: str, file: UploadFile = File(...)):
    market, ticker = _parse_key(key)
    if not file.filename:
        raise HTTPException(status_code=400, detail="filename required")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="empty file")
    claims_io.save_source_markdown(ticker, market, file.filename, content)
    return RedirectResponse(url=f"/research/{key}", status_code=303)
