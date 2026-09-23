"""surf · A股 ETF 全量抓取与规则层剔除。

零 LLM 调用。本文件只做两件事：抓全市场 ETF，按**资产类别**规则打剔除标记。

与旧版的关键差异（DESIGN §6.1 改版）：
1. **不再返回「筛完的池子」，而是返回全量 + 剔除原因**。被剔除的标的要在
   `/surf/universe` 页面上带理由显示——只有能看见砍了什么，才可能发现砍错了。
2. **不再在这里做主题归一**。旧版用「名称去掉基金公司后缀」当主题键，导致
   「港股通医疗ETF」「恒生医药ETF」「港股创新药ETF」被当成三个主题，
   11 只港股医药系全部入池、霸占 RS60 前 20 的 11 席，通道 B 无席可看。
   主题归一改由 LLM 判定（写入 themes.json），本文件不参与。
3. **风格/因子词从排除表移出**。「红利/价值/成长/低波/等权/自由现金流」剔的不是
   资产类别而是**载体资格**（成分按财务特征聚合而非按产业聚合），那是判断不是事实，
   规则做不全——「银行AH优选」就漏在表外。这类交给 LLM 层（DESIGN §6.1 两层过滤器）。
"""
from __future__ import annotations

import os
import sys

import pandas as pd


def _no_proxy() -> None:
    """akshare 走国内源，必须清掉代理环境变量，否则连接被墙/被拒。

    ⚠️ 这是**永久 pop**，对整个进程生效。混市场抓取时（A股+港股/美股）
    必须在每只标的前按市场重设代理，不能依赖调用顺序（DESIGN §6.4 ⑧）。
    """
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
              "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(k, None)


# ---------------------------------------------------------------------------
# 规则层：只剔**资产类别与标的范围**——这些是硬事实，规则能做对。
# 载体资格（风格/因子/套利/收益型）不在这里，见模块 docstring 第 3 点。
# ---------------------------------------------------------------------------
ASSET_CLASS_EXCLUDE: dict[str, list[str]] = {
    "货币/理财": ["货币", "现金", "理财", "短融", "融资", "日利", "添益", "保证金"],
    "债券": ["债", "国债", "政金"],
    "商品": ["黄金", "白银", "豆粕", "原油", "商品", "能源化工", "金ETF"],
    "A股宽基指数": [
        "沪深300", "中证300", "中证500", "中证1000", "中证2000", "中证A500", "中证A50",
        "上证50", "科创50", "科创100", "科创200", "创业板", "科创创业", "深证100",
        "上证180", "上证380", "上证指数", "深证成指", "中证100", "MSCI", "富时",
        "国证2000", "中证800", "深证50", "深成", "双创", "科创综指", "A股ETF", "快线",
        # 产品名里不带指数公司前缀的漏网宽基：「A500ETF华夏」不含「中证A500」
        "A50", "A100", "A150",
    ],
    "海外/地域宽基": [
        "纳指", "纳斯达克", "道琼斯", "标普", "日经", "东证", "德国", "法国", "东南亚",
        "沙特", "越南", "印度", "巴西", "美国", "亚太", "全球", "海外", "新兴市场",
        "恒生指数", "恒生中国", "恒生科技", "H股", "中概", "MSCI中国",
        "恒生ETF", "港股通50",
    ],
}

# 粗筛：当日成交额。阈值比 DESIGN §6.1 的 3000 万放宽，留出当日缩量的余量，
# 精筛（近 20 日日均成交额）在 scan_cn.py 用历史数据完成。
MIN_TURNOVER = 2000e4


def _asset_class_reason(name: str) -> tuple[str, str] | None:
    """命中资产类别排除词则返回 (原因码细类, 命中的词)，否则 None。"""
    for bucket, words in ASSET_CLASS_EXCLUDE.items():
        for w in words:
            if w in name:
                return bucket, w
    return None


def build_universe(min_turnover: float = MIN_TURNOVER) -> pd.DataFrame:
    """抓全市场 ETF，逐只标注规则层结论。

    返回全量（不是筛完的池子），列：
      代码 / 名称 / 最新价 / 成交额 / 剔除原因 / 剔除说明

    `剔除原因` 为空串表示通过规则层；非空取值见 DESIGN §6.1 过滤原因码：
      - ``asset_class``  资产类别（货币/债/商品/宽基/地域宽基）
      - ``illiquid``     当日成交额不足

    LLM 层（``not_carrier``）与同主题折叠（``dedup``）在 scan_cn.py 完成。
    """
    _no_proxy()
    import akshare as ak

    df = ak.fund_etf_category_sina(symbol="ETF基金")
    df = df.copy()
    df["成交额"] = pd.to_numeric(df["成交额"], errors="coerce").fillna(0)

    reasons, notes = [], []
    for _, r in df.iterrows():
        hit = _asset_class_reason(str(r["名称"]))
        if hit:
            bucket, word = hit
            reasons.append("asset_class")
            notes.append(f"{bucket}（名称含「{word}」）")
        elif r["成交额"] <= min_turnover:
            reasons.append("illiquid")
            notes.append(f"当日成交额 {r['成交额'] / 1e4:.0f} 万 ≤ {min_turnover / 1e4:.0f} 万")
        else:
            reasons.append("")
            notes.append("")

    df["剔除原因"] = reasons
    df["剔除说明"] = notes
    out = df[["代码", "名称", "最新价", "成交额", "剔除原因", "剔除说明"]]
    return out.reset_index(drop=True)


if __name__ == "__main__":
    u = build_universe()
    passed = u[u["剔除原因"] == ""]
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "etf_universe_cn.csv"))
    u.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"全量 {len(u)} 只，规则层通过 {len(passed)} 只 -> {out}", file=sys.stderr)
    print(u["剔除原因"].value_counts().to_string())
