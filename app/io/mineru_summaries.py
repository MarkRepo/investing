"""MinerU summary I/O — read/write structured LLM summaries and registry."""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from app.config import BASE_PATH

SUMMARIES_DIR = BASE_PATH / "mineru_summaries"
REGISTRY_FILE = SUMMARIES_DIR / "registry.json"
MINERU_ROOT = Path.home() / "MinerU"

# Report ID → source directory mapping (discovered at generation time,
# seeded here for known reports).
KNOWN_REPORTS: list[dict] = [
    {
        "report_id": "chaowan",
        "title": "2025年中国潮玩行业市场研究报告",
        "topic": "潮玩",
        "source_pdf": "潮玩.pdf",
        "source_dir": "潮玩.pdf-91631bd7-8aed-4321-9fab-3a0d770ade29",
    },
    {
        "report_id": "dikong-jingji",
        "title": "2025年中国低空经济市场研究报告",
        "topic": "低空经济",
        "source_pdf": "低空经济.pdf",
        "source_dir": "低空经济.pdf-ac807ebb-6a83-4345-8350-2e8fb4b8b704",
    },
    {
        "report_id": "shangye-hangtian",
        "title": "商业航天行业研究报告",
        "topic": "商业航天",
        "source_pdf": "商业航天.pdf",
        "source_dir": "商业航天.pdf-58f6b3b7-231d-4296-9585-bc32209f584a",
    },
    {
        "report_id": "ai-suanli",
        "title": "AI算力专题报告",
        "topic": "AI算力",
        "source_pdf": "AI算力.pdf",
        "source_dir": "AI算力.pdf-abd2b524-e096-48d2-93f1-573cdb4d8404",
    },
    {
        "report_id": "he-jubian",
        "title": "核聚变行业研究报告",
        "topic": "核聚变",
        "source_pdf": "核聚变.pdf",
        "source_dir": "核聚变.pdf-9314b977-0a8a-4a1c-bead-702091be19b9",
        "source_id": "bocisec-cn-nuclear-fusion-2025-9314b977",
    },
    {
        "report_id": "chongwu-hangye",
        "title": "2025年中国宠物行业市场研究报告",
        "topic": "宠物行业",
        "source_pdf": "2025-china-pet-industry-market-report.pdf",
        "source_dir": "2025-china-pet-industry-market-report.pdf-dc0eb908-e7b9-4ea9-a2af-addaff7684ce",
    },
]

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


def _ensure_dir() -> None:
    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)


def _parse_front_matter(text: str) -> tuple[dict, str]:
    """Split YAML front matter from markdown body. Returns ({meta}, body)."""
    m = _FRONT_MATTER_RE.match(text)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, m.group(2).lstrip()


def _render_front_matter(meta: dict, body: str) -> str:
    return f"---\n{yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()}\n---\n\n{body}"


def list_summaries() -> list[dict]:
    """Return sorted list of summary metadata from registry."""
    _ensure_dir()
    if not REGISTRY_FILE.exists():
        return []
    with open(REGISTRY_FILE, encoding="utf-8") as f:
        entries = json.load(f)
    return sorted(entries, key=lambda e: e.get("report_id", ""))


def read_summary(report_id: str) -> tuple[dict, str]:
    """Load {report_id}.md, return (front_matter, markdown_body)."""
    path = SUMMARIES_DIR / f"{report_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"summary {report_id!r} not found at {path}")
    text = path.read_text(encoding="utf-8")
    return _parse_front_matter(text)


def write_summary(report_id: str, meta: dict, body: str) -> None:
    """Write summary markdown with YAML front matter."""
    _ensure_dir()
    path = SUMMARIES_DIR / f"{report_id}.md"
    path.write_text(_render_front_matter(meta, body), encoding="utf-8")


def update_registry(entries: list[dict]) -> None:
    """Write registry.json atomically."""
    _ensure_dir()
    tmp = REGISTRY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY_FILE)


def source_id_to_report_id() -> dict[str, str]:
    """Return {source_id: report_id} for all known reports that have a source_id."""
    return {r["source_id"]: r["report_id"] for r in KNOWN_REPORTS if r.get("source_id")}


_CROSS_LINK_PRIORITY = {"sonnet46": 0, "gemini-3.1-pro": 1, "qwen36plus": 2}


def source_id_to_best_report_id() -> dict[str, str]:
    """Return {source_id: report_id} pointing to the highest-priority model summary."""
    registry = list_summaries()
    pdf_to_best: dict[str, tuple[int, str]] = {}
    for r in registry:
        model = r.get("model") or "qwen3"
        if model not in _CROSS_LINK_PRIORITY:
            continue
        pdf = r.get("source_pdf", "")
        priority = _CROSS_LINK_PRIORITY[model]
        if pdf not in pdf_to_best or priority < pdf_to_best[pdf][0]:
            pdf_to_best[pdf] = (priority, r["report_id"])
    result = {}
    for r in KNOWN_REPORTS:
        if r.get("source_id"):
            best = pdf_to_best.get(r.get("source_pdf", ""))
            if best:
                result[r["source_id"]] = best[1]
    return result


def get_full_md_path(source_dir: str) -> Path | None:
    """Resolve full.md path under ~/MinerU/{source_dir}/."""
    candidate = MINERU_ROOT / source_dir / "full.md"
    if candidate.exists():
        return candidate
    fallback = MINERU_ROOT / source_dir / "full-clean.md"
    if fallback.exists():
        return fallback
    return None


def get_pdf_path(source_dir: str) -> Path | None:
    """Resolve the original PDF inside ~/MinerU/{source_dir}/ (named *_origin.pdf)."""
    d = MINERU_ROOT / source_dir
    if not d.is_dir():
        return None
    for p in d.glob("*_origin.pdf"):
        return p
    return None
