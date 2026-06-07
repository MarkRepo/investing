"""联网 smoke：逐个验证登记表 fred_series_id 能否从 FRED 解析。
用法：FRED_API_KEY=... python -m prism.scripts.fred_smoke
非单元测试（需 key + 网络）。"""
from __future__ import annotations

from prism.scripts import fred_fetch
from prism.scripts import macro_registry as reg

SLUG, VAR = "global-macro-rates-liquidity", "opus4.8"
PROXY_NOTE = {"DTWEXAFEGS": "DXY 代理（非 ICE 真 DXY）"}


def main():
    data = reg.read_registry(SLUG, VAR)
    ok = bad = 0
    for e in data["inputs"]:
        sid = e.get("fred_series_id")
        if not sid or sid == "__DERIVED__":
            continue
        try:
            val, as_of = fred_fetch.fetch_latest_observation(sid)
            status = "OK " if val is not None else "空值"
            ok += val is not None
            bad += val is None
        except Exception as ex:  # noqa: BLE001
            status, as_of, val = f"ERR {ex}", "-", "-"
            bad += 1
        note = PROXY_NOTE.get(sid, "")
        print(f"[{status}] {sid:14s} {e['name']:30s} val={val} asof={as_of} {note}")
    print(f"\n解析成功 {ok} / 失败或空 {bad}")


if __name__ == "__main__":
    main()
