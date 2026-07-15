"""Web-search auto-ingest engine for prism. Zero LLM calls.

工作分工：
  - LLM 操作（WebSearch / WebFetch / 判断 confidence）由主 agent 在 workflow 里发起
  - 本脚本只做后处理：域名分类 / 写 inbox / 调 add_material / 更新 todo / 维护搜索日志

参考: feedback_llm_workflow.md
"""
from __future__ import annotations

import json
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

# search-log entry 的 disposition（修 prescan-health 假阴性，2026-06）：
# 主 agent 跑了 query 但主动没 register 时，须用 log_search_skipped 留痕并分类原因。
# check_prescan_health 据此区分"已覆盖所以跳过"（=校准成功）vs"低质所以跳过"（=没校准）。
DISPOSITION_REGISTERED = "registered"        # 走 register_web_search_batch 入库（默认，看 n_high/n_mid）
# 主动跳过且"已覆盖"类 — 该 slot 的材料早在库/被别 query 覆盖，等同校准成功
SKIP_DISPOSITIONS_COVERED = frozenset({"skipped-duplicate", "skipped-covered"})
# 主动跳过且"低质"类 — 返回了 hit 但全非权威、无一进库，是诚实的未校准（不算 hit）
SKIP_DISPOSITIONS_LOWTIER = frozenset({"skipped-lowtier"})
VALID_SKIP_DISPOSITIONS = SKIP_DISPOSITIONS_COVERED | SKIP_DISPOSITIONS_LOWTIER

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

# ---------------------------------------------------------------------------
# 域族 overlay 收敛回路（PRISM_VALIDATION F4 修）—— 分层白名单的"族"层
# 全局核心表 WHITELIST_DOMAINS 跨族通用、几乎不增长；族 overlay 随主 agent 的
# llm-judged-official 判断累积。脚本当 oracle，overlay/log 永不进主 agent 上下文。
# ---------------------------------------------------------------------------

_STATE_DIR = PRISM_ROOT / "state" / "whitelist"
PROMOTION_THRESHOLD = 2          # 同族同 host 被判 official ≥ N 次 → 晋升进 overlay
_OVERLAY_CACHE: dict[str, set[str]] = {}   # family -> hosts，进程内内容缓存


def _matches(domain: str, hosts: set[str]) -> bool:
    """exact 命中或作为某 host 的子域（endswith '.<host>'）。"""
    if not domain:
        return False
    if domain in hosts:
        return True
    return any(domain.endswith("." + h) for h in hosts)


def _overlay_path(family: str) -> Path:
    return _STATE_DIR / "overlays" / f"{family}.json"


def _load_overlay(family: str) -> set[str]:
    """读族 overlay 的 hosts 集（带进程内缓存）。缺文件 → 空集，不抛。
    返回防御性副本，调用方对结果的任何改动都不会污染 _OVERLAY_CACHE。"""
    if family in _OVERLAY_CACHE:
        return set(_OVERLAY_CACHE[family])
    hosts: set[str] = set()
    p = _overlay_path(family)
    if p.is_file():
        try:
            hosts = {str(h) for h in (json.loads(p.read_text(encoding="utf-8")).get("hosts") or [])}
        except Exception:
            hosts = set()
    _OVERLAY_CACHE[family] = hosts
    return set(hosts)


