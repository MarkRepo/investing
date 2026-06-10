"""recipe 通道的通用抓取（β）。零 LLM：读登记表里 fetch_method=='recipe' 且
availability=='scripted' 且有 fetch_recipe 的输入，按 recipe 抓取 → record_observation。

fetch_method 是「脚本执行通道」：fred-api 走 fred_fetch，recipe 走本模块。
availability 为 scriptable_todo / llm 的项不在此抓（它们走 headless LLM 取数）；
本模块只跑已配好 recipe 的 scripted 项。判源 + 写 recipe 是逐条增量的 LLM 工作（对话里做）。
单测 mock httpx（同 fred_fetch）。"""
from __future__ import annotations

import csv
import io
import re
import sys
from html import unescape

import httpx

from prism.scripts import macro_registry as reg


def _dig(obj, path):
    for key in path:
        if obj is None:
            return None
        try:
            obj = obj[key]
        except (KeyError, IndexError, TypeError):
            return None
    return obj


def _parse_json(payload, cfg) -> tuple[float | None, str | None]:
    """JSON 取值：json_path/date_path 是键/索引序列（原 fetch_by_recipe 逻辑）。"""
    val = _dig(payload, cfg.get("json_path") or [])
    as_of = _dig(payload, cfg.get("date_path") or [])
    as_of = str(as_of) if as_of is not None else None
    try:
        return (float(val) if val is not None else None), as_of
    except (ValueError, TypeError):
        return None, as_of


def _parse_csv(text, cfg) -> tuple[float | None, str | None]:
    """CSV 取值：value_column 取列、row 选行（latest=末行/first=首行/整数=索引）、
    date_column 取日期。值转 float 失败 → (None, as_of)。诚实降级，不抛。"""
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return None, None
    sel = cfg.get("row", "latest")
    if sel == "latest":
        r = rows[-1]
    elif sel == "first":
        r = rows[0]
    else:
        try:
            r = rows[int(sel)]
        except (ValueError, IndexError, TypeError):
            return None, None
    raw = r.get(cfg.get("value_column"))
    date_col = cfg.get("date_column")
    as_of = str(r.get(date_col)) if date_col and r.get(date_col) is not None else None
    try:
        return (float(raw) if raw not in (None, "") else None), as_of
    except (ValueError, TypeError):
        return None, as_of


def _parse_matrix(text, cfg) -> tuple[float | None, str | None]:
    """透视表（实体作行、周期作列）取值：找首格 == row_label 的数据行，取第 col_index 列（0=标签）。
    日期从首格 == header_label 的表头行同列取。供 Treasury TIC（Tab 分隔、前置元数据行）这类表。
    参数 {delimiter='\\t', header_label, row_label, col_index=1}。任何对不上 → 诚实 (None, as_of)。"""
    delim = cfg.get("delimiter", "\t")
    col = cfg.get("col_index", 1)
    header_label = cfg.get("header_label")
    row_label = cfg.get("row_label")
    header_cells = None
    as_of = None
    for line in text.splitlines():
        cells = [c.strip() for c in line.split(delim)]
        if not cells or not cells[0]:
            continue
        if header_label and cells[0] == header_label:
            header_cells = cells
            continue
        if row_label and cells[0] == row_label:
            if header_cells and col < len(header_cells):
                as_of = header_cells[col]
            raw = cells[col] if col < len(cells) else None
            try:
                return (float(raw) if raw not in (None, "") else None), as_of
            except (ValueError, TypeError):
                return None, as_of
    return None, as_of


_PARSERS = {"json": _parse_json, "csv": _parse_csv, "matrix": _parse_matrix}
_TEXT_KINDS = {"csv", "matrix"}  # 这些 kind 喂 resp.text；json 喂 resp.json()


