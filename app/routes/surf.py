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
from markdown.extensions.toc import slugify_unicode as _toc_slugify_unicode
import yaml
from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR, SURF_DIR

router = APIRouter(prefix="/surf", tags=["surf"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))

_MD_EXTENSIONS = ["tables", "fenced_code", "mdx_truly_sane_lists", "toc"]
# 默认 slugify 走 ASCII 化，中文标题会被整段剥空 —— 「## 1. 本次数据质量问题」→ id "1"，
# 「### 左上角 · 出手」→ 空串退化成 "_1"，锚点既不可读又极易碰撞。
_MD_CONFIGS = {"toc": {"slugify": _toc_slugify_unicode, "anchorlink": False}}
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
    return _md.markdown(raw, extensions=_MD_EXTENSIONS, extension_configs=_MD_CONFIGS)


def _render_doc(raw: str, prefix: str = "") -> tuple[str, list[dict]]:
    """渲染长文档，同时取出 h2/h3 目录。

    扫描 summary 五百多行、卡片 log 同量级，整篇平铺只能靠滚轮找章节。
    `markdown.markdown()` 每次新建实例，toc 拿不回来，所以这里显式建实例再读
    `toc_tokens`。h4 以下不进目录——再深就不是导航而是正文复制。

    `prefix` 给锚点加前缀：同一页渲染多篇（扫描页两个 tab、卡片页正文+日志）时，
    toc 扩展只在**单个实例内**去重，跨篇同名标题会撞 id，点目录跳到另一篇去。
    """
    cfg = {"toc": {**_MD_CONFIGS["toc"],
                   "slugify": lambda v, sep: prefix + _toc_slugify_unicode(v, sep)}}
    md = _md.Markdown(extensions=_MD_EXTENSIONS, extension_configs=cfg)
    html = md.convert(raw)
    toc: list[dict] = []

    def _walk(tokens: list) -> None:
        # 按 token 自报的 level 过滤，不靠嵌套深度——文档有没有 h1 标题会让深度整体位移
        for t in tokens:
            if t["level"] in (2, 3):
                toc.append({"id": t["id"], "name": t["name"], "level": t["level"]})
            _walk(t.get("children") or [])

    _walk(getattr(md, "toc_tokens", []))
    return html, toc


def _scan_dates() -> list[str]:
    """**完整扫描**的日期，倒序（最新在前）。

    判据是有 `matrix.yaml` 或 `summary.md` —— 即通道 A 跑过、2×2 填过。
    只跑了候选池构建（`scan_cn.py fetch/finalize`）而没做产业判定的目录不算一期扫描，
    否则首页会把它当成最新一期，2×2 与 headline 全部变空。
    """
    d = SURF_DIR / "scans"
    if not d.is_dir():
        return []
    return sorted((x.name for x in d.iterdir() if x.is_dir()
                   and ((x / "matrix.yaml").is_file() or (x / "summary.md").is_file())),
                  reverse=True)


def _data_dates() -> list[str]:
    """有 ETF 指标数据的日期，倒序。是 `_scan_dates()` 的超集——
    候选池已重建但产业判定未做的期次也在内，指标时间序列要用它，不能漏掉。
    """
    d = SURF_DIR / "scans"
    if not d.is_dir():
        return []
    return sorted((x.name for x in d.iterdir() if x.is_dir()
                   and ((x / "cn_etf.csv").is_file() or (x / "us_etf.csv").is_file())),
                  reverse=True)


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


def _latest_quotes() -> dict[str, dict]:
    """`surf/latest_quotes.csv` → {代码: 行}。

    由 `surf/scripts/refresh_quotes.py` 生成，与 scans/ 的扫描快照分开：
    快照是向前验证的历史记录，不可改；但「距止损还有多远」必须用最新收盘价算
    （扫描 #001 建卡时新浪当日数据未发布，快照停在建卡日前一天）。
    仍只取收盘价，不取盘中（DESIGN §10.1）。
    """
    _, rows = _read_csv(SURF_DIR / "latest_quotes.csv")
    return {r["代码"]: r for r in rows if r.get("代码")}


def _cn_market(code: str) -> str:
    """A 股代码 → 交易所代码，与 /prices、/financials 的 URL 前缀一致。"""
    if code[:2] in ("60", "68") or code[:1] == "9":
        return "SSE"
    if code[:1] in ("0", "3"):
        return "SZSE"
    return "BSE"


