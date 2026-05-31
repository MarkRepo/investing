"""决策链输入合同（A 层）—— machine-readable。

这是 0/1/2/3 收料/抽料的组织脊柱之一（另一轴是 thesis 的 K# 覆盖）。
合同 = 三条 case 决策链（_company_case / _industry_funnel / _arena_funnel）
各环【必带硬落地】对**输入**的机械投影：要让每一环能落地，上游必须供给哪几类资料/数据。

关键性质（见 plan §关键设计原理 1/3）：
  - **type 常量、不依赖具体标的知识** —— 研究任何 company/industry/arena 之前就已知，无循环依赖。
    （命门特化深度是 B 层 decomposition，知识驱动、迭代，不在本文件。）
  - 与 thesis 的 K# **解耦**：K# 是 thesis 脊柱（addresses 字段），本合同是输入脊柱（rings 字段）。
  - **不新发明**：每项都能在对应 case 文档 §3.2【必带硬落地】找到出处；改合同必须同步改
    `_company_case.md`/`_industry_funnel.md`/`_arena_funnel.md` 与 prose 版 `_input_contract.md`。

字段：
  code          : 稳定标识（材料/findings 的 `rings` 标签用此），全小写 kebab，type 内唯一
  ring          : 服务的决策环序号（1=看懂 2=定价锚 3=WMBT 4=下注 5=证伪 6=行动）
  label         : 中文一句话（gap 报告 / 收料 todo 展示用）
  served_by     : 该项可由哪些源满足（gap ring 轴据此查源，见 gap_detector 双轴）
                  material-like（实收文件类）: material / fetch_report / web / user → 查材料 rings
                  structured（结构化数据类）  : financial_data / market_data / smm → 查 API/缓存存在性
                  一项可被多源满足（任一满足即覆盖）。
  source_hints  : 收料阶段建议的资料类型（source_type / 检索方向），非强制
  hard          : True = plan 认定的"真·欠供"（旧流程从不产出，重构后新增的胃口），收料须显式排期；
                  可得性受限时（如 A 股前瞻 consensus 在付费墙后）允许诚实降级为 user todo / 数据缺失。
  api_satisfiable: True = 某结构化源**单独即可满足**该项（财务弧线/估值锚由 financial_data/market_data
                  在合成期自动拉，给 ticker 即可），gap ring 轴不把"无材料"误判为红色缺口。
                  缺省 False = 材料强制项（质性，必须有实收材料；structured 源只能补充，不能独立满足）——
                  这恰好是 gap ring 轴的**可靠红色信号**（三项真·欠供全在此列）。

训练知识**不计入任何项的覆盖** —— 合同项只认实收料 / API，缺料只能标"训练知识估算"或"数据缺失"，不冒充。
"""
from __future__ import annotations

# 实收文件类源（gap ring 轴查材料 rings 计数）
MATERIAL_SOURCES = frozenset({"material", "fetch_report", "web", "user"})
# 结构化数据类源（gap ring 轴查 API/缓存存在性，无 mat_id）
API_SOURCES = frozenset({"financial_data", "market_data", "smm"})


