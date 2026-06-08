"""llm-web 输入的通用抓取（β）。零 LLM：读登记表里 fetch_method=='llm-web' 且
availability=='scripted' 且有 fetch_recipe 的输入，按 recipe 抓取 → record_observation。

availability 为 scriptable_todo / no_stable_source 的跳过并计数，绝不假装抓到。判源 +
写 recipe + 评 authority/availability 是逐条增量的 LLM 工作（对话里做），本脚本只跑已配好的。
单测 mock httpx（同 fred_fetch）。"""
from __future__ import annotations

import sys

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


def fetch_by_recipe(recipe: dict, *, client=None) -> tuple[float | None, str | None]:
    """按 fetch_recipe 抓一个数值。recipe: {url, parse:{json_path:[...], date_path:[...]}}。
    仅支持 JSON 取值（json_path/date_path 是键/索引序列）。client 可注入（测试 mock）。"""
    url = recipe.get("url")
    if not url:
        return None, None
    parse = recipe.get("parse") or {}
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if owns:
            client.close()
    val = _dig(payload, parse.get("json_path") or [])
    as_of = _dig(payload, parse.get("date_path") or [])
    as_of = str(as_of) if as_of is not None else None
    try:
        return (float(val) if val is not None else None), as_of
    except (ValueError, TypeError):
        return None, as_of


def run_llmweb_fetch(slug: str, variant: str, *, client=None) -> dict:
    """抓所有 fetch_method=='llm-web' 且 availability=='scripted' 且有 recipe 的输入。
    待脚本 / 无稳定源 的诚实跳过并计数。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_no_source = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "llm-web":
            continue
        avail = e.get("availability")
        if avail == "no_stable_source":
            skipped_no_source += 1
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
            "skipped_no_source": skipped_no_source, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"llm-web 抓取: {run_llmweb_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
