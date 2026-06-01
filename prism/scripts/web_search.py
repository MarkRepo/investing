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
        min_score: float = 0.3,
    ):
        self.providers = providers
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
            tier = classify_hit_domain_tier(h.url)
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
    try:
        from prism.scripts.providers.exa import ExaProvider
        out.append(ExaProvider())
    except (RuntimeError, ValueError):
        pass
    try:
        from prism.scripts.providers.serper import SerperProvider
        out.append(SerperProvider())
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
    s.add_argument("--include-domains", default=None, help="comma-separated")
    s.add_argument("--exclude-domains", default=None)
    s.add_argument("--need-extract", action="store_true")
    s.add_argument("--output", choices=["stdout", "sidecar"], default="stdout")
    s.add_argument("--slug", default=None)
    s.add_argument("--variant", default=None)
    s.add_argument("--triggered-by", default=None)
    s.add_argument("--addresses", default=None, help="comma-separated")

    pp = sub.add_parser("postprocess",
                        help="postprocess external hits from WebSearch fallback")
    pp.add_argument("--source", default="websearch_fallback",
                    help="source_provider tag for these hits")
    pp.add_argument("--query", required=True)
    pp.add_argument("--slug", required=True)
    pp.add_argument("--variant", required=True)
    pp.add_argument("--triggered-by", required=True)
    pp.add_argument("--addresses", default="")

    sub.add_parser("status", help="show key pool status across providers")

    rd = sub.add_parser(
        "review-digest",
        help="紧凑 index 投影一个 _websearch_raw sidecar（判 tier 不爆上下文）",
    )
    rd.add_argument("--raw-path", default=None,
                    help="search --output=sidecar 写回的 raw_path（相对/绝对皆可）")
    rd.add_argument("--slug", default=None,
                    help="兜底：无 --raw-path 时取 topics/{slug}/inbox/_websearch_raw 最新 json")
    rd.add_argument("--variant", default=None,
                    help="仅用于 family-aware 白名单判定（不参与路径解析）")
    rd.add_argument("--show", default=None,
                    help="逗号分隔 hit 下标，展开其 snippet 整段（默认无则只打 index）")
    rd.add_argument("--full", action="store_true",
                    help="与 --show 连用：额外展开该 hit 的 raw_content 整段")
    return p


def _cmd_search(args) -> int:
    providers = _default_providers()
    if not providers:
        sys.stderr.write(json.dumps({
            "status": "config_error",
            "reason": "no provider configured (check API keys)",
        }) + "\n")
        return EXIT_CONFIG

    adp = WebSearchAdapter(providers)
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

    # ---- sidecar 模式（H2-compliance 修法 2026-05-28）----
    # 不调 register_web_search_batch！原因：adapter 不该替 LLM 做 tier 判断。
    # 全部 hit 写到 prism/topics/{slug}/inbox/_websearch_raw/{ts}_{query_hash}.json
    # 主 agent 读 raw 文件 → 自行判 tier → 调 register_web_search_batch 走 H2 救回。
    # 之前的"sidecar 自动 register"会让非 WHITELIST hit 全 'other' tier → low band drop，
    # 实质架空 H2 救回；改为只持久化 raw 数据。
    if not all([args.slug, args.variant, args.triggered_by]):
        sys.stderr.write(json.dumps({
            "status": "config_error",
            "reason": "--output=sidecar 需要 --slug --variant --triggered-by",
        }) + "\n")
        return EXIT_CONFIG

    import hashlib
    from datetime import datetime, timezone
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    raw_dir = (repo_root / "prism" / "topics" / args.slug
               / "inbox" / "_websearch_raw")
    raw_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    qhash = hashlib.md5(args.query.encode("utf-8")).hexdigest()[:8]
    raw_path = raw_dir / f"{ts}_{qhash}.json"
    addresses = [a for a in args.addresses.split(",") if a] if args.addresses else []
    payload = {
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "query": args.query,
        "intent": args.intent,
        "days": args.days,
        "slug": args.slug,
        "variant": args.variant,
        "triggered_by": args.triggered_by,
        "addresses": addresses,
        "n_hits": len(hits),
        "hits": [h.to_dict() for h in hits],
    }
    raw_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    sys.stdout.write(json.dumps({
        "status": "sidecar_written",
        "raw_path": str(raw_path.relative_to(repo_root)),
        "n_hits": len(hits),
        "next_step": (
            "主 agent 读 raw 文件 → 判 tier → 调 register_web_search_batch（H2 救回）"
        ),
    }, ensure_ascii=False, indent=2))
    return EXIT_OK if hits else EXIT_NO_HITS


