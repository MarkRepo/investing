"""prism search — web prescan 完整流程封装。

封装顺序：
  1. build_search_queries → 枚举覆盖槽
  2. 对每条 query 调 WebSearch/exa（由调用方提供搜索结果）
  3. register_web_search_batch → 落盘 + 去重
  4. H2 救回（drop_ratio > 0.8 时，对 dropped_hits 调 extract_url_features）
  5. check_prescan_health → 返回健康摘要

调用方负责真实 WebSearch 调用（本文件不直接调 LLM 工具），把 hits list 传给
run_search_batch。这样可在 LLM agent 层面逐 query 调用，也可在测试中 mock hits。

典型 agent 用法（伪代码）：
    from prism.scripts.search import build_queries, run_search_batch, prescan_summary
    queries = build_queries(slug, variant)
    for q in queries:
        hits = web_search(q["query"])  # LLM agent 调 WebSearch
        result = run_search_batch(slug, variant, q, hits)
        if result["needs_h2_rescue"]:
            rescued = rescue_h2(slug, variant, q, result["dropped_hits"])
    summary = prescan_summary(slug, variant, queries)

设计约束：零 LLM、零新业务逻辑——只组合 web_prescan.py 中的既有函数。
"""
from __future__ import annotations

from typing import Any


# --------------------------------------------------------------------------- #
# 查询槽枚举                                                                   #
# --------------------------------------------------------------------------- #

def build_queries(slug: str, variant: str, recency_days: int = 90) -> list[dict]:
    """返回本次 prescan 需要覆盖的搜索 query 列表。

    每个 dict 的 key：query / ring_codes / priority / triggered_by 等。
    直接代理到 web_prescan.build_search_queries，保持签名一致。
    """
    from prism.scripts.web_prescan import build_search_queries
    return build_search_queries(slug, variant, recency_days=recency_days)


# --------------------------------------------------------------------------- #
# 单批次落盘                                                                   #
# --------------------------------------------------------------------------- #

def run_search_batch(
    slug: str,
    variant: str,
    query_spec: dict,
    hits: list[dict],
    full_texts: dict[str, str] | None = None,
    inline_finding: dict | None = None,
) -> dict:
    """把一条 query 的搜索结果入库，返回入库摘要 + H2 救回提示。

    参数：
      query_spec: build_queries 返回列表中的单条 dict（含 query / triggered_by / rings 等）
      hits: WebSearch/exa 真实返回的命中列表（每项含 url/title/snippet）
      full_texts: {url: full_text} 可选（有 full text 时直接写 finding）
      inline_finding: 可选 inline finding dict（同 register_web_search_batch 协议）

    返回 dict（是 register_web_search_batch 的原始返回值的超集）：
      n_high, n_mid, n_low, mat_ids, n_dropped_invalid, n_dropped_low,
      drop_ratio, dropped_hits, silent_failure, failure_mode,
      needs_h2_rescue (bool, 新增),
      h2_hint (str, 新增, 说明如何做 H2 救回)
    """
    from prism.scripts.web_prescan import (
        register_web_search_batch,
        log_search_skipped,
    )

    query_str = query_spec.get("query", "")
    triggered_by = query_spec.get("triggered_by", "00-prescan")
    rings = query_spec.get("rings") or query_spec.get("ring_codes")
    addresses = query_spec.get("addresses")

    if not hits:
        log_search_skipped(
            slug, variant, query_str, triggered_by,
            n_results=0, reason="hits list empty"
        )
        return {
            "n_high": 0, "n_mid": 0, "n_low": 0, "mat_ids": [],
            "n_dropped_invalid": 0, "n_dropped_low": 0,
            "drop_ratio": 0.0, "dropped_hits": [],
            "silent_failure": False, "failure_mode": "upstream_empty",
            "needs_h2_rescue": False, "h2_hint": "",
        }

    result = register_web_search_batch(
        slug=slug,
        variant=variant,
        query=query_str,
        addresses=addresses or [],
        triggered_by=triggered_by,
        hits=hits,
        full_texts=full_texts,
        inline_finding=inline_finding,
        rings=rings,
    )

    # H2 rescue hint (F9 / A3)
    drop_ratio = result.get("drop_ratio", 0.0)
    failure_mode = result.get("failure_mode", "none")
    dropped_hits = result.get("dropped_hits", [])
    needs_h2 = drop_ratio > 0.8 and failure_mode == "all_low_band" and bool(dropped_hits)

    h2_hint = ""
    if needs_h2:
        h2_hint = (
            f"F9 警告：drop_ratio={drop_ratio:.0%}，{len(dropped_hits)} 条命中被丢弃（all_low_band）。"
            f"请调 rescue_h2() 对 dropped_hits 做 LLM tier 判定后重新 register。"
        )

    return {
        **result,
        "needs_h2_rescue": needs_h2,
        "h2_hint": h2_hint,
    }


# --------------------------------------------------------------------------- #
# H2 救回                                                                      #
# --------------------------------------------------------------------------- #

def rescue_h2(
    slug: str,
    variant: str,
    query_spec: dict,
    dropped_hits: list[dict],
) -> dict:
    """对被丢弃的 hits 做 domain_tier LLM 判定，重新 register 官方/高可信结果。

    返回：{n_rescued, mat_ids, skipped}
    调用方负责已有 extract_url_features 的 LLM tier 判定结果时把 domain_tier 填入
    dropped_hits 后再传入本函数。本函数只做 register 入库，不调 LLM。
    """
    from prism.scripts.web_prescan import register_web_search_batch

    query_str = query_spec.get("query", "")
    triggered_by = query_spec.get("triggered_by", "00-prescan") + "-h2"
    rings = query_spec.get("rings") or query_spec.get("ring_codes")
    addresses = query_spec.get("addresses") or []

    # 只 register domain_tier 已被 LLM 判定为官方/高可信的
    rescue_hits = [
        h for h in dropped_hits
        if h.get("domain_tier") in ("llm-judged-official", "official", "tier1", "tier2")
    ]
    skipped = len(dropped_hits) - len(rescue_hits)

    if not rescue_hits:
        return {"n_rescued": 0, "mat_ids": [], "skipped": skipped}

    result = register_web_search_batch(
        slug=slug,
        variant=variant,
        query=query_str,
        addresses=addresses,
        triggered_by=triggered_by,
        hits=rescue_hits,
        rings=rings,
    )
    mat_ids = result.get("mat_ids", [])
    return {"n_rescued": len(mat_ids), "mat_ids": mat_ids, "skipped": skipped}


# --------------------------------------------------------------------------- #
# 健康检查                                                                      #
# --------------------------------------------------------------------------- #

def prescan_summary(
    slug: str,
    variant: str,
    queries: list[dict],
    triggered_by_prefix: str = "00-prescan",
) -> dict:
    """跑 prescan 健康检查，返回覆盖率/失血率摘要。

    queries: build_queries 的返回值（用于 expected_queries 参数）。
    返回 check_prescan_health 的原始 dict（含 coverage_pct / n_healthy / n_low_band 等）。
    """
    from prism.scripts.web_prescan import check_prescan_health

    expected_queries = [q.get("query", "") for q in queries]
    return check_prescan_health(
        slug=slug,
        variant=variant,
        expected_queries=expected_queries,
        triggered_by_prefix=triggered_by_prefix,
    )
