"""按 SEC 10-K / 10-Q 标准 Item 模版切片 htm，输出 section markdown + 元数据。

设计意图（成本优化）：SEC htm 一份 3-7MB（~50-100k tokens），其中 30-50% 是
TOC/封面/法律声明/高管薪酬/Exhibits 等下游不需要的噪声。按 Item 锚点切片后，
下游 workflow 03/04 按 K# 只读对应 section，typical 节省 60-70% token。

10-K Item 锚点（17 CFR 229 强制）：
    Item 1   Business                       → 业务全景 / 03 叙事
    Item 1A  Risk Factors                   → 06 风险
    Item 7   MD&A                           → 02 周期 / 04 估值
    Item 7A  Quantitative & Qual Risk       → 06 风险
    Item 8   Financial Statements           → 04 估值 / 06 财务风险
    其余 Item 默认丢弃（可选保留 Item 3 Legal / Item 9A Controls）

10-Q 结构：
    Part I  Item 1  Financial Statements    → 04 估值
            Item 2  MD&A                    → 02 / 04 / catalyst
            Item 3  Quantitative Risk       → 06
    Part II Item 1A Risk Factors (changes)  → 06
    其余 Item 默认丢弃

输出布局：
    materials/sec/{ticker}_{form}_{filing_date}/
        ├── _meta.yaml                    # split_ok / sections 列表 / 字数
        ├── item_1_business.md
        ├── item_1a_risk.md
        ├── item_7_mda.md
        ├── item_7a_quant_risk.md
        └── item_8_financial.md

CLI:
    python3 -m prism.scripts.sec_section_split path/to/HOOD_10-K.htm
    python3 -m prism.scripts.sec_section_split --dir prism/topics/us-robinhood/materials
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup

log = logging.getLogger("sec_section_split")

# Item → 输出文件名（按 K# 用途命名，方便下游记忆）
_10K_SECTIONS = {
    "1":   "item_1_business",
    "1A":  "item_1a_risk",
    "7":   "item_7_mda",
    "7A":  "item_7a_quant_risk",
    "8":   "item_8_financial",
}

_10Q_SECTIONS = {
    "PartI_1":  "item_1_financial",   # Part I 第一节（财报，常无显式 Item 1 标题）
    "PartI_2":  "item_2_mda",
    "PartI_3":  "item_3_quant_risk",
    "PartII_1A": "item_1a_risk",
}

# Item → 默认 addresses 标签（下游 workflow 03 抽 finding 时按 K# 选 section）
_10K_DEFAULT_ADDRESSES = {
    "item_1_business":   ["scope", "Q1", "K3", "K5"],
    "item_1a_risk":      ["risk", "K1", "K6"],
    "item_7_mda":        ["Q1", "K2", "K4", "K5"],
    "item_7a_quant_risk": ["risk", "K2"],
    "item_8_financial":  ["valuation", "Q1"],
}
_10Q_DEFAULT_ADDRESSES = {
    "item_1_financial":  ["valuation", "Q1"],
    "item_2_mda":        ["Q1", "K2", "K5"],
    "item_3_quant_risk": ["risk", "K2"],
    "item_1a_risk":      ["risk", "K1", "K6"],
}

# 20-F (外国发行人年报，类比 10-K)：核心 5 个 Item
# Item 3  Key Information (含 Item 3.D Risk Factors)
# Item 4  Information on the Company (Business)
# Item 5  Operating and Financial Review (MD&A)
# Item 11 Quantitative & Qualitative Risk
# Item 18 Financial Statements
_20F_SECTIONS = {
    "3":  "item_3_key_info",
    "4":  "item_4_business",
    "5":  "item_5_mda",
    "11": "item_11_quant_risk",
    "18": "item_18_financial",
}
_20F_DEFAULT_ADDRESSES = {
    "item_3_key_info":    ["risk", "K1", "K6"],
    "item_4_business":    ["scope", "Q1", "K3", "K5"],
    "item_5_mda":         ["Q1", "K2", "K4", "K5"],
    "item_11_quant_risk": ["risk", "K2"],
    "item_18_financial":  ["valuation", "Q1"],
}

_ITEM_RE = re.compile(r"^\s*ITEM\s+(\d{1,2}[A-Z]?)\b", re.IGNORECASE)
# Part 锚点必须独立成行（不能是 "Part I, Item 1" 这种 cross-reference）。
# 后续字符必须是空白/句点/破折号/冒号/行尾——明确拒绝逗号。
_PART_RE = re.compile(r"^\s*PART\s+(I|II|III|IV)(?=\s|\.|$|[\-—:])", re.IGNORECASE)
_LETTER_RE = re.compile(r"[A-Za-z]")


def _line_has_title(line: str, item_id: str) -> bool:
    """判断 'ITEM N. ...' 行是否是 body 锚点（标题非空），而非 TOC 桩条。

    TOC stubs 形如 'ITEM 1.' 或 'ITEM 1A'，body 形如 'ITEM 1. BUSINESS' /
    'ITEM 7. MANAGEMENT'S DISCUSSION...'。
    标准：去掉 'ITEM N.' 后剩余文本含字母且 ≥ 2 字符。
    """
    s = line.strip()
    m = re.match(
        r"^\s*ITEM\s+" + re.escape(item_id) + r"\.?\s*(.*?)\s*$",
        s,
        re.IGNORECASE,
    )
    if not m:
        return False
    tail = m.group(1).strip()
    return len(tail) >= 2 and bool(_LETTER_RE.search(tail))


def _line_part_has_title(line: str) -> bool:
    """判断 'PART I/II ...' 是 body 还是 TOC 桩。同上：剩余文本 ≥ 2 字母字符。"""
    s = line.strip()
    m = re.match(r"^\s*PART\s+(I|II|III|IV)\.?\s*[\-—:]?\s*(.*?)\s*$", s, re.IGNORECASE)
    if not m:
        return False
    tail = m.group(2).strip()
    return len(tail) >= 2 and bool(_LETTER_RE.search(tail))


def _detect_form(filename: str) -> str | None:
    """从文件名提取 form 类型。约定：{year}_{ticker}_{form}_{date}.htm"""
    parts = Path(filename).stem.split("_")
    for p in parts:
        u = p.upper()
        if u in {"10-K", "10-Q", "20-F", "6-K", "40-F"}:
            return u
    return None


def _extract_lines(htm_path: Path) -> list[str]:
    raw = htm_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")
    # 去掉 script/style 噪声
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n")
    return [l for l in text.split("\n") if l.strip()]


def _find_item_anchors(lines: list[str]) -> list[tuple[int, str]]:
    """返回 [(lineno, item_id), ...]，按 lineno 升序。"""
    hits: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if len(s) > 250:
            continue
        m = _ITEM_RE.match(s)
        if m:
            hits.append((i, m.group(1).upper()))
    return hits


def _find_part_anchors(lines: list[str]) -> list[tuple[int, str]]:
    """10-Q 用 Part I/II 划分。返回 [(lineno, 'I'|'II'|...), ...]，按 lineno 升序。"""
    hits = []
    for i, line in enumerate(lines):
        s = line.strip()
        if len(s) > 200:
            continue
        m = _PART_RE.match(s)
        if m:
            hits.append((i, m.group(1).upper()))
    return hits


def _item_rank(item_id: str) -> tuple[int, int]:
    """把 item_id 映射成可比较的规范序 rank：'1'→(1,0), '1A'→(1,1), '7A'→(7,1)。

    SEC Item 编号规范顺序 = (数字, 字母后缀序)。字母后缀 A=1, B=2, …；无后缀=0。
    body 段落一定按此 rank 单调递增出现，cross-reference 会打乱顺序——正是 LIS 用来
    甄别 body vs cross-ref 的依据。
    """
    m = re.match(r"(\d+)([A-Z]*)", item_id.upper())
    if not m:
        return (999, 0)
    num = int(m.group(1))
    suffix = m.group(2)
    suf_rank = 0
    for ch in suffix:
        suf_rank = suf_rank * 26 + (ord(ch) - ord("A") + 1)
    return (num, suf_rank)


def _lis_by_rank(anchors: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """从按行号升序的 (lineno, item_id) 中取**规范序严格递增的最长子序列 (LIS)**。

    真 body 段落一定按 Item 规范序单调递增；cross-reference（如 MD&A 里回指
    "Item 1A. Risk Factors"）会出现在乱序位置、破坏单调性，因此不会进入 LIS，被自动剔除。
    同一 item 的多次 title 出现（页眉重复），LIS 只保留能延续最长递增链的那一个
    （通常即真 body 位置）。O(n²)，n≤~50，可忽略。
    """
    n = len(anchors)
    if n == 0:
        return []
    ranks = [_item_rank(item) for _, item in anchors]
    # dp[i] = 以 i 结尾的最长严格递增链长度；prev[i] = 前驱下标
    dp = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if ranks[j] < ranks[i] and dp[j] + 1 > dp[i]:
                dp[i] = dp[j] + 1
                prev[i] = j
    # 取最长链的结尾；并列时取更靠后的（body 在 TOC/前置 cross-ref 之后）
    best = max(range(n), key=lambda i: (dp[i], i))
    chain: list[tuple[int, str]] = []
    k = best
    while k != -1:
        chain.append(anchors[k])
        k = prev[k]
    chain.reverse()
    return chain


def _select_body_anchors_10k(
    lines: list[str], item_hits: list[tuple[int, str]]
) -> dict[str, int]:
    """10-K body 锚点：先按 title 过滤掉 TOC 桩，再用规范序 LIS 剔除 cross-reference。

    旧策略"每个 item 取最后一次出现"会被出现在真 body **之后**的 cross-reference
    抢占锚点（如 PLTR 10-K 里 MD&A/治理段回指 "Item 1A. Risk Factors" 出现在 L2575，
    把真 Item 1A(L1552) 的锚点覆盖掉）。改为 title 过滤 + LIS 后，只保留规范序单调
    递增的 body 链，cross-reference 因乱序被自动排除。
    """
    title_hits = [(ln, item) for ln, item in item_hits if _line_has_title(lines[ln], item)]
    body_chain = _lis_by_rank(title_hits)
    return {item: ln for ln, item in body_chain}


def split_10k(htm_path: Path) -> dict:
    """切 10-K。返回 {'form': '10-K', 'sections': [...], 'split_ok': bool, ...}"""
    lines = _extract_lines(htm_path)
    item_hits = _find_item_anchors(lines)
    body = _select_body_anchors_10k(lines, item_hits)

    # 按 lineno 排序的所有 body Item，用于确定 section 结束行
    sorted_body = sorted(body.items(), key=lambda kv: kv[1])
    end_map: dict[str, int] = {}
    for (item, start), (_, next_start) in zip(sorted_body, sorted_body[1:]):
        end_map[item] = next_start
    if sorted_body:
        end_map[sorted_body[-1][0]] = len(lines)

    sections = []
    for item_key, section_name in _10K_SECTIONS.items():
        if item_key not in body:
            sections.append({"item": item_key, "name": section_name, "found": False, "word_count": 0})
            continue
        start = body[item_key]
        end = end_map[item_key]
        body_lines = lines[start:end]
        text = "\n".join(body_lines).strip()
        sections.append({
            "item": item_key,
            "name": section_name,
            "found": True,
            "start_line": start,
            "end_line": end,
            "word_count": len(text.split()),
            "text": text,
            "addresses": _10K_DEFAULT_ADDRESSES.get(section_name, []),
        })

    found_count = sum(1 for s in sections if s["found"])
    split_ok = found_count >= 3  # 至少切出 3 段才算成功（兜底）

    return {
        "form": "10-K",
        "split_ok": split_ok,
        "total_lines": len(lines),
        "item_hits": len(item_hits),
        "body_anchors": len(body),
        "sections": sections,
    }


def split_10q(htm_path: Path) -> dict:
    """切 10-Q。Part I 第一节常无显式 'Item 1' 标题（直接进财报报表），需特殊处理。

    策略：
    1. 找到第一个 body Item（间隔下一 item > 500 行）作上界，定位 Part I body anchor
    2. Part II body = part_i_body 之后的最后一个 Part II 锚点
    3. Part I Item 1 财报：从 Part I body 起点到 Part I 内第一个 has-title item
    4. Part II Item 1A：直接取 has-title 锚点
    """
    lines = _extract_lines(htm_path)
    part_hits = _find_part_anchors(lines)
    item_hits = _find_item_anchors(lines)

    sections_out: list[dict] = []

    # Part II body 分界点 = 最后一个 Part II 锚点（body 永远在 TOC 之后）
    part_ii_body = max((ln for ln, p in part_hits if p == "II"), default=None)
    part_ii_start = part_ii_body if part_ii_body is not None else len(lines)

    # Part I body anchor = 最后一个位于 part_ii_start 之前 的 Part I 锚点
    # （SCHW 文档末尾页眉里还会冒出一次 'Part I'，得排除）
    part_i_body_start = max(
        (ln for ln, p in part_hits if p == "I" and ln < part_ii_start),
        default=None,
    )

    # 每个 Part 内：先按 title 过滤掉 TOC 桩，再用规范序 LIS 剔除 cross-reference，
    # 得到干净的 body item 锚点。旧策略"取最后一次出现"会被出现在 body 段落**内部**的
    # cross-reference 当成边界（如 PLTR 10-Q 里 MD&A 段回指 "Item 1A. Risk Factors"(L2443)
    # 把 Item 2 MD&A 截成 32 行；Part II 风险段回指 "Item 7."(L3109) 把风险因素截成 97 行）。
    pi_title = [(ln, it) for ln, it in item_hits if ln < part_ii_start and _line_has_title(lines[ln], it)]
    pii_title = [(ln, it) for ln, it in item_hits if ln >= part_ii_start and _line_has_title(lines[ln], it)]
    part_i_items: dict[str, int] = {it: ln for ln, it in _lis_by_rank(pi_title)}
    part_ii_items: dict[str, int] = {it: ln for ln, it in _lis_by_rank(pii_title)}

    # ---- Part I Item 1（财报报表）----
    # 两种 layout：
    # (A) 标准：财报报表无 Item 1 标题，直接放在 Part I 开头 → Item 2 MD&A 之前
    # (B) SCHW 风格：财报报表有显式 Item 1 body 标题，放在 Item 2 MD&A **之后**
    sorted_pi = sorted(part_i_items.items(), key=lambda kv: kv[1])

    # 判断 part_i_items["1"] 是不是真 body：要求它到下一个 Part I item 的间隔 > 500 行
    # （TOC 里 Item 1 通常和 Item 1A/2/3 紧邻；body Item 1 后面跟着大段财报表格）
    item_1_is_body = False
    if "1" in part_i_items:
        i1 = part_i_items["1"]
        later = [v for v in part_i_items.values() if v > i1] + [part_ii_start]
        if min(later) - i1 > 500:
            item_1_is_body = True

    if item_1_is_body:
        item_1_start = part_i_items["1"]
        later_starts = [v for v in part_i_items.values() if v > item_1_start] + [part_ii_start]
        item_1_end = min(later_starts)
    elif sorted_pi:
        # 无 Item 1 body 标题：财报报表夹在 Part I body anchor 与第一个 Part I body item 之间
        # 但 sorted_pi[0] 可能还是 TOC 项（如 HOOD 把 Item 1/1A/5/6 都堆在 L1398-L1416），
        # 找第一个 prev_gap > 500 的 item 作为 item_1_end（= 第一个 body item 起点）
        prev = part_i_body_start if part_i_body_start is not None else 0
        item_1_end = sorted_pi[-1][1]  # fallback：最后一个 item
        for _item_id, ln in sorted_pi:
            if ln - prev > 500:
                item_1_end = ln
                break
            prev = ln
        if part_i_body_start is not None and part_i_body_start < item_1_end:
            item_1_start = part_i_body_start
        else:
            # 无 Part I body anchor → 用 lookback 兜底（10-Q 财报通常 1000-3000 行）
            item_1_start = max(0, item_1_end - 2500)
    else:
        # 既无 Item 1 也无任何 Part I body item → 弃
        item_1_start = item_1_end = 0

    if item_1_end > item_1_start + 50:  # 至少 50 行才视为有效
        text = "\n".join(lines[item_1_start:item_1_end]).strip()
        sections_out.append({
            "item": "PartI_1", "name": "item_1_financial", "found": True,
            "start_line": item_1_start, "end_line": item_1_end,
            "word_count": len(text.split()),
            "text": text,
            "addresses": _10Q_DEFAULT_ADDRESSES["item_1_financial"],
        })
    else:
        sections_out.append({"item": "PartI_1", "name": "item_1_financial", "found": False, "word_count": 0})

    # ---- Part I Item 2 / Item 3 ----
    for item_key, sec_key in [("2", "PartI_2"), ("3", "PartI_3")]:
        if item_key in part_i_items:
            start = part_i_items[item_key]
            next_starts = [v for v in part_i_items.values() if v > start] + [part_ii_start]
            end = min(next_starts)
            sec_name = _10Q_SECTIONS[sec_key]
            text = "\n".join(lines[start:end]).strip()
            sections_out.append({
                "item": sec_key, "name": sec_name, "found": True,
                "start_line": start, "end_line": end,
                "word_count": len(text.split()),
                "text": text,
                "addresses": _10Q_DEFAULT_ADDRESSES[sec_name],
            })
        else:
            sections_out.append({"item": sec_key, "name": _10Q_SECTIONS[sec_key], "found": False, "word_count": 0})

    # ---- Part II Item 1A (Risk Factors changes) ----
    if "1A" in part_ii_items:
        start = part_ii_items["1A"]
        next_starts = [v for v in part_ii_items.values() if v > start] + [len(lines)]
        end = min(next_starts)
        sec_name = _10Q_SECTIONS["PartII_1A"]
        text = "\n".join(lines[start:end]).strip()
        sections_out.append({
            "item": "PartII_1A", "name": sec_name, "found": True,
            "start_line": start, "end_line": end,
            "word_count": len(text.split()),
            "text": text,
            "addresses": _10Q_DEFAULT_ADDRESSES[sec_name],
        })
    else:
        sections_out.append({"item": "PartII_1A", "name": _10Q_SECTIONS["PartII_1A"], "found": False, "word_count": 0})

    found_count = sum(1 for s in sections_out if s["found"])
    split_ok = found_count >= 2  # 至少切出 Item 1 财报 + Item 2 MD&A 才算成功

    return {
        "form": "10-Q",
        "split_ok": split_ok,
        "total_lines": len(lines),
        "part_body_anchors": sum(1 for v in (part_i_body_start, part_ii_body) if v is not None),
        "item_body_anchors": len(part_i_items) + len(part_ii_items),
        "sections": sections_out,
    }


def split_20f(htm_path: Path) -> dict:
    """切 20-F（外国发行人年报）。结构与 10-K 不同：

    - Items 1-19 而非 1-15
    - body 内每页用 'ITEM N TITLE' 作 page header（同一 Item 重复出现 N 次）→
      不能用 10-K 的"取最后一次"策略（会落到 page header tail），
      改用"body region 内首次出现"。
    - Risk Factors 在 Item 3.D 而非独立 Item 1A
    """
    lines = _extract_lines(htm_path)
    item_hits = _find_item_anchors(lines)
    part_hits = _find_part_anchors(lines)

    # body region 起点 = 最后一个 PART I 锚点（TOC 的 PART I 在前）
    part_i_anchors = [ln for ln, p in part_hits if p == "I"]
    body_region_start = max(part_i_anchors) if part_i_anchors else 0

    # body anchor = 首次出现在 body region 内的 lineno
    body: dict[str, int] = {}
    for lineno, item in item_hits:
        if lineno >= body_region_start and item not in body:
            body[item] = lineno

    # 排序，建 end_map（同 10-K：下一个 body Item 的起点）
    sorted_body = sorted(body.items(), key=lambda kv: kv[1])
    end_map: dict[str, int] = {}
    for (item, start), (_, next_start) in zip(sorted_body, sorted_body[1:]):
        end_map[item] = next_start
    if sorted_body:
        end_map[sorted_body[-1][0]] = len(lines)

    sections = []
    for item_key, section_name in _20F_SECTIONS.items():
        if item_key not in body:
            sections.append({"item": item_key, "name": section_name, "found": False, "word_count": 0})
            continue
        start = body[item_key]
        end = end_map[item_key]
        body_lines = lines[start:end]
        text = "\n".join(body_lines).strip()
        sections.append({
            "item": item_key,
            "name": section_name,
            "found": True,
            "start_line": start,
            "end_line": end,
            "word_count": len(text.split()),
            "text": text,
            "addresses": _20F_DEFAULT_ADDRESSES.get(section_name, []),
        })

    found_count = sum(1 for s in sections if s["found"])
    split_ok = found_count >= 3  # 至少切 3 段（5 核心 Item 找到 3 即过）

    return {
        "form": "20-F",
        "split_ok": split_ok,
        "total_lines": len(lines),
        "item_hits": len(item_hits),
        "body_anchors": len(body),
        "sections": sections,
    }


def split_file(htm_path: Path, out_dir: Path | None = None) -> dict:
    """切单份 htm。out_dir 不传时默认 htm_path 同级的 sec/{stem}/。

    返回 _meta.yaml 内容（不含 section text body）。失败则 meta['split_ok']=False，
    不写任何 section 文件，下游照常读原 htm。
    """
    form = _detect_form(htm_path.name)
    if form == "10-K":
        result = split_10k(htm_path)
    elif form == "10-Q":
        result = split_10q(htm_path)
    elif form == "20-F":
        result = split_20f(htm_path)
    else:
        return {"form": form, "split_ok": False, "reason": f"unsupported form {form!r}"}

    if not result["split_ok"]:
        log.warning("%s: split failed (found %d sections, need ≥3 for 10-K / ≥2 for 10-Q)",
                    htm_path.name, sum(1 for s in result["sections"] if s["found"]))
        return result

    # 默认输出目录: 同级 sec/{stem}/
    if out_dir is None:
        out_dir = htm_path.parent / "sec" / htm_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # 写每个 section
    section_meta_list = []
    for s in result["sections"]:
        meta = {k: v for k, v in s.items() if k != "text"}
        if s["found"]:
            out_path = out_dir / f"{s['name']}.md"
            out_path.write_text(s["text"], encoding="utf-8")
            meta["file"] = out_path.name
        section_meta_list.append(meta)

    meta_doc = {
        "source_htm": htm_path.name,
        "form": result["form"],
        "split_ok": True,
        "total_lines": result["total_lines"],
        "sections": section_meta_list,
    }
    (out_dir / "_meta.yaml").write_text(
        yaml.dump(meta_doc, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    total_section_words = sum(s.get("word_count", 0) for s in result["sections"])
    log.info("%s → %d sections, %d words kept (out of %d total lines)",
             htm_path.name,
             sum(1 for s in result["sections"] if s["found"]),
             total_section_words,
             result["total_lines"])
    return meta_doc


def split_dir(materials_dir: Path) -> list[dict]:
    """批量切 materials_dir 下所有 *.htm（10-K/10-Q）。"""
    metas = []
    for htm in sorted(materials_dir.glob("*.htm")):
        form = _detect_form(htm.name)
        if form not in {"10-K", "10-Q", "20-F"}:
            log.info("Skip %s (form=%s)", htm.name, form)
            continue
        try:
            metas.append(split_file(htm))
        except Exception as e:
            log.exception("Split failed for %s: %s", htm.name, e)
            metas.append({"source_htm": htm.name, "split_ok": False, "error": str(e)})
    return metas


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="切 SEC 10-K/10-Q htm 为 section md")
    p.add_argument("path", nargs="?", help="单个 htm 文件路径")
    p.add_argument("--dir", help="批量处理一个 materials 目录下所有 *.htm")
    p.add_argument("--out", help="输出目录（默认同级 sec/{stem}/）")
    args = p.parse_args()

    if args.dir:
        metas = split_dir(Path(args.dir))
        ok = sum(1 for m in metas if m.get("split_ok"))
        print(f"\nProcessed {len(metas)} files, {ok} OK, {len(metas)-ok} failed")
        return 0 if ok == len(metas) else 1
    if not args.path:
        p.error("需要 path 或 --dir")
    out_dir = Path(args.out) if args.out else None
    meta = split_file(Path(args.path), out_dir)
    if not meta.get("split_ok"):
        print(f"FAIL: {meta.get('reason') or 'see logs'}", file=sys.stderr)
        return 1
    print(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
