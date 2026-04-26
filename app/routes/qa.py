"""QA warnings & gap-report routes.

- ``GET /qa``                             跨 scope 汇总（公司 + 行业）
- ``GET /qa/{scope}``                     scope 详情（scope = MARKET_TICKER 或 industry:SLUG）
- ``POST /qa/{scope}/warnings/{wid}/resolve``  标 resolved
- ``POST /qa/{scope}/warnings/{wid}/dismiss``  标 dismissed
- ``POST /qa/{scope}/warnings/{wid}/reopen``   回到 open（用于手滑撤销）
"""
from __future__ import annotations

import markdown as md
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import qa as qa_io

router = APIRouter(prefix="/qa", tags=["qa"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


def _validate_scope(scope: str) -> str:
    """Ensure a path-param scope parses. Returns it unchanged on success."""
    try:
        qa_io._resolve_scope_dir(scope)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return scope


@router.get("")
def index(request: Request):
    rows = qa_io.summarize_by_scope()
    total_open = sum(r["open"] for r in rows)
    return templates.TemplateResponse(
        request,
        "qa/index.html",
        {"rows": rows, "total_open": total_open},
    )


@router.get("/{scope}")
def scope_detail(request: Request, scope: str, status: str = "open"):
    scope = _validate_scope(scope)
    if status not in ("open", "resolved", "dismissed", "all"):
        status = "open"

    warnings_all = qa_io.read_warnings(scope)
    if status == "all":
        warnings_view = warnings_all
    else:
        warnings_view = [w for w in warnings_all if w.get("status") == status]

    # Group the view by rule
    by_rule: dict[str, list[dict]] = {}
    for w in warnings_view:
        by_rule.setdefault(w["rule"], []).append(w)

    status_counts = {"open": 0, "resolved": 0, "dismissed": 0}
    for w in warnings_all:
        st = w.get("status", "open")
        status_counts[st] = status_counts.get(st, 0) + 1

    gap_md, gap_generated_at = qa_io.read_gap_markdown(scope)
    gap_html = md.markdown(gap_md, extensions=["fenced_code", "tables"]) if gap_md else ""

    return templates.TemplateResponse(
        request,
        "qa/company.html",
        {
            "key": scope,
            "scope": scope,
            "scope_kind": qa_io._scope_kind(scope),
            "by_rule": by_rule,
            "status": status,
            "status_counts": status_counts,
            "total_view": len(warnings_view),
            "gap_html": gap_html,
            "gap_generated_at": gap_generated_at,
            "rule_descriptions": _RULE_DESC,
        },
    )


@router.post("/{scope}/warnings/{wid}/resolve")
def mark_resolved(scope: str, wid: str, note: str = Form("")):
    scope = _validate_scope(scope)
    ok = qa_io.update_status(scope, wid, "resolved", note=note or None)
    if not ok:
        raise HTTPException(status_code=404, detail=f"warning {wid} not found")
    return RedirectResponse(url=f"/qa/{scope}", status_code=303)


@router.post("/{scope}/warnings/{wid}/dismiss")
def mark_dismissed(scope: str, wid: str, note: str = Form("")):
    scope = _validate_scope(scope)
    ok = qa_io.update_status(scope, wid, "dismissed", note=note or None)
    if not ok:
        raise HTTPException(status_code=404, detail=f"warning {wid} not found")
    return RedirectResponse(url=f"/qa/{scope}", status_code=303)


@router.post("/{scope}/warnings/{wid}/reopen")
def mark_reopened(scope: str, wid: str):
    scope = _validate_scope(scope)
    ok = qa_io.update_status(scope, wid, "open")
    if not ok:
        raise HTTPException(status_code=404, detail=f"warning {wid} not found")
    return RedirectResponse(url=f"/qa/{scope}?status=all", status_code=303)


_RULE_DESC = {
    "fidelity": "evidence_quote 在原文中未找到（可能拼接/改写）",
    "empty_evidence": "answered 缺 evidence_quote",
    "self_contradict_specific": "level=specific 但 answer_text 含'未提及/未披露'等",
    "polarity_mismatch": "polarity 与 claim_text 情感词冲突（可能误报）",
    "proposed_dup": "proposed_question 与 existing checklist item 重合",
    "checklist_company_contamination": "checklist question 含 participant 公司名（跨公司对比失效）",
}
