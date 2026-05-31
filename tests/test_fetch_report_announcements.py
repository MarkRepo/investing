"""F7: A股公告标题噪声黑名单 + 类目默认（纯函数，无网络）。

报告 F7 原诊断"annual 过抓 99 份公告"已在公告双轨重构后失效；当前残留噪声来自
fetch_announcements_cn 整类目拉取。修法：标题级黑名单（保守·只删确定治理/中介噪声，
催化剂一律留）+ 移除 gqjl（股权激励）默认类目。
"""
import re

from scripts import fetch_report_prism as frp


# 必须被丢弃的治理/中介程序性噪声
NOISE_TITLES = [
    "荣昌生物关于2022年A股限制性股票激励计划之B类权益预留授予第一个归属期符合归属条件",
    "北京海润天睿律师事务所关于荣昌生物2022年A股限制性股票激励计划之A类权益第三个归属",
    "立信会计师事务所关于四川百利天恒2025年度募集资金存放与使用情况鉴证报告",
    "关于召开2024年年度股东大会的独立董事候选人公告",
    "华泰联合证券有限责任公司关于荣昌生物2025年度持续督导现场检查报告",
    "公司章程修正案",
    "薪酬与考核委员会关于2024年度董事监事高级管理人员薪酬的议案",
    "审计委员会2025年度对会计师事务所履行监督职责情况报告",
    "H股公告",
    "内部控制审计报告",
]

# 必须被保留的催化剂（临床/BD/业绩/季报/年报本体）
CATALYST_TITLES = [
    "恒瑞医药关于获得药物临床试验批准通知书的公告",
    "恒瑞医药关于药品纳入突破性治疗品种名单的公告",
    "恒瑞医药2026年第一季度报告",
    "荣昌生物2025年度业绩快报公告",
    "四川百利天恒药业股份有限公司2025年年度业绩预告",
    "恒瑞医药2025年年度报告",
    "关于全资子公司与BMS签署独家许可协议暨对外授权的公告",
    "关于核心产品III期临床达到主要终点（OS）的提示性公告",
]


def test_noise_titles_dropped():
    for t in NOISE_TITLES:
        assert re.search(frp._TITLE_NOISE_RE, t), f"应丢弃噪声: {t}"


def test_catalyst_titles_kept():
    for t in CATALYST_TITLES:
        assert not re.search(frp._TITLE_NOISE_RE, t), f"误杀催化剂: {t}"


def test_gqjl_removed_from_default_categories():
    """股权激励类目移出默认（经黑名单后本就清零）。"""
    assert "gqjl" not in frp._ANNOUNCEMENT_CATEGORIES
    # 业绩预告/快报这条催化剂类目必须保留
    assert "yjygjxz" in frp._ANNOUNCEMENT_CATEGORIES
