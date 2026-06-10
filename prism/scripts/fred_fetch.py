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


def _apply_op(op: str, vals: list[float]) -> float:
    """通用派生算子：sub=首项依次减后项；add=求和。未知抛 ValueError（不静默）。"""
    if op == "sub":
        r = vals[0]
        for v in vals[1:]:
            r -= v
        return r
    if op == "add":
        return sum(vals)
    raise ValueError(f"未知 derived.op: {op!r}（支持 sub/add）")


def run_fred_fetch(slug: str, variant: str, *, client=None,
                   only: set[str] | None = None) -> dict:
    """抓所有 fetch_method==fred-api 且有 fred_series_id 的输入，落 observed。
    派生项（fred_series_id=='__DERIVED__'）在常规抓取后计算：
      - 带 derived:{op, series:[...]} 的，直接拉各 FRED series 按 op 算（如 SOFR−IORB）；
      - 净流动性按构成输入名（WALCL/TGA/RRP 的已抓值）算。
    only 给定时只抓名字在其中的项（web 单条手动抓取用）；缺省抓全部。返回 summary。"""
    data = reg.read_registry(slug, variant)
    fetched = skipped = derived = failed = 0
    values: dict[str, float | None] = {}

    for e in data["inputs"]:
        if e.get("fetch_method") != "fred-api":
            skipped += 1
            continue
        if only is not None and e["name"] not in only:
            continue
        sid = e.get("fred_series_id")
        if not sid or sid == "__DERIVED__":
            continue
        try:
            val, as_of = fetch_latest_observation(sid, client=client)
        except Exception as exc:           # HTTP/网络异常：记错、跳过，不连累其余 series
            reg.record_fetch_error(slug, variant, e["name"], msg=f"{sid}: {exc}")
            failed += 1
            continue
        if val is None:
            reg.record_fetch_error(slug, variant, e["name"], msg=f"{sid}: API 返回空值")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=val, as_of=as_of)
        values[e["name"]] = val
        fetched += 1

    # 通用派生：derived:{op, series} —— 直接拉各 series（缓存避免重复请求）后按 op 计算
    series_cache: dict[str, float | None] = {}

    def _series(sid: str) -> float | None:
        if sid not in series_cache:
            try:
                v, _ = fetch_latest_observation(sid, client=client)
            except Exception:              # 异常等同取不到，归一为 None；具体记错在派生项处
                v = None
            series_cache[sid] = v
        return series_cache[sid]

    for e in data["inputs"]:
        if e.get("fetch_method") != "fred-api" or e.get("fred_series_id") != "__DERIVED__":
            continue
        if only is not None and e["name"] not in only:
            continue
        spec = e.get("derived")
        if not spec:
            continue
        series_ids = spec.get("series") or []
        legs = [_series(s) for s in series_ids]
        if not legs or any(v is None for v in legs):
            missing = [s for s, v in zip(series_ids, legs) if v is None] or ["无 series 配置"]
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=f"派生腿取数失败: {', '.join(missing)}")
            failed += 1
            continue
        reg.record_observation(slug, variant, e["name"], value=_apply_op(spec.get("op"), legs))
        derived += 1

    # 净流动性派生（按构成输入名，非 series）
    assets, tga, rrp = (values.get(n) for n in _NET_LIQ_PARTS)
    if (only is None or _NET_LIQ_NAME in only) and None not in (assets, tga, rrp):
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
