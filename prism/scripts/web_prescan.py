"""Web-search auto-ingest engine for prism. Zero LLM calls.

工作分工：
  - LLM 操作（WebSearch / WebFetch / 判断 confidence）由主 agent 在 workflow 里发起
  - 本脚本只做后处理：域名分类 / 写 inbox / 调 add_material / 更新 todo / 维护搜索日志

参考: feedback_llm_workflow.md
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

from prism.scripts import topic as topic_io
from prism.scripts.manifest import (
    add_material, make_search_meta, find_by_url, refresh_web_search_meta,
    mark_processed,
)

PRISM_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# WebSearch 并发限流常量（修 ISSUE-001）
# ---------------------------------------------------------------------------
# Anthropic WebSearch 有未文档化的窗口限流，超阈值不抛错只返空。本组常量是
# workflow 文档 + 主 agent 行为约束的 single source of truth。
WEB_SEARCH_BATCH_LIMIT = 5            # 单条消息最多并行的 WebSearch 调用数
WEB_SEARCH_BATCH_INTERVAL_S = 10      # 两批之间的最小间隔（秒）
WEB_SEARCH_SERIAL_RETRY_INTERVAL_S = 30  # 检测到限流后串行重试的间隔（秒）
WEB_SEARCH_FAIL_THRESHOLD = 0.5       # 优先 query 入库率 <50% → prescan_status='failed'

# ---------------------------------------------------------------------------
# 域名白名单 — 命中即 high confidence
# ---------------------------------------------------------------------------

WHITELIST_DOMAINS: set[str] = {
    # ---- 监管机构 ----
    "csrc.gov.cn", "sec.gov", "hkex.com.hk", "hkma.gov.hk",
    "cac.gov.cn", "pbc.gov.cn", "mof.gov.cn", "miit.gov.cn",
    "sac.net.cn", "amac.org.cn",
    "federalreserve.gov", "treasury.gov", "ustr.gov",
    "fca.org.uk", "bankofengland.co.uk",
    "esma.europa.eu", "ecb.europa.eu",
    "fsa.go.jp", "boj.or.jp",
    "dart.fss.or.kr", "fss.or.kr", "bok.or.kr",
    "mas.gov.sg",
    "ftc.gov", "fcc.gov", "doj.gov",
    "ec.europa.eu", "europarl.europa.eu", "ofcom.org.uk", "gov.uk",
    "meti.go.jp", "jftc.go.jp",
    # ---- 中国部委 + 行业协会 ----
    "gov.cn", "stats.gov.cn", "ndrc.gov.cn", "mofcom.gov.cn",
    "sasac.gov.cn", "customs.gov.cn", "mee.gov.cn", "mohurd.gov.cn",
    "chinatax.gov.cn",
    "caam.org.cn", "cnpia.org",
    # ---- 交易所 ----
    "sse.com.cn", "szse.cn", "bse.cn",
    "nasdaq.com", "nyse.com",
    "lseg.com", "londonstockexchange.com",
    "jpx.co.jp", "krx.co.kr",
    "asx.com.au", "tsx.com", "tmxmoney.com", "six-group.com",
    # ---- 国际组织 ----
    "imf.org", "worldbank.org", "bis.org", "oecd.org",
    "fred.stlouisfed.org", "bls.gov", "census.gov", "bea.gov", "eia.gov",
    "data.oecd.org",
    # ---- 主流财经媒体 ----
    "ft.com", "wsj.com", "reuters.com", "bloomberg.com",
    "economist.com", "nikkei.com",
    "21jingji.com", "cls.cn", "caixin.com", "wallstreetcn.com",
    "yicai.com", "stcn.com", "cnstock.com",
    "sohu.com",  # search aggregator 经常命中财联社/澎湃转载
    "barrons.com", "marketwatch.com", "cnbc.com", "forbes.com",
    "scmp.com", "asia.nikkei.com", "channelnewsasia.com",
    # ---- 产业垂直 ----
    "36kr.com", "huxiu.com", "tmtpost.com", "leiphone.com",
    "geekpark.net", "ithome.com", "jiqizhixin.com",
    "technode.com", "theinformation.com", "stratechery.com",
    "semianalysis.com", "techcrunch.com", "theverge.com",
    "arstechnica.com", "theregister.com",
    "eet-china.com",
    # ---- 数据/研究机构 ----
    "counterpointresearch.com", "idc.com", "gartner.com", "semi.org",
    "trendforce.com", "omdia.com", "canalys.com", "statista.com",
    "ihsmarkit.com", "spglobal.com",
    "mckinsey.com", "bcg.com", "bain.com",
    "deloitte.com", "pwc.com", "ey.com", "kpmg.com",
    "iresearch.com.cn", "qianzhan.com",
    # ---- 学术 ----
    "arxiv.org", "nature.com", "science.org", "scholar.google.com",
    "semanticscholar.org", "ieee.org", "acm.org", "sciencedirect.com",
    # ---- 公司公告平台 ----
    "cninfo.com.cn", "edgar.sec.gov", "businesswire.com", "prnewswire.com",
    # ---- 投资者讨论 / 侧面信号 ----
    "xueqiu.com", "jisilu.cn", "seekingalpha.com",
    "linkedin.com", "glassdoor.com",
    # ---- 中国主流财经媒体 子域兜底（已在 endswith 匹配范围）----
    "sina.com.cn",      # finance.sina.com.cn / cj.sina.com.cn / vip.stock.finance.sina.com.cn
    "qq.com",           # finance.qq.com / file.finance.qq.com (券商研报托管)
    "oeeee.com",        # 南方都市报
    # ---- 中国医药行业垂直（2026-05 实战补 — H2 教训）----
    "pharmcube.com",            # 医药魔方（bydrug.pharmcube.com 通过 endswith 命中）
    "pharnexcloud.com",         # 摩熵医药（原药融云）
    "phirda.com",               # 医药地理
    "baogaobox.com",            # 远瞻慧库 / 报告盒子
    "zhihuiya.com",             # 智慧芽（synapse.zhihuiya.com 通过 endswith）
    "nephro-online.com",        # 肾科在线
    "ihemato.com",              # 血液学
    # ---- 中国券商研报平台 ----
    "fxbaogao.com",     # 发现报告
    "spdbi.com",        # 浦银国际
    "hibor.net",        # 慧博
    "bocomgroup.com",   # 交银国际研报托管
    # ---- 海外医药 / Biotech 行业媒体 ----
    "fiercebiotech.com", "fiercepharma.com",
    "biopharmadive.com",
    "oncologypipeline.com",     # ApexOnco
    "endpts.com",               # Endpoints News
    "firstwordpharma.com",
    "thebambooworks.com",       # Bamboo Works
    "allsci.com",
    # ---- 政府监管补充 ----
    "nhsa.gov.cn",      # 国家医保局
    "nmpa.gov.cn",      # 国家药监局
}

# 子域识别 — 含这些 token 视为公司 IR 页（high）
_IR_SUBDOMAIN_TOKENS = ("ir.", "investor.", "investors.", "corporate.")


def _domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        # strip port + www
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.split(":")[0]
    except Exception:
        return ""


def classify_domain(url: str) -> str:
    """Return 'whitelist' / 'llm-judged-official' / 'other'.

    'llm-judged-official' is only set when the caller explicitly passes
    domain_tier='llm-judged-official' via register_web_search_result —
    this function alone never returns it from a URL.
    """
    domain = _domain_of(url)
    if not domain:
        return "other"
    # exact match
    if domain in WHITELIST_DOMAINS:
        return "whitelist"
    # suffix match (e.g. foo.sec.gov)
    for wl in WHITELIST_DOMAINS:
        if domain.endswith("." + wl):
            return "whitelist"
    # IR sub-domain heuristic
    if any(tok in domain for tok in _IR_SUBDOMAIN_TOKENS):
        return "whitelist"
    return "other"


def confidence_for_tier(domain_tier: str) -> float:
    """Default numeric confidence per tier. Caller may override with explicit value."""
    return {"whitelist": 0.9, "llm-judged-official": 0.7, "other": 0.4}.get(domain_tier, 0.3)


# ---------------------------------------------------------------------------
# URL 客观特征提取 — 给主 agent 做 LLM 判断的事实依据，不做主观分类
# ---------------------------------------------------------------------------
# 设计原则（H2 教训, 2026-05）：脚本只做 deterministic 测量，不返回 tier/hint/confidence；
# 所有主观判断（这个 url 是否权威源、是否值得 llm-judged-official）完全交给主 agent LLM。
# 参 memory/feedback_prescan_domain_tier.md + _review_2026-05-26_rongchang_workflow00.md H2

_LOW_SIGNAL_HOST_TOKENS = (
    # 明确低信噪 host pattern — 这是 deterministic 黑名单（不是启发式）
    "blog.", "bbs.", "tieba.", "zhidao.", "wenku.baidu.",
    "csdn.net", "cnblogs.com", "jianshu.com", "douban.com",
)

_ANNOUNCE_PATH_TOKENS = (
    # URL path 里出现这些 token 通常意味着是公告/年报/招股书等正式披露
    "uploadfile", "announce", "disclosure", "notice", "bulletin",
    "annualreport", "annual_report", "prospectus", "circular",
    "pdf",  # path 含 pdf 子目录或直接 .pdf 文件
)

_NEWS_PATH_TOKENS = (
    # 普通新闻文章路径 — 既不加分也不减分，纯标记
    "news", "article", "story", "post", "detail",
)


def _extract_subdomain_tokens(url: str) -> list[str]:
    """Return list of recognized subdomain tokens (e.g. ['ir'], ['investor'], ['finance'])."""
    domain = _domain_of(url)
    if not domain or "." not in domain:
        return []
    # subdomain = host 去掉 last 2 labels（粗略）
    parts = domain.split(".")
    if len(parts) <= 2:
        return []
    subdomain = ".".join(parts[:-2])
    known = ("ir", "investor", "investors", "corporate", "finance",
             "news", "blog", "bbs", "forum", "m", "mobile", "app")
    return [tok for tok in known if tok in subdomain.split(".")]


def _tld_class(url: str) -> str:
    """Coarse TLD classification: 'gov' / 'gov.cn' / 'gov.hk' / 'edu' / 'org' / 'com' / 'cn' / 'other'."""
    domain = _domain_of(url)
    if not domain:
        return "other"
    if domain.endswith(".gov.cn") or domain.endswith(".gov.hk"):
        return domain.rsplit(".", 2)[-2] + "." + domain.rsplit(".", 1)[-1]  # 'gov.cn' / 'gov.hk'
    for suffix in (".gov", ".edu", ".org", ".com", ".cn", ".hk", ".jp", ".uk", ".eu"):
        if domain.endswith(suffix):
            return suffix.lstrip(".")
    return "other"


def _extract_path_tokens(url: str, vocabulary: tuple[str, ...]) -> list[str]:
    """Return subset of vocabulary present in URL path (lowercase, substring match)."""
    try:
        path = urlparse(url).path.lower()
    except Exception:
        return []
    return [tok for tok in vocabulary if tok in path]


def _matches_low_signal_blacklist(url: str) -> bool:
    domain = _domain_of(url)
    return any(tok in domain for tok in _LOW_SIGNAL_HOST_TOKENS)


def extract_url_features(urls: list[str]) -> dict[str, dict]:
    """Return objective deterministic features per URL — for main-agent LLM judgment.

    The script never returns tier / hint / confidence — those are LLM's job.
    Main agent should combine these features with title/snippet + training
    knowledge to decide whether to pass domain_tier='llm-judged-official'.

    Per-url dict keys:
      - in_whitelist (bool): classify_domain == 'whitelist'
      - host (str): bare domain (no www., no port)
      - subdomain_tokens (list[str]): recognized subdomain markers
        (e.g. ['ir'] for ir.tencent.com, ['finance'] for finance.sina.com.cn)
      - tld_class (str): 'gov' / 'gov.cn' / 'edu' / 'org' / 'com' / 'cn' / ...
      - path_is_pdf (bool): URL path ends with .pdf
      - path_announce_tokens (list[str]): path contains
        ['uploadfile','announce','disclosure','prospectus','annual_report',...]
      - path_news_tokens (list[str]): path contains ['news','article','detail',...]
      - path_depth (int): number of '/' separators
      - known_low_signal_host (bool): host matches hardcoded
        blog/forum/Q&A blacklist (csdn / blog. / bbs. / zhidao. / ...)
    """
    out: dict[str, dict] = {}
    for url in urls:
        out[url] = {
            "in_whitelist": classify_domain(url) == "whitelist",
            "host": _domain_of(url),
            "subdomain_tokens": _extract_subdomain_tokens(url),
            "tld_class": _tld_class(url),
            "path_is_pdf": url.lower().endswith(".pdf"),
            "path_announce_tokens": _extract_path_tokens(url, _ANNOUNCE_PATH_TOKENS),
            "path_news_tokens": _extract_path_tokens(url, _NEWS_PATH_TOKENS),
            "path_depth": max(0, url.count("/") - 2),
            "known_low_signal_host": _matches_low_signal_blacklist(url),
        }
    return out


def funnel_band(confidence: float) -> str:
    """三档分流：>=0.8 high / >=0.5 mid / else low"""
    if confidence >= 0.8:
        return "high"
    if confidence >= 0.5:
        return "mid"
    return "low"


# ---------------------------------------------------------------------------
# 查询词构造 — 通用 across topic types
# ---------------------------------------------------------------------------

# H3 v2：WebSearch 最佳 query 长度 5-15 词。脚本不做关键词提取（切到非核心名词反而
# 误导），强制让主 agent 在 create_topic 时显式给 short_name + search_terms。
# 策略（优先级）：
#   1. search_terms 优先：short_name + 前 3 个 term
#   2. 短 question 兜底：short_name + question
#   3. 都没有：short_name 单独（最 dumb）
#   4. 老 yaml 无 short_name：fall back display_name（仅向后兼容）
_SCOPE_QUERY_MAX_CHARS = 40
_TRAILING_NOISE_RE = re.compile(r"[，。；：、,;:\s]+$")


def _short_scope_query(
    display_name: str,
    short_name: str | None,
    question: str,
    search_terms: list[str] | None,
) -> str:
    """构造 scope 主查询（H3 v2 — 不做关键词提取）。

    优先级：
      1. search_terms 给了 → short_name + 前 3 个 term（不读 question）
      2. question 短（≤25）→ short_name + question
      3. 都没合适的 → short_name 单独
      4. 老 yaml 无 short_name → display_name 兜底（不截断；新 topic 会被 create_topic gate 挡住）

    create_topic gate 保证新 topic 必有 short_name + 长 question 必有 search_terms，
    故脚本永远不需要"假装聪明"地切 question。
    """
    name = (short_name or display_name or "").strip()
    if search_terms:
        terms = " ".join(s.strip() for s in search_terms[:3] if s and s.strip())
        out = f"{name} {terms}".strip()
    else:
        q = (question or "").strip()
        if q and len(q) <= 25:
            out = f"{name} {q}"
        else:
            # 长 question + 缺 search_terms 仅出现于老 yaml；用 short_name/display_name 兜底
            out = name
    if len(out) > _SCOPE_QUERY_MAX_CHARS:
        out = out[:_SCOPE_QUERY_MAX_CHARS]
    out = _TRAILING_NOISE_RE.sub("", out)
    return out


def build_search_queries(slug: str, variant: str, recency_days: int = 90) -> list[dict]:
    """根据 topic.yaml + thesis_v{N} + roadmap.yaml 构造查询词列表。

    通用 across company / industry / arena / concept：
      - scope.question + scope.search_terms 派生主查询（H3：长 question 截断）
      - scope.ticker（如有）+ 近期事件子查询
      - thesis killer questions 派生每 K# 一条（H3：不再叠 question）
      - roadmap L4 hunting question 派生每条一查
      - concepts 派生概念扩展查询

    返回 [{query, addresses, recency_days, kind}, ...]
    """
    topic = topic_io.read_topic(slug, variant)
    scope = topic.get("scope") or {}
    display_name = topic.get("display_name") or slug
    short_name = scope.get("short_name") or None
    # H3 v2：query 拼接统一用 short_name（无则 fall back display_name 兜底）
    name_for_query = short_name or display_name
    ttype = topic.get("type") or "concept"
    question = scope.get("question") or ""
    ticker = scope.get("ticker") or ""
    search_terms = scope.get("search_terms") or None

    queries: list[dict] = []

    # 1. 主问题查询 — 覆盖任何 topic（H3 v2：short_name 优先）
    scope_q = _short_scope_query(display_name, short_name, question, search_terms)
    if scope_q:
        queries.append({
            "query": scope_q,
            "addresses": ["scope"],
            "recency_days": recency_days,
            "kind": "scope",
        })

    # 2. company 专属：ticker + 近期事件
    if ttype == "company" and ticker:
        # ticker 形如 US_FUTU / SZSE_300073 — 取后段
        ticker_short = ticker.split("_", 1)[-1] if "_" in ticker else ticker
        for kw in ("最新公告", "监管处罚", "业绩预告", "高管变动"):
            queries.append({
                "query": f"{name_for_query} {ticker_short} {kw}",
                "addresses": ["scope"],
                "recency_days": recency_days,
                "kind": "company-event",
            })

    # 3. industry / arena 专属：行业政策 + 技术突破
    #    H3 v2 修：优先用 search_terms 拼 base（短、精准、搜索友好），
    #    无 search_terms 才 fallback name_for_query（避免 display_name 贪心 + 截断）
    if ttype in ("industry", "arena"):
        if search_terms:
            industry_base = " ".join(
                s.strip() for s in search_terms[:2] if s and s.strip()
            )
        else:
            industry_base = name_for_query
        for kw in ("行业政策", "技术突破", "产能变化", "龙头新闻"):
            queries.append({
                "query": f"{industry_base} {kw}",
                "addresses": ["scope"],
                "recency_days": recency_days,
                "kind": "industry-event",
            })

    # 4. concept 专属：概念扩展
    if ttype == "concept":
        concepts = topic.get("concepts") or []
        for c in concepts[:3]:
            queries.append({
                "query": f"{c} 最新进展",
                "addresses": ["scope"],
                "recency_days": recency_days,
                "kind": "concept-update",
            })

    # 5. roadmap L4 hunting questions — 适用所有类型
    # H3 v3：删除 killer-question kind（冗余 — scope 含 search_terms 已宽覆盖，
    #         l4-hunting 已逐条 K# 对齐）。L4 query 必须用 search_keywords，
    #         避免 question 长句被 WebSearch 当无意义字串。
    roadmap_path = PRISM_ROOT / "topics" / slug / variant / "roadmap.yaml"
    if roadmap_path.is_file():
        try:
            roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8")) or {}
            l4 = ((roadmap.get("learning_track") or {}).get("l4_hunting") or [])
            for q in l4:
                addrs = q.get("addresses") or []
                kws = q.get("search_keywords") or []
                if kws:
                    terms = " ".join(str(s).strip() for s in kws[:3] if str(s).strip())
                    if terms:
                        queries.append({
                            "query": f"{name_for_query} {terms}",
                            "addresses": addrs or ["scope"],
                            "recency_days": recency_days,
                            "kind": "l4-hunting",
                        })
                else:
                    qtext = q.get("question") or q.get("text") or ""
                    addr_label = ",".join(addrs) if addrs else "?"
                    print(
                        f"⚠ l4-hunting query 跳过 [addresses={addr_label}]：缺 search_keywords 字段；"
                        f"原 question='{qtext[:30]}...'。回 workflow 01 Step 2 补 search_keywords。",
                        file=sys.stderr,
                    )
        except Exception:
            pass

    return queries


# ---------------------------------------------------------------------------
# 落地：写 inbox/web-search/*.md + 入 manifest
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9\-一-鿿]+")


def _slugify(text: str, max_len: int = 50) -> str:
    s = text.lower().strip()
    s = _SLUG_RE.sub("-", s).strip("-")
    return s[:max_len] or "untitled"


def _web_search_inbox_dir(slug: str) -> Path:
    """Topic-scoped inbox subdir for web-search results."""
    p = PRISM_ROOT / "topics" / slug / "inbox" / "web-search"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _build_inbox_md(
    title: str, url: str, query: str, snippet: str, full_text: str | None,
    confidence: float, domain_tier: str, addresses: list[str], searched_at: str,
) -> str:
    """Render frontmatter + body for inbox/web-search/*.md."""
    fm = {
        "title": title,
        "url": url,
        "query": query,
        "searched_at": searched_at,
        "confidence": confidence,
        "domain_tier": domain_tier,
        "addresses": addresses,
        "source": "web-search",
    }
    fm_yaml = yaml.dump(fm, allow_unicode=True, sort_keys=False).strip()
    body_parts = [f"# {title}", "", f"**URL**: {url}", "", "## Snippet", "", snippet.strip()]
    if full_text:
        body_parts += ["", "## Full text (via WebFetch)", "", full_text.strip()]
    body = "\n".join(body_parts)
    return f"---\n{fm_yaml}\n---\n\n{body}\n"


def register_web_search_result(
    slug: str,
    variant: str,
    query: str,
    url: str,
    title: str,
    snippet: str,
    addresses: list[str],
    full_text: str | None = None,
    confidence: float | None = None,
    domain_tier: str | None = None,
    triggered_by: str | None = None,
    rings: list[str] | None = None,
) -> dict:
    """Register one web-search hit: write inbox/.md + add_material.

    rings: optional 决策链输入合同 codes（如 web 收来的 consensus/historical-mirror），
           写入 manifest 材料，使 web-source 料也进 gap ring 轴覆盖。

    Returns: {
        'mat_id': str | None,        # None if band=='low' (not registered)
        'band': 'high'|'mid'|'low',
        'confidence': float,
        'domain': str,
        'domain_tier': str,
        'filename': str | None,
    }

    Funneling:
      - high (>=0.8) → write inbox + register to manifest (source_type='web-search')
      - mid  (>=0.5) → write inbox + register to manifest with notes='待用户确认'
      - low  (<0.5)  → only log, don't write inbox or manifest
    """
    domain = _domain_of(url)
    if domain_tier is None:
        domain_tier = classify_domain(url)
    if confidence is None:
        confidence = confidence_for_tier(domain_tier)
    band = funnel_band(confidence)
    result: dict = {
        "mat_id": None,
        "band": band,
        "confidence": confidence,
        "domain": domain,
        "domain_tier": domain_tier,
        "filename": None,
        "duplicate": False,
    }

    if band == "low":
        return result

    # URL 去重：90 天 expire 后重扫同一 URL 时只刷新 searched_at/expire_at + 合并 addresses，
    # 不写新 inbox 也不新建 mat 条目。
    existing = find_by_url(slug, variant, url)
    if existing is not None:
        refresh_web_search_meta(
            slug, variant, existing["id"],
            query=query, addresses=addresses,
            triggered_by=triggered_by,
        )
        result["mat_id"] = existing["id"]
        result["filename"] = existing.get("filename")
        result["duplicate"] = True
        return result

    searched_at = datetime.now(timezone.utc).isoformat()
    safe_title = _slugify(title or query)
    date_prefix = searched_at[:10]
    filename = f"{date_prefix}_{safe_title}.md"
    inbox_dir = _web_search_inbox_dir(slug)
    file_path = inbox_dir / filename
    md = _build_inbox_md(
        title=title, url=url, query=query, snippet=snippet, full_text=full_text,
        confidence=confidence, domain_tier=domain_tier, addresses=addresses,
        searched_at=searched_at,
    )
    file_path.write_text(md, encoding="utf-8")

    notes_bits = [f"query={query!r}"]
    if band == "mid":
        notes_bits.append("待用户确认")
    notes = " | ".join(notes_bits)

    search_meta = make_search_meta(
        query=query, url=url, domain=domain, domain_tier=domain_tier,
        searched_at=searched_at, triggered_by=triggered_by,
    )
    mat_id = add_material(
        slug=slug, filename=filename, source_type="web-search", variant=variant,
        notes=notes, source_path=file_path,
        addresses=addresses, confidence=confidence, search_meta=search_meta,
        rings=rings,
    )
    result["mat_id"] = mat_id
    result["filename"] = filename
    return result


# ---------------------------------------------------------------------------
# 即兴 web-search inline finding（修 B2 — 消除"入库无 finding"黑洞）
# ---------------------------------------------------------------------------

# 03/04/05 即兴 web-search 默认自动产 inline finding 的 trigger 集合
_INLINE_FINDING_TRIGGERS = frozenset({"03-extract", "04-synth", "05-critic"})


def register_inline_finding(
    slug: str,
    variant: str,
    mat_id: str,
    content: str,
    addresses: list[str],
    quality: str = "medium",
    bias: str = "neutral",
    extra_frontmatter: dict | None = None,
) -> Path:
    """为即兴 web-search mat 写 outputs/findings_{mat_id}.md + mark_processed。

    最小 frontmatter（5 字段）：mat_id / source_type / extracted / quality / bias / addresses
    若 finding 文件已存在 → skip（不覆盖手写 finding），仅确保 processed=True。

    用于 03/04/05 在合成中遇到具体缺口时点状补料的"即兴 web-search"——避免之前
    "入库无 finding → 被产出 referenced → 05-critic 找不到论据"的黑洞。
    """
    from prism.scripts.topic import _topic_path

    out_dir = _topic_path(slug, variant).parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    finding_path = out_dir / f"findings_{mat_id}.md"

    if not finding_path.exists():
        fm: dict = {
            "mat_id": mat_id,
            "source_type": "web-search-inline",
            "extracted": datetime.now(timezone.utc).date().isoformat(),
            "quality": quality,
            "bias": bias,
            "addresses": list(addresses or []),
        }
        if extra_frontmatter:
            fm.update(extra_frontmatter)
        fm_yaml = yaml.dump(fm, allow_unicode=True, sort_keys=False).strip()
        body = (content or "").strip() or "(no content)"
        finding_path.write_text(f"---\n{fm_yaml}\n---\n\n{body}\n", encoding="utf-8")

    # 不论是否新写，标 processed（幂等）
    mark_processed(slug, mat_id, variant)
    return finding_path


def register_web_search_batch(
    slug: str,
    variant: str,
    query: str,
    addresses: list[str],
    triggered_by: str,
    hits: list[dict],
    full_texts: dict[str, str] | None = None,
    inline_finding: bool | None = None,
    rings: list[str] | None = None,
) -> dict:
    """One-call batch wrapper for the 6-step prescan ritual.

    rings: optional 决策链输入合同 codes，整批 hit 统一打（如这一轮专搜 consensus / 镜鉴）；
           写入材料 + inline finding frontmatter，使 web-source 料进 gap ring 轴。

    主 agent 把一轮 WebSearch 结果整批传进来，本 helper 完成：
      - 对每条 hit 调 register_web_search_result（自动判 domain_tier + funnel band）
      - 累计 mat_ids 后调 auto_resolve_todos
      - append_search_log（按 triggered_by 标签）

    每个 hit dict 必备 keys: title, url, snippet
    可选 keys: confidence (0-1, override), domain_tier ('whitelist'|'llm-judged-official'|'other')

    full_texts: optional dict of url → full_text fetched via WebFetch by main agent.

    triggered_by ∈ {'00-prescan','01-prescan','02-step0','03-extract','04-synth',
                    '05-critic','06-daily-monitor','07-drilldown'}

    inline_finding: 是否对每条 high/mid mat 自动产 inline finding（修 B2 — 即兴
      web-search 不再悬挂）。
      - None（默认）→ triggered_by ∈ {'03-extract','04-synth','05-critic'} 自动开启
      - True / False → 显式 override

    Returns:
        {
            'n_high': int, 'n_mid': int, 'n_low': int,
            'mat_ids': list[str|None],
            'resolved_todos': list[dict],
            'duplicates': int,
            # ---- 修 H2 (2026-05) 新增：让丢弃显式 + 给主 agent 救回 kit ----
            'n_dropped_invalid': int,    # url/title 空被丢
            'n_dropped_low': int,        # band='low' 被丢
            'drop_ratio': float,         # (n_dropped_invalid + n_dropped_low) / len(hits)
            'dropped_hits': list[dict],  # 被丢的 hit 完整保留 + reason，主 agent 直接判后补登
            'silent_failure': bool,      # = failure_mode != 'none'（向后兼容字段）
            'failure_mode': str,         # 'upstream_empty' / 'all_low_band' / 'none'（精准分流）
        }

    dropped_hits 每项 schema:
        {'url': str, 'title': str, 'snippet': str,
         'reason': 'invalid' | 'low-band',
         'auto_domain_tier': 'whitelist' | 'other',
         'auto_confidence': float}
    """
    full_texts = full_texts or {}
    n_high = n_mid = n_low = duplicates = 0
    n_dropped_invalid = 0
    n_dropped_low = 0
    mat_ids: list[str | None] = []
    dropped_hits: list[dict] = []

    for hit in hits:
        url = hit.get("url", "")
        title = hit.get("title", "")
        snippet = hit.get("snippet", "")
        if not url or not title:
            mat_ids.append(None)
            n_low += 1
            n_dropped_invalid += 1
            dropped_hits.append({
                "url": url, "title": title, "snippet": snippet,
                "reason": "invalid",
                "auto_domain_tier": None,
                "auto_confidence": None,
            })
            continue
        r = register_web_search_result(
            slug=slug,
            variant=variant,
            query=query,
            url=url,
            title=title,
            snippet=snippet,
            addresses=addresses,
            full_text=full_texts.get(url),
            confidence=hit.get("confidence"),
            domain_tier=hit.get("domain_tier"),
            triggered_by=triggered_by,
            rings=rings,
        )
        mat_ids.append(r["mat_id"])
        band = r["band"]
        if band == "high":
            n_high += 1
        elif band == "mid":
            n_mid += 1
        else:
            n_low += 1
            n_dropped_low += 1
            dropped_hits.append({
                "url": url, "title": title, "snippet": snippet,
                "reason": "low-band",
                "auto_domain_tier": r.get("domain_tier"),
                "auto_confidence": r.get("confidence"),
            })
        if r.get("duplicate"):
            duplicates += 1

    new_ids = [m for m in mat_ids if m]
    resolved = auto_resolve_todos(slug, variant, new_ids) if new_ids else []

    # 即兴 web-search 自动产 inline finding（修 B2）
    if inline_finding is None:
        do_inline = triggered_by in _INLINE_FINDING_TRIGGERS
    else:
        do_inline = bool(inline_finding)
    inline_finding_paths: list[str] = []
    if do_inline and new_ids:
        for hit, mat_id in zip(hits, mat_ids):
            if not mat_id:
                continue
            snippet = (hit.get("snippet") or "").strip()
            title = (hit.get("title") or "").strip()
            url = (hit.get("url") or "").strip()
            full_text = (full_texts or {}).get(url, "")
            body_parts = [f"# {title}", "", f"**URL**: {url}", "", f"**Query**: {query}", ""]
            if snippet:
                body_parts += ["## Snippet", "", snippet, ""]
            if full_text:
                body_parts += ["## Full text", "", full_text.strip(), ""]
            body = "\n".join(body_parts).strip()
            _ef = {"url": url, "query": query, "triggered_by": triggered_by}
            if rings:
                _ef["rings"] = sorted(set(rings))
            fp = register_inline_finding(
                slug=slug, variant=variant, mat_id=mat_id,
                content=body, addresses=list(addresses),
                quality="medium", bias="neutral",
                extra_frontmatter=_ef,
            )
            inline_finding_paths.append(str(fp))

    append_search_log(
        slug=slug, variant=variant, query=query,
        n_results=len(hits),
        n_high=n_high, n_mid=n_mid, n_low=n_low,
        triggered_by=triggered_by,
    )

    total = max(1, len(hits))
    drop_ratio = round((n_dropped_invalid + n_dropped_low) / total, 2)

    # 每次都打简短摘要 — 不设硬阈值告警（参 H2 修订设计：脚本不替主 agent 判该不该救回）
    # 主 agent 看到 drop_ratio + dropped urls 自己决定要不要扫 dropped_hits + 救回
    import sys
    n_in = n_high + n_mid
    summary_line = (
        f"register_web_search_batch[{triggered_by}]: {len(hits)} hits → "
        f"入库 high={n_high} mid={n_mid}, dropped={n_dropped_invalid + n_dropped_low} "
        f"(invalid={n_dropped_invalid} low={n_dropped_low}) drop_ratio={drop_ratio}"
    )
    print(summary_line, file=sys.stderr)
    if drop_ratio >= 0.5 and n_dropped_low > 0:
        # drop_ratio 高且有真正"低分丢弃"（不是 invalid）时附 dropped url 列表给主 agent 扫
        sample_urls = [d["url"] for d in dropped_hits if d["reason"] == "low-band"][:10]
        print(
            f"  → drop_ratio≥0.5: 扫 dropped_hits + 调 extract_url_features 后决定救回。\n"
            f"  → 被丢 url (前 10)：\n    - " + "\n    - ".join(sample_urls),
            file=sys.stderr,
        )

    # failure_mode 三态（取代单 bool silent_failure 的语义混淆）：
    #   'upstream_empty' — hits=0，疑似 WebSearch 上游静默限流，建议等 30s 串行重试
    #   'all_low_band'   — hits>0 但 n_in=0，全 'other' tier drop，建议走 H2 救回（extract_url_features + LLM 判 tier）
    #   'none'           — 至少有 1 条入库
    # silent_failure: bool 保留向后兼容（仍 = upstream_empty or all_low_band）
    if len(hits) == 0:
        failure_mode = 'upstream_empty'
    elif n_in == 0:
        failure_mode = 'all_low_band'
    else:
        failure_mode = 'none'
    silent_failure = failure_mode != 'none'

    if failure_mode == 'upstream_empty':
        print(
            f"⚠️  [upstream_empty] query={query!r} hits=0 — "
            f"疑似 WebSearch 上游静默限流。"
            f"建议：等 {WEB_SEARCH_SERIAL_RETRY_INTERVAL_S}s 后串行重试本 query；"
            f"连 3 个 query upstream_empty → 转 WebFetch 兜底已知权威 URL。",
            file=sys.stderr,
        )
    elif failure_mode == 'all_low_band':
        print(
            f"⚠️  [all_low_band] query={query!r} hits={len(hits)} 全 drop low band — "
            f"非限流，需走 H2 救回：调 extract_url_features(dropped_urls) → "
            f"LLM 判 tier → 救回列表带 domain_tier='llm-judged-official' 再调一次本函数。"
            f"若救回后仍 0 入库 → 此 query 关键词不对，换 query 而非重试。",
            file=sys.stderr,
        )

    return {
        "n_high": n_high,
        "n_mid": n_mid,
        "n_low": n_low,
        "mat_ids": mat_ids,
        "resolved_todos": resolved,
        "duplicates": duplicates,
        "n_dropped_invalid": n_dropped_invalid,
        "n_dropped_low": n_dropped_low,
        "drop_ratio": drop_ratio,
        "dropped_hits": dropped_hits,
        "silent_failure": silent_failure,
        "failure_mode": failure_mode,
        "inline_finding_paths": inline_finding_paths,
    }


# ---------------------------------------------------------------------------
# todo 自动覆盖
# ---------------------------------------------------------------------------

def auto_resolve_todos(slug: str, variant: str, new_mat_ids: list[str]) -> list[dict]:
    """扫 user_todos：若 todo.addresses 与本批新 mat 的 addresses 有交集，
    标 status=done + 追加 covered_by + 写 coverage_note。

    Returns: list of {task, mat_ids} resolved this round.
    """
    if not new_mat_ids:
        return []
    from prism.scripts.manifest import read_manifest

    manifest = read_manifest(slug, variant)
    mat_addr_map: dict[str, list[str]] = {}
    for m in manifest.get("materials") or []:
        if m["id"] in new_mat_ids:
            mat_addr_map[m["id"]] = list(m.get("addresses") or [])

    if not mat_addr_map:
        return []

    data = topic_io.read_topic(slug, variant)
    todos = data.get("user_todos") or []
    resolved: list[dict] = []

    for todo in todos:
        if not isinstance(todo, dict):
            continue
        if todo.get("status") == "done":
            continue
        # reverse-check 写的 todo 语义是"补 roadmap.yaml"，单纯收一份 K# 材料不算闭环；
        # 必须等用户/workflow 01 真的把 K# 加到 L4/tier 后人工标 done。
        if "reverse-check" in (todo.get("source_hint") or ""):
            continue
        todo_addrs = todo.get("addresses") or []
        if not todo_addrs:
            continue
        # 使用 addresses_match 严格事件匹配：todo 'K1@evt' 必须 mat 也带 'K1@evt' 才覆盖；
        # 裸 K1 todo 接受任何 K1*（向后兼容）。修 [[feedback-addresses-granularity]] 假阳性。
        matched = [
            mid for mid, addrs in mat_addr_map.items()
            if topic_io.addresses_match(todo_addrs, addrs)
        ]
        if not matched:
            continue
        existing = set(todo.get("covered_by") or [])
        merged = sorted(existing | set(matched))
        todo["covered_by"] = merged
        todo["status"] = "done"
        todo["coverage_note"] = f"已由 web-search {', '.join(matched)} 覆盖"
        resolved.append({"task": todo.get("task", ""), "mat_ids": matched})

    if resolved:
        topic_io.set_user_todos(slug, todos, variant)
    return resolved


# ---------------------------------------------------------------------------
# 搜索日志（每 topic 一份 yaml）
# ---------------------------------------------------------------------------

def _search_log_path(slug: str, variant: str) -> Path:
    return PRISM_ROOT / "topics" / slug / variant / "web_search_log.yaml"


def append_search_log(
    slug: str,
    variant: str,
    query: str,
    n_results: int,
    n_high: int,
    n_mid: int,
    n_low: int,
    triggered_by: str,
) -> None:
    """Append a search round to per-topic web_search_log.yaml.

    triggered_by ∈ {'01-prescan', '02-step0', '06-daily-monitor', '07-drilldown'}
    """
    path = _search_log_path(slug, variant)
    entries: list[dict] = []
    if path.is_file():
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            entries = data.get("entries") or []
        except Exception:
            entries = []
    entries.append({
        "searched_at": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "triggered_by": triggered_by,
        "n_results": n_results,
        "n_high": n_high,
        "n_mid": n_mid,
        "n_low": n_low,
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump({"slug": slug, "variant": variant, "entries": entries},
                  allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def list_search_log(slug: str, variant: str) -> list[dict]:
    """Read all search-log entries for a topic, newest first."""
    path = _search_log_path(slug, variant)
    if not path.is_file():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    entries = data.get("entries") or []
    return list(reversed(entries))


# ---------------------------------------------------------------------------
# ISSUE-001：prescan 健康度检查（用于 set_thesis 前置）
# ---------------------------------------------------------------------------

def check_prescan_health(
    slug: str,
    variant: str,
    expected_queries: int,
    triggered_by_prefix: str = "00-prescan",
) -> dict:
    """统计 prescan 命中率，返回 full / partial / failed 三态判断。

    Args:
        slug, variant: topic
        expected_queries: 主 agent 实际意图跑的 query 数（如 baseline 第五节列了 10 条优先 query）
        triggered_by_prefix: 只统计 triggered_by 以此前缀开头的 entries（默认 '00-prescan' 同时
            覆盖 '00-prescan-baseline'）

    Returns:
        {
            'status': 'full' / 'partial' / 'failed',
            'queries_run': int,         # web_search_log 中匹配前缀的实际 entry 数
            'queries_with_hits': int,   # 其中 n_high+n_mid >= 1 的条数
            'hit_rate': float,          # queries_with_hits / max(expected_queries, queries_run)
            'failure_reason': str | None,  # status != 'full' 时给一句话原因
        }

    判定规则：
      - hit_rate >= 1.0 且 queries_run >= expected_queries → 'full'
      - hit_rate >= WEB_SEARCH_FAIL_THRESHOLD (0.5) → 'partial'
      - hit_rate <  WEB_SEARCH_FAIL_THRESHOLD       → 'failed'

      （expected_queries 取下限 1 避免除零；queries_run 不足 expected 时按 expected 算 hit_rate）
    """
    log = list_search_log(slug, variant)
    matched = [
        e for e in log
        if isinstance(e.get("triggered_by"), str)
        and e["triggered_by"].startswith(triggered_by_prefix)
    ]
    queries_run = len(matched)
    queries_with_hits = sum(
        1 for e in matched
        if (e.get("n_high") or 0) + (e.get("n_mid") or 0) >= 1
    )
    denom = max(expected_queries, queries_run, 1)
    hit_rate = round(queries_with_hits / denom, 3)

    if queries_run == 0:
        return {
            "status": "failed",
            "queries_run": 0,
            "queries_with_hits": 0,
            "hit_rate": 0.0,
            "failure_reason": (
                f"prescan 一条都没跑（expected_queries={expected_queries}）"
                f" — WebSearch 工具可能不可用或主 agent 跳过 Step 4.5a"
            ),
        }

    if hit_rate >= 1.0 and queries_run >= expected_queries:
        return {
            "status": "full",
            "queries_run": queries_run,
            "queries_with_hits": queries_with_hits,
            "hit_rate": hit_rate,
            "failure_reason": None,
        }

    if hit_rate >= WEB_SEARCH_FAIL_THRESHOLD:
        return {
            "status": "partial",
            "queries_run": queries_run,
            "queries_with_hits": queries_with_hits,
            "hit_rate": hit_rate,
            "failure_reason": (
                f"prescan 入库率 {hit_rate:.0%}（{queries_with_hits}/{denom}），"
                f"低于满分但高于失败阈值 {WEB_SEARCH_FAIL_THRESHOLD:.0%}"
            ),
        }

    return {
        "status": "failed",
        "queries_run": queries_run,
        "queries_with_hits": queries_with_hits,
        "hit_rate": hit_rate,
        "failure_reason": (
            f"prescan 入库率 {hit_rate:.0%}（{queries_with_hits}/{denom}），"
            f"低于失败阈值 {WEB_SEARCH_FAIL_THRESHOLD:.0%} — "
            f"疑似 WebSearch 限流静默返空 / 区域阻断 / API 失效"
        ),
    }


# ---------------------------------------------------------------------------
# 02 Step 0 智能 recency 判定（修 S1）
# ---------------------------------------------------------------------------

_PRESCAN_TRIGGERS = {"00-prescan", "00-prescan-baseline", "01-prescan", "02-step0"}


def should_run_step0(slug: str, variant: str) -> dict:
    """02 Step 0 是否要跑 prescan，跑就给 recency_days；不跑给 reason。

    决策表（基于 web_search_log.yaml 中最近一次 _PRESCAN_TRIGGERS 内的 entry）：
      - 任一 prescan 距今 ≤ 7 天        → skip（紧接 01-prescan 或上一次 02-step0）
      - 最近 02-step0 在 (7, 14] 天      → recency_days=7（增量扫近一周）
      - 最近 02-step0 在 (14, 60] 天     → recency_days=30（按原默认）
      - 无 02-step0 历史 或 > 60 天      → recency_days=90（首跑/久未扫，兜底回看）

    Returns:
        {
            'should_run': bool,
            'recency_days': int | None,   # None when should_run=False
            'reason': str,                # 单行可读理由
            'last_prescan': dict | None,  # 最近的 entry，便于汇报
        }
    """
    log = list_search_log(slug, variant)  # newest first
    prescans = [e for e in log if e.get("triggered_by") in _PRESCAN_TRIGGERS]

    if not prescans:
        return {
            "should_run": True,
            "recency_days": 90,
            "reason": "无任何 prescan 历史，首跑回看 90 天",
            "last_prescan": None,
        }

    latest = prescans[0]
    latest_at = _parse_iso(latest.get("searched_at"))
    if latest_at is None:
        return {
            "should_run": True,
            "recency_days": 90,
            "reason": "最近 prescan 时间戳无法解析，按首跑回看 90 天",
            "last_prescan": latest,
        }
    now = datetime.now(timezone.utc)
    days_since_latest = (now - latest_at).days

    if days_since_latest <= 7:
        return {
            "should_run": False,
            "recency_days": None,
            "reason": f"最近 prescan 距今 {days_since_latest} 天（≤7），跳过",
            "last_prescan": latest,
        }

    # 区分"最近是 02-step0"和"最近只是 00/01-prescan"
    step0_entries = [e for e in prescans if e.get("triggered_by") == "02-step0"]
    if not step0_entries:
        # 只有 00/01-prescan 历史 → 当前算"02 首跑"，按 30 天增量
        return {
            "should_run": True,
            "recency_days": 30,
            "reason": f"无 02-step0 历史（最近 01/00-prescan 距今 {days_since_latest} 天），按 30 天增量扫",
            "last_prescan": latest,
        }

    step0_at = _parse_iso(step0_entries[0].get("searched_at"))
    if step0_at is None:
        return {
            "should_run": True,
            "recency_days": 90,
            "reason": "最近 02-step0 时间戳无法解析，回看 90 天兜底",
            "last_prescan": step0_entries[0],
        }
    step0_days = (now - step0_at).days

    if step0_days <= 14:
        return {
            "should_run": True,
            "recency_days": 7,
            "reason": f"最近 02-step0 距今 {step0_days} 天（≤14），增量扫近 7 天",
            "last_prescan": step0_entries[0],
        }
    if step0_days <= 60:
        return {
            "should_run": True,
            "recency_days": 30,
            "reason": f"最近 02-step0 距今 {step0_days} 天（14-60），默认 30 天 window",
            "last_prescan": step0_entries[0],
        }
    return {
        "should_run": True,
        "recency_days": 90,
        "reason": f"最近 02-step0 距今 {step0_days} 天（>60），回看 90 天兜底",
        "last_prescan": step0_entries[0],
    }


def _parse_iso(s):
    """Local ISO parser (mirrors manifest._parse_iso for log timestamps)."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