def fetch_by_recipe(recipe: dict, *, client=None) -> tuple[float | None, str | None]:
    """按 fetch_recipe 抓一个数值。recipe: {kind?, url, method?, headers?, body?, parse:{...}}。
    kind 缺省 'json'（向后兼容现有写法）；按 kind 派发解析器。未知 kind 抛 ValueError（不静默）。
    method 缺省 GET；POST 传 body（json）。headers 可选。client 可注入（测试 mock）。"""
    url = recipe.get("url")
    if not url:
        return None, None
    kind = recipe.get("kind", "json")
    parser = _PARSERS.get(kind)
    if parser is None:
        raise ValueError(f"未知 fetch_recipe.kind: {kind!r}（支持 {sorted(_PARSERS)}）")
    parse = recipe.get("parse") or {}
    method = (recipe.get("method") or "GET").upper()
    headers = recipe.get("headers")
    body = recipe.get("body")
    # 仅在显式给定时才传 headers/json，保持与既有 mock client（get(url, timeout=)）的兼容。
    kw: dict = {"timeout": 30}
    if headers:
        kw["headers"] = headers
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        if method == "POST":
            resp = client.post(url, json=body, **kw)
        else:
            resp = client.get(url, **kw)
        resp.raise_for_status()
        payload = resp.text if kind in _TEXT_KINDS else resp.json()
    finally:
        if owns:
            client.close()
    return parser(payload, parse)


_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_ANY_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def fetch_text(url: str, *, client=None) -> str:
    """固定 URL 取正文，喂给 headless LLM 判读用（如央行声明/报告索引页）。
    GET → 去 script/style → 去标签 → 反转义实体 → collapse 空白。

    刻意不挂在 fetch_by_recipe 上：那条只管 json/csv 数值提取，保持纯粹；
    文本是给 LLM 读的，不是 value。多跳（索引→最新条目）由 headless LLM 侧决定。
    client 可注入（测试 mock）。"""
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        raw = resp.text
    finally:
        if owns:
            client.close()
    raw = _SCRIPT_STYLE.sub(" ", raw)
    raw = _ANY_TAG.sub(" ", raw)
    return _WS.sub(" ", unescape(raw)).strip()


def run_recipe_fetch(slug: str, variant: str, *, client=None,
                     only: set[str] | None = None) -> dict:
    """抓所有 fetch_method=='recipe' 且 availability=='scripted' 且有 recipe 的输入。
    待脚本 / LLM取（llm）的诚实跳过并计数（它们走 headless LLM 取数）。
    only 给定时只抓名字在其中的项（web 单条手动抓取用）；缺省抓全部。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = derived = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "recipe":
            continue
        if only is not None and e["name"] not in only:
            continue
        if e.get("derived", {}).get("from_inputs"):
            continue  # 按名派生项在下方单独跑（待各腿 observed 落盘后）
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("fetch_recipe"):
            skipped_todo += 1
            continue
        val, as_of = fetch_by_recipe(e["fetch_recipe"], client=client)
        if val is None:
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1

    # 按名派生：derived:{op, from_inputs:[名…]} —— 读各腿最新 observed.value 后按 op 算。
    # 在 recipe 抓取之后跑、且重读登记表，确保本轮 recipe 腿与更早 fred run 的腿都已落盘可见。
    derived_specs = [e for e in data["inputs"]
                     if e.get("fetch_method") == "recipe" and e.get("derived", {}).get("from_inputs")
                     and (only is None or e["name"] in only)]
    if derived_specs:
        from prism.scripts.fred_fetch import _apply_op
        fresh = reg.read_registry(slug, variant)
        by_name = {x["name"]: x for x in fresh["inputs"]}
        for e in derived_specs:
            spec = e["derived"]
            if e.get("availability") != "scripted":
                skipped_todo += 1
                continue
            legs = [((by_name.get(n) or {}).get("observed") or {}).get("value")
                    for n in spec["from_inputs"]]
            if any(v is None for v in legs):
                failed += 1
                continue
            reg.record_observation(slug, variant, e["name"], value=_apply_op(spec["op"], legs))
            derived += 1

    return {"fetched": fetched, "derived": derived, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"recipe 抓取: {run_recipe_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
