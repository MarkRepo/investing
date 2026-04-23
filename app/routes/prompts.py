"""Prompts index: list all LLM prompt docs available at /prompts/*.md.

The raw markdown files are served via StaticFiles mount in main.py. This router
provides the HTML index page so you can quickly find and copy prompts during a
Claude conversation — LLM ops live in conversation, Python only post-processes.
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR

router = APIRouter(tags=["prompts"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))

# Repo-fixed path: prompts ship with source, not with user data
_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "prompts"


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _first_paragraph(text: str) -> str:
    lines = []
    in_para = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if in_para:
                break
            continue
        if not stripped:
            if in_para:
                break
            continue
        if stripped.startswith(">") or stripped.startswith("---"):
            if in_para:
                break
            continue
        in_para = True
        lines.append(stripped)
    return " ".join(lines)[:240]


def _list_prompt_docs():
    rows = []
    if not _PROMPTS_DIR.exists():
        return rows
    for p in sorted(_PROMPTS_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        rows.append({
            "slug": p.stem,
            "filename": p.name,
            "title": _first_heading(text) or p.stem,
            "summary": _first_paragraph(text),
            "raw_path": f"/prompts/{p.name}",
        })
    return rows


@router.get("/prompts", response_class=HTMLResponse)
def prompts_index(request: Request):
    rows = _list_prompt_docs()
    return templates.TemplateResponse(
        request,
        "prompts/index.html",
        {"rows": rows},
    )
