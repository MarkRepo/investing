"""Competence self-check I/O + scoring.

Answer storage convention in ``competence-check.md`` body:

    ### Q1 做什么 [specific]
    答案文本 ...

    ### Q2 怎么赚钱 [vague]
    ...

Levels:
    unanswered (0)  vague (0.5)  specific (1)

Gate (DESIGN §1 第 3 条): ``universal >= 8 and sector >= 3`` → in_competence.
"""
import re
from pathlib import Path
from typing import Any

import yaml

from app import config as cfg
from app.config import VALID_SECTORS

LEVELS = ("unanswered", "vague", "specific")
LEVEL_WEIGHTS = {"unanswered": 0.0, "vague": 0.5, "specific": 1.0}
PASS_UNIVERSAL = 8.0
PASS_SECTOR = 3.0

_ANSWER_RE = re.compile(
    r"^### (?P<id>\S+) (?P<label>.+?) \[(?P<level>\w+)\]$",
    re.MULTILINE,
)


def _load_questions(sector: str) -> tuple[list[dict], list[dict]]:
    core_path = cfg.CONTROLLED_VOCAB_DIR / "competence-core.yaml"
    sector_path = cfg.SECTOR_VOCAB_DIR / f"{sector}.yaml"

    core = yaml.safe_load(core_path.read_text(encoding="utf-8"))
    universal_questions = core["universal_questions"]

    sector_questions: list[dict] = []
    if sector_path.exists():
        sec = yaml.safe_load(sector_path.read_text(encoding="utf-8"))
        sector_questions = sec.get("sector_questions") or []
    return universal_questions, sector_questions


def _parse_answers(body: str) -> dict[str, dict]:
    """Return {question_id: {"label": str, "level": str, "text": str}}."""
    out: dict[str, dict] = {}
    matches = list(_ANSWER_RE.finditer(body))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        text = body[start:end].strip()
        out[m.group("id")] = {
            "label": m.group("label").strip(),
            "level": m.group("level").strip(),
            "text": text,
        }
    return out


def _frontmatter_split(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    return fm, text[end + len("\n---") :].lstrip("\n")


def _frontmatter_emit(fm: dict) -> str:
    order = [
        "ticker", "market", "check_date", "sector",
        "universal_score", "sector_score", "in_competence", "gaps",
    ]
    ordered: dict = {}
    for k in order:
        if k in fm:
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered:
            ordered[k] = v
    return "---\n" + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n"


def _competence_path(ticker: str, market: str, base: Path | None) -> Path:
    root = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    return root / f"{market}_{ticker}" / "competence-check.md"


def read_competence(ticker: str, market: str, base: Path | None = None) -> dict:
    """Return ``{fm, body, answers, sector, universal, sector_questions}``."""
    path = _competence_path(ticker, market, base)
    if not path.exists():
        raise FileNotFoundError(str(path))
    fm, body = _frontmatter_split(path.read_text(encoding="utf-8"))
    sector = fm.get("sector") or ""
    universal, sector_qs = ([], [])
    if sector:
        universal, sector_qs = _load_questions(sector)
    return {
        "frontmatter": fm,
        "body": body,
        "answers": _parse_answers(body),
        "sector": sector,
        "universal_questions": universal,
        "sector_questions": sector_qs,
    }


def score_competence(
    answers: dict[str, str],
    universal_questions: list[dict],
    sector_questions: list[dict],
) -> dict:
    """Compute scores from a ``{question_id: level}`` map.

    Returns ``{universal_score, sector_score, in_competence, gaps}``. A gap is
    any question whose level is not ``specific``.
    """
    u = sum(LEVEL_WEIGHTS.get(answers.get(q["id"], "unanswered"), 0.0) for q in universal_questions)
    s = sum(LEVEL_WEIGHTS.get(answers.get(q["id"], "unanswered"), 0.0) for q in sector_questions)
    gaps = [
        q["id"]
        for q in (list(universal_questions) + list(sector_questions))
        if answers.get(q["id"], "unanswered") != "specific"
    ]
    return {
        "universal_score": u,
        "sector_score": s,
        "in_competence": u >= PASS_UNIVERSAL and s >= PASS_SECTOR,
        "gaps": gaps,
    }


def write_competence(
    ticker: str,
    market: str,
    sector: str,
    check_date: str,
    answers: dict[str, dict],
    base: Path | None = None,
) -> Path:
    """Persist competence-check.md with refreshed scores in frontmatter.

    ``answers`` is ``{id: {"label": str, "level": str, "text": str}}``.
    """
    if sector not in VALID_SECTORS:
        raise ValueError(f"unknown sector {sector!r}; valid: {VALID_SECTORS}")

    universal_questions, sector_questions = _load_questions(sector)
    levels_only = {qid: info["level"] for qid, info in answers.items()}
    scores = score_competence(levels_only, universal_questions, sector_questions)

    fm = {
        "ticker": ticker,
        "market": market,
        "check_date": check_date,
        "sector": sector,
        "universal_score": scores["universal_score"],
        "sector_score": scores["sector_score"],
        "in_competence": scores["in_competence"],
        "gaps": scores["gaps"],
    }

    lines = [f"# 能力圈自检：{ticker}", ""]
    lines.append("## 通用 12 问")
    lines.append("")
    for q in universal_questions:
        info = answers.get(q["id"], {"level": "unanswered", "text": ""})
        level = info.get("level") or "unanswered"
        text = info.get("text") or ""
        lines.append(f"### {q['id']} {q['label']} [{level}]")
        lines.append(f"_{q['prompt']}_")
        lines.append("")
        lines.append(text.strip() or "_(未填)_")
        lines.append("")

    if sector_questions:
        lines.append(f"## 行业补丁：{sector}")
        lines.append("")
        for q in sector_questions:
            info = answers.get(q["id"], {"level": "unanswered", "text": ""})
            level = info.get("level") or "unanswered"
            text = info.get("text") or ""
            lines.append(f"### {q['id']} {q['label']} [{level}]")
            lines.append(f"_{q['prompt']}_")
            lines.append("")
            lines.append(text.strip() or "_(未填)_")
            lines.append("")

    body = "\n".join(lines)
    path = _competence_path(ticker, market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_frontmatter_emit(fm) + "\n" + body, encoding="utf-8")
    return path
