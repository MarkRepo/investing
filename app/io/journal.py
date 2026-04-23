"""Investment decision journal I/O (DESIGN §3.5).

File layout: ``journal/decisions/{year}-Q{q}/{YYYY-MM-DD}-{ticker}-{action}.md``
Entry id:    ``{YYYY-MM-DD}-{ticker}-{action}`` (stable, filesystem-safe)

Process score (1-5, filled at decision time) and result score (null-until-
backfilled) live in frontmatter for quick aggregation; reasoning prose lives
in the markdown body.
"""
import hashlib
import re
from dataclasses import dataclass
from datetime import date as date_cls
from pathlib import Path
from typing import Any

import yaml

from app import config as cfg

ACTIONS = ("buy", "sell", "pass", "miss", "add", "trim")

FRONTMATTER_KEYS = (
    "id",
    "date",
    "ticker",
    "market",
    "action",
    "price",
    "position_change",
    "v0_snapshot_path",
    "v0_snapshot_hash",
    # process score (1-5, filled at decision time)
    "process_quality",
    "process_rigor",
    "process_rule_adherence",
    "process_emotional_control",
    # result score (null until backfilled)
    "pnl_3m",
    "pnl_6m",
    "pnl_12m",
    "result_quality",
    "result_luck_factor",
)

# Stable body skeleton; sections line up with parser.
SECTIONS: tuple[str, ...] = (
    "决策内容",
    "V0 当时状态",
    "决策时的情绪状态",
    "决策前偏见自查（四问）",
    "决策的 5 个支撑理由",
    "我当时最担心的事",
    "过程评分说明（为什么打这些分）",
    "结果评分说明（后续填）",
)

_SEC_RE = re.compile(r"^## (\d+)\. (.+)$", re.MULTILINE)
_ID_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([A-Z0-9.]+)-(buy|sell|pass|miss|add|trim)$")


@dataclass
class JournalPaths:
    quarter_dir: Path
    file_path: Path
    entry_id: str


def _quarter(d: date_cls) -> int:
    return (d.month - 1) // 3 + 1


def _decisions_root(base: Path | None) -> Path:
    return (Path(base) / "journal" / "decisions") if base else (cfg.JOURNAL_DIR / "decisions")


def build_paths(
    d: date_cls, ticker: str, action: str, base: Path | None = None
) -> JournalPaths:
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {ACTIONS}")
    ticker = ticker.strip().upper()
    entry_id = f"{d.isoformat()}-{ticker}-{action}"
    qdir = _decisions_root(base) / f"{d.year}-Q{_quarter(d)}"
    return JournalPaths(qdir, qdir / f"{entry_id}.md", entry_id)


def parse_entry_id(entry_id: str) -> tuple[date_cls, str, str]:
    m = _ID_RE.match(entry_id)
    if not m:
        raise ValueError(f"invalid entry id: {entry_id!r}")
    date_str, ticker, action = m.groups()
    y, mo, d = (int(x) for x in date_str.split("-"))
    return date_cls(y, mo, d), ticker, action


# --- V0 snapshot helpers -----------------------------------------------------


def v0_snapshot_hash(v0_text: str) -> str:
    return hashlib.sha256(v0_text.encode("utf-8")).hexdigest()[:12]


def read_v0_snapshot(
    ticker: str, market: str, base: Path | None = None
) -> tuple[str, str, str]:
    """Return (relative_path, hash, body_excerpt) for the current V0, or empty strings."""
    root = Path(base) / "companies" if base else cfg.COMPANIES_DIR
    v0 = root / f"{market}_{ticker}" / "v0.md"
    if not v0.exists():
        return "", "", ""
    text = v0.read_text(encoding="utf-8")
    rel = v0.relative_to(Path(base) if base else cfg.BASE_PATH).as_posix()
    return rel, v0_snapshot_hash(text), text


# --- Frontmatter / body helpers ---------------------------------------------


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm = yaml.safe_load(text[3:end].strip()) or {}
    return fm, text[end + len("\n---") :].lstrip("\n")


def _emit_frontmatter(fm: dict) -> str:
    ordered: dict = {}
    for k in FRONTMATTER_KEYS:
        if k in fm:
            ordered[k] = fm[k]
    for k, v in fm.items():
        if k not in ordered:
            ordered[k] = v
    return "---\n" + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False).rstrip() + "\n---\n"


def split_sections(body: str) -> dict[int, str]:
    matches = list(_SEC_RE.finditer(body))
    out: dict[int, str] = {i: "" for i in range(1, len(SECTIONS) + 1)}
    for i, m in enumerate(matches):
        sec = int(m.group(1))
        if sec not in out:
            continue
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[sec] = body[start:end].rstrip() + "\n"
    return out


def join_sections(sections: dict[int, str], ticker: str, action: str, entry_date: str) -> str:
    parts = [f"# 决策：{ticker} · {action} · {entry_date}\n"]
    for i, title in enumerate(SECTIONS, start=1):
        text = (sections.get(i) or "").strip()
        if text and not text.startswith("## "):
            text = f"## {i}. {title}\n{text}"
        elif not text:
            text = f"## {i}. {title}\n"
        parts.append(text.rstrip() + "\n")
    return "\n".join(parts)


