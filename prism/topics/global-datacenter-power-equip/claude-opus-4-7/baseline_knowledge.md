# Baseline Knowledge — global-datacenter-power-equip

> Auto-generated from web prescan 2026-05-28 | 12 search queries | prescan_status: partial

## 1. Scope & Key Players

**核心问题**: 数据中心机房内配电、UPS、液冷的竞争格局与弹性

**三大全球龙头**:
- **Vertiv (VRT)** — 纯正DC基础设施标的，唯一同时覆盖电源(UPS/PDU)+制冷的公司，FY2025营收$10.2B (+27.7%), $15B backlog (+109%), 2026指引$13.25-13.75B营收, adj EPS $5.97-6.07, forward PE ~53x
- **Eaton (ETN)** — 电气巨头，Q1 2026 record $7.5B营收, Electrical Americas backlog +44% to $14.5B, 2026年3月完成$9.5B收购Boyd Thermal进入液冷
- **Schneider Electric (SU)** — 欧洲龙头，Q1 2026 €9.77B营收, double-digit有机增长, 硬件+软件整合最强，DC管理软件护城河

**二级玩家**:
- **nVent (NVT)** — ~30% DC exposure (多元玩家中最高), Q3 2025加入NVIDIA合作伙伴网络, Siemens合作
- **Delta Electronics** — 台湾电源专家，成本竞争力强
- **中国**: 科华数据(UPS国内领先)、科士达(UPS+储能)、英维克(液冷全链条龙头)、曙光数创(浸没液冷)

## 2. Market Sizing

| 细分市场 | 2025 规模 | 预测 | CAGR |
|---------|---------|------|------|
| DC Power总市场 | $35.14B | $50.51B (2030) | ~7.5% |
| DC UPS | $8.76B | $12.47B (2030) | 7.3% |
| DC Liquid Cooling | $4.8B | ~$7B (2029, Dell'Oro) | 18-20% |
| AI DC Liquid Cooling | $3.7B (2026) | $18.1B (2036) | ~17% |

## 3. Technology Trends

**HVDC架构转型**:
- NVIDIA GTC 2025发布800V DC架构，面向Rubin/Kyber平台
- 传统54V/48V在MW级rack不够用（64U rack space被power shelf占满）
- Vertiv 2025年10月宣布2026年推出完整800V HVDC产品线
- 关键判断: 800VDC还不是硬需求—Rubin NVL72 (2026-2027) rack density 180-220kW，三相AC仍可支撑。Phase 1是rack-level DC，非全栈DC
- Meta ±400V方案预计2026 Q1落地；百度/阿里启动±750V研发

**机柜功率密度**:
- GB200 NVL72: 132kW/rack
- Blackwell Ultra/Rubin: 250-900kW by 2026-2027
- NVIDIA Kyber (576 Rubin Ultra GPUs): 目标1MW/rack
- 100kW+ rack基建成本$200-300K/rack

**液冷渗透**:
- Dell'Oro: 2025年液冷市场近翻倍至~$3B, 2029年$7B
- 直接到芯片冷板是当前主流；浸没仍小众
- Jensen CES 2026: Vera Rubin支持45°C液冷(多数气候可实现free cooling)
- 30-40kW/rack以上液冷必须；AI rack全液冷

## 4. Competitive Dynamics

**Vertiv**:
- 优势: 纯正标的、唯一电源+冷却全覆盖、$15B backlog锁定2026-2027营收、液冷市占率>11.3%行业第一、252% Q4订单增速
- 风险: 53x PE估值溢价、HVDC转型执行风险、hyperscaler capex周期

**Eaton**:
- 优势: 电气盘柜+配电霸主地位、$14.5B Electrical Americas backlog、Boyd Thermal补全液冷短板、多元业务降周期风险
- 风险: $9.5B收购对价22.5x EBITDA偏贵、整合执行风险、DC纯度不如Vertiv

**Schneider**:
- 优势: EcoStruxure软件生态、端到端DC解决方案、欧股估值相对美股更理性、全球渠道最广
- 风险: 欧股流动性、外汇波动(欧元)、DC纯度不如Vertiv

**HVDC对传统UPS的"颠覆"风险**:
- UPS仍在增长(7.3% CAGR)，不会一夜消失
- HVDC主要针对新建AI工厂；传统+colo DC仍以UPS为主
- UPS厂商(Vertiv/Eaton/Schneider)同时在布局HVDC—属于产品线扩展而非被颠覆
- 真正的风险: HVDC供应链可能引入新竞争者(Delta/台达等电源专家)

## 5. Key Events & Catalysts

- 2026年3月: Eaton完成Boyd Thermal $9.5B收购
- 2026年: Vertiv推出800V HVDC产品线
- 2026 Q1: Meta ±400V方案落地
- 2026 H2: NVIDIA Rubin平台ramp (180-220kW racks)
- 2027: Rubin Ultra NVL576 (3.6kW TDP, 目标1MW/rack)
- Hyperscaler capex: 2026年云计算巨头DC投资>$600B

## 6. Gaps (未校准/需补)

- 缺少Eaton/Schneider/Vertiv具体DC收入占比拆解（多元业务掩盖pure-play exposure）
- 中国本土玩家(科华/科士达/英维克)的营收规模、增速、技术差异缺乏定量数据
- HVDC对UPS的替代速度缺乏权威预测
- 三巨头的具体估值对比(PE/EV/EBITDA)和华尔街目标价需补
- 液冷各技术路线(冷板vs浸没vs两相)的市场份额和增速差异
- 缺少卖方研报(大摩/高盛/UBS对Vertiv/Eaton的评级和目标价)