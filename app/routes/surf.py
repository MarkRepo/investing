"""surf 趋势跟随系统视图 — /surf。

    /surf              卡片状态面板 + 本期 2×2 判定 + 扫描历史 + 黑名单
    /surf/card/{slug}  卡片详情：交易参数、证伪条件清单、正文、指标时间序列、决策日志
    /surf/scan/{date}  扫描详情：摘要、产业扫描原文、各表指标快照

只读消费 `surf/` 下的文件，不写任何东西。证伪条件的触发状态由每周扫描时
写入 card.md 的 frontmatter，本层只负责展示（DESIGN §3 的向前验证留痕）。

与 prism 零代码交叉（DESIGN 附录 B）：不 import prism 任何模块，markdown
渲染在此独立实现一份。
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import markdown as _md
import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR, SURF_DIR

router = APIRouter(prefix="/surf", tags=["surf"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))

_MD_EXTENSIONS = ["tables", "fenced_code", "mdx_truly_sane_lists"]
_FRONTMATTER_RE = re.compile(r"^---\n(?P<fm>.*?)\n---\n", re.DOTALL)

# 扫描目录下的表格文件：文件名 → (标签, 说明)
_SCAN_TABLES = [
    ("cn_etf.csv", "A股 ETF", "候选池指标快照"),
    ("us_etf.csv", "美股 ETF", "候选池指标快照"),
    ("cn_boards.csv", "行业资金流", "同花顺 90 行业 · 5 日"),
    ("cn_board_summary.csv", "行业广度", "同花顺 90 行业 · 当日涨跌家数"),
    ("cn_concepts.csv", "概念资金流", "同花顺 387 概念 · 5 日"),
]


# ---------------------------------------------------------------- 读取

def _split_frontmatter(raw: str) -> tuple[dict, str]:
    """拆出 YAML frontmatter 与正文。无 frontmatter 时返回 ({}, 原文)。"""
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    try:
        fm = yaml.safe_load(m.group("fm")) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, raw[m.end():]


def _render_md(raw: str) -> str:
    return _md.markdown(raw, extensions=_MD_EXTENSIONS)


def _scan_dates() -> list[str]:
    """所有扫描日期，倒序（最新在前）。"""
    d = SURF_DIR / "scans"
    if not d.is_dir():
        return []
    return sorted((x.name for x in d.iterdir() if x.is_dir()), reverse=True)


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    """读 CSV 为 (列名, 行字典)。脚本用 utf-8-sig 写出，带 BOM。"""
    if not path.is_file():
        return [], []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _quote(code: str, date: str) -> dict | None:
    """某期扫描中该标的的指标行。美股 ETF 与 A 股 ETF 代码格式不同，不会撞号。"""
    if not code:
        return None
    for name in ("cn_etf.csv", "us_etf.csv"):
        _, rows = _read_csv(SURF_DIR / "scans" / date / name)
        for r in rows:
            if r.get("代码") == code:
                return r
    return None


def _timeline(code: str) -> list[dict]:
    """该标的在历次扫描中的关键指标，按日期正序。

    数据天然散在各期 scans/*/{cn,us}_etf.csv 中，不额外存储，避免与扫描快照
    产生不一致。只有一期时返回单点，结构照常可用。
    """
    out = []
    for date in reversed(_scan_dates()):
        q = _quote(code, date)
        if not q:
            continue
        out.append({
            "date": date,
            "close": q.get("收盘"),
            "ret5": q.get("ret5"),
            "ret60": q.get("ret60"),
            "rs60": q.get("RS60"),
            "pos": q.get("位置分位"),
            "vol": q.get("量能比"),
            "flow": q.get("板块5日资金净额_亿"),
            "breadth": q.get("板块当日广度_%"),
            "structure": q.get("趋势结构"),
        })
    return out


def _f(v) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _parse_card(path: Path, latest_date: str | None) -> dict:
    """卡片文件 → 渲染所需的全部数据（frontmatter + 正文 + 实时对照）。"""
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    slug = fm.get("slug") or path.parent.name
    trade = fm.get("trade") or {}
    code = (fm.get("ticker") or {}).get("code", "")

    quote = _quote(code, latest_date) if latest_date else None
    cur = _f(quote.get("收盘")) if quote else None
    # 现价缺失时（该标的不在候选池 / 尚未扫描）回落到建卡参考价，
    # 页面标注数据日期，不做实时拉取（周频系统，日内价格无决策意义）。
    cur = cur if cur is not None else _f(trade.get("entry_ref"))

    stop = _f(trade.get("stop_tech")) or _f(trade.get("stop_hard"))
    hard = _f(trade.get("stop_hard"))
    target = _f(trade.get("target"))

    gauge = None
    if cur and stop and target and target > stop:
        gauge = {
            "pct": max(0.0, min(100.0, (cur - stop) / (target - stop) * 100)),
            "to_stop": (cur / stop - 1) * 100,
            "to_hard": (cur / hard - 1) * 100 if hard else None,
            "to_target": (target / cur - 1) * 100,
        }

    fals = fm.get("falsifiers") or []
    log_path = path.parent / "log.md"

    return {
        "fm": fm, "slug": slug,
        "title": fm.get("title", slug),
        "status": fm.get("status", "unknown"),
        "priority": fm.get("priority", ""),
        "stage": fm.get("stage", ""),
        "market": fm.get("market", ""),
        "created": str(fm.get("created", "")),
        "ticker": fm.get("ticker") or {},
        "trade": trade,
        "falsifiers": fals,
        "n_triggered": sum(1 for f in fals if f.get("triggered")),
        "n_falsifiers": len(fals),
        "current": cur,
        "quote": quote,
        "gauge": gauge,
        "body_html": _render_md(body),
        "log_html": _render_md(log_path.read_text(encoding="utf-8")) if log_path.is_file() else "",
    }


def _load_cards(latest_date: str | None) -> list[dict]:
    d = SURF_DIR / "cards"
    if not d.is_dir():
        return []
    cards = [_parse_card(p / "card.md", latest_date)
             for p in sorted(d.iterdir()) if (p / "card.md").is_file()]
    # 在跟的排前，其次按优先级，最后按建卡日期倒序
    order = {"following": 0, "watching": 1, "exited": 2}
    cards.sort(key=lambda c: (order.get(c["status"], 9),
                              0 if c["priority"] == "primary" else 1,
                              c["created"]), reverse=False)
    return cards


def _load_yaml(path: Path):
    if not path.is_file():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None


def _scan_headline(date: str) -> str:
    m = _load_yaml(SURF_DIR / "scans" / date / "matrix.yaml")
    return (m or {}).get("headline", "")


# ---------------------------------------------------------------- 路由

@router.get("")
def surf_index(request: Request):
    dates = _scan_dates()
    latest = dates[0] if dates else None
    return templates.TemplateResponse(request, "surf/index.html", {
        "cards": _load_cards(latest),
        "matrix": _load_yaml(SURF_DIR / "scans" / latest / "matrix.yaml") if latest else None,
        "blacklist": _load_yaml(SURF_DIR / "blacklist.yaml") or [],
        "scans": [{"date": d, "headline": _scan_headline(d)} for d in dates],
        "latest": latest,
    })


@router.get("/card/{slug}")
def surf_card(slug: str, request: Request):
    path = SURF_DIR / "cards" / slug / "card.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"卡片不存在：{slug}")
    dates = _scan_dates()
    latest = dates[0] if dates else None
    card = _parse_card(path, latest)
    return templates.TemplateResponse(request, "surf/card.html", {
        "card": card,
        "timeline": _timeline((card["ticker"] or {}).get("code", "")),
        "latest": latest,
    })


@router.get("/scan/{date}")
def surf_scan(date: str, request: Request):
    d = SURF_DIR / "scans" / date
    if not d.is_dir():
        raise HTTPException(status_code=404, detail=f"扫描不存在：{date}")

    docs = []
    for fname, label in (("summary.md", "技术佐证与 2×2 判定"),
                         ("channel_A_industry_scan.md", "通道 A 产业扫描原文")):
        f = d / fname
        if f.is_file():
            docs.append({"key": fname, "label": label,
                         "html": _render_md(f.read_text(encoding="utf-8"))})

    tables = []
    for fname, label, desc in _SCAN_TABLES:
        cols, rows = _read_csv(d / fname)
        if rows:
            tables.append({"key": fname, "label": label, "desc": desc,
                           "cols": cols, "rows": rows, "n": len(rows)})

    return templates.TemplateResponse(request, "surf/scan.html", {
        "date": date,
        "docs": docs,
        "tables": tables,
        "matrix": _load_yaml(d / "matrix.yaml"),
        "scans": _scan_dates(),
    })
