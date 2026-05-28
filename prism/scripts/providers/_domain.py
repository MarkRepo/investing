"""Domain tier 黑名单（H2 设计：脚本只做 deterministic 黑名单，不替 LLM 判权威源）。

历史：早期版本含 GENERIC_AUTHORITATIVE_HOSTS + CLUSTER_AUTHORITATIVE_HOSTS 白名单，
但 H2 教训（参 memory/feedback_prescan_domain_tier.md）确认主观分类应交由主 agent LLM，
脚本只保留"明确低信噪"黑名单。2026-05-28 删除白名单，简化为单一黑名单。
"""
from __future__ import annotations

LOW_SIGNAL_HOSTS = frozenset({
    "x.com", "twitter.com", "youtube.com", "youtu.be",
    "reddit.com", "facebook.com", "instagram.com",
    "tiktok.com", "weibo.com",
})


def classify_hit_domain_tier(url: str) -> str | None:
    """根据 url hostname 预判 domain_tier。

    Returns:
        'other' — 命中黑名单（社交媒体等低信噪源）
        None    — 不预判，让 register_web_search_result 走 LLM 判断流程
    """
    from urllib.parse import urlparse
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return None
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]

    if host in LOW_SIGNAL_HOSTS:
        return "other"

    return None
