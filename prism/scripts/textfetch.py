"""取文通道：登记表驱动的原文下载（零 LLM）。

与 fred_fetch / recipe_fetch 平行——后两者抓「数值」(observed.value)；本通道抓「原文」
存本地缓存(local_cache_path)，供 headless LLM 以 Read 判读立场（鹰鸽/松紧）。立场判读仍需 LLM，
故取文源的 availability 仍是 llm/scriptable_todo，不是 scripted。

各源抓法不同（FOMC 走 Fed 日历页、别的源走别的索引/解析），故**按每条输入的 text_fetch 字段
路由到对应 fetcher**，而非「检测到取文类就跑那个唯一实现」。加新取文源 =
  (1) 写一个 fetch_one(slug, variant, entry) -> dict（自行下载、写 local_cache_path、回 fingerprint）
  (2) 注册进 _FETCHERS
  (3) 登记表给该输入加 text_fetch: <key>
之后它自动进「批量刷新」+ 定时巡检 + 去重门，无需再改路由/调度器。

fetcher 契约：fetch_one(slug, variant, entry, *, client=None) -> dict，至少含
  ok: bool          本次是否抓到（批量计数读它）
  fingerprint: str  稳定身份指纹（去重门据此判内容是否变化；各源自报，如 FOMC=声明/纪要 URL）
并负责调 reg.set_local_cache_path 写回该 entry 的缓存路径。
"""
from __future__ import annotations

import sys

from prism.scripts import china_us_fetch
from prism.scripts import fomc_fetch
from prism.scripts import hfcaa_fetch
from prism.scripts import macro_registry as reg
from prism.scripts import politburo_fetch
from prism.scripts import qra_fetch

# text_fetch 取值 → 该源的 fetcher。键须 ⊆ macro_registry.VALID_TEXT_FETCH（validator 据后者校验登记表）。
_FETCHERS = {
    "fomc": fomc_fetch.fetch_one,
    "qra": qra_fetch.fetch_one,
    "china_us": china_us_fetch.fetch_one,
    "hfcaa": hfcaa_fetch.fetch_one,
    "politburo": politburo_fetch.fetch_one,
}


def fetch_entry(slug: str, variant: str, entry: dict, *, client=None) -> dict | None:
    """按 entry['text_fetch'] 路由到对应 fetcher 抓一条。非取文项（无 text_fetch 或未注册）→ None。
    web fetch-llm 预抓单条用：拿回该项自己的 fingerprint（不再假设全局单源同一指纹）。"""
    fn = _FETCHERS.get(entry.get("text_fetch"))
    if fn is None:
        return None
    return fn(slug, variant, entry, client=client)


def run_textfetch(slug: str, variant: str, *, client=None,
                  only: set[str] | None = None) -> dict:
    """抓所有带 text_fetch（且已注册 fetcher）的输入，逐条按 text_fetch 路由。零 LLM。
    only 给定时只抓名字在其中的项（web 单条手动抓取用）；缺省抓全部。
    返回 {name: fetcher 结果 dict}；单条失败吞掉记 {"error": ...}，不毁整批。"""
    data = reg.read_registry(slug, variant)
    results: dict[str, dict] = {}
    for e in data.get("inputs") or []:
        if not e.get("text_fetch"):
            continue
        if only is not None and e["name"] not in only:
            continue
        if e["text_fetch"] not in _FETCHERS:
            msg = f"未注册的 text_fetch: {e['text_fetch']!r}"
            results[e["name"]] = {"error": msg}
            reg.record_fetch_error(slug, variant, e["name"], msg=msg)
            continue
        try:
            res = _FETCHERS[e["text_fetch"]](slug, variant, e, client=client)
            results[e["name"]] = res
        except Exception as exc:                       # 网络/解析失败：记一行、跳过，不连累其余取文源
            results[e["name"]] = {"error": str(exc)}
            reg.record_fetch_error(slug, variant, e["name"], msg=str(exc))
            continue
        # 失败标记持久化到 observed（fred/recipe 走 record_observation 自动清，取文不调它故在此显式清/记）
        if res.get("error") or not res.get("ok"):
            reg.record_fetch_error(slug, variant, e["name"],
                                   msg=res.get("error") or "取文未成功（fetcher 返回 ok=False）")
        else:
            reg.record_fetch_error(slug, variant, e["name"], msg=None)  # 成功 → 清错
    return results


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    slug = argv[0] if len(argv) > 0 else "global-macro-rates-liquidity"
    variant = argv[1] if len(argv) > 1 else "opus4.8"
    out = run_textfetch(slug, variant)
    if not out:
        print("无取文项（无输入设 text_fetch）")
        return
    for name, res in out.items():
        if res.get("error"):
            print(f"✗ {name}: {res['error']}")
        else:
            print(f"{'✓' if res.get('ok') else '✗'} {name}: fp={res.get('fingerprint')} cache={res.get('cache_path')}")


if __name__ == "__main__":
    main()
