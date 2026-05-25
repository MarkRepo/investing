"""Web-search auto-ingest engine for prism. Zero LLM calls.

工作分工：
  - LLM 操作（WebSearch / WebFetch / 判断 confidence）由主 agent 在 workflow 里发起
  - 本脚本只做后处理：域名分类 / 写 inbox / 调 add_material / 更新 todo / 维护搜索日志

参考: feedback_llm_workflow.md
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

from prism.scripts import topic as topic_io
from prism.scripts.manifest import (
    add_material, make_search_meta, find_by_url, refresh_web_search_meta,
)

PRISM_ROOT = Path(__file__).resolve().parent.parent

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

def build_search_queries(slug: str, variant: str, recency_days: int = 90) -> list[dict]:
    """根据 topic.yaml + thesis_v{N} + roadmap.yaml 构造查询词列表。

    通用 across company / industry / arena / concept：
      - scope.question 派生主查询
      - scope.ticker（如有）+ 近期事件子查询
      - thesis killer questions 派生每 K# 一条
      - roadmap L4 hunting question 派生每条一查
      - concepts 派生概念扩展查询

    返回 [{query, addresses, recency_days, kind}, ...]
    """
    topic = topic_io.read_topic(slug, variant)
    scope = topic.get("scope") or {}
    display_name = topic.get("display_name") or slug
    ttype = topic.get("type") or "concept"
    question = scope.get("question") or ""
    ticker = scope.get("ticker") or ""

    queries: list[dict] = []

    # 1. 主问题查询 — 覆盖任何 topic
    if question:
        queries.append({
            "query": f"{display_name} {question}",
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
                "query": f"{display_name} {ticker_short} {kw}",
                "addresses": ["scope"],
                "recency_days": recency_days,
                "kind": "company-event",
            })

    # 3. industry / arena 专属：行业政策 + 技术突破
    if ttype in ("industry", "arena"):
        for kw in ("行业政策", "技术突破", "产能变化", "龙头新闻"):
            queries.append({
                "query": f"{display_name} {kw}",
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

    # 5. thesis K# 派生 — 适用所有类型
    thesis_block = topic.get("thesis") or {}
    cur_v = thesis_block.get("current_version")
    if cur_v is not None:
        try:
            from prism.scripts.outputs import extract_killer_questions
            ks = extract_killer_questions(slug, variant, cur_v)
            for k in ks:
                queries.append({
                    "query": f"{display_name} {question} {k}",
                    "addresses": [k],
                    "recency_days": recency_days,
                    "kind": "killer-question",
                })
        except Exception:
            pass

    # 6. roadmap L4 hunting questions — 适用所有类型
    roadmap_path = PRISM_ROOT / "topics" / slug / variant / "roadmap.yaml"
    if roadmap_path.is_file():
        try:
            roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8")) or {}
            l4 = ((roadmap.get("learning_track") or {}).get("l4_hunting") or [])
            for q in l4:
                qtext = q.get("question") or q.get("text") or ""
                addrs = q.get("addresses") or []
                if qtext:
                    queries.append({
                        "query": f"{display_name} {qtext}",
                        "addresses": addrs or ["scope"],
                        "recency_days": recency_days,
                        "kind": "l4-hunting",
                    })
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
) -> dict:
    """Register one web-search hit: write inbox/.md + add_material.

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
        searched_at=searched_at,
    )
    mat_id = add_material(
        slug=slug, filename=filename, source_type="web-search", variant=variant,
        notes=notes, source_path=file_path,
        addresses=addresses, confidence=confidence, search_meta=search_meta,
    )
    result["mat_id"] = mat_id
    result["filename"] = filename
    return result


def register_web_search_batch(
    slug: str,
    variant: str,
    query: str,
    addresses: list[str],
    triggered_by: str,
    hits: list[dict],
    full_texts: dict[str, str] | None = None,
) -> dict:
    """One-call batch wrapper for the 6-step prescan ritual.

    主 agent 把一轮 WebSearch 结果整批传进来，本 helper 完成：
      - 对每条 hit 调 register_web_search_result（自动判 domain_tier + funnel band）
      - 累计 mat_ids 后调 auto_resolve_todos
      - append_search_log（按 triggered_by 标签）

    每个 hit dict 必备 keys: title, url, snippet
    可选 keys: confidence (0-1, override), domain_tier ('whitelist'|'llm-judged-official'|'other')

    full_texts: optional dict of url → full_text fetched via WebFetch by main agent.

    triggered_by ∈ {'00-prescan','01-prescan','02-step0','03-extract','04-synth',
                    '05-critic','06-daily-monitor','07-drilldown'}

    Returns:
        {
            'n_high': int, 'n_mid': int, 'n_low': int,
            'mat_ids': list[str|None],
            'resolved_todos': list[dict],
            'duplicates': int,
        }
    """
    full_texts = full_texts or {}
    n_high = n_mid = n_low = duplicates = 0
    mat_ids: list[str | None] = []

    for hit in hits:
        url = hit.get("url", "")
        title = hit.get("title", "")
        snippet = hit.get("snippet", "")
        if not url or not title:
            mat_ids.append(None)
            n_low += 1
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
        )
        mat_ids.append(r["mat_id"])
        band = r["band"]
        if band == "high":
            n_high += 1
        elif band == "mid":
            n_mid += 1
        else:
            n_low += 1
        if r.get("duplicate"):
            duplicates += 1

    new_ids = [m for m in mat_ids if m]
    resolved = auto_resolve_todos(slug, variant, new_ids) if new_ids else []

    append_search_log(
        slug=slug, variant=variant, query=query,
        n_results=len(hits),
        n_high=n_high, n_mid=n_mid, n_low=n_low,
        triggered_by=triggered_by,
    )

    return {
        "n_high": n_high,
        "n_mid": n_mid,
        "n_low": n_low,
        "mat_ids": mat_ids,
        "resolved_todos": resolved,
        "duplicates": duplicates,
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
