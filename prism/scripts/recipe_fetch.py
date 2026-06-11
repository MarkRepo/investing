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


def _parse_html(text, cfg) -> tuple[float | None, str | None]:
    """HTML 正则取值：value_regex 必填（第 1 捕获组=值），date_regex 选填（第 1 捕获组=日期）。
    两条正则都对**整页原文**跑（带 re.DOTALL），故可把区段锚点写进正则自身
    （如 'chart-stat-lastrows.*?<span class="val">([\\d.,]+)' 避开页头同名块）。
    值去千分位逗号后转 float；任何对不上 → 诚实 (None, as_of)，不抛。
    供「固定 URL、值嵌在静态 HTML、无免费 json/csv 接口」的第三方镜像（如 macromicro）。"""
    vr = cfg.get("value_regex")
    if not vr:
        return None, None
    vm = re.search(vr, text, re.DOTALL)
    raw = vm.group(1) if vm else None
    as_of = None
    dr = cfg.get("date_regex")
    if dr:
        dm = re.search(dr, text, re.DOTALL)
        as_of = dm.group(1) if dm else None
    try:
        return (float(raw.replace(",", "")) if raw not in (None, "") else None), as_of
    except (ValueError, TypeError, AttributeError):
        return None, as_of


def _parse_json_scan(payload, cfg) -> tuple[float | None, str | None]:
    """JSON 列表扫描取值（供「取列表里首个命中项」的 feed，如中房网周报 datalist）。
    在 list_path 定位的列表里找首个 match_field 命中 match_regex 的项；从该项 value_field
    （缺省=match_field）用 value_regex（第 1 组）抽数值；sign_negative_regex 命中则取负
    （中文涨跌词无 +/−，靠它给「下降/减少」判负）；date_field（+可选 date_regex）取日期。
    列表新→旧排序时即取最新一条。吃 resp.json()（非 _TEXT_KINDS）。任何对不上 → 诚实
    (None, as_of)，不抛。"""
    items = _dig(payload, cfg.get("list_path") or [])
    if not isinstance(items, list):
        return None, None
    mf, mr = cfg.get("match_field"), cfg.get("match_regex")
    vf = cfg.get("value_field") or mf
    vr = cfg.get("value_regex")
    df, dr = cfg.get("date_field"), cfg.get("date_regex")
    neg = cfg.get("sign_negative_regex")
    mrx = re.compile(mr) if mr else None
    for it in items:
        if not isinstance(it, dict):
            continue
        mval = str(it.get(mf, "")) if mf else ""
        if mrx and not mrx.search(mval):
            continue
        sval = str(it.get(vf, "")) if vf else mval
        as_of = None
        if df:
            dsrc = str(it.get(df, ""))
            if dr:
                dm = re.search(dr, dsrc)
                as_of = dm.group(1) if dm else None
            else:
                as_of = dsrc or None
        if not vr:
            return None, as_of
        vm = re.search(vr, sval)
        if not vm:
            return None, as_of
        try:
            num = float(vm.group(1))
        except (ValueError, IndexError, TypeError):
            return None, as_of
        if neg and re.search(neg, sval):
            num = -num
        return num, as_of
    return None, None


_PARSERS = {"json": _parse_json, "csv": _parse_csv, "matrix": _parse_matrix,
            "html": _parse_html, "json_scan": _parse_json_scan}
_TEXT_KINDS = {"csv", "matrix", "html"}  # 这些 kind 喂 resp.text；json/json_scan 喂 resp.json()


def _cip_basis(legs: list[float], params: dict) -> float:
    """抛补利率平价（CIP）3M 跨币种基差，返回 bps。供按名派生 op=='cip_basis'。
    legs 顺序固定 [spot, fwd_pips, usd_3m_ois%, foreign_3m_ois%]；
    params: {tau=0.25, pip_scale, usd_role:'quote'|'base'}。

    远期 F = S + fwd_pips/pip_scale；r 由百分点转小数。基差挂在非美元腿上：
      usd_role=='quote'（如 EURUSD，USD 在报价侧、外币=基准 EUR）:
          b = ((1+r_usd·τ)·(S/F) − 1)/τ − r_for
      usd_role=='base' （如 USDJPY，USD 在基准侧、外币=报价 JPY）:
          b = ((F/S)·(1+r_usd·τ) − 1)/τ − r_for
    返回 b·1e4（bps）。usd_role 非法或腿数 ≠4 抛 ValueError。"""
    if len(legs) != 4:
        raise ValueError(f"cip_basis 须 4 腿 [spot, fwd_pips, usd_ois, foreign_ois]，得到 {len(legs)}")
    spot, fwd_pips, usd_ois, for_ois = legs
    tau = float(params.get("tau", 0.25))
    pip_scale = float(params.get("pip_scale", 10000))
    usd_role = params.get("usd_role", "quote")
    S = float(spot)
    F = S + float(fwd_pips) / pip_scale
    r_usd = float(usd_ois) / 100.0
    r_for = float(for_ois) / 100.0
    if usd_role == "quote":
        b = ((1 + r_usd * tau) * (S / F) - 1) / tau - r_for
    elif usd_role == "base":
        b = ((F / S) * (1 + r_usd * tau) - 1) / tau - r_for
    else:
        raise ValueError(f"未知 cip_basis usd_role: {usd_role!r}（支持 quote/base）")
    return b * 1e4


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
        try:
            val, as_of = fetch_by_recipe(e["fetch_recipe"], client=client)
        except Exception as exc:           # HTTP 403/404/超时/未知 kind 等：记错、跳过，不连累其余源
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            url = (e.get("fetch_recipe") or {}).get("url", "")
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"recipe 解析未取到值（源结构可能变更）: {url}")
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
                missing = [n for n, v in zip(spec["from_inputs"], legs) if v is None]
                reg.record_fetch_error(slug, variant, e["name"],
                                       msg=f"派生腿缺值: {', '.join(missing)}")
                failed += 1
                continue
            op = spec["op"]
            if op == "cip_basis":
                # CIP 基差：除算值外，as_of 取各腿日期最小值（暴露最旧腿的陈旧度）
                try:
                    val = _cip_basis(legs, spec.get("params") or {})
                except Exception as exc:
                    reg.record_fetch_error(slug, variant, e["name"], msg=f"cip_basis 计算失败: {exc}")
                    failed += 1
                    continue
                as_ofs = [a for a in
                          (((by_name.get(n) or {}).get("observed") or {}).get("as_of")
                           for n in spec["from_inputs"]) if a]
                reg.record_observation(slug, variant, e["name"], value=val,
                                       as_of=(min(as_ofs) if as_ofs else None))
            else:
                reg.record_observation(slug, variant, e["name"], value=_apply_op(op, legs))
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
