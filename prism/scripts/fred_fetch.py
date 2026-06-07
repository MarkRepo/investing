"""FRED 自动抓取（第二期）。零 LLM：读登记表里 fetch_method==fred-api 的输入，
拉最新观测，调 macro_registry.record_observation 落 observed。单测 mock httpx。"""
from __future__ import annotations

import os
import sys

import httpx

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def get_fred_api_key() -> str:
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY 未设置（见 .env.example）")
    return key


def fetch_latest_observation(series_id: str, *, client=None) -> tuple[float | None, str | None]:
    """拉某 FRED series 的最新一条观测。返回 (value, as_of)；缺测/无数据返回 (None, date|None)。
    client 可注入（测试 mock）；默认用 httpx。"""
    params = {
        "series_id": series_id,
        "api_key": get_fred_api_key(),
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(FRED_BASE, params=params, timeout=30)
        resp.raise_for_status()
        obs = resp.json().get("observations") or []
    finally:
        if owns:
            client.close()
    if not obs:
        return None, None
    rec = obs[0]
    raw = rec.get("value")
    as_of = rec.get("date")
    if raw in (None, "", "."):
        return None, as_of
    try:
        return float(raw), as_of
    except ValueError:
        return None, as_of


from prism.scripts import macro_registry as reg

# 净流动性派生：name → (被减项构成)
_NET_LIQ_NAME = "净流动性(=资产−TGA−RRP)"
_NET_LIQ_PARTS = ("美联储资产 WALCL(QT 节奏)", "TGA 余额", "RRP 逆回购")  # assets, minus, minus


def run_fred_fetch(slug: str, variant: str, *, client=None) -> dict:
    """抓所有 fetch_method==fred-api 且有 fred_series_id 的输入，落 observed。
    __DERIVED__（净流动性）在常规抓取后由构成项计算。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped = derived = failed = 0
    values: dict[str, float | None] = {}

    for e in data["inputs"]:
        if e.get("fetch_method") != "fred-api":
            skipped += 1
            continue
        sid = e.get("fred_series_id")
        if not sid or sid == "__DERIVED__":
            continue
        val, as_of = fetch_latest_observation(sid, client=client)
        if val is None:
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        values[e["name"]] = val
        fetched += 1

    # 净流动性派生
    assets, tga, rrp = (values.get(n) for n in _NET_LIQ_PARTS)
    if None not in (assets, tga, rrp):
        nl = assets - tga - rrp
        reg.record_observation(slug, variant, _NET_LIQ_NAME, value=nl)
        derived += 1

    return {"fetched": fetched, "derived": derived, "skipped": skipped, "failed": failed}


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    summary = run_fred_fetch(slug, variant)
    print(f"FRED 抓取: {summary}")


if __name__ == "__main__":
    main()