INPUT_CONTRACT: dict[str, list[dict]] = {
    # ───────────────────────── company ─────────────────────────
    "company": [
        {
            "code": "biz-moat-unit-econ", "ring": 1,
            "label": "生意模式/收入拆解(量×价×结构)/护城河强弱/单位经济(毛利·单客·ROIC)",
            "served_by": ["material", "smm"],
            "source_hints": ["sell-side-note", "annual-report"],
        },
        {
            "code": "mgmt-capital-alloc", "ring": 1,
            "label": "管理层 track record + 资本配置历史(回购/分红/并购回报) + 激励治理",
            "served_by": ["material", "user"],
            "source_hints": ["annual-report", "proxy-statement", "policy"],
            "hard": True,
        },
        {
            "code": "financial-arc", "ring": 1,
            "label": "多年财务弧线(3-5Y 营收/利润率/ROIC/FCF 走势+拐点)",
            "served_by": ["financial_data"],
            "source_hints": ["financial_data"],
            "api_satisfiable": True,
        },
        {
            "code": "valuation-anchor", "ring": 2,
            "label": "当前价/估值倍数反推隐含 CAGR·终值PE·IRR",
            "served_by": ["market_data", "material"],
            "source_hints": ["market_data", "sell-side-note"],
            "api_satisfiable": True,
        },
        {
            "code": "consensus", "ring": 2,
            "label": "卖方一致预期/目标价模型(反推对照基准)",
            "served_by": ["material", "user"],
            "source_hints": ["sell-side-note"],
            "hard": True,
        },
        {
            "code": "valuation-percentile", "ring": 2,
            "label": "历史区间 + 全球 peer 估值水位",
            "served_by": ["market_data", "material"],
            "source_hints": ["market_data", "sell-side-note"],
            "api_satisfiable": True,
        },
        {
            "code": "bull-bear", "ring": 4,
            "label": "多空论据(喂④期望收益加总)",
            "served_by": ["material", "web"],
            "source_hints": ["sell-side-note"],
        },
        {
            "code": "historical-mirror", "ring": 5,
            "label": "历史失败镜鉴(相似剧本怎么崩)",
            "served_by": ["material", "web"],
            "source_hints": ["industry-research", "web-article"],
            "hard": True,
        },
    ],
    # ───────────────────────── industry ─────────────────────────
    "industry": [
        {
            "code": "value-chain-profit-pool", "ring": 1,
            "label": "价值链全貌+利润池定位(谁赚走·量×价×结构)+驱动因子+周期位",
            "served_by": ["material", "smm"],
            "source_hints": ["industry-research", "sell-side-note"],
        },
        {
            "code": "industry-financial-arc", "ring": 1,
            "label": "行业代表主体多年财务弧线(龙头/聚合 3-5Y)",
            "served_by": ["financial_data"],
            "source_hints": ["financial_data"],
            "api_satisfiable": True,
        },
        {
            "code": "leader-valuation-anchor", "ring": 2,
            "label": "龙头/细分倍数反推增速 + 相对水位(历史+全球peer) + 叙事资金流",
            "served_by": ["market_data", "material"],
            "source_hints": ["market_data", "sell-side-note"],
            "api_satisfiable": True,
        },
        {
            "code": "migration-path-evidence", "ring": 3,
            "label": "利润池迁移路径/结构性假设证据(谁攫取价值·渗透曲线·政策路径)",
            "served_by": ["material", "web"],
            "source_hints": ["industry-research", "web-article"],
        },
        {
            "code": "arena-scoring-inputs", "ring": 4,
            "label": "各 arena 6 维评分料(利润池规模/增速/竞争结构/估值水位/周期位)",
            "served_by": ["material"],
            "source_hints": ["industry-research", "sell-side-note"],
        },
        {
            "code": "industry-mirror", "ring": 5,
            "label": "历史行业镜鉴(利润没兑现/迁移没发生——电信capex·光伏)",
            "served_by": ["material", "web"],
            "source_hints": ["industry-research", "web-article"],
            "hard": True,
        },
    ],
    # ───────────────────────── arena ─────────────────────────
    "arena": [
        {
            "code": "biz-value-chain-position", "ring": 1,
            "label": "怎么赚钱+价值链卡位+路线之争+客户结构+赛道周期位",
            "served_by": ["material"],
            "source_hints": ["industry-research", "sell-side-note"],
        },
        {
            "code": "winner-variables", "ring": 2,
            "label": "关键胜负变量(成本曲线/技术代差/客户锁定/规模/牌照)",
            "served_by": ["material", "smm"],
            "source_hints": ["industry-research", "sell-side-note"],
        },
        {
            "code": "peer-valuation-anchor", "ring": 2,
            "label": "被当赢家那几家的当前估值(PE/PS 相对赛道·是否透支)",
            "served_by": ["market_data", "financial_data", "material"],
            "source_hints": ["market_data", "financial_data"],
            "api_satisfiable": True,
        },
        {
            "code": "peer-comparison-financials", "ring": 4,
            "label": "候选公司横比矩阵(≥5家·收入/ROIC/毛利/负债/PE/历史PE/路线/客户)",
            "served_by": ["financial_data", "material"],
            "source_hints": ["financial_data", "sell-side-note"],
            "api_satisfiable": True,
        },
        {
            "code": "arena-mirror", "ring": 5,
            "label": "历史镜鉴(曾经赢家如何被取代——Nokia/Kodak)",
            "served_by": ["material", "web"],
            "source_hints": ["industry-research", "web-article"],
            "hard": True,
        },
    ],
}


