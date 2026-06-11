"""macromicro 取数通道（FRED/akshare/yfinance 都没有的专有序列）。零 LLM：读登记表里
fetch_method=='macromicro' 且 availability=='scripted' 且有 macromicro 配置块的输入，
两步法抓 MacroMicro 图表 series 最新值 → record_observation。

与 fred_fetch / recipe_fetch / akshare_fetch / yfinance_fetch 平行（脚本「数值」通道）。
MacroMicro 覆盖 FRED/akshare/yfinance 都缺的序列——典型如 **日频 JPY 3M TONA OIS**（FRED 只有
月频陈值、cbonds/Bloomberg 付费）。仿 fred_fetch：核心 fetch_by_macromicro 可注入 client（测试 mock）。

取数机制（两步，复刻浏览器匿名访问）：
  ① GET 任意 MacroMicro 页面，正则取页脚 `data-stk` 会话 token（每次加载会换，故每次现取）；
  ② GET /charts/data/{chart_id}，带 `Authorization: Bearer <stk>` 与 `Docref` 头，返 JSON。
返回 data 形如 {"c:{id}": [series0, series1, ...]}，每 series=[[日期串, 值], ...]（多档=多期限）。
故配置用 series_index 选档（如 JPY OIS 图的 3M 那条）。

注意（实测踩到）：
  - **限流**：连打会返 {"success":1,"data":[]}（空）。内建退避重试；定时巡检每日 1 次不会触发。
  - **缺 token**：裸请求返 {"success":0,"msg":"error #1170"}；token 失效同样空，重试取新 token。
  - **ToS**：MacroMicro 为商业源、转载需授权——本通道仅供自用研究工具按低频取数，已知风险。
"""
from __future__ import annotations

import math
import re
import sys
import time

from prism.scripts import macro_registry as reg

_BASE = "https://sc.macromicro.me"
_DATA_URL = _BASE + "/charts/data/{chart_id}"
_TOKEN_RE = re.compile(r'data-stk="([0-9a-f]+)"')
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
# 默认客户端头：须足够像真浏览器，否则 MacroMicro 反爬会直接断 TLS（表现为 SSL EOF，而非 #1158）。
_BROWSER_HEADERS = {
    "User-Agent": _UA,
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}


def _to_float(v) -> float | None:
    """单元转 float；NaN/空/非数 → None。值含千分位逗号/百分号则去掉。"""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.replace(",", "").replace("%", "").strip()
        if not v:
            return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _find_all_series(obj) -> list[list]:
    """递归找出响应里所有时间序列（元素为 [日期串, 值] 的列表），按出现顺序返回。
    对 data 是 {chart:[series...]} / {chart:{series:[...]}} / 直接 [series...] 等结构都稳健。"""
    out: list[list] = []

    def walk(x):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            if x and isinstance(x[0], list) and len(x[0]) >= 2 and isinstance(x[0][0], str):
                out.append(x)            # 命中一条 series，不再下钻其内部
            else:
                for v in x:
                    walk(v)

    walk(obj)
    return out


def _latest_point(series: list) -> tuple[float | None, str | None]:
    """series=[[日期串, 值], ...]，解析日期取 max 那点（防意外乱序）。返回 (值, 日期 ISO)。"""
    best_date = None
    best_val = None
    for pt in series:
        if not isinstance(pt, list) or len(pt) < 2:
            continue
        d = str(pt[0])[:10]
        if best_date is None or d > best_date:   # ISO 日期串可直接字典序比较
            best_date = d
            best_val = pt[1]
    return _to_float(best_val), best_date


def _import_httpx():
    import httpx  # 惰性导入
    return httpx


