"""Monthly 10% claim audit (DESIGN §5 V2 maintenance loop).

Random sample claims extracted in a given month; review them against the
extraction prompt's rules. The goal is to catch prompt drift early by
spot-checking ~10% per month.
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import claims

router = APIRouter(prefix="/research-audit", tags=["research-audit"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def audit_page(
    request: Request,
    month: str | None = None,
    pct: float = 0.10,
):
    # Build a list of available extraction months from all claims
    all_claims = claims.iter_all_claims()
    months = sorted({
        str(c.get("extracted_at", ""))[:7]
        for c in all_claims
        if c.get("extracted_at")
    }, reverse=True)
    result = claims.audit_sample(month=month, pct=pct) if all_claims else {
        "total": 0, "pool": 0, "sample": [], "month": month, "pct": pct, "seed_used": None,
    }
    return templates.TemplateResponse(
        request,
        "research_audit/index.html",
        {"result": result, "months": months, "pct": pct},
    )