def required_inputs(topic_type: str) -> list[dict]:
    """返回某 type 的输入合同类目（list of dict）。未知 type → []。"""
    return list(INPUT_CONTRACT.get(topic_type, []))


def ring_codes(topic_type: str) -> set[str]:
    """返回某 type 所有合同项的 code 集合（材料/findings 合法 rings 标签）。"""
    return {item["code"] for item in INPUT_CONTRACT.get(topic_type, [])}


def get_item(topic_type: str, code: str) -> dict | None:
    """按 code 取单个合同项。"""
    for item in INPUT_CONTRACT.get(topic_type, []):
        if item["code"] == code:
            return item
    return None


def hard_undersupply_codes(topic_type: str) -> set[str]:
    """plan 认定的三项真·欠供（须显式排期收料）的 code 集合。"""
    return {item["code"] for item in INPUT_CONTRACT.get(topic_type, []) if item.get("hard")}


def is_material_served(item: dict) -> bool:
    """该项是否可由实收文件类源满足（gap 查材料 rings）。"""
    return bool(set(item.get("served_by") or []) & MATERIAL_SOURCES)


def is_api_served(item: dict) -> bool:
    """该项是否列了结构化数据类源（gap 查 API/缓存存在性）。"""
    return bool(set(item.get("served_by") or []) & API_SOURCES)


def is_api_satisfiable(item: dict) -> bool:
    """某结构化源是否**单独即可满足**该项（财务/估值类，合成期自动拉）。
    False = 材料强制项（质性，必须有实收材料）—— gap ring 轴的可靠红色信号。"""
    return bool(item.get("api_satisfiable"))


def default_report_rings(report_type: str, topic_type: str = "company") -> list[str]:
    """财报/公告类 fetcher 自动登记材料时的默认 rings，**按 topic.type 取向**（修 F10）。

    年报/招股书是完整的生意+治理+财务载体；季报/公告偏时效财务弧线。
    这些是**收料期粗标**，03 抽取时按实际内容在 finding frontmatter 精修/补 rings。
    旧实现恒返 company code → industry/arena 材料被打 company rings、与其合同零交集，
    gap A 轴永报全 uncovered（F10）。现按 type 映射到各自合同 code；未知 type 回退 company。
    """
    is_full = report_type in ("annual", "prospectus", "10-K", "10-k", "20-F", "40-F")
    if topic_type == "industry":
        return (["industry-financial-arc", "value-chain-profit-pool"]
                if is_full else ["industry-financial-arc"])
    if topic_type == "arena":
        return (["peer-comparison-financials", "peer-valuation-anchor"]
                if is_full else ["peer-comparison-financials"])
    # company（默认/兜底，行为不变）
    if report_type in ("annual", "10-K", "10-k"):
        return ["financial-arc", "mgmt-capital-alloc", "biz-moat-unit-econ"]
    if report_type == "prospectus":
        return ["biz-moat-unit-econ", "financial-arc", "mgmt-capital-alloc"]
    # quarterly / 公告 / 其它
    return ["financial-arc"]


def all_codes() -> set[str]:
    """跨所有 type 的全部 code（findings 标签宽松校验用）。"""
    out: set[str] = set()
    for items in INPUT_CONTRACT.values():
        out |= {i["code"] for i in items}
    return out
