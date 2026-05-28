"""Tavily Web Search 兼容 shim — 旧入口转发到 providers.tavily。

历史调用方（如 prism/scripts/web_prescan.py 的旧路径）保留 import 兼容。
新代码请直接 from prism.scripts.providers.tavily import TavilyProvider。
"""
from __future__ import annotations

from prism.scripts.providers._domain import (
    LOW_SIGNAL_HOSTS,
    classify_hit_domain_tier,
)
from prism.scripts.providers.tavily import TavilyProvider


def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_raw_content: bool = False,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    days: int | None = None,
    timeout_s: int = 30,
) -> list[dict]:
    """旧 API：返回 list[dict]，schema 与 register_web_search_batch hits 对齐。"""
    p = TavilyProvider(timeout_s=timeout_s)
    hits = p.search(
        query,
        max_results=max_results,
        days=days,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        need_extract=include_raw_content,
        search_depth=search_depth,
    )
    return [h.to_dict() for h in hits]


def tavily_search_batch(
    queries: list[str],
    max_results_per_query: int = 5,
    search_depth: str = "basic",
    days: int | None = None,
) -> dict[str, list[dict]]:
    return {
        q: tavily_search(
            q,
            max_results=max_results_per_query,
            search_depth=search_depth,
            days=days,
        )
        for q in queries
    }


__all__ = [
    "tavily_search", "tavily_search_batch", "classify_hit_domain_tier",
    "LOW_SIGNAL_HOSTS",
]