def _cmd_postprocess(args) -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.stderr.write(json.dumps({"status": "no_input"}) + "\n")
        return EXIT_CONFIG
    items = json.loads(raw)
    hits = [
        Hit(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("snippet", ""),
            score=item.get("score"),
            raw_content=item.get("raw_content"),
            source_provider=args.source,
        )
        for item in items
    ]
    adp = WebSearchAdapter(providers=[])
    processed = adp.postprocess_external_hits(hits)

    from prism.scripts import web_prescan
    addresses = [a for a in args.addresses.split(",") if a]
    result = web_prescan.register_web_search_batch(
        slug=args.slug,
        variant=args.variant,
        query=args.query,
        addresses=addresses,
        triggered_by=args.triggered_by,
        hits=[h.to_dict() for h in processed],
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_OK


def _cmd_review_digest(args) -> int:
    """紧凑、无损、领域中立地投影一个 _websearch_raw sidecar，供主 agent 判 tier。

    判 tier 是 LLM 的活（留在对话里）；本命令只做机械切片 + 惰性展开，绝不替主
    agent 判 tier、绝不按内容截选（避免把 F5 修成新 F3）：
      - 默认 = index：每条 hit 一行
        ``[idx] WL=Y/N host tld_class | title | snip=NNN raw=NNN/none [flags]``
        —— 零正文，不灌 snippet/raw_content 进上下文。flags 透传确定性特征
        （low_signal/pdf/announce/sub:*）+ provider 已设的 domain_tier + published_at。
      - ``--show IDX[,IDX]``：展开指定 hit 的 snippet 整段（引擎给定，原样不截）。
      - ``--show --full``：额外展开该 hit 的 raw_content 整段；缺失则提示走 WebFetch。

    特征复用 ``web_prescan.extract_url_features``（确定性，从不返回 tier/confidence）。
    """
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]

    # 1. 解析 raw json 路径：--raw-path 优先；否则 --slug 取 _websearch_raw 最新
    raw_path: Path | None = None
    auto_picked = False        # 是否走 --slug 自动选（非显式 --raw-path）
    n_candidates = 0           # --slug 模式下同目录候选数（>1 时自动选有歧义）
    if args.raw_path:
        p = Path(args.raw_path)
        raw_path = p if p.is_absolute() else (repo_root / p)
    elif args.slug:
        raw_dir = (repo_root / "prism" / "topics" / args.slug
                   / "inbox" / "_websearch_raw")
        candidates = sorted(raw_dir.glob("*.json")) if raw_dir.is_dir() else []
        n_candidates = len(candidates)
        if candidates:
            raw_path = candidates[-1]  # 名字 {ts}_{qhash}，ts ISO 可排序 → 末位最新
            auto_picked = True
    if raw_path is None or not raw_path.is_file():
        sys.stderr.write(json.dumps({
            "status": "config_error",
            "reason": f"raw json 不存在（--raw-path / --slug 二选一）: "
                      f"{args.raw_path or args.slug}",
        }, ensure_ascii=False) + "\n")
        return EXIT_CONFIG

    payload = json.loads(raw_path.read_text(encoding="utf-8"))
    hits = payload.get("hits") or []
    slug = payload.get("slug")
    variant = payload.get("variant")

    # 2. --show：惰性展开指定记录（整段，不截选）
    if args.show is not None:
        try:
            idxs = [int(x) for x in args.show.split(",") if x.strip() != ""]
        except ValueError:
            sys.stderr.write(json.dumps({
                "status": "config_error",
                "reason": f"--show 需逗号分隔整数: {args.show!r}",
            }, ensure_ascii=False) + "\n")
            return EXIT_CONFIG
        # 溯源横幅（[adapter-snippet] 修）：把"在 digest 哪个 raw / 哪条 query / 有几条 hit"
        # 显式打到 stdout。两个作用：①--slug 自动选恒取最新 json，prescan 多 query 秒级
        # 连发时易选错查询——横幅让选错一眼可见，不再靠重试盲猜；②即便 idx 越界（下方），
        # stdout 也已有内容，不再"静默空输出"（错误走 stderr，被 `| sed`/`head` 丢弃时看着像空）。
        banner = (
            f"# raw: {raw_path.name}  query: {payload.get('query')!r}  "
            f"n_hits: {len(hits)}"
        )
        if auto_picked and n_candidates > 1:
            banner += (
                f"  ⚠ --slug 自动选了 {n_candidates} 个 raw 里的最新一个；"
                f"若非你要的 query，请改用 --raw-path 显式指定"
            )
        sys.stdout.write(banner + "\n")
        out: list[str] = []
        for idx in idxs:
            if idx < 0 or idx >= len(hits):
                # 同时落 stdout（可见，防 `| sed` 丢 stderr 时看着像空）+ stderr（机读）
                msg = (
                    f"[idx {idx} 越界：该 raw 仅 {len(hits)} 条 hit]"
                    + ("  ← --slug 可能选到了空/别的 query，用 --raw-path 指定"
                       if auto_picked else "")
                )
                sys.stdout.write(msg + "\n")
                sys.stderr.write(json.dumps({
                    "status": "config_error",
                    "reason": f"idx {idx} 越界（n_hits={len(hits)}）",
                }, ensure_ascii=False) + "\n")
                return EXIT_CONFIG
            h = hits[idx]
            out.append(f"===== [{idx}] {(h.get('title') or '').strip()} =====")
            out.append(f"URL: {h.get('url', '')}")
            if args.full:
                raw = h.get("raw_content")
                if raw:
                    out.append("\n--- raw_content (整段) ---")
                    out.append(raw)
                else:
                    out.append(
                        "\n[raw_content 缺失（搜索时未 --need-extract）→ "
                        "用 WebFetch 抓该 url 全文]"
                    )
            else:
                out.append("\n--- snippet (整段) ---")
                out.append(h.get("snippet") or "")
            out.append("")
        sys.stdout.write("\n".join(out) + "\n")
        return EXIT_OK

    # 3. 默认 = index 投影（零正文）
    from prism.scripts.web_prescan import extract_url_features
    urls = [h.get("url", "") for h in hits]
    feats = extract_url_features(urls, slug, variant)

    rp_disp = (raw_path.relative_to(repo_root)
               if raw_path.is_relative_to(repo_root) else raw_path)
    lines = [
        f"raw_path: {rp_disp}",
        f"query: {payload.get('query')!r}  intent: {payload.get('intent')}  "
        f"addresses: {payload.get('addresses')}  triggered_by: {payload.get('triggered_by')}",
        f"n_hits: {len(hits)}  （--show IDX 展开 snippet；--show IDX --full 展开 raw_content）",
        "",
    ]
    for idx, h in enumerate(hits):
        url = h.get("url", "")
        f = feats.get(url, {})
        wl = "Y" if f.get("in_whitelist") else "N"
        host = f.get("host") or "?"
        tld = f.get("tld_class") or "?"
        snip_len = len(h.get("snippet") or "")
        raw = h.get("raw_content")
        raw_repr = str(len(raw)) if raw else "none"
        title = (h.get("title") or "").replace("\n", " ").strip()
        flags: list[str] = []
        if f.get("known_low_signal_host"):
            flags.append("low_signal")
        if f.get("path_is_pdf"):
            flags.append("pdf")
        if f.get("path_announce_tokens"):
            flags.append("announce")
        if f.get("subdomain_tokens"):
            flags.append("sub:" + "/".join(f["subdomain_tokens"]))
        if h.get("domain_tier"):
            flags.append(f"tier={h['domain_tier']}")
        if h.get("published_at"):
            flags.append(f"pub={h['published_at']}")
        flag_str = ("  [" + " ".join(flags) + "]") if flags else ""
        lines.append(
            f"[{idx}] WL={wl} {host} {tld} | {title} | "
            f"snip={snip_len} raw={raw_repr}{flag_str}"
        )
    sys.stdout.write("\n".join(lines) + "\n")
    return EXIT_OK


def _cmd_status() -> int:
    providers = _default_providers()
    if not providers:
        sys.stderr.write(json.dumps({"status": "config_error"}) + "\n")
        return EXIT_CONFIG
    for p in providers:
        if not hasattr(p, "pool"):
            continue
        s = p.pool.status()
        active = sum(1 for k in s["keys"]
                     if not k["disabled"] and not k["cooldown_until"])
        used_total = sum(k["used_today"] for k in s["keys"])
        cap_total = s["free_quota"] * len(s["keys"])
        sys.stdout.write(
            f"{s['provider']}: {len(s['keys'])} keys, "
            f"{active} active, today {used_total}/{cap_total} "
            f"({used_total // len(s['keys'])}/{s['free_quota']} avg)\n"
        )
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.cmd == "search":
        return _cmd_search(args)
    if args.cmd == "postprocess":
        return _cmd_postprocess(args)
    if args.cmd == "review-digest":
        return _cmd_review_digest(args)
    if args.cmd == "status":
        return _cmd_status()
    return EXIT_CONFIG


if __name__ == "__main__":
    sys.exit(main())
