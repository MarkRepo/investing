"""ECB SDMX 取数通道（欧元区利率，FRED/akshare/yfinance 都缺或不日频的序列）。零 LLM：
读登记表里 fetch_method=='ecb' 且 availability=='scripted' 且有 ecb 配置块的输入 → record_observation。

与其余脚本数值通道平行。ECB Data Portal API（`data-api.ecb.europa.eu/service/data/{flow}/{key}`）
无鉴权、稳定、返干净 CSV（`format=csvdata`，列含 TIME_PERIOD / OBS_VALUE）。

唯一 mode `hybrid_3m_ois`——**日频 EUR 3M OIS 混合构造**（CIP 跨币种基差的欧元 OIS 腿）：
  ECB 免费数据里 3M OIS 真利率（MMSR）是「维持期(MP)」频（~6 周一更、滞后数周），不日频；
  €STR(EST 数据集)日频。故混合：
      EUR_3M_OIS(t) = €STR(t) + [真3M_OIS − €STR]@最近MP锚点
  锚点期限溢价用 MMSR 最近值与**同一锚点日**的 €STR 之差（抓锚点日 €STR 防策略已步进时 carry 被污染）。
  返回值日频新鲜（as_of=€STR 日期），中枢锚定真 OIS。三次 CSV GET：
    ① MMSR 3M OIS 最新 → (mmsr_val, mmsr_date)
    ② EST €STR 最新   → (estr_now, estr_date)
    ③ EST €STR @mmsr_date → estr_anchor
"""
from __future__ import annotations

import csv
import io
import math
import sys

from prism.scripts import macro_registry as reg

_BASE = "https://data-api.ecb.europa.eu/service/data/{flow}/{key}"
_HEADERS = {"Accept": "text/csv",
            "User-Agent": "prism-macro-research (admin@prism.local)"}


def _to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _parse_csv_last(text: str) -> tuple[float | None, str | None]:
    """ECB csvdata：取末行（=最新观测）的 OBS_VALUE / TIME_PERIOD。空 → (None, None)。"""
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        return None, None
    last = rows[-1]
    return _to_float(last.get("OBS_VALUE")), last.get("TIME_PERIOD")


def _import_httpx():
    import httpx  # 惰性导入
    return httpx


def _get(client, flow: str, key: str, query: str) -> tuple[float | None, str | None]:
    url = _BASE.format(flow=flow, key=key) + "?format=csvdata" + query
    resp = client.get(url, headers=_HEADERS)
    resp.raise_for_status()
    return _parse_csv_last(resp.text)


def fetch_by_ecb(cfg: dict, *, client=None) -> tuple[float | None, str | None]:
    """按 ecb 配置抓一个数值。cfg: {mode, ois_key, estr_key, ois_flow?='MMSR', estr_flow?='EST'}。
    mode=='hybrid_3m_ois'：见模块 docstring。任一关键腿取不到 → 诚实 (None, None)，不抛。
    未知 mode 抛 ValueError（不静默）。client 可注入（测试 mock：.get(url, headers=) → .text/.raise_for_status()）。"""
    mode = cfg.get("mode")
    if mode != "hybrid_3m_ois":
        raise ValueError(f"未知 ecb.mode: {mode!r}（支持 hybrid_3m_ois）")
    ois_key = cfg.get("ois_key")
    estr_key = cfg.get("estr_key")
    if not ois_key or not estr_key:
        raise ValueError("ecb hybrid_3m_ois 须配 ois_key 与 estr_key")
    ois_flow = cfg.get("ois_flow", "MMSR")
    estr_flow = cfg.get("estr_flow", "EST")

    owns = client is None
    if owns:
        client = _import_httpx().Client(timeout=30, follow_redirects=True)
    try:
        mmsr_val, mmsr_date = _get(client, ois_flow, ois_key, "&lastNObservations=1")
        estr_now, estr_date = _get(client, estr_flow, estr_key, "&lastNObservations=1")
        if mmsr_val is None or estr_now is None or not mmsr_date:
            return None, None
        # 锚点日 €STR（MP 日为工作日，应有值）；缺则退化用当前 €STR（carry≈期限溢价仍近似）
        estr_anchor, _ = _get(client, estr_flow, estr_key,
                              f"&startPeriod={mmsr_date}&endPeriod={mmsr_date}")
        if estr_anchor is None:
            estr_anchor = estr_now
        carry = mmsr_val - estr_anchor
        return estr_now + carry, estr_date
    finally:
        if owns:
            client.close()


def run_ecb_fetch(slug: str, variant: str, *, only: set[str] | None = None,
                  client=None) -> dict:
    """抓所有 fetch_method=='ecb' 且 availability=='scripted' 且有 ecb 配置的输入。
    llm 项诚实跳过计数。only 给定时只抓名字在其中的项。失败记 record_fetch_error 计数，不连累其余。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped_todo = skipped_llm = failed = 0
    for e in data["inputs"]:
        if e.get("fetch_method") != "ecb":
            continue
        if only is not None and e["name"] not in only:
            continue
        avail = e.get("availability")
        if avail == "llm":
            skipped_llm += 1
            continue
        if avail != "scripted" or not e.get("ecb"):
            skipped_todo += 1
            continue
        try:
            val, as_of = fetch_by_ecb(e["ecb"], client=client)
        except Exception as exc:
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"ecb 未取到值（源结构变更或缺腿）: mode={e['ecb'].get('mode')}")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        fetched += 1
    return {"fetched": fetched, "skipped_todo": skipped_todo,
            "skipped_llm": skipped_llm, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:  # 活体冒烟：日频 EUR 3M OIS 混合
        v, d = fetch_by_ecb({"mode": "hybrid_3m_ois",
                             "ois_key": "B.U2._X._Z.S1ZV._Z.O._X.WR._X.FE._Z._Z.EUR._Z",
                             "estr_key": "B.EU000A2X2A25.WT"})
        print(f"EUR 3M OIS (hybrid): {v} @ {d}")
        return
    slug = argv[0]
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    print(f"ecb 抓取: {run_ecb_fetch(slug, variant)}")


if __name__ == "__main__":
    main()