def _linkable() -> set[str]:
    """能跳 /prices 与 /financials 的标的集合（形如 SSE_600276）。

    这两个页面的可跳转集合完全由 prism 的 company 主题决定（`companies/` 目录
    为空时全靠 topic 兜底），surf 的趋势股绝大多数不在其中，点进去是 404。
    故只对已覆盖的给链接 —— 链接的有无本身就指示「这只有没有做过基本面功课」。

    走 `app.io.company` 这层共用数据适配器，不 import prism（DESIGN 附录 B）。
    """
    try:
        from app.io import company as company_io
        return {c["key"] for c in company_io.list_companies()}
    except Exception:
        return set()


def _stock_key(code: str, market: str) -> str:
    """个股 → /prices/{key} 的 key。港股代码在 companies 里是 5 位带前导零。"""
    if market == "US":
        return f"US_{code}"
    if market == "HK":
        return f"HKEX_{code.zfill(5)}"
    return f"{_cn_market(code)}_{code}"


def _timeline(code: str) -> list[dict]:
    """该标的在历次扫描中的关键指标，按日期正序。

    数据天然散在各期 scans/*/{cn,us}_etf.csv 中，不额外存储，避免与扫描快照
    产生不一致。只有一期时返回单点，结构照常可用。
    """
    out = []
    for date in reversed(_data_dates()):
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


def _parse_card(path: Path, latest_date: str | None,
                lq: dict[str, dict] | None = None,
                linkable: set[str] | None = None) -> dict:
    """卡片文件 → 渲染所需的全部数据（frontmatter + 正文 + 实时对照）。"""
    fm, body = _split_frontmatter(path.read_text(encoding="utf-8"))
    slug = fm.get("slug") or path.parent.name
    trade = fm.get("trade") or {}
    code = (fm.get("ticker") or {}).get("code", "")

    lq = lq if lq is not None else _latest_quotes()
    linkable = linkable if linkable is not None else _linkable()

    quote = _quote(code, latest_date) if latest_date else None
    snap = _f(quote.get("收盘")) if quote else None
    snap_date = (quote or {}).get("日期") or latest_date

    # 取价优先级：latest_quotes.csv（最新收盘）→ 扫描快照 → 建卡参考价。
    # 不做实时拉取（周频系统，日内价格无决策意义，DESIGN §10.1）。
    fresh = lq.get(code)
    cur, cur_date, cur_src = None, None, ""
    if fresh:
        cur, cur_date, cur_src = _f(fresh.get("收盘")), fresh.get("日期"), "最新收盘"
    if cur is None and snap is not None:
        cur, cur_date, cur_src = snap, snap_date, "扫描快照"
    if cur is None:
        cur, cur_date, cur_src = _f(trade.get("entry_ref")), "", "建卡参考价"

    entry = _f(trade.get("entry_ref"))
    # 建卡参考价与最新收盘的偏移。扫描 #001 两张卡片都因新浪当日数据未发布
    # 而冻结在建卡日前一天，追入会把单笔风险放大到设计区间之外，必须显式提示。
    drift = (cur / entry - 1) * 100 if cur and entry else None

    # 操作止损 = 两道里**先触发**的那道，即价位更高的那个。
    # 两张卡片方向相反：医药 ma60(0.8900) 紧于硬止损(0.8823)，美股软件反过来
    # ma60(98.60) 紧于硬止损(96.00)。只写「距止损」会被读成硬止损，故取 max
    # 并标明是哪一道（首页与卡片页同一口径）。
    tech = _f(trade.get("stop_tech"))
    hard = _f(trade.get("stop_hard"))
    stop = max(x for x in (tech, hard) if x is not None) if (tech or hard) else None
    stop_label = "ma60" if (tech is not None and stop == tech) else "硬止损"
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
    stocks = []
    for s in fm.get("stocks") or []:
        s = dict(s)
        key = _stock_key(str(s.get("code", "")), s.get("market", "CN"))
        s["key"] = key
        # prism 未覆盖的标的不给链接 —— /prices/{key} 会 404，见 _linkable()
        s["linked"] = key in linkable
        q = lq.get(str(s.get("code", "")))
        s["last_close"] = _f(q.get("收盘")) if q else None
        s["last_date"] = (q or {}).get("日期")
        sp = _f(s.get("stop_price"))
        s["to_stop"] = (s["last_close"] / sp - 1) * 100 if s["last_close"] and sp else None
        stocks.append(s)
    log_path = path.parent / "log.md"
    body_html, body_toc = _render_doc(body, prefix="b-")
    log_html, log_toc = (_render_doc(log_path.read_text(encoding="utf-8"), prefix="l-")
                         if log_path.is_file() else ("", []))

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
        # 个股增强层（DESIGN §6.5）。verdict: follow 进交易清单，watch 观察池，
        # reject 已否定。tradable=false 是港股，只展示卡位，不可交易。
        "stocks": stocks,
        "stocks_follow": [s for s in stocks if s.get("verdict") == "follow"],
        "stocks_watch": [s for s in stocks if s.get("verdict") in ("watch", "reject")],
        "prism_refs": fm.get("prism_refs") or [],
        "stop_op": stop,
        "stop_op_label": stop_label,
        "risk_pct": (cur / stop - 1) * 100 if cur and stop else None,
        "current": cur,
        "current_date": cur_date,
        "current_src": cur_src,
        "entry_ref": entry,
        "drift": drift,
        "quote": quote,
        "gauge": gauge,
        "body_html": body_html, "body_toc": body_toc,
        "log_html": log_html, "log_toc": log_toc,
    }


