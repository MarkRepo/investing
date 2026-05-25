"""Sanity tests for WHITELIST_DOMAINS coverage."""
import pytest

from prism.scripts.web_prescan import WHITELIST_DOMAINS, classify_domain


@pytest.mark.parametrize("url,expected", [
    # CN regulators
    ("https://www.csrc.gov.cn/abc", "whitelist"),
    ("https://www.miit.gov.cn/abc", "whitelist"),
    ("https://www.ndrc.gov.cn/abc", "whitelist"),
    # FTC / FCC / EC
    ("https://www.ftc.gov/news/abc", "whitelist"),
    ("https://ec.europa.eu/competition/abc", "whitelist"),
    # 产业垂直
    ("https://36kr.com/article/abc", "whitelist"),
    ("https://www.theinformation.com/articles/abc", "whitelist"),
    ("https://semianalysis.com/p/abc", "whitelist"),
    # 数据机构
    ("https://www.counterpointresearch.com/abc", "whitelist"),
    ("https://www.idc.com/getdoc.jsp?abc", "whitelist"),
    ("https://www.trendforce.com/abc", "whitelist"),
    # 学术
    ("https://arxiv.org/abs/2401.00001", "whitelist"),
    ("https://www.nature.com/articles/abc", "whitelist"),
    # 数据港
    ("https://fred.stlouisfed.org/series/abc", "whitelist"),
    ("https://www.bls.gov/news.release/abc", "whitelist"),
    # IR sub-domain heuristic
    ("https://ir.tencent.com/news", "whitelist"),
    ("https://investors.apple.com/abc", "whitelist"),
    # Off-whitelist
    ("https://random-blog.example/x", "other"),
])
def test_classify_domain(url, expected):
    assert classify_domain(url) == expected


def test_whitelist_size_grew():
    """Sanity: whitelist 扩展后至少 130 项（原 ~60，新增 ~90 → ~150）。"""
    assert len(WHITELIST_DOMAINS) >= 130
