"""一次性：把当前 m_regime_read 的判断逆向落成首份评估快照（regime_eval_log v1）。

input_snapshot 自动列全登记表所有输入（值取自现有 observed，未抓记 null —— 诚实盲区）；
CONCLUSIONS 手填，内容逐字抄自真实 outputs/m_regime_read.md（2026-06-07 快照）的结论行，
based_on 的 input 名与 macro_inputs.yaml 的 name 逐字一致（否则 append_evaluation 报"悬空"）。
role ∈ {load_bearing, confirming, background}。本脚本零 LLM 运行：只是把已写好的判断结构化落盘。
"""
from prism.scripts import eval_snapshot as es
from prism.scripts import macro_registry as reg

SLUG, VARIANT = "global-macro-rates-liquidity", "opus4.8"

# 评估快照对应 m_regime_read v1（generated 2026-06-07）。8 条结论：综合 + 三体制×(美/中) + 象限 + 脆弱度。
CONCLUSIONS = [
    {"id": "overall", "label": "综合判断", "state": "中美背离·美紧中松 分化体制（强度 6/10）",
     "based_on": [
         {"input": "联邦基金目标区间", "role": "load_bearing"},
         {"input": "HY OAS", "role": "confirming"},
         {"input": "社融 TSF", "role": "load_bearing"},
         {"input": "USDCNY", "role": "confirming"}],
     "causal": "美利率高位筑顶/加息尾部风险 + 美信用利差极窄但脆弱（美紧），叠加中国宽货币紧信用、人民币意外企稳（中松）→「中美背离·美紧中松」分化体制。组合应偏防御、压久期、警惕美元/美利率尾部，对纯 A 股内需票相对淡定。强度 6/10：方向清晰但三体制内部各有张力、拐点敏感。"},

    {"id": "rates_us", "label": "美国利率体制", "state": "高位筑顶·加息尾部风险升温·曲线熊平",
     "based_on": [
         {"input": "联邦基金目标区间", "role": "load_bearing"},
         {"input": "CME FedWatch 隐含路径", "role": "load_bearing"},
         {"input": "FOMC 点阵图(SEP)", "role": "confirming"},
         {"input": "美联储官员讲话(主席)", "role": "confirming"},
         {"input": "非农就业 NFP", "role": "confirming"},
         {"input": "2Y/10Y/30Y 国债", "role": "load_bearing"},
         {"input": "10Y 实际利率 TIPS", "role": "confirming"}],
     "causal": "政策利率高位（3.50–3.75%）+ 新主席 Warsh 转鹰 + 5 月非农大超预期 → FedWatch 加息概率升温、降息预期逆转为加息风险；2Y 被「不降息」钉住、长端被通胀/发债推高 → 2Y/10Y 利差压到近一年最窄的熊平。10Y 实际利率约 2.11% 是成长股估值硬约束。净判：美利率高且可能更高，对长久期资产不友好。"},

    {"id": "rates_cn", "label": "中国利率体制", "state": "低位偏松·方向中性偏下",
     "based_on": [
         {"input": "中国 10Y CGB + 资产荒需求", "role": "load_bearing"},
         {"input": "DR007/R007", "role": "load_bearing"},
         {"input": "LPR 1Y/5Y(5Y=房贷链)", "role": "confirming"},
         {"input": "7天 OMO 逆回购利率(新锚)", "role": "confirming"},
         {"input": "货币政策执行报告 MPR", "role": "confirming"}],
     "causal": "10Y CGB 回落至约 1.7% 历史低位区间 + DR007/DR001 低位 + 货政报告定调「适度宽松、结构性工具为主」→ 中国钱便宜且偏松，托底国内顺周期与红利；与美国约 4.5% 形成约 −280bp 温差。短期更可能用结构性工具而非全面降准降息。"},

    {"id": "liquidity_us", "label": "美国流动性体制", "state": "量中性·信用利差极窄·风险偏好亢奋但脆弱",
     "based_on": [
         {"input": "HY OAS", "role": "load_bearing"},
         {"input": "IG OAS", "role": "load_bearing"},
         {"input": "净流动性(=资产−TGA−RRP)", "role": "load_bearing"},
         {"input": "美联储资产 WALCL(QT 节奏)", "role": "confirming"},
         {"input": "RRP 逆回购", "role": "confirming"}],
     "causal": "QT 尾声 + RRP 池基本耗尽 → 净流动性量中性、不再是顺风（此项为定性估算，未取到单一权威即时值）；但 IG OAS 约 72bp / HY OAS 约 257–283bp 处本信用周期极窄 → 信用市场风险偏好仍极度亢奋、几乎不为违约补偿。双刃剑：当下托估值，但缓冲极薄，利差一旦从极窄走阔对高 β 风险资产杀伤最快。"},

    {"id": "liquidity_cn", "label": "中国流动性体制", "state": "宽货币 × 紧信用（有水·鱼不出来）",
     "based_on": [
         {"input": "社融 TSF", "role": "load_bearing"},
         {"input": "信贷脉冲", "role": "load_bearing"},
         {"input": "M1/M2/剪刀差", "role": "load_bearing"},
         {"input": "贷款增速", "role": "confirming"}],
     "causal": "央行→银行这层水足（DR007 低、社融/M2 合理），但社融同比回落至约 7.8% 历史低点、贷款增速创记录低、居民贷款同比萎缩 → 银行→实体这层堵住，典型宽货币 × 紧信用、「推绳子」风险。M1-M2 剪刀差仍为负但持续收窄，是边际改善信号但绝对水平仍指向需求偏弱。"},

    {"id": "fx_cny", "label": "人民币汇率体制", "state": "企稳偏强·外资边际回流·中性偏友好（深度负利差悬顶）",
     "based_on": [
         {"input": "USDCNY", "role": "load_bearing"},
         {"input": "DXY", "role": "confirming"},
         {"input": "广义/EM加权美元(Fed DTWEXBGS)", "role": "confirming"},
         {"input": "北向资金", "role": "load_bearing"},
         {"input": "中美 10Y 利差", "role": "confirming"},
         {"input": "PBoC 中间价 + 逆周期因子", "role": "confirming"}],
     "causal": "USDCNY 约 6.78、年内升值约 3% + DXY 偏软（约 96）+ 北向/海外主动基金 4 年来转净流入 → 人民币意外企稳、汇率端当下中性偏友好。中美 10Y 利差约 −280bp 深度倒挂本是理论压力源，但套利链当前失灵——由 DXY 软 + 中间价维稳 + 全球去美元化再配置三股力量对冲。DXY 转强或政策容忍度变化即可能快速反转为承压+外资流出。"},

    {"id": "quadrant", "label": "增长/通胀象限", "state": "滞胀（训练知识估算）",
     "based_on": [
         {"input": "核心 PCE", "role": "load_bearing"},
         {"input": "CME FedWatch 隐含路径", "role": "confirming"},
         {"input": "WTI 油价(+供给/需求分解)", "role": "confirming"},
         {"input": "信贷脉冲", "role": "confirming"}],
     "causal": "通胀侧：美核心通胀粘性、降息预期逆转为加息风险、油价（$100，Iran 冲突）抬升通胀预期 → 通胀压力未解；增长侧：高利率压制需求、无明显反弹信号、中国信用传导不畅 → 增长偏弱。高通胀压力 + 增长放缓 = 滞胀格。独立于三体制（市场体制），当前一致指向防御但未来可背离。象限当前为训练知识估算（缺最新逐月增长/通胀实测）。"},

    {"id": "fragility", "label": "脆弱度", "state": "高（fragility = high）",
     "based_on": [
         {"input": "2Y/10Y/30Y 国债", "role": "load_bearing"},
         {"input": "HY OAS", "role": "load_bearing"},
         {"input": "IG OAS", "role": "confirming"},
         {"input": "持仓拥挤(CFTC + CTA/vol-target + basis-trade规模)", "role": "confirming"},
         {"input": "USDJPY / 日元 carry", "role": "confirming"},
         {"input": "VIX", "role": "background"}],
     "causal": "2Y/10Y 利差压到近一年最窄 + IG/HY OAS 处历史极窄 → 缓冲极薄；风险偏好亢奋、波动率压低 = 低波动末段；深度负利差下 carry 头寸拥挤（日元 carry 为阈值尾部触发），一旦反转易踩踏；PBoC 保汇率/Fed 通胀优先/人民币企稳延续等承重假设叠加，任一证伪即强制重判 → 脆弱度高，综合信心要被它折减。"},
]


def build():
    registry = reg.read_registry(SLUG, VARIANT)
    used_names = {b["input"] for c in CONCLUSIONS for b in c["based_on"]}
    snapshot = []
    for e in registry["inputs"]:
        obs = e.get("observed") or {}
        snapshot.append({
            "name": e["name"],
            "value": obs.get("value"),                 # 未抓 → None（诚实盲区）
            "as_of": obs.get("as_of") or None,
            "used": e["name"] in used_names,
        })
    return {"evaluated_at": "2026-06-07",
            "note": "首份快照（由 backfill_macro_snapshot 从 m_regime_read v1 逆向补写）",
            "input_snapshot": snapshot, "conclusions": CONCLUSIONS}


def main():
    payload = build()
    version = es.append_evaluation(SLUG, VARIANT, payload)
    used = sum(1 for s in payload["input_snapshot"] if s["used"])
    print(f"写入评估快照 v{version}，输入 {len(payload['input_snapshot'])} 条（参与 {used} 条），"
          f"结论 {len(payload['conclusions'])} 条")


if __name__ == "__main__":
    main()