def fetch_by_macromicro(cfg: dict, *, client=None, sleep=time.sleep) -> tuple[float | None, str | None]:
    """按 macromicro 配置抓一个数值。cfg: {chart_id, series_index?=0, page_url?, value_scale?=1, retries?=4}。
    两步法见模块 docstring。series_index 选第几条 series（多期限图按档位，0 起）。
    value_scale 给定时乘到值上（如百分点→bps 用 100）。任何对不上 → 诚实 (None, None)，不抛；
    限流/空数据按 retries 退避重试。client 可注入（测试 mock：需支持 .get(url[,headers]) → .text/.json()）。"""
    chart_id = cfg.get("chart_id")
    if chart_id is None or str(chart_id).strip() == "":
        raise ValueError("macromicro 配置缺 chart_id")
    chart_id = str(chart_id).strip()
    if not chart_id.isdigit():
        raise ValueError(f"macromicro chart_id 须为数字: {chart_id!r}")
    # page_url 必填：它既是 data-stk token 来源，又是数据接口校验的 Docref——
    # Docref 必须是真正嵌该图的页面（用首页等会被 #1158 拒；/charts/{id} 无 slug 会 redirect 到无 token 桩页）。
    page_url = cfg.get("page_url")
    if not page_url:
        raise ValueError("macromicro 配置缺 page_url（图的规范页 URL，作 token 来源与 Docref）")
    series_index = int(cfg.get("series_index", 0))
    scale = cfg.get("value_scale")
    retries = int(cfg.get("retries", 4))

    owns = client is None
    if owns:
        client = _import_httpx().Client(timeout=30, follow_redirects=True,
                                        headers=dict(_BROWSER_HEADERS))
    try:
        data_url = _DATA_URL.format(chart_id=chart_id)
        last_err: Exception | None = None
        for attempt in range(max(1, retries)):
            last = attempt == retries - 1
            try:
                # ① 每轮现取 token（会随页面加载轮换）
                page = client.get(page_url)
                m = _TOKEN_RE.search(getattr(page, "text", "") or "")
                if not m:
                    raise ValueError("MacroMicro 页面未找到 data-stk token（站点结构可能变更）")
                stk = m.group(1)
                # 数据请求须像真浏览器 XHR（带 Referer/X-Requested-With/sec-fetch-*），
                # 否则反爬直接断 TLS（SSL EOF）。Docref/Referer = 图页。
                headers = {"Authorization": f"Bearer {stk}", "Docref": page_url,
                           "Referer": page_url, "X-Requested-With": "XMLHttpRequest",
                           "Accept": "application/json, text/plain, */*",
                           "sec-fetch-dest": "empty", "sec-fetch-mode": "cors",
                           "sec-fetch-site": "same-origin"}
                # ② 带 token 打数据接口
                js = client.get(data_url, headers=headers).json()
            except Exception as exc:                    # 瞬时网络/SSL/解析错：退避重试，末轮才抛
                last_err = exc
                if last:
                    raise
                sleep(5)
                continue
            payload = js.get("data") if isinstance(js, dict) else None
            all_series = _find_all_series(payload) if payload else []
            if not all_series:                         # success:0(#1170) 或 限流空 → 退避重试
                if last:
                    return None, None
                sleep(5)
                continue
            if series_index >= len(all_series):
                raise ValueError(
                    f"macromicro series_index={series_index} 越界（图 {chart_id} 仅 {len(all_series)} 条 series）")
            val, as_of = _latest_point(all_series[series_index])
            if val is not None and scale is not None:
                val = val * float(scale)
            return val, as_of
        return None, None
    finally:
        if owns:
            client.close()


def run_macromicro_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                         client=None) -> dict:
    """抓所有 fetch_method=='macromicro' 且 availability=='scripted' 且有 macromicro 配置的输入。
    llm 项诚实跳过计数（它们走 headless LLM）。only 给定时只抓名字在其中的项（web 单条手动抓）。
    失败（抛异常/取不到值）记 record_fetch_error 并计数，不连累其余。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "macromicro":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("macromicro"):
            skipped_todo += 1
            continue
        try:
            val, as_of = fetch_by_macromicro(e["macromicro"], client=client)
        except Exception as exc:                       # 配置/网络/结构等：记错、跳过，不连累其余
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"macromicro 未取到值（限流或源变更）: chart {e['macromicro'].get('chart_id')}")
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
    print(f"macromicro 抓取: {run_macromicro_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
