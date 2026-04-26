"""Arena IO: 竞技场（arena）级别的能力圈归档。

Arena = "产品类别 + 客户场景 + 地理范围 + 价位段" 四维定义的战场，粒度能列出
3-10 家核心对手。每个 arena 目录下三个文件：

- ``definition.md``：frontmatter + 四维 + 边界 + 参与者列表（YAML list）
- ``checklist.yaml``：看懂本 arena 的能力维度清单 + 版本历史
- ``competence-notes.md``：跨公司答案库（按 ticker 小节分段）

能力圈模型：arena checklist 驱动 ingest subagent 主动追问；ingest 产出的答案
合并到 notes；用户 approve 的 proposed_additions 自增 checklist 版本。

**公司 → arena 的真源**：``companies/{market}_{ticker}/meta.md.arenas``（list[str]
of slug）。definition.md 的 ``participants`` 字段是冗余视图，由 ``participants_add``
在关联时同步维护。

本模块不调 LLM；合并策略 / 格式化都是纯 Python。
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app import config as cfg
from app.io import company as company_io


# --- paths -------------------------------------------------------------------


def _arenas_dir(base: Path | None) -> Path:
    return Path(base) / "arenas" if base else cfg.ARENAS_DIR


def _arena_dir(slug: str, base: Path | None) -> Path:
    return _arenas_dir(base) / slug


def _definition_path(slug: str, base: Path | None) -> Path:
    return _arena_dir(slug, base) / "definition.md"


def _checklist_path(slug: str, base: Path | None) -> Path:
    return _arena_dir(slug, base) / "checklist.yaml"


def _notes_path(slug: str, base: Path | None) -> Path:
    return _arena_dir(slug, base) / "competence-notes.md"


# --- frontmatter helpers -----------------------------------------------------


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    return fm, text[end + len("\n---") :].lstrip("\n")


def _emit_frontmatter(fm: dict) -> str:
    return (
        "---\n"
        + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).rstrip()
        + "\n---\n"
    )


# --- definition.md -----------------------------------------------------------


def slug_exists(slug: str, base: Path | None = None) -> bool:
    return _definition_path(slug, base).exists()


def list_arenas(base: Path | None = None) -> list[dict[str, Any]]:
    """Return one summary per arena under ``arenas/``."""
    root = _arenas_dir(base)
    if not root.exists():
        return []
    out: list[dict[str, Any]] = []
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        def_path = d / "definition.md"
        if not def_path.exists():
            continue
        fm, _ = _split_frontmatter(def_path.read_text(encoding="utf-8"))
        out.append(
            {
                "slug": fm.get("slug") or d.name,
                "name": fm.get("name"),
                "participants": fm.get("participants") or [],
                "created": fm.get("created"),
                "last_updated": fm.get("last_updated"),
            }
        )
    return out


def write_definition(
    slug: str,
    fm: dict | None = None,
    body: str | None = None,
    base: Path | None = None,
    *,
    name: str | None = None,
    definition_text: str | None = None,
    participants: list[dict] | None = None,
    industry: str | None = None,
    battleground_focus: str | None = None,
    today: date | None = None,
) -> Path:
    """Create or overwrite ``arenas/{slug}/definition.md``.

    Two call styles are supported:

    - Legacy: ``write_definition(slug, fm_dict, body_str, base=...)`` — caller
      supplies the full frontmatter dict (must include ``slug``) and body.
    - Dimensioned (spec §2.2): ``write_definition(slug=..., name=...,
      definition_text=..., industry=..., battleground_focus=..., base=...)`` —
      helper builds the frontmatter from the kwargs.

    ``industry`` and ``battleground_focus`` are optional; legacy arenas without
    them still read correctly. ``participants`` if present must be a list of
    dicts with ``{market, ticker, name, role}``.
    """
    if fm is None:
        today_iso = (today or date.today()).isoformat()
        fm = {
            "slug": slug,
            "name": name,
            "created": today_iso,
            "last_updated": today_iso,
            "participants": participants or [],
        }
        if industry is not None:
            fm["industry"] = industry
        if battleground_focus is not None:
            fm["battleground_focus"] = battleground_focus
        body = definition_text if definition_text is not None else ""
    else:
        # merge in any explicit kwargs (allows callers to layer new fields onto
        # an existing fm dict).
        if industry is not None:
            fm["industry"] = industry
        if battleground_focus is not None:
            fm["battleground_focus"] = battleground_focus
        if body is None:
            body = ""
    if fm.get("slug") != slug:
        raise ValueError(f"frontmatter slug {fm.get('slug')!r} != path slug {slug!r}")
    participants = fm.get("participants")
    if participants is not None:
        if not isinstance(participants, list):
            raise ValueError("participants must be a list of dicts")
        for p in participants:
            if not isinstance(p, dict) or not {"market", "ticker"}.issubset(p):
                raise ValueError(
                    "each participant must be a dict with at least market+ticker"
                )
            if not isinstance(p["ticker"], str):
                p["ticker"] = str(p["ticker"])

    path = _definition_path(slug, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _emit_frontmatter(fm) + "\n" + body.lstrip()
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    _ensure_narrative_skeletons(slug, fm.get("name") or slug, base)
    return path


def read_definition(slug: str, base: Path | None = None) -> dict:
    """Return ``{frontmatter, body, exists}``."""
    path = _definition_path(slug, base)
    if not path.exists():
        return {"frontmatter": {}, "body": "", "exists": False}
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    return {"frontmatter": fm, "body": body, "exists": True}


def participants_add(
    slug: str,
    ticker: str,
    market: str,
    name: str,
    role: str = "challenger",
    base: Path | None = None,
) -> Path:
    """Append a participant to ``definition.md`` if not already listed.

    Returns the definition path. No-op if the ``(market, ticker)`` pair is
    already in the list.
    """
    info = read_definition(slug, base=base)
    if not info["exists"]:
        raise FileNotFoundError(f"arena {slug} has no definition.md")
    fm = dict(info["frontmatter"])
    participants = list(fm.get("participants") or [])
    pair = (market, str(ticker))
    for p in participants:
        if (p.get("market"), str(p.get("ticker"))) == pair:
            return _definition_path(slug, base)
    participants.append(
        {"market": market, "ticker": str(ticker), "name": name, "role": role}
    )
    fm["participants"] = participants
    fm["last_updated"] = date.today().isoformat()
    return write_definition(slug, fm, info["body"], base=base)


# --- checklist.yaml ----------------------------------------------------------


_PREDEFINED_TAGS = frozenset(
    {
        "industry_structure",
        "competitive_position",
        "growth_drivers",
        "customer_structure",
        "technology",
        "policy_environment",
        "financial_model",
        "risk",
    }
)


def read_checklist(slug: str, base: Path | None = None) -> dict:
    """Return the checklist dict or ``{}`` if missing."""
    path = _checklist_path(slug, base)
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _validate_items(items: list[dict]) -> None:
    if not isinstance(items, list):
        raise ValueError("items must be a list")
    if len(items) > 15:
        raise ValueError(f"checklist supports at most 15 items, got {len(items)}")
    seen: set[str] = set()
    for it in items:
        if not isinstance(it, dict):
            raise ValueError(f"item must be a dict: {it!r}")
        for k in ("id", "question", "why_matters", "typical_evidence_section", "tags"):
            if k not in it:
                raise ValueError(f"item {it.get('id')!r} missing field: {k}")
        if not isinstance(it["id"], str) or not it["id"]:
            raise ValueError("item id must be non-empty str")
        if it["id"] in seen:
            raise ValueError(f"duplicate item id: {it['id']}")
        seen.add(it["id"])
        if not isinstance(it["typical_evidence_section"], list):
            raise ValueError(
                f"item {it['id']}: typical_evidence_section must be a list"
            )
        tags = it["tags"]
        if not isinstance(tags, list) or not (1 <= len(tags) <= 3):
            raise ValueError(
                f"item {it['id']}: tags must be a list of 1-3 entries"
            )
        for t in tags:
            if t not in _PREDEFINED_TAGS:
                raise ValueError(
                    f"item {it['id']}: tag {t!r} not in predefined set {sorted(_PREDEFINED_TAGS)}"
                )


def write_checklist(
    slug: str,
    items: list[dict],
    changelog_entry: dict | None = None,
    base: Path | None = None,
) -> Path:
    """Create v1 or bump existing version.

    ``changelog_entry`` is a dict like ``{source_id, changes}`` (date/version
    are filled in automatically). If ``None``, a minimal entry is synthesized.
    """
    _validate_items(items)
    existing = read_checklist(slug, base=base)
    today = date.today().isoformat()
    if existing:
        new_version = int(existing.get("version", 0)) + 1
        changelog = list(existing.get("changelog") or [])
    else:
        new_version = 1
        changelog = []
    entry = {"version": new_version, "date": today}
    if changelog_entry:
        for k in ("source_id", "changes"):
            if k in changelog_entry:
                entry[k] = changelog_entry[k]
    changelog.append(entry)

    doc = {
        "slug": slug,
        "version": new_version,
        "last_updated": today,
        "changelog": changelog,
        "items": items,
    }
    path = _checklist_path(slug, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(doc, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


# --- competence-notes.md -----------------------------------------------------


_LEVEL_RANK = {"specific": 3, "vague": 2, "unanswered": 1}


def consolidate_answers(raw_findings: list[dict]) -> list[dict]:
    """Collapse multiple subagents' answers for the same ``q_id``.

    Rule: pick the highest level (``specific`` > ``vague`` > ``unanswered``);
    within the same level, pick the one with the longest ``evidence_quote``.
    """
    by_q: dict[str, dict] = {}
    for f in raw_findings or []:
        qid = f.get("q_id")
        if not qid:
            continue
        lvl = f.get("level", "unanswered")
        rank = _LEVEL_RANK.get(lvl, 0)
        ev_len = len(f.get("evidence_quote") or "")
        prev = by_q.get(qid)
        if prev is None:
            by_q[qid] = f
            continue
        prev_rank = _LEVEL_RANK.get(prev.get("level", "unanswered"), 0)
        prev_ev_len = len(prev.get("evidence_quote") or "")
        if rank > prev_rank or (rank == prev_rank and ev_len > prev_ev_len):
            by_q[qid] = f
    return list(by_q.values())


def _ticker_section_header(ticker: str, market: str, name: str) -> str:
    return f"## {market}_{ticker} · {name}"


def _read_notes_body(slug: str, base: Path | None) -> tuple[dict, str]:
    path = _notes_path(slug, base)
    if not path.exists():
        return {"slug": slug}, f"# 认知库 · {slug}\n"
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    if not fm:
        fm = {"slug": slug}
    return fm, body


def append_notes(
    slug: str,
    ticker: str,
    market: str,
    name: str,
    answered_items: list[dict],
    source_id: str,
    checklist_version: int,
    base: Path | None = None,
) -> Path:
    """Append / replace a ticker's answer block in ``competence-notes.md``.

    If the ticker section already exists, it is replaced (same q_id gets
    overwritten by the newer source). Items with ``level=='unanswered'`` are
    dropped — the notes file is a knowledge base, not a TODO list.
    """
    ticker = str(ticker)
    kept = [a for a in (answered_items or []) if a.get("level") != "unanswered"]
    if not kept:
        # nothing to write, but still ensure the file exists so later appends
        # have a place to go
        path = _notes_path(slug, base)
        if not path.exists():
            fm, body = _read_notes_body(slug, base)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_emit_frontmatter(fm) + "\n" + body, encoding="utf-8")
        return path

    today = date.today().isoformat()
    section_header = _ticker_section_header(ticker, market, name)

    lines = [section_header, ""]
    # dedup by q_id, latest wins (already consolidated upstream, but guard)
    seen: set[str] = set()
    for a in kept:
        qid = a.get("q_id")
        if not qid or qid in seen:
            continue
        seen.add(qid)
        answer = (a.get("answer_text") or "").strip()
        quote = (a.get("evidence_quote") or "").strip()
        level = a.get("level") or "specific"
        lines.append(f"### {qid} · level={level}")
        lines.append(
            f"来源：{source_id} · checklist v{checklist_version} · {today}"
        )
        lines.append("")
        if answer:
            lines.append(answer)
            lines.append("")
        if quote:
            for ln in quote.splitlines():
                lines.append(f"> {ln}")
            lines.append("")
    ticker_block = "\n".join(lines).rstrip() + "\n"

    fm, body = _read_notes_body(slug, base)

    # find and replace an existing block for this ticker, else append.
    import re as _re

    pattern = _re.compile(
        r"(^|\n)"
        + _re.escape(section_header)
        + r"\s*\n(.*?)(?=\n## |\Z)",
        flags=_re.DOTALL,
    )
    new_body, n = pattern.subn(lambda m: m.group(1) + ticker_block, body)
    if n == 0:
        if not body.endswith("\n"):
            body += "\n"
        new_body = body + "\n" + ticker_block

    fm = dict(fm)
    fm["slug"] = slug
    path = _notes_path(slug, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _emit_frontmatter(fm) + "\n" + new_body.lstrip()
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    return path


# --- reverse lookup ---------------------------------------------------------


def find_by_company(
    ticker: str, market: str, base: Path | None = None
) -> list[str]:
    """Return arena slugs a company belongs to, read from its meta.md."""
    fm = company_io.read_meta(ticker, market, base=base)
    arenas = fm.get("arenas") or []
    if isinstance(arenas, str):
        arenas = [a.strip() for a in arenas.split(",") if a.strip()]
    return list(arenas)


# --- combined read -----------------------------------------------------------


def read_arena(slug: str, base: Path | None = None) -> dict:
    """Return ``{definition_fm, definition_body, checklist, notes_text, exists}``."""
    d = read_definition(slug, base=base)
    checklist = read_checklist(slug, base=base)
    notes_path = _notes_path(slug, base)
    notes_text = notes_path.read_text(encoding="utf-8") if notes_path.exists() else ""
    return {
        "slug": slug,
        "definition_fm": d["frontmatter"],
        "definition_body": d["body"],
        "checklist": checklist,
        "notes_text": notes_text,
        "exists": d["exists"],
    }


# --- notes parsing (inverse of append_notes) ---------------------------------

import re as _re

_TICKER_HEADER_RE = _re.compile(r"^##\s+(?P<market>[A-Z]+)_(?P<ticker>[^\s·]+)\s*·\s*(?P<name>.+?)\s*$")
_QUESTION_HEADER_RE = _re.compile(r"^###\s+(?P<qid>\S+)\s*·\s*level=(?P<level>\S+)\s*$")
_SOURCE_LINE_RE = _re.compile(
    r"^来源：(?P<sid>.+?)\s*·\s*checklist\s+v(?P<ver>\d+)\s*·\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$"
)


def parse_notes(slug: str, base: Path | None = None) -> dict:
    """Parse ``competence-notes.md`` into structured dict.

    Inverse of ``append_notes``. Returns::

        {
          "by_ticker": {"{market}_{ticker}": {"name", "answers": {qid: {...}}}},
          "by_question": {qid: [{"market", "ticker", "name", ...}, ...]},
        }
    """
    path = _notes_path(slug, base)
    if not path.exists():
        return {"by_ticker": {}, "by_question": {}}
    _, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    lines = body.splitlines()

    by_ticker: dict[str, dict] = {}
    by_question: dict[str, list] = {}

    current_ticker_key: str | None = None
    current_ticker_meta: dict | None = None
    current_q: dict | None = None
    q_body_lines: list[str] = []

    def _flush_question():
        nonlocal current_q, q_body_lines
        if current_q is None or current_ticker_key is None:
            current_q = None
            q_body_lines = []
            return
        answer_lines: list[str] = []
        quote_lines: list[str] = []
        source_id = None
        ver = None
        date = None
        saw_source = False
        for ln in q_body_lines:
            if not saw_source:
                m = _SOURCE_LINE_RE.match(ln.strip())
                if m:
                    source_id = m.group("sid")
                    ver = int(m.group("ver"))
                    date = m.group("date")
                    saw_source = True
                    continue
                if not ln.strip():
                    continue
            if ln.startswith("> "):
                quote_lines.append(ln[2:])
            elif ln.startswith(">"):
                quote_lines.append(ln[1:])
            else:
                answer_lines.append(ln)
        # strip leading/trailing blank lines from answer/quote
        while answer_lines and not answer_lines[0].strip():
            answer_lines.pop(0)
        while answer_lines and not answer_lines[-1].strip():
            answer_lines.pop()
        while quote_lines and not quote_lines[0].strip():
            quote_lines.pop(0)
        while quote_lines and not quote_lines[-1].strip():
            quote_lines.pop()
        entry = {
            "level": current_q["level"],
            "answer": "\n".join(answer_lines),
            "quote": "\n".join(quote_lines),
            "source_id": source_id,
            "checklist_version": ver,
            "date": date,
        }
        qid = current_q["qid"]
        by_ticker[current_ticker_key]["answers"][qid] = entry
        by_question.setdefault(qid, []).append(
            {
                "market": current_ticker_meta["market"],
                "ticker": current_ticker_meta["ticker"],
                "name": current_ticker_meta["name"],
                **entry,
            }
        )
        current_q = None
        q_body_lines = []

    for ln in lines:
        m_t = _TICKER_HEADER_RE.match(ln)
        if m_t:
            _flush_question()
            current_ticker_meta = {
                "market": m_t.group("market"),
                "ticker": m_t.group("ticker"),
                "name": m_t.group("name"),
            }
            current_ticker_key = f"{current_ticker_meta['market']}_{current_ticker_meta['ticker']}"
            by_ticker[current_ticker_key] = {
                "name": current_ticker_meta["name"],
                "answers": {},
            }
            continue
        m_q = _QUESTION_HEADER_RE.match(ln)
        if m_q:
            _flush_question()
            if current_ticker_key is None:
                # orphaned question header — ignore
                current_q = None
                continue
            current_q = {"qid": m_q.group("qid"), "level": m_q.group("level")}
            q_body_lines = []
            continue
        if current_q is not None:
            q_body_lines.append(ln)
    _flush_question()
    return {"by_ticker": by_ticker, "by_question": by_question}


def company_summary(
    ticker: str, market: str, base: Path | None = None
) -> list[dict]:
    """Per-arena summary for a company: counts of specific / vague / unanswered.

    Returns one row per arena the company is listed under in its meta.md.
    """
    ticker = str(ticker)
    slugs = find_by_company(ticker, market, base=base)
    key = f"{market}_{ticker}"
    out: list[dict] = []
    for slug in slugs:
        cl = read_checklist(slug, base=base)
        items = cl.get("items") or []
        total = len(items)
        item_ids = [it.get("id") for it in items]
        notes = parse_notes(slug, base=base)
        answers = notes["by_ticker"].get(key, {}).get("answers", {})
        spec = sum(1 for qid in item_ids if answers.get(qid, {}).get("level") == "specific")
        vague = sum(1 for qid in item_ids if answers.get(qid, {}).get("level") == "vague")
        answered = spec + vague
        unanswered = total - answered
        definition = read_definition(slug, base=base)
        out.append(
            {
                "slug": slug,
                "name": definition["frontmatter"].get("name"),
                "total": total,
                "answered_specific": spec,
                "answered_vague": vague,
                "unanswered": unanswered,
            }
        )
    return out


# ---------- Narrative (6-dim, spec §4.1) ----------

_ARENA_NARRATIVE_TEMPLATE = """
### 来源 {institution} {date} (sha8={sha8})
source_id: {source_id}

