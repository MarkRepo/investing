# Thesis v0 — global-datacenter-power-equip

> 版本: v0 | 日期: 2026-05-28 | prescan_status: partial | 强度: 8/10

## 一句话结论

**做多 Vertiv (VRT) + Eaton (ETN) 双轨，配 Schneider (SU) 作为防御腿。** AI 数据中心机房内配电+液冷是 AI infra 赛道中"确定性最高的物理瓶颈"——不管谁赢芯片战，机柜功率密度从 10kW → 132kW → 1MW 的结构性升级不可逆，UPS+配电+液冷三件套的增量支出刚性堪比"卖铲子"。

## 核心逻辑链

### K1: 机房功率密度升级是不可逆的结构性趋势（确定性: 高）

- GB200 NVL72 已达 132kW/rack，Blackwell Ultra/Rubin 目标 250-900kW，NVIDIA 2025 OCP 发布 1MW rack 设计
- 传统 enterprise DC 机柜 5-10kW，AI 训练 rack 是 10-50x 的功率跳升
- 功率密度每翻一倍，配电(PDU/busway/switchgear) + 冷却(液冷替代风冷)的每 MW 支出增加 30-60%
- 即使 AI 芯片路线图出现延迟，功率密度长期方向不变（推理需求同样推高密度）

**反方**: 如果 AI capex 泡沫破裂，hyperscaler 订单可能断崖式下跌。但 $15B+ backlog 提供 12-18 个月缓冲垫。

### K2: Vertiv 是赛道最纯的"双引擎"标的（确定性: 高）

- 唯一同时覆盖电源(UPS/PDU/switchgear) + 冷却(液冷CDU/冷板/浸没)的大型供应商
- FY2025 $10.2B 营收(+27.7%), $15B backlog(+109%), 2026 指引 $13.25-13.75B (+27-29%)
- Q4 2025 有机订单增速 252%，book-to-bill ~2.9x → 2026-2027 营收锁定
- 液冷市占率 >11.3% 行业第一，2025 年 Dell'Oro 液冷市场翻倍，Vertiv 是最大受益者
- 2026 年推出 800V HVDC 产品线，与 NVIDIA 深度合作，不会因架构切换被淘汰
- 目标 2029 年 operating margin 25%（当前 23.2%）

**反方**: 53x forward PE，市场已price in高增长。Q4 252%订单增速不可持续（基数效应+前端loaded）。任何指引miss都会重创股价。

### K3: Eaton 是"配电基本盘+液冷期权"组合（确定性: 中-高）

- 电气配电(switchgear/panelboard/busway)是 Eaton 核心地盘——无论风冷还是液冷，数据中心必须用这些设备
- Electrical Americas Q1 2026 backlog +44% to $14.5B, rolling 12-month organic orders +42%
- Boyd Thermal $9.5B 收购(2026年3月完成): $1.5B 液冷营收，一次补齐液冷短板。22.5x EBITDA 偏贵但战略价值合理——Eaton 从配电延伸进液冷，实现"电源+冷却"全覆盖
- 多元业务(Aerospace +44% backlog, Mobility 2027 Q1 分拆)降低 DC 周期风险
- 相对 Vertiv 估值更合理（多元业务压低倍数），DC 加速可能驱动 re-rating

**反方**: Boyd 整合执行风险。$9.5B 对价在利率 4%+ 环境下融资成本高。DC 纯度不如 Vertiv，beta 较低。

### K4: Schneider 是防御腿——软件护城河+欧股估值（确定性: 中）

- EcoStruxure DC 管理软件是差异化的护城河（Vertiv/Eaton 软件弱很多）
- Q1 2026 €9.77B 营收, double-digit 有机增长, DC 需求是主要驱动力
- 端到端能力(从 MV 配电到机柜 PDU 到液冷到 DCIM 软件)
- 欧股上市估值相对美股更理性

**反方**: 欧元汇率波动。DC 纯度不如 Vertiv。非美股投资者可及性差。

## 不在 thesis 里的东西（刻意排除）

- **中国本土玩家(科华/科士达/英维克)**: 国内 AI 算力 boom 有弹性，但技术差距+政策风险+流动性差，不在全球配置的 core thesis 里。可作为"中国 AI infra"独立 topic
- **nVent**: ~30% DC exposure 有吸引力，但规模太小($13B market cap vs Vertiv $68B)，且正在被 Vertiv/Eaton 挤压
- **液冷 specialist (CoolIT/LiquidStack/Asetek)**: 非上市或太小，缺少流动性

## 风险清单

1. **Hyperscaler capex 拐点**: 2027年后如果AI投资回报不如预期，云计算巨头可能削减DC capex → backlog可被cancel/renegotiate
2. **HVDC 颠覆 UPS**: 虽然我认为是演进非革命，但 800V DC 架构如果在 2028+ 成为主流，传统 UPS 需求可能加速下降(Vertiv/Eaton 都在布局所以受益方相同，但过渡期盈利波动)
3. **Vertiv 估值风险**: 53x PE + 252% 订单增速不可持续，guidance miss 会导致双杀(P/E压缩+EPS下调)
4. **Boyd 整合风险**: $9.5B 收购的文化/技术/客户整合，任何delay或synergy不达预期都会拖累 Eaton
5. **地缘政治**: 关税对电气设备供应链的冲击（Eaton/Schneider 全球制造网络复杂）
6. **竞争加剧**: Delta/华为等亚洲厂商在液冷/HVDC领域的技术追赶可能压低利润率

## 推荐配置

| 标的 | 方向 | 核心逻辑 | 仓位建议 | 风险等级 |
|------|------|---------|---------|---------|
| Vertiv (VRT) | 做多 | DC电源+冷却最纯标的，backlog锁定高增长 | 核心仓位 5-8% | 中-高(估值) |
| Eaton (ETN) | 做多 | 配电基本盘+Boyd液冷期权，多元防御 | 核心仓位 5-8% | 中 |
| Schneider (SU) | 做多 | 软件护城河+欧股防御，DC需求弹性 | 卫星仓位 3-5% | 中-低 |

## 待校准事项（prescan partial — 需补资料）

- [ ] 三巨头 DC 收入占比精确拆解(Eaton Electrical Americas 中 DC 占比？Schneider DC 占比？)
- [ ] 卖方目标价与评级汇总(GS/MS/UBS/JPM 对 VRT/ETN/SU 最新 PT)
- [ ] 液冷各技术路线市场份额(冷板 vs 浸没 vs 两相)及增速
- [ ] HVDC vs UPS 替代时间线的权威第三方预测
- [ ] Boyd Thermal 详细财务和客户构成(对 NVIDIA 依赖度？)
- [ ] 中国本土玩家定量对比(营收/利润率/技术路线)
- [ ] Schneider 2025 全年报和 2026 展望详细指引