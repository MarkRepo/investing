from __future__ import annotations

import json
import sys
from urllib.parse import urlparse, urlunparse

from prism.scripts.providers.base import Hit, ProviderError
from prism.scripts.providers._domain import classify_hit_domain_tier
from prism.scripts.router import classify_intent, rank_providers


def _canonical_url(url: str) -> str:
    """去 query 中的 tracking 参数（utm_*, fbclid 等）。"""
    parsed = urlparse(url)
    query = "&".join(
        kv for kv in parsed.query.split("&")
        if kv and not kv.split("=")[0].lower().startswith(("utm_", "fbclid", "gclid"))
    )
    return urlunparse(parsed._replace(query=query, fragment=""))


class WebSearchAdapter:
    def __init__(
        self,
        providers: list,
        *,
        cluster: str | None = None,
        min_score: float = 0.3,
    ):
        self.providers = providers
        self.cluster = cluster
        self.min_score = min_score

    def search(
        self,
        query: str,
        *,
        intent: str | None = None,
        max_results: int = 5,
        days: int | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        need_extract: bool = False,
    ) -> list[Hit]:
        intent = intent or classify_intent(query)
        ranked = rank_providers(self.providers, intent=intent)
        if not ranked:
            raise RuntimeError(f"no healthy provider for intent={intent}")

        last_err: Exception | None = None
        for p in ranked:
            try:
                hits = p.search(
                    query,
                    max_results=max_results,
                    days=days,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                    need_extract=need_extract,
                )
            except ProviderError as e:
                last_err = e
                continue
            if not hits:
                continue
            top = max((h.score or 0.0) for h in hits)
            if top < self.min_score:
                continue
            return self._postprocess(hits)

        raise RuntimeError(
            f"all providers exhausted for query={query!r}: {last_err}"
        )

    def _postprocess(self, hits: list[Hit]) -> list[Hit]:
        seen: set[str] = set()
        out: list[Hit] = []
        for h in hits:
            canon = _canonical_url(h.url)
            if canon in seen:
                continue
            seen.add(canon)
            tier = classify_hit_domain_tier(h.url, cluster=self.cluster)
            if tier:
                h.domain_tier = tier
            out.append(h)
        return out

    def postprocess_external_hits(self, hits: list[Hit]) -> list[Hit]:
        """供 WebSearch fallback 使用：吃外部 hit list，跑 dedup + domain_tier。"""
        return self._postprocess(hits)
