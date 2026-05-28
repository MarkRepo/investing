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


# ---------------- CLI ----------------

import argparse

EXIT_OK = 0
EXIT_PARTIAL = 10
EXIT_NO_HITS = 20
EXIT_DEGRADED = 30
EXIT_ALL_EXHAUSTED = 40
EXIT_CONFIG = 50


def _default_providers() -> list:
    """按可用 key 决定加载哪些 provider；缺 key 的 provider 跳过。"""
    out = []
    try:
        from prism.scripts.providers.tavily import TavilyProvider
        out.append(TavilyProvider())
    except (RuntimeError, ValueError):
        pass
    return out


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="web_search")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="run web search via adapter")
    s.add_argument("query")
    s.add_argument("--intent",
                   choices=["news", "semantic", "exact", "general",
                            "vertical:patent", "vertical:scholar",
                            "vertical:image", "vertical:map"],
                   default=None)
    s.add_argument("--max-results", type=int, default=5)
    s.add_argument("--days", type=int, default=None)
    s.add_argument("--cluster", default=None)
    s.add_argument("--include-domains", default=None, help="comma-separated")
    s.add_argument("--exclude-domains", default=None)
    s.add_argument("--need-extract", action="store_true")
    s.add_argument("--output", choices=["stdout", "sidecar"], default="stdout")
    s.add_argument("--slug", default=None)
    s.add_argument("--variant", default=None)
    s.add_argument("--triggered-by", default=None)
    s.add_argument("--addresses", default=None, help="comma-separated")
    return p


def _cmd_search(args) -> int:
    providers = _default_providers()
    if not providers:
        sys.stderr.write(json.dumps({
            "status": "config_error",
            "reason": "no provider configured (check API keys)",
        }) + "\n")
        return EXIT_CONFIG

    adp = WebSearchAdapter(providers, cluster=args.cluster)
    inc = args.include_domains.split(",") if args.include_domains else None
    exc = args.exclude_domains.split(",") if args.exclude_domains else None
    try:
        hits = adp.search(
            args.query,
            intent=args.intent,
            max_results=args.max_results,
            days=args.days,
            include_domains=inc,
            exclude_domains=exc,
            need_extract=args.need_extract,
        )
    except RuntimeError as e:
        sys.stderr.write(json.dumps({
            "status": "all_exhausted",
            "reason": str(e),
            "fallback_hint": "use_websearch_tool",
        }) + "\n")
        return EXIT_ALL_EXHAUSTED

    if args.output == "stdout":
        sys.stdout.write(json.dumps(
            [h.to_dict() for h in hits], ensure_ascii=False, indent=2,
        ))
        return EXIT_OK if hits else EXIT_NO_HITS

    if not all([args.slug, args.variant, args.triggered_by]):
        sys.stderr.write(json.dumps({
            "status": "config_error",
            "reason": "--output=sidecar 需要 --slug --variant --triggered-by",
        }) + "\n")
        return EXIT_CONFIG

    from prism.scripts.web_prescan import register_web_search_batch
    addresses = args.addresses.split(",") if args.addresses else []
    result = register_web_search_batch(
        slug=args.slug,
        variant=args.variant,
        query=args.query,
        addresses=addresses,
        triggered_by=args.triggered_by,
        hits=[h.to_dict() for h in hits],
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_OK if hits else EXIT_NO_HITS


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.cmd == "search":
        return _cmd_search(args)
    return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
