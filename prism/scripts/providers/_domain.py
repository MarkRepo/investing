"""Domain tier 分类（搬自 tavily_search.py）。

LOW_SIGNAL_HOSTS / GENERIC_AUTHORITATIVE_HOSTS / CLUSTER_AUTHORITATIVE_HOSTS
是 cluster 专属与全行业通用权威源白名单，classify_hit_domain_tier 由
adapter 后处理调用，给每条 Hit 写入 domain_tier。
"""
from __future__ import annotations

LOW_SIGNAL_HOSTS = frozenset({
    "x.com", "twitter.com", "youtube.com", "youtu.be",
    "reddit.com", "facebook.com", "instagram.com",
    "tiktok.com", "weibo.com",
})

GENERIC_AUTHORITATIVE_HOSTS = frozenset({
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "cnbc.com",
    "marketwatch.com", "barrons.com", "economist.com", "nikkei.com",
    "investing.com", "seekingalpha.com", "yahoo.com", "finance.yahoo.com",
    "21jingji.com", "yicai.com", "caixin.com", "stcn.com", "cls.cn",
    "eastmoney.com", "sina.com.cn", "163.com", "thepaper.cn",
    "sec.gov", "nrc.gov", "energy.gov", "doe.gov", "eia.gov",
    "iaea.org", "iea.org", "europa.eu", "csrc.gov.cn", "stats.gov.cn",
    "ndrc.gov.cn", "gov.cn", "miit.gov.cn", "mof.gov.cn",
    "spglobal.com", "moodys.com", "fitchratings.com",
    "tradingeconomics.com", "statista.com",
    "nature.com", "science.org", "sciencedirect.com", "nih.gov", "pubmed.ncbi.nlm.nih.gov",
})

CLUSTER_AUTHORITATIVE_HOSTS: dict[str, frozenset[str]] = {
    "uranium-nuclear": frozenset({
        "world-nuclear.org", "world-nuclear-news.org", "neimagazine.com",
        "ans.org", "nucnet.org", "nuclearnewswire.com",
        "uranium.info", "numerco.com", "sightlineu3o8.com", "uxc.com",
        "cmegroup.com", "ux.com",
        "mining.com", "mining-journal.com", "kitco.com", "northernminer.com",
        "investingnews.com", "theoregongroup.com", "stockhead.com.au",
        "discoveryalert.com.au", "theextractormagazine.com",
        "miningweekly.com", "creamermedia.com",
        "cameco.com", "kazatomprom.kz", "sprott.com", "orano.group",
        "urenco.com", "urencousa.com", "centrusenergy.com",
        "nexgenenergy.com", "nexgenenergy.ca",
        "denisonmines.com", "paladinenergy.com",
        "bossenergy.com.au", "bossenergy.com",
        "energyfuels.com", "uraniumenergy.com", "ur-energy.com",
        "fissionuranium.com", "goviex.com",
        "converdyn.com",
        "nuscalepower.com", "x-energy.com", "oklo.com",
        "terrapower.com", "bwxt.com", "bwxtechnologies.com",
        "cgnpc.com.cn", "cnnc.com.cn",
        "iea.org", "csis.org", "atlanticcouncil.org",
        "etftrends.com", "vaneck.com", "sprottetfs.com",
        "nrc.gov", "cnsc-ccsn.gc.ca", "iaac-aeic.gc.ca",
        "wikipedia.org", "en.wikipedia.org",
        "ecofinagency.com", "manaramagazine.org",
        "congress.gov", "strtrade.com",
        "dfcfw.com", "pdf.dfcfw.com",
    }),
}


def classify_hit_domain_tier(url: str, cluster: str | None = None) -> str | None:
    """根据 url hostname 预判 domain_tier。

    Returns:
        'llm-judged-official' — 已知权威源
        'other'               — 显式低信号站点
        None                  — 不预判，让 register_web_search_result 走默认
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

    if cluster and cluster in CLUSTER_AUTHORITATIVE_HOSTS:
        if host in CLUSTER_AUTHORITATIVE_HOSTS[cluster]:
            return "llm-judged-official"
        for known in CLUSTER_AUTHORITATIVE_HOSTS[cluster]:
            if host.endswith("." + known):
                return "llm-judged-official"

    if host in GENERIC_AUTHORITATIVE_HOSTS:
        return "llm-judged-official"
    for known in GENERIC_AUTHORITATIVE_HOSTS:
        if host.endswith("." + known):
            return "llm-judged-official"

    return None