# --- Public CRUD -------------------------------------------------------------


def create_entry(
    entry_date: date_cls,
    ticker: str,
    market: str,
    action: str,
    *,
    price: float = 0,
    position_change: float = 0,
    v0_snapshot_path: str = "",
    v0_snapshot_hash_: str = "",
    v0_body_preview: str = "",
    base: Path | None = None,
) -> JournalPaths:
    """Create a new journal entry with skeleton body. Refuses to overwrite."""
    ticker = ticker.strip().upper()
    paths = build_paths(entry_date, ticker, action, base=base)
    if paths.file_path.exists():
        raise FileExistsError(str(paths.file_path))
    paths.quarter_dir.mkdir(parents=True, exist_ok=True)

    fm: dict[str, Any] = {
        "id": paths.entry_id,
        "date": entry_date.isoformat(),
        "ticker": ticker,
        "market": market,
        "action": action,
        "price": price,
        "position_change": position_change,
        "v0_snapshot_path": v0_snapshot_path or None,
        "v0_snapshot_hash": v0_snapshot_hash_ or None,
        "process_quality": None,
        "process_rigor": None,
        "process_rule_adherence": None,
        "process_emotional_control": None,
        "pnl_3m": None,
        "pnl_6m": None,
        "pnl_12m": None,
        "result_quality": None,
        "result_luck_factor": None,
    }

    # Pre-fill section 2 with a compact V0 snapshot if provided.
    sec2 = ""
    if v0_body_preview:
        sec2 = (
            "（以下为决策时 V0 的 frontmatter + 首段摘要，快照哈希："
            f"`{v0_snapshot_hash_ or 'n/a'}`）\n\n```markdown\n"
            + v0_body_preview[:1200]
            + ("\n…（截断）" if len(v0_body_preview) > 1200 else "")
            + "\n```\n"
        )
    sections = {1: "", 2: sec2, 3: "", 4: "", 5: "", 6: "", 7: "", 8: ""}
    body = join_sections(sections, ticker, action, entry_date.isoformat())

    paths.file_path.write_text(_emit_frontmatter(fm) + "\n" + body, encoding="utf-8")
    return paths


def read_entry(entry_id: str, base: Path | None = None) -> dict:
    d, ticker, action = parse_entry_id(entry_id)
    paths = build_paths(d, ticker, action, base=base)
    if not paths.file_path.exists():
        raise FileNotFoundError(str(paths.file_path))
    fm, body = _split_frontmatter(paths.file_path.read_text(encoding="utf-8"))
    return {
        "frontmatter": fm,
        "body": body,
        "sections": split_sections(body),
        "path": paths.file_path,
    }


def write_entry(entry_id: str, fm: dict, body: str, base: Path | None = None) -> Path:
    d, ticker, action = parse_entry_id(entry_id)
    paths = build_paths(d, ticker, action, base=base)
    paths.quarter_dir.mkdir(parents=True, exist_ok=True)
    paths.file_path.write_text(_emit_frontmatter(fm) + "\n" + body, encoding="utf-8")
    return paths.file_path


def list_entries(
    base: Path | None = None,
    ticker: str | None = None,
    market: str | None = None,
) -> list[dict]:
    """Scan decisions/ and return a summary list sorted by date desc."""
    root = _decisions_root(base)
    if not root.exists():
        return []
    out: list[dict] = []
    for md in root.rglob("*.md"):
        fm, _ = _split_frontmatter(md.read_text(encoding="utf-8"))
        if ticker and str(fm.get("ticker", "")).upper() != ticker.upper():
            continue
        if market and str(fm.get("market", "")).upper() != market.upper():
            continue
        fm["_path"] = str(md)
        out.append(fm)
    out.sort(key=lambda x: str(x.get("date") or ""), reverse=True)
    return out


# --- Bias self-check ---------------------------------------------------------

BIAS_QUESTIONS = (
    ("emotional_tie", "对这家公司有感情吗？（老客户、情怀、个人体验绑定）"),
    ("source_balance", "信息来源平衡吗？还是只读了利好/利空一边？"),
    ("proving_thesis", "是不是在证明自己某个长期观点？"),
    ("swap_test", "如果朋友刚卖掉这只股，我现在会怎么评估？"),
)


def bias_warnings(answers: dict[str, str], reasons: dict[str, str]) -> list[str]:
    """Return list of bias question ids flagged as 'yes' but unexplained.

    Rule (DESIGN §3.5): any 'yes' answered + reasoning too short (<30 chars) →
    flag as "decision paused 24h candidate".
    """
    flagged: list[str] = []
    for qid, _ in BIAS_QUESTIONS:
        if answers.get(qid, "").lower() == "yes":
            if len(reasons.get(qid, "").strip()) < 30:
                flagged.append(qid)
    return flagged
