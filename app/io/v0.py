"""V0 markdown file I/O.

V0 files live at ``companies/{market}_{ticker}/v0.md`` and consist of a YAML
frontmatter block delimited by ``---`` fences followed by a markdown body.

Frontmatter keys are always emitted in a fixed order to keep diffs stable.
"""
import re
from pathlib import Path
from typing import Any

import yaml

from app import config as cfg

FRONTMATTER_KEY_ORDER = (
    "ticker",
    "market",
    "entry_date",
    "position_size_pct",
    "status",
    "last_reviewed",
    "last_reviewed_period",
)

SECTION_TITLES = (
    "1. 买入逻辑",
    "2. 差异化观点（二阶思维）",
    "3. 估值锚",
    "4. 买入区间",
    "5. 卖出触发",
    "6. 什么不算推翻（噪音清单）",
    "7. 当前状态",
)

_HEADING_RE = re.compile(r"^## (\d)\. .*$", re.MULTILINE)


def _companies_dir(base: Path | None) -> Path:
    if base is None:
        return cfg.COMPANIES_DIR
    return Path(base) / "companies"


def _v0_path(ticker: str, market: str, base: Path | None) -> Path:
    return _companies_dir(base) / f"{market}_{ticker}" / "v0.md"


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown document into (frontmatter_dict, body_str)."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    raw = text[3:end].strip()
    fm = yaml.safe_load(raw) or {}
    if "ticker" in fm and not isinstance(fm["ticker"], str):
        # all-digit tickers (BSE 920118, A-share 600519, HK 0700) in unquoted YAML
        # come back as int; normalize here so downstream str ops don't crash.
        fm["ticker"] = str(fm["ticker"])
    body_start = end + len("\n---")
    body = text[body_start:].lstrip("\n")
    return fm, body


def _emit_frontmatter(fm: dict[str, Any]) -> str:
    """Dump frontmatter with FRONTMATTER_KEY_ORDER keys first, extras after."""
    ordered: dict[str, Any] = {}
    for k in FRONTMATTER_KEY_ORDER:
        if k in fm:
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered:
            ordered[k] = v
    body = yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip() + "\n"
    return f"---\n{body}---\n"


def read_v0(ticker: str, market: str, base: Path | None = None) -> dict[str, Any]:
    """Return ``{'frontmatter': dict, 'body': str}``.

    Raises FileNotFoundError if the file does not exist.
    """
    path = _v0_path(ticker, market, base)
    text = path.read_text(encoding="utf-8")
    fm, body = _parse_frontmatter(text)
    return {"frontmatter": fm, "body": body}


def write_v0(
    ticker: str,
    market: str,
    frontmatter: dict[str, Any],
    body: str,
    base: Path | None = None,
) -> Path:
    """Write a V0 file, creating parent directories as needed."""
    path = _v0_path(ticker, market, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _emit_frontmatter(frontmatter) + "\n" + body.lstrip("\n")
    path.write_text(text, encoding="utf-8")
    return path


def split_sections(body: str) -> dict[int, str]:
    """Split V0 body into a ``{1: text, 2: text, ..., 7: text}`` dict.

    Each section includes the heading line so round-trips preserve formatting.
    Any content before section 1 (title block, preamble) is dropped — the
    caller is expected to re-emit the H1 from the template on save.
    """
    matches = list(_HEADING_RE.finditer(body))
    out: dict[int, str] = {i: "" for i in range(1, 8)}
    for i, m in enumerate(matches):
        sec = int(m.group(1))
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[sec] = body[start:end].rstrip() + "\n"
    return out


def join_sections(sections: dict[int, str], ticker: str) -> str:
    """Reassemble body from a 7-section dict, emitting a fixed H1 at the top."""
    parts = [f"# V0: {ticker}\n"]
    for i in range(1, 8):
        text = (sections.get(i) or "").strip()
        if text and not text.startswith("## "):
            text = f"## {SECTION_TITLES[i - 1]}\n{text}"
        if not text:
            text = f"## {SECTION_TITLES[i - 1]}\n"
        parts.append(text.rstrip() + "\n")
    return "\n".join(parts)


def list_all_v0s(
    base: Path | None = None,
    status_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Scan ``companies/*/v0.md`` and return summary entries."""
    companies = _companies_dir(base)
    if not companies.exists():
        return []

    out: list[dict[str, Any]] = []
    for v0 in sorted(companies.glob("*/v0.md")):
        fm, _ = _parse_frontmatter(v0.read_text(encoding="utf-8"))
        if status_filter is not None and fm.get("status") != status_filter:
            continue
        out.append(
            {
                "ticker": fm.get("ticker"),
                "market": fm.get("market"),
                "status": fm.get("status"),
                "last_reviewed": fm.get("last_reviewed"),
                "entry_date": fm.get("entry_date"),
                "position_size_pct": fm.get("position_size_pct", 0),
                "v0_path": str(v0),
            }
        )
    return out
