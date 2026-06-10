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


_PARSERS = {"json": _parse_json, "csv": _parse_csv}


def fetch_by_recipe(recipe: dict, *, client=None) -> tuple[float | None, str | None]:
    """按 fetch_recipe 抓一个数值。recipe: {kind?, url, parse:{...}}。
    kind 缺省 'json'（向后兼容现有写法）；按 kind 派发解析器。未知 kind 抛 ValueError
    （不静默）。client 可注入（测试 mock）。"""
    url = recipe.get("url")
    if not url:
        return None, None
    kind = recipe.get("kind", "json")
    parser = _PARSERS.get(kind)
    if parser is None:
        raise ValueError(f"未知 fetch_recipe.kind: {kind!r}（支持 {sorted(_PARSERS)}）")
    parse = recipe.get("parse") or {}
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json() if kind == "json" else resp.text
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
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "recipe":
            continue
        if only is not None and e["name"] not in only:
            continue
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
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"recipe 抓取: {run_recipe_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