def _family_of(slug: str, variant: str) -> str | None:
    """域族 key = parent_topic || slug。

    prescan 阶段 sidecar 未生成、cluster_tags 不可得，故用 create_topic 即写入的
    parent_topic（无父的 industry 根 topic 用自身 slug）。读不到 topic → None
    （= 退化为全局表 only，行为同历史）。
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except Exception:
        return None
    return topic.get("parent_topic") or slug


def _promotion_log_path() -> Path:
    return _STATE_DIR / "_promotion_log.json"


def _read_promotion_log() -> dict:
    p = _promotion_log_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8")) or {}
    except Exception:
        print(f"[web_prescan] WARNING: corrupt promotion log {p}, starting fresh",
              file=sys.stderr)
        return {}
    return data if isinstance(data, dict) else {}


def _write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except Exception:
        tmp.unlink(missing_ok=True)   # 别把半截 tmp replace 进目标，也别留垃圾
        raise


def _append_to_overlay(family: str, host: str, display_name: str | None = None) -> None:
    p = _overlay_path(family)
    doc = {"family": family, "display_name": None, "hosts": [], "promoted_count": 0}
    if p.is_file():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            loaded = None
        if not isinstance(loaded, dict):
            # 损坏/非对象 overlay：警告 + 跳过写入，绝不用空 doc 覆盖已晋升的 host
            print(f"[web_prescan] WARNING: corrupt overlay {p}, skip write (existing preserved)",
                  file=sys.stderr)
            return
        doc = loaded
    hosts = sorted(set(doc.get("hosts") or []) | {host})
    doc["hosts"] = hosts
    doc["promoted_count"] = len(hosts)
    doc["family"] = family
    # display_name 是给人看的中文标签（机器键仍是英文 family）。仅显式传入时写/更新；
    # _promote 自动建族时不传 → 保留已有值或置 None（人可后补），绝不覆盖已写好的中文名。
    if display_name:
        doc["display_name"] = display_name
    elif "display_name" not in doc:
        doc["display_name"] = None
    _write_json_atomic(p, doc)
    _OVERLAY_CACHE.pop(family, None)   # 失效内容缓存 → 下次 classify 读到新值


def _promote(family: str, host: str, topic_id: str) -> bool:
    """记 LLM-judged-official 一次；同族同 host 跨 ≥ PROMOTION_THRESHOLD 个不同
    topic 被判 → 晋升进 overlay。返回 True 当且仅当本次触发了晋升。

    幂等且同 topic 去重：topics 列表存放已计数的 topic_id，重复不再 +count。
    """
    if not family or not host:
        return False
    log = _read_promotion_log()
    fam = log.setdefault(family, {})
    entry = fam.setdefault(host, {"count": 0, "topics": [], "promoted": False})

    if topic_id not in entry["topics"]:
        entry["topics"].append(topic_id)
        entry["count"] = len(entry["topics"])

    did_promote = False
    if not entry["promoted"] and entry["count"] >= PROMOTION_THRESHOLD:
        _append_to_overlay(family, host)
        entry["promoted"] = True
        did_promote = True

    _write_json_atomic(_promotion_log_path(), log)
    return did_promote


# 占位/编造 URL 守卫（修 [fabricated-url]）：主 agent 注册 web 材料时 url 必须从
# review-digest 原样拷贝，禁止凭记忆构造。命中任一明显占位特征即视为编造 → raise，
# 逼主 agent 回去拷真链接（占位 URL 是确定性错误，不该静默入库挂假出处）。
# 这是纯机械校验（零 LLM），符合"脚本只做校验+写入"的分工。
_PLACEHOLDER_URL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"[xX]{4,}", "含 xxxx 占位段"),
    (r"(?i)example\.(com|org|net|edu)", "example.* 保留域(RFC 占位)"),
    (r"\.\.\.|…", "含省略号(URL 被截断/未拷全)"),
    (r"[<>{}]", "含模板尖括号/花括号占位"),
    (r"(?i)placeholder|your-?domain|your-?url", "含 placeholder/your-* 占位词"),
)


def _looks_like_placeholder_url(url: str) -> str | None:
    """命中占位/编造特征则返回原因串，否则 None。供 register_web_search_result 守卫用。"""
    if not url:
        return None
    for pat, reason in _PLACEHOLDER_URL_PATTERNS:
        if re.search(pat, url):
            return reason
    return None


def _domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        # strip port + www
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc.split(":")[0]
    except Exception:
        return ""


def classify_domain(url: str, family: str | None = None) -> str:
    """Return 'whitelist' / 'llm-judged-official' / 'other'.

    命中顺序：① 全局核心表 WHITELIST_DOMAINS → ② 族 overlay（仅当传 family）
    → ③ IR 子域启发式。family=None 时行为与历史完全一致（向后兼容）。

    'llm-judged-official' 只在 caller 显式传 domain_tier 时出现，本函数不从 URL 产出它。
    """
    domain = _domain_of(url)
    if not domain:
        return "other"
    if _matches(domain, WHITELIST_DOMAINS):              # ① 全局核心表
        return "whitelist"
    if family and _matches(domain, _load_overlay(family)):  # ② 族 overlay（F4 收敛）
        return "whitelist"
    if any(tok in domain for tok in _IR_SUBDOMAIN_TOKENS):  # ③ IR 子域启发式
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


def extract_url_features(
    urls: list[str], slug: str | None = None, variant: str | None = None
) -> dict[str, dict]:
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
    family = _family_of(slug, variant) if slug else None
    out: dict[str, dict] = {}
    for url in urls:
        out[url] = {
            "in_whitelist": classify_domain(url, family) == "whitelist",
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
# 覆盖槽枚举 — 通用 across topic types
# ---------------------------------------------------------------------------


def build_search_queries(slug: str, variant: str, recency_days: int = 90) -> list[dict]:
    """枚举本 topic 需要 web 覆盖的"槽位"——不再拼 query 文本。

    设计原则（见 memory feedback_llm_workflow）：query 措辞是 LLM 判断，不该写死在
    模板里。旧版对 industry/arena 套死后缀 `行业政策/技术突破/产能变化/龙头新闻`，
    其中"产能变化"是制造业预设，套创新药等行业即产垃圾 query（PRISM_VALIDATION F3）。
    本函数因此只做机械记账，把"查什么"交还给对话里的主 agent：

      - 枚举"哪些 address 需要被覆盖"：scope / company 主体 / industry 行业面 /
        每个 concept / 每条 roadmap L4 hunting（逐条 K# 对齐）
      - 每个槽位附 ``hint``（原始素材：名称 / ticker / question / search_terms /
        search_keywords），供主 agent 用领域知识写 query
      - 绑定 ``addresses`` + ``recency_days`` + ``kind``（gap_detector 的覆盖账依赖
        addresses，故这层必须保留 + 保证 K#/L4 完备枚举）

    主 agent 拿到清单后，逐槽写实际 query（addresses 原样带回），再打 adapter +
    入库 —— 见 ``_web_prescan_shared.md``。

    返回 ``[{addresses, kind, recency_days, hint}, ...]``。
    **无 ``query`` 键**：query 文本由 LLM 在对话里产出，脚本不代笔。
    """
    topic = topic_io.read_topic(slug, variant)
    scope = topic.get("scope") or {}
    display_name = topic.get("display_name") or slug
    short_name = scope.get("short_name") or None
    name = short_name or display_name
    ttype = topic.get("type") or "concept"
    question = scope.get("question") or ""
    ticker = scope.get("ticker") or ""
    search_terms = scope.get("search_terms") or None

    slots: list[dict] = []

    # 1. scope 主覆盖 — 任何 topic 都有
    slots.append({
        "addresses": ["scope"],
        "kind": "scope",
        "recency_days": recency_days,
        "hint": {
            "short_name": short_name,
            "display_name": display_name,
            "question": question,
            "search_terms": search_terms,
        },
    })

    # 2. company 专属：ticker 主体的近期事件（查询轴由主 agent 自定，不再写死
    #    最新公告/监管处罚/业绩预告/高管变动 这套）
    if ttype == "company" and ticker:
        # ticker 形如 US_FUTU / SZSE_300073 — 取后段
        ticker_short = ticker.split("_", 1)[-1] if "_" in ticker else ticker
        slots.append({
            "addresses": ["scope"],
            "kind": "company-event",
            "recency_days": recency_days,
            "hint": {"name": name, "ticker": ticker_short},
        })

    # 3. industry / arena 专属：行业级事件（查询轴由主 agent 按领域定，
    #    不再写死"产能变化"等制造业预设 —— F3 修复）
    if ttype in ("industry", "arena"):
        if search_terms:
            base_terms = [s.strip() for s in search_terms[:2] if s and s.strip()]
        else:
            base_terms = [name]
        slots.append({
            "addresses": ["scope"],
            "kind": "industry-event",
            "recency_days": recency_days,
            "hint": {"base_terms": base_terms},
        })

    # 4. concept 专属：每个 concept 一槽
    if ttype == "concept":
        for c in (topic.get("concepts") or [])[:3]:
            slots.append({
                "addresses": ["scope"],
                "kind": "concept-update",
                "recency_days": recency_days,
                "hint": {"concept": c},
            })

    # 5. roadmap L4 hunting questions — 适用所有类型，逐条 K# 对齐。
    #    旧版在缺 search_keywords 时整槽跳过（= 覆盖漏洞）；现统一出槽，
    #    主 agent 拿 question + 任何已有 search_keywords 自行措辞。
    roadmap_path = PRISM_ROOT / "topics" / slug / variant / "roadmap.yaml"
    if roadmap_path.is_file():
        try:
            roadmap = yaml.safe_load(roadmap_path.read_text(encoding="utf-8")) or {}
            l4 = ((roadmap.get("learning_track") or {}).get("l4_hunting") or [])
            for q in l4:
                addrs = q.get("addresses") or []
                slots.append({
                    "addresses": addrs or ["scope"],
                    "kind": "l4-hunting",
                    "recency_days": recency_days,
                    "hint": {
                        "name": name,
                        "question": q.get("question") or q.get("text") or "",
                        "search_keywords": q.get("search_keywords") or [],
                    },
                })
        except Exception:
            pass

    return slots


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

    Raises:
        ValueError: url 命中占位/编造特征（xxxx / example.* / 省略号 / 模板括号 /
            placeholder 等）。主 agent 须回 review-digest 原样拷真实 URL 再重试。
    """
    placeholder_reason = _looks_like_placeholder_url(url)
    if placeholder_reason:
        raise ValueError(
            f"占位/编造 URL 被拒（{placeholder_reason}）: {url!r}。"
            f"web 材料的 url 必须从 review-digest 原样拷贝，不能凭记忆/构造。"
            f"回去拷真实链接后重试。"
        )
    domain = _domain_of(url)
    if domain_tier is None:
        domain_tier = classify_domain(url, _family_of(slug, variant))
    elif domain_tier == "llm-judged-official":
        family = _family_of(slug, variant)   # None if topic not found on disk
        if family:
            # 主 agent 显式判权威 → 喂收敛回路（跨 topic 达阈值自动晋升进 overlay）
            _promote(family, domain, f"{slug}/{variant}")
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
      - append_search_log（按 triggered_by 标签）
    prescan 只入库 + funnel + 写 log，**绝不碰 todo**——todo 闭环走产 todo 阶段的
    当场 fetch + 主 agent 按文档身份 mark_todo_fetch/update_user_todo_status。

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
    # prescan 只入库 + funnel + 写 log，绝不碰 todo 闭环——todo 收齐由产 todo 的阶段
    # 当场 fetch、主 agent 按文档身份走 mark_todo_fetch/update_user_todo_status 闭环。

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
    disposition: str = DISPOSITION_REGISTERED,
) -> None:
    """Append a search round to per-topic web_search_log.yaml.

    triggered_by ∈ {'01-prescan', '02-step0', '06-daily-monitor', '07-drilldown'}

    disposition：本轮 query 的处置。默认 'registered'（走 register_web_search_batch 入库，
      健康度看 n_high/n_mid）。主动跑了但没入库的轮次由 log_search_skipped 写入
      SKIP_DISPOSITIONS_* 之一——让 check_prescan_health 区分"已覆盖跳过"vs"低质跳过"。
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
        "disposition": disposition,
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump({"slug": slug, "variant": variant, "entries": entries},
                  allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def log_search_skipped(
    slug: str,
    variant: str,
    query: str,
    triggered_by: str,
    n_results: int,
    reason: str,
) -> None:
    """记录一条"跑了 WebSearch 但主动没 register"的 query，让 prescan 健康度不再假阴性。

    用法：主 agent 跑完一条 prescan/即兴 query、判定**无需入库**时调本函数留痕，
    而不是静默丢弃（静默 = web_search_log 无痕 = check_prescan_health 误判为未搜到）。

    reason 必须如实分类（影响健康度判定）：
      - 'skipped-duplicate' / 'skipped-covered'：top hit 已在库 / 已被别的 query 覆盖
        → check_prescan_health 记为命中（该 slot 已校准）
      - 'skipped-lowtier'：返回了 hit 但全非权威、无一值得入库
        → 不记命中（诚实的未校准，等同 all_low_band；critic 会列进"未校准清单"）

    ⚠️ 不要用 'skipped-covered' 把低质 slot 刷成假覆盖——只有 top hit 确属已在库/已覆盖
    才标 covered，判不准就标 lowtier。

    n_results：本轮 WebSearch 实际返回的原始 hit 数（>0 证明工具未限流；=0 应改走限流重试）。
    """
    if reason not in VALID_SKIP_DISPOSITIONS:
        raise ValueError(
            f"reason={reason!r} 非法，必须为 "
            f"{sorted(VALID_SKIP_DISPOSITIONS)} 之一"
        )
    append_search_log(
        slug=slug, variant=variant, query=query,
        n_results=n_results, n_high=0, n_mid=0, n_low=n_results,
        triggered_by=triggered_by, disposition=reason,
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
# 原生 WebSearch tool 痕迹记录 + empty todo 搜索证据校验
# ---------------------------------------------------------------------------

def log_native_websearch(
    slug: str, variant: str, query: str,
    n_results: int, triggered_by: str = "00-deep-fetch",
    disposition: str = "native-websearch-tool",
) -> None:
    """原生 WebSearch tool 搜完后调此函数留痕，让 verify_empty_todos_searched 可查。

    adapter 走 register_web_search_batch 时会自动写 web_search_log；
    但原生 WebSearch tool 不经过 adapter，需主 agent 显式调本函数留痕。
    """
    append_search_log(
        slug=slug, variant=variant, query=query,
        n_results=n_results, n_high=0, n_mid=0, n_low=n_results,
        triggered_by=triggered_by, disposition=disposition,
    )


def verify_empty_todos_searched(
    slug: str, variant: str,
) -> dict:
    """检查每条 fetch_status='empty' 的 todo 是否有对应搜索痕迹。

    搜索痕迹来源：
      - adapter: web_search_log 中的 entry（register_web_search_batch 自动写入）
      - 原生 WebSearch tool: log_native_websearch 写入的 entry
      - 手动 fetch: fetch_report_prism 在 manifest 中的记录（仅当 note 引用时）

    返回 dict：
      - verified: bool — 是否所有 empty todo 都有搜索痕迹
      - empty_todos: list[dict] — 所有 empty todo
      - unverified: list[dict] — 无搜索痕迹的 empty todo
    """
    from prism.scripts.topic import read_topic

    try:
        todos = read_topic(slug, variant).get("user_todos", []) or []
    except FileNotFoundError:
        return {"verified": True, "empty_todos": [], "unverified": []}

    empty_todos = [
        t for t in todos
        if isinstance(t, dict)
        and t.get("fetch_status") == "empty"
        and t.get("status") in ("pending", "in_progress")
    ]

    if not empty_todos:
        return {"verified": True, "empty_todos": [], "unverified": []}

    # 收集所有搜索痕迹：web_search_log 的 query 字段
    log_entries = list_search_log(slug, variant)
    searched_queries = {e.get("query", "") for e in log_entries}

    # 对每条 empty todo，查 task 关键词是否在任一搜索 query 中出现
    unverified = []
    for t in empty_todos:
        task = t.get("task", "")
        # 从 task 中取核心名词作为搜索关键词（取前 8 个字作为最小匹配单元）
        task_core = task[:8] if len(task) >= 4 else task
        # 检查是否有搜索 query 包含 task 的核心关键词
        found = any(
            task_core in q or any(
                word in q for word in task_core.replace("（", " ").replace("）", " ").replace("：", " ").replace(":", " ").split()
                if len(word) >= 2
            )
            for q in searched_queries
        )
        if not found:
            unverified.append(t)

    return {
        "verified": len(unverified) == 0,
        "empty_todos": empty_todos,
        "unverified": unverified,
    }


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
            'queries_with_hits': int,   # 已校准的条数：n_high+n_mid>=1 或 disposition 属"已覆盖跳过"
            'queries_skipped_covered': int,  # 其中靠 log_search_skipped 标"已覆盖"贡献的
            'hit_rate': float,          # queries_with_hits / max(expected_queries, queries_run)
            'failure_reason': str | None,  # status != 'full' 时给一句话原因
        }

    "命中"= 该 query 的 slot 已被新鲜证据校准。两种算命中（修 prescan-health 假阴性）：
      1. register_web_search_batch 入库了 high/mid（n_high+n_mid>=1）
      2. 主 agent 用 log_search_skipped 标 'skipped-duplicate'/'skipped-covered'
         （top hit 已在库/已覆盖 → 该 slot 本就校准过）
    不算命中：'skipped-lowtier'（返回了但全低质）、n_results=0（限流静默）——都是诚实的未校准。

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

    def _is_hit(e: dict) -> bool:
        if (e.get("n_high") or 0) + (e.get("n_mid") or 0) >= 1:
            return True
        # 主动跳过且属"已覆盖"类 → 该 slot 已校准，记命中（修假阴性）。
        # 'skipped-lowtier' 与无 disposition 的限流空轮都不命中。
        return e.get("disposition") in SKIP_DISPOSITIONS_COVERED

    queries_with_hits = sum(1 for e in matched if _is_hit(e))
    queries_skipped_covered = sum(
        1 for e in matched if e.get("disposition") in SKIP_DISPOSITIONS_COVERED
    )
    denom = max(expected_queries, queries_run, 1)
    hit_rate = round(queries_with_hits / denom, 3)

    if queries_run == 0:
        # 状态感知（修 #4）：本趟 log 空 ≠ 一定失败。materials 是 slug 级共享、
        # web_search_log 是 per-variant——复用/手动投料/重启都会"料在、log 空"。
        # 故回退查 manifest 是否已有网搜料（search_meta 或 source_type==web-search，
        # 后者兜底 mat_id churn 致 search_meta 未随复用带过来），有则判 'inherited' 而非 failed。
        from prism.scripts.manifest import read_manifest
        web_mats = [
            m for m in read_manifest(slug, variant).get("materials", [])
            if m.get("search_meta") or m.get("source_type") == "web-search"
        ]
        if web_mats:
            return {
                "status": "inherited",
                "queries_run": 0,
                "queries_with_hits": len(web_mats),
                "queries_skipped_covered": 0,
                "hit_rate": None,
                "failure_reason": None,
                "note": (
                    f"本趟未跑 prescan query，但 manifest 已有 {len(web_mats)} 条网搜料垫底"
                    f"（复用/手动投料）。这是诊断不是 gate——按 ≥partial 处理，不阻塞升 stage。"
                ),
            }
        return {
            "status": "failed",
            "queries_run": 0,
            "queries_with_hits": 0,
            "queries_skipped_covered": 0,
            "hit_rate": 0.0,
            "failure_reason": (
                f"prescan 一条都没跑且无任何网搜料（expected_queries={expected_queries}）"
                f" — WebSearch 工具可能不可用或主 agent 跳过 Step 4.5a"
            ),
        }

    if hit_rate >= 1.0 and queries_run >= expected_queries:
        return {
            "status": "full",
            "queries_run": queries_run,
            "queries_with_hits": queries_with_hits,
            "queries_skipped_covered": queries_skipped_covered,
            "hit_rate": hit_rate,
            "failure_reason": None,
        }

    if hit_rate >= WEB_SEARCH_FAIL_THRESHOLD:
        return {
            "status": "partial",
            "queries_run": queries_run,
            "queries_with_hits": queries_with_hits,
            "queries_skipped_covered": queries_skipped_covered,
            "hit_rate": hit_rate,
            "failure_reason": (
                f"prescan 校准率 {hit_rate:.0%}（{queries_with_hits}/{denom}，"
                f"含 {queries_skipped_covered} 条已覆盖跳过），"
                f"低于满分但高于失败阈值 {WEB_SEARCH_FAIL_THRESHOLD:.0%}"
            ),
        }

    return {
        "status": "failed",
        "queries_run": queries_run,
        "queries_with_hits": queries_with_hits,
        "queries_skipped_covered": queries_skipped_covered,
        "hit_rate": hit_rate,
        "failure_reason": (
            f"prescan 校准率 {hit_rate:.0%}（{queries_with_hits}/{denom}），"
            f"低于失败阈值 {WEB_SEARCH_FAIL_THRESHOLD:.0%} — "
            f"疑似 WebSearch 限流静默返空 / 区域阻断 / API 失效（或主动跳过的 query 未用 "
            f"log_search_skipped 留痕）"
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
