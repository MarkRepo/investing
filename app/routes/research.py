"""Research workbench routes (V1 simplified: no LLM, all manual)."""
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import claims as claims_io

router = APIRouter(prefix="/research/{key}", tags=["research"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))

_SORT_KEYS = ("extracted_at", "subject_tag", "polarity", "source_id")
_ORDERS = ("asc", "desc")
_PER_PAGE = 50


def _parse_key(key: str) -> tuple[str, str]:
    if "_" not in key:
        raise HTTPException(status_code=404, detail="invalid key")
    market, ticker = key.split("_", 1)
    return market, ticker


def _filter_claims(
    claims: list[dict], subject_tag: str, polarity: str, source_id: str
) -> list[dict]:
    out = claims
    if subject_tag:
        out = [c for c in out if c.get("subject_tag") == subject_tag]
    if polarity:
        out = [c for c in out if c.get("polarity") == polarity]
    if source_id:
        out = [c for c in out if (c.get("source_id") or "") == source_id]
    return out


def _sort_claims(claims: list[dict], sort: str, order: str) -> list[dict]:
    if sort not in _SORT_KEYS:
        sort = "extracted_at"
    if order not in _ORDERS:
        order = "desc"
    reverse = order == "desc"

    # Two-key sort: None / "" sorts last regardless of order, then by value.
    def _key(c):
        v = c.get(sort)
        missing = v is None or v == ""
        # When reverse=True we want "missing last" — so missing=1 sorts after missing=0 ascending
        # But Python reverses both keys. Use flip: for reverse, put missing first in raw then reverse.
        if reverse:
            return (0 if missing else 1, v if v is not None else "")
        return (1 if missing else 0, v if v is not None else "")

    return sorted(claims, key=_key, reverse=reverse)


def _paginate(items: list, page: int, per_page: int = _PER_PAGE) -> tuple[list, int, int]:
    total = len(items)
    if total == 0:
        return [], 1, 1
    total_pages = (total + per_page - 1) // per_page
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    return items[start : start + per_page], page, total_pages


@router.get("")
def index(
    request: Request,
    key: str,
    page: int = Query(1, ge=1),
    sort: str = Query("extracted_at"),
    order: str = Query("desc"),
    subject_tag: str = Query(""),
    polarity: str = Query(""),
    source_id: str = Query(""),
):
    market, ticker = _parse_key(key)
    all_claims = claims_io.read_claims(ticker, market)
    # distinct source_ids across the full set, for the filter dropdown
    source_id_options = sorted(
        {(c.get("source_id") or "") for c in all_claims} - {""}
    )
    filtered = _filter_claims(all_claims, subject_tag, polarity, source_id)
    sorted_claims = _sort_claims(filtered, sort, order)
    page_items, page, total_pages = _paginate(sorted_claims, page)
    consensus = claims_io.consensus_map(filtered)
    sources = claims_io.list_sources(ticker, market)
    subjects = claims_io.load_subjects()

    if sort not in _SORT_KEYS:
        sort = "extracted_at"
    if order not in _ORDERS:
        order = "desc"

    filter_state = {
        "sort": sort,
        "order": order,
        "subject_tag": subject_tag,
        "polarity": polarity,
        "source_id": source_id,
    }

    return templates.TemplateResponse(
        request,
        "research/index.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "claims": page_items,
            "total": len(filtered),
            "all_total": len(all_claims),
            "page": page,
            "total_pages": total_pages,
            "filter_state": filter_state,
            "source_id_options": source_id_options,
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
    all_claims = claims_io.read_claims(ticker, market)
    return templates.TemplateResponse(
        request,
        "research/index.html",
        {
            "key": key, "ticker": ticker, "market": market,
            "claims": all_claims[:_PER_PAGE],
            "total": len(all_claims),
            "all_total": len(all_claims),
            "page": 1,
            "total_pages": max(1, (len(all_claims) + _PER_PAGE - 1) // _PER_PAGE),
            "filter_state": {"sort": "extracted_at", "order": "desc", "subject_tag": "", "polarity": "", "source_id": ""},
            "source_id_options": sorted({(c.get("source_id") or "") for c in all_claims} - {""}),
            "consensus": claims_io.consensus_map(all_claims),
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