def _load_cards(latest_date: str | None) -> list[dict]:
    d = SURF_DIR / "cards"
    if not d.is_dir():
        return []
    # 两个共用查询各算一次，不在卡片循环里重复做
    lq, linkable = _latest_quotes(), _linkable()
    cards = [_parse_card(p / "card.md", latest_date, lq, linkable)
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


# ---------------------------------------------------------------- 候选池漏斗

# 过滤原因码 -> (展示名, 一句话解释)。顺序即页面展示顺序。
_FILTER_LABELS = {
    "asset_class": ("资产类别", "货币/债券/商品/宽基指数——规则层剔除，这些是硬事实"),
    "not_carrier": ("非趋势载体", "成分按财务特征/所有制/套利聚合而非按产业，LLM 层判定"),
    "illiquid": ("流动性不足", "成交额或规模低于门槛"),
    "dedup": ("同主题折叠", "同一主题只留成交额最大的一只作代表，被折叠的不代表被否定"),
    "fetch_failed": ("抓取失败", "数据源无历史或样本不足"),
}

# 2×2 非左上角格子 -> (判定名, 下期动作)。左上角走「建卡」不在此表。
_VERDICTS = {
    "too_early": ("逻辑成立·技术未确认", "重点复看，二波可能从这里来"),
    "speculation": ("纯炒作", "入黑名单，满足重评条件才复看"),
    "ignore": ("忽略", "低频复看"),
}


def _universe_dates() -> list[str]:
    """有候选池留痕的扫描日。扫描 #001 早于本机制，不在其中。"""
    root = SURF_DIR / "scans"
    if not root.is_dir():
        return []
    out = [d.name for d in root.iterdir()
           if (d / "universe_cn.csv").is_file() or (d / "universe_us.csv").is_file()]
    return sorted(out, reverse=True)


def _latest_matrix(date: str) -> tuple[dict | None, str | None]:
    """取本期 matrix.yaml；本期还没判（通道 A 未跑）时回落到最近一期，并回报其日期。"""
    for d in [date] + _scan_dates():
        m = _load_yaml(SURF_DIR / "scans" / d / "matrix.yaml")
        if m:
            return m, d
    return None, None


def _theme_verdicts(matrix: dict | None) -> dict[str, dict]:
    """主题键 -> 判定。左上角(follow)的主题标 card，其余标 verdict。"""
    out: dict[str, dict] = {}
    for cell, items in ((matrix or {}).get("cells", {}) or {}).items():
        for it in items or []:
            # 同向但未选作载体：判过了，只是没买它——和「没看过」「看过否了」都不同
            for th in it.get("themes_covered") or []:
                out[th] = {"kind": "verdict", "label": "同向·未选作载体",
                           "name": it.get("name"), "card": it.get("card"),
                           "note": "与已建卡方向同向，技术层比较后未选它作载体",
                           "next": "跟踪相对强弱，若持续跑赢现载体则考虑换仓"}
            for th in it.get("themes") or []:
                if cell == "follow":
                    out[th] = {"kind": "card", "label": "已建卡", "name": it.get("name"),
                               "card": it.get("card"), "note": it.get("note", ""),
                               "next": "每周核对证伪条件"}
                    continue
                else:
                    label, nxt = _VERDICTS.get(cell, (cell, ""))
                    if it.get("stage_error"):
                        label, nxt = "阶段错", "观察是否回调后走二波"
                    out[th] = {"kind": "verdict", "label": label, "name": it.get("name"),
                               "card": None, "note": it.get("note", ""), "next": nxt}
    return out


def _theme_scope() -> tuple[dict[str, dict], list[dict]]:
    """读 `surf/theme_scope.yaml`：主题键 -> 所属不覆盖组，以及组清单。

    这些主题**不是本期没看**，是本系统的框架对它们不适用（金融的驱动力是利率、
    行业容器不按产业聚合）。混在「未判定」里会每期逼人重新纠结一次，
    同时把覆盖率人为做低。
    """
    cfg = _load_yaml(SURF_DIR / "theme_scope.yaml") or {}
    groups = cfg.get("groups") or []
    idx = {th: {"id": g.get("id"), "label": g.get("label"), "why": g.get("why", "")}
           for g in groups for th in (g.get("themes") or [])}
    return idx, groups


# 技术层四条「值得看一眼」的信号。一条都不中 = 没有任何判据在喊我，
# 归入「技术层零支持」折叠起来；中了任意一条就留在「真·未讨论」里，欠着要交代。
# ⚠️ 这是**分诊**不是判定：中了信号不代表该跟，只代表不该无声跳过。
_SIGNAL_NAMES = ("多头排列", "RS5≥60", "放量", "中期强且在高位")


def _vol_gate(themes: list[dict]) -> float:
    """「放量」的门槛取池内 75 分位，不用固定 1.0。

    2026-09-22 实测：A 股池 `量能比` 中位 0.64、美股 0.96——同一个 1.0 在 A 股是
    p90、在美股是 p53，严格度差一个数量级，固定阈值等于对两个市场用两把尺子。
    RS 本来就是池内百分位，量能也按池内相对口径才自洽。
    下限仍压在 1.0：全池缩量时 0.79 不该被叫做「放量」。
    """
    vals = sorted(v for v in (_f(t["vol"]) for t in themes) if v is not None)
    if not vals:
        return 1.0
    return max(1.0, round(vals[int(len(vals) * 0.75)], 2))


def _tech_signals(t: dict, vol_gate: float) -> list[str]:
    hits = [
        t["structure"] == "多头排列",
        (_f(t["rs5"]) or 0) >= 60,
        (_f(t["vol"]) or 0) >= vol_gate,
        # RS60 单独用会把「跌得比别人少」的防御板块误判成趋势（本期 A 股消费系
        # RS60 全部 70+ 但位置分位不到 20），所以必须与位置分位同看
        (_f(t["rs60"]) or 0) >= 60 and (_f(t["pos"]) or 0) >= 60,
    ]
    return [n for n, h in zip(_SIGNAL_NAMES, hits) if h]


def _universe_block(date: str, mkt: str, verdicts: dict[str, dict],
                    scope: dict[str, dict]) -> dict | None:
    """把一个市场的候选池整理成漏斗六段。

    建卡 / 判定淘汰 / **不覆盖** / **真·未讨论** / **技术层零支持** / 入池前剔除。

    中间三段原先是一个笼统的「未判定」，三类完全不同性质的东西混在一起：
    框架不适用的、技术判据全否的、和真正欠着没交代的。#002 的 57 个未判定里
    只有个位数属于最后一类，混着看就看不出来了。
    """
    d = SURF_DIR / "scans" / date
    _, rows = _read_csv(d / f"universe_{mkt}.csv")
    if not rows:
        return None
    _, pool = _read_csv(d / f"{mkt}_etf.csv")

    # 入池的按主题归拢；一个主题一行（代表标的 + 指标），再挂上判定结果
    themes: dict[str, dict] = {}
    for r in pool:
        th = r.get("主题") or "未判定"
        if th.startswith("基准"):   # SPY/QQQ 是参照系不是候选方向
            continue
        # 判定键带市场前缀，「软件」在两个池子里都有
        v = verdicts.get(f"{mkt}:{th}")
        themes[th] = {
            "theme": th, "code": r.get("代码"), "name": r.get("名称"),
            "ret5": r.get("ret5"), "ret20": r.get("ret20"), "ret60": r.get("ret60"),
            "rs5": r.get("RS5"), "rs60": r.get("RS60"), "pos": r.get("位置分位"),
            "structure": r.get("趋势结构"), "vol": r.get("量能比"),
            "verdict": v,
        }
    ordered = sorted(themes.values(),
                     key=lambda x: -float(x["rs5"] or 0))

    carded = [t for t in ordered if t["verdict"] and t["verdict"]["kind"] == "card"]
    judged = [t for t in ordered if t["verdict"] and t["verdict"]["kind"] == "verdict"]

    # 未判定再分三档，见 docstring
    vol_gate = _vol_gate(ordered)
    out_scope, unjudged, silent = [], [], []
    for t in ordered:
        if t["verdict"]:
            continue
        sc = scope.get(f"{mkt}:{t['theme']}")
        if sc:
            t["scope"] = sc
            out_scope.append(t)
            continue
        t["signals"] = _tech_signals(t, vol_gate)
        (unjudged if t["signals"] else silent).append(t)
    out_scope.sort(key=lambda t: (t["scope"]["id"], -(_f(t["rs60"]) or 0)))

    # 入池前剔除，按原因分组
    groups: dict[str, list] = {}
    for r in rows:
        why = (r.get("剔除原因") or "").strip()
        if not why:
            continue
        groups.setdefault(why, []).append(
            {"code": r.get("代码"), "name": r.get("名称"), "note": r.get("剔除说明") or ""})
    filtered = [{"code": k, "label": _FILTER_LABELS.get(k, (k, ""))[0],
                 "desc": _FILTER_LABELS.get(k, (k, ""))[1],
                 "rows": sorted(v, key=lambda x: x["code"])}
                for k, v in sorted(groups.items(),
                                   key=lambda kv: list(_FILTER_LABELS).index(kv[0])
                                   if kv[0] in _FILTER_LABELS else 99)]

    return {
        "market": mkt, "n_raw": len(rows), "n_pool": len(pool), "n_theme": len(themes),
        "carded": carded, "judged": judged, "unjudged": unjudged,
        "out_scope": out_scope, "silent": silent,
        # 覆盖率分母剔掉不覆盖的那批——那不是漏，是框架不适用
        "n_scoped": len(themes) - len(out_scope),
        "n_done": len(carded) + len(judged),
        "vol_gate": vol_gate,
        "filtered": filtered, "n_filtered": sum(len(g["rows"]) for g in filtered),
    }


# ---------------------------------------------------------------- 路由

@router.get("")
def surf_index(request: Request):
    dates = _scan_dates()
    latest = dates[0] if dates else None
    # 价格回落用最新有指标数据的一期（可能晚于最近一次完整扫描）
    px = (_data_dates() or [latest])[0]
    return templates.TemplateResponse(request, "surf/index.html", {
        "cards": _load_cards(px),
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
    px = (_data_dates() or [latest])[0]
    card = _parse_card(path, px, _latest_quotes(), _linkable())
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
    for i, (fname, label) in enumerate((("summary.md", "技术佐证与 2×2 判定"),
                                        ("channel_A_industry_scan.md", "通道 A 产业扫描原文")), 1):
        f = d / fname
        if f.is_file():
            html, toc = _render_doc(f.read_text(encoding="utf-8"), prefix=f"d{i}-")
            docs.append({"key": fname, "label": label, "html": html, "toc": toc})

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


@router.get("/universe")
@router.get("/universe/{date}")
def surf_universe(request: Request, date: str | None = None):
    dates = _universe_dates()
    if not dates:
        raise HTTPException(status_code=404, detail="尚无候选池留痕，先跑一次 scan_cn.py fetch")
    date = date or dates[0]
    if date not in dates:
        raise HTTPException(status_code=404, detail=f"该期无候选池留痕：{date}")

    matrix, m_date = _latest_matrix(date)
    verdicts = _theme_verdicts(matrix)
    scope, scope_groups = _theme_scope()
    blocks = [b for b in (_universe_block(date, "cn", verdicts, scope),
                          _universe_block(date, "us", verdicts, scope)) if b]
    return templates.TemplateResponse(request, "surf/universe.html", {
        "date": date, "dates": dates, "blocks": blocks,
        "scope_groups": scope_groups,
        "signal_names": list(_SIGNAL_NAMES),
        "matrix_date": m_date, "matrix_stale": m_date != date,
        "labels": {"cn": "A 股", "us": "美股"},
    })