{block}
"""

_ARENA_CN_TITLES = {
    "definition": "战场定义与博弈焦点",
    "participants": "参与者与相对位置",
    "decisive_factors": "博弈规则与胜负手",
    "trajectory": "演进轨迹与触发事件",
    "narratives": "多空叙事",
    "investment_view": "决策启示",
}


def _arena_narrative_path(slug: str, dim: str, base: Path | None) -> Path:
    if dim not in cfg.ARENA_DIMENSIONS:
        raise ValueError(f"unknown arena dim {dim!r}; must be one of {cfg.ARENA_DIMENSIONS}")
    if dim == "definition":
        return _definition_path(slug, base)
    return _arena_dir(slug, base) / f"{dim.replace('_', '-')}.md"


def _ensure_narrative_skeletons(slug: str, name: str, base: Path | None) -> None:
    """Create 5 narrative .md skeletons (excluding definition.md) if missing."""
    for dim in cfg.ARENA_DIMENSIONS:
        if dim == "definition":
            continue
        path = _arena_narrative_path(slug, dim, base)
        if not path.exists():
            header = f"# {_ARENA_CN_TITLES[dim]} · {name}\n\n*slug: {slug} · 维度: {dim}*\n\n"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(header, encoding="utf-8")


def read_narrative(slug: str, dim: str, base: Path | None = None) -> str:
    path = _arena_narrative_path(slug, dim, base)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_narrative_block(
    slug: str, dim: str, block: str, source_meta: dict, base: Path | None = None
) -> None:
    path = _arena_narrative_path(slug, dim, base)
    for key in ("institution", "date", "sha8", "source_id"):
        if key not in source_meta:
            raise ValueError(f"source_meta missing {key}")
    rendered = _ARENA_NARRATIVE_TEMPLATE.format(
        institution=source_meta["institution"],
        date=source_meta["date"],
        sha8=source_meta["sha8"],
        source_id=source_meta["source_id"],
        block=block.rstrip(),
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(rendered)


def find_by_industry(industry_slug: str, base: Path | None = None) -> list[str]:
    """Return list of arena slugs whose definition.md frontmatter.industry == industry_slug."""
    root = _arenas_dir(base)
    if not root.exists():
        return []
    result = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        def_path = _definition_path(child.name, base)
        if not def_path.exists():
            continue
        try:
            data = read_definition(child.name, base=base)
        except Exception:
            continue
        fm = data.get("frontmatter", {})
        if fm.get("industry") == industry_slug:
            result.append(fm.get("slug", child.name))
    return result
