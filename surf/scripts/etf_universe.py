"""surf · A股 ETF 候选池筛选。

零 LLM 调用。只做数据抓取与规则筛选。
筛选规则见 docs/superpowers/specs/2026-09-21-surf-design.md §6.1。
"""
from __future__ import annotations

import os
import sys

import pandas as pd


def _no_proxy() -> None:
    """akshare 走国内源，必须清掉代理环境变量，否则连接被墙/被拒。"""
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)


# 排除：货币/债券/现金管理、商品、宽基与策略指数、海外宽基。
# 目标是只留「行业 / 主题」ETF —— 即能代表一条产业趋势的标的。
EXCLUDE_PATTERN = "|".join([
    # 货币与债券
    "货币", "债", "国债", "政金", "现金", "理财", "短融", "融资", "日利", "添益", "保证金",
    # 商品
    "黄金", "白银", "豆粕", "原油", "商品", "能源化工", "金ETF",
    # A股宽基与策略指数
    "沪深300", "中证300", "中证500", "中证1000", "中证2000", "中证A500", "中证A50",
    "上证50", "科创50", "科创100", "科创200", "创业板", "科创创业", "深证100",
    "上证180", "上证380", "上证指数", "深证成指", "中证100",
    "MSCI", "富时", "红利", "价值", "成长", "质量", "低波", "等权", "基本面", "自由现金流",
    "大盘", "中盘", "小盘", "超大", "A50", "A500", "龙头指数",
    # 海外与地域宽基
    "纳指", "纳斯达克", "道琼斯", "标普", "日经", "东证", "德国", "法国", "东南亚",
    "沙特", "越南", "印度", "巴西", "美国", "亚太", "全球", "海外", "新兴市场",
    "恒生指数", "恒生中国", "恒生科技指数", "H股", "中概", "MSCI中国",
    # 所有制/地方主题，不代表产业趋势
    "国企", "央企", "国新", "上海", "深圳", "北京", "广东",
    # 首轮扫描漏网的宽基与策略指数（"恒生ETF" 精确匹配，不误伤恒生科技/恒生医药等主题）
    "国证2000", "中证800", "深证50", "深成", "双创", "科创综指",
    "A股ETF", "恒生ETF", "港股通50", "高股息", "消费50", "快线",
])

# 两阶段筛选（DESIGN §6.1 要求的是「近 20 日日均成交额 > 3000 万」）：
# 这里只做当日成交额粗筛，阈值放宽到 2000 万留出余量——当日可能恰逢缩量；
# 精筛在 scan_cn.py 里用历史数据算出的 amt20 完成。
MIN_TURNOVER = 2000e4


def build_universe(min_turnover: float = MIN_TURNOVER) -> pd.DataFrame:
    """返回筛选后的 A 股行业/主题 ETF 候选池。

    这是粗筛。精筛（近 20 日日均成交额）在 scan_cn.py 中完成。

    列：代码（带 sh/sz 前缀）、名称、主题、最新价、成交额。
    """
    _no_proxy()
    import akshare as ak

    df = ak.fund_etf_category_sina(symbol="ETF基金")
    df["成交额"] = pd.to_numeric(df["成交额"], errors="coerce")
    df = df[df["成交额"] > min_turnover]
    df = df[~df["名称"].str.contains(EXCLUDE_PATTERN, regex=True, na=False)]

    # 同一主题保留成交额最大的一只：用去掉基金公司后缀的名称做主题键。
    # 「半导体设备ETF国泰」「半导体设备ETF易方达」→ 同一主题「半导体设备ETF」。
    df = df.copy()
    df["主题"] = df["名称"].str.replace(r"ETF.*$", "ETF", regex=True)
    df = df.sort_values("成交额", ascending=False).drop_duplicates("主题", keep="first")

    return df[["代码", "名称", "主题", "最新价", "成交额"]].reset_index(drop=True)


if __name__ == "__main__":
    u = build_universe()
    out = os.path.join(os.path.dirname(__file__), "..", "etf_universe_cn.csv")
    u.to_csv(os.path.abspath(out), index=False, encoding="utf-8-sig")
    print(f"候选池 {len(u)} 只 -> {os.path.abspath(out)}")
    print(u.head(40).to_string())
