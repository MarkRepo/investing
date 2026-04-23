"""Self-discipline dashboard: surface the patterns you'd rather not look at.

DESIGN §8 坑 3 / §9 成功标准:
- 无 V0 快照买入 (borrowed conviction without a written commitment)
- 情绪卖出 (selling for reasons listed in V0 "什么不算推翻")
- 季度复盘跳过 (连续 2 个季度缺失 → "要不要买指数基金"的硬提示)

These metrics live in the journal but get lost in the per-decision view; this
module aggregates them so they become impossible to ignore.
"""
from __future__ import annotations

from datetime import date as date_cls
from pathlib import Path

from app import config as cfg
from app.io import journal as journal_io
from app.io import review as review_io

# Keywords that flag "this reason is on the V0 noise list" (DESIGN §3.2 §6).
# Matched against Chinese reasoning prose in journal section 5 (支撑理由).
NOISE_KEYWORDS = (
    "利率", "美联储", "央行", "加息", "降息",
    "地缘政治", "战争",
    "vix", "恐慌", "恐慌指数",
    "cpi", "ppi", "通胀",
    "宏观", "板块轮动",
    "新闻", "消息面",
)

BUY_ACTIONS = ("buy", "add")
SELL_ACTIONS = ("sell", "trim")


def no_v0_snapshot_buys(base: Path | None = None) -> list[dict]:
    """Every buy/add that didn't snapshot a V0 — borrowed conviction.

    Returns entries sorted by date desc.
    """
    out: list[dict] = []
    for fm in journal_io.list_entries(base=base):
        if fm.get("action") not in BUY_ACTIONS:
            continue
        if fm.get("v0_snapshot_path"):
            continue
        out.append(fm)
    return out


def emotional_sells(base: Path | None = None) -> list[dict]:
    """Every sell/trim whose body contains V0-noise keywords.

    The check is lossy by design — a keyword hit is "maybe emotional," not
    proof. The point is to surface them for review, not to automate judgement.
    """
    out: list[dict] = []
    root = (Path(base) / "journal" / "decisions") if base else (cfg.JOURNAL_DIR / "decisions")
    if not root.exists():
        return out
    for fm in journal_io.list_entries(base=base):
        if fm.get("action") not in SELL_ACTIONS:
            continue
        path = fm.get("_path")
        if not path:
            continue
        try:
            text = Path(path).read_text(encoding="utf-8").lower()
        except OSError:
            continue
        hits = [kw for kw in NOISE_KEYWORDS if kw in text]
        if hits:
            out.append({**fm, "_noise_hits": hits})
    return out


def _quarter_range(start_year: int, end_year: int) -> list[str]:
    qs: list[str] = []
    for y in range(start_year, end_year + 1):
        for q in (1, 2, 3, 4):
            qs.append(f"{y}-Q{q}")
    return qs


def review_gaps(today: date_cls | None = None, base: Path | None = None) -> dict:
    """Report which recent quarters lack a quarterly-review file.

    A quarter counts as "reviewed" if ``journal/quarterly-reviews/{Q}.md`` exists.

    Returns:
        {
          "recent": [{quarter, reviewed, is_current}],  # most recent 6 quarters
          "consecutive_missing": N,  # count of most recent closed quarters missing
          "red_flag": bool,  # consecutive_missing >= 2 → DESIGN §8 坑 6
        }
    """
    t = today or date_cls.today()
    reviews_dir = (
        (Path(base) / "journal" / "quarterly-reviews")
        if base else (cfg.JOURNAL_DIR / "quarterly-reviews")
    )
    present = {p.stem for p in reviews_dir.glob("*.md")} if reviews_dir.exists() else set()

    current = review_io.quarter_key(t)
    # Build last 6 quarters (most recent first) up to and including current
    cy, cq = (int(x) for x in current.replace("Q", "").split("-"))
    recent: list[dict] = []
    y, q = cy, cq
    for _ in range(6):
        qkey = f"{y}-Q{q}"
        recent.append({
            "quarter": qkey,
            "reviewed": qkey in present,
            "is_current": qkey == current,
        })
        q -= 1
        if q == 0:
            q = 4
            y -= 1

    # Count consecutive missing among CLOSED quarters (skip the current one)
    consecutive = 0
    for item in recent:
        if item["is_current"]:
            continue
        if item["reviewed"]:
            break
        consecutive += 1

    return {
        "recent": recent,
        "consecutive_missing": consecutive,
        "red_flag": consecutive >= 2,
    }


def summary(today: date_cls | None = None, base: Path | None = None) -> dict:
    """Top-level dashboard payload."""
    no_v0 = no_v0_snapshot_buys(base=base)
    emo = emotional_sells(base=base)
    gaps = review_gaps(today=today, base=base)
    return {
        "no_v0_count": len(no_v0),
        "no_v0_entries": no_v0,
        "emotional_sell_count": len(emo),
        "emotional_sell_entries": emo,
        "review_gaps": gaps,
        "noise_keywords": list(NOISE_KEYWORDS),
    }
