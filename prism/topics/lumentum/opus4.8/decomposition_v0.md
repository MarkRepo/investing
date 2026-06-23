---
slug: lumentum
variant: opus4.8
version: 0
written_at: 2026-06-23
convergence_status: open
---

# decomposition_v0 — Lumentum Holdings (LITE)

> 薄知识冷启动拆解（thesis_v0 + K# + baseline §六 prescan 校准）。v0 不做 LLM critic，
> 只标置信度 tag（收料对冲用）+ 机械自检。深度版 v1 留给 I6 厚料 delta 重拆。
> **核心语境**：重估已发生，命门全部关于"重估能否被基本面维持"，而非"会不会重估"。

## 一、命门 1-3（最决定 thesis 成败的特化问题）

- **命门 1 — EML 稀缺定价的耐久性（Coherent 6 寸 InP 威胁）**（置信度：**中 / 偏低**）
  整个重估的财务地基是 ~48% 毛利率 + 定价权，而它由 EML 供给缺口（~25-30%）驱动。**Lumentum 3 寸 InP vs Coherent 6 寸 InP（4x dies/wafer + 更低成本）的良率赛跑**决定稀缺何时终结。Coherent 同获 NVIDIA $2B、自称 100G/200G EML 领导者——这不是水涨船高的小竞品，是体量更大、成本结构可能更优的正面对手。若 Coherent 良率追平，scarcity premium 蒸发 → 毛利/ASP/估值三杀。→ 覆盖 K1、K2。
  **薄拆解风险**：Coherent 6 寸良率/成本是 half_public/hard，需卖方深度 + OFC 技术披露 + 三方（LightCounting/Yole）份额拆分。**最高优先级砸料。**

- **命门 2 — 估值隐含预期 vs 可兑现的增长/毛利**（置信度：**中**）
  ~$900、forward PE 50x、PS 27x。当前价已计入 FY27 ~$4.8-5.7B 营收 + 高毛利 + OCS/CPO 全兑现。命门是：**反推隐含的 normalized 盈利能力有多高，下行情景（增长降速+毛利回落）的公允价垫有多厚**（bear narrative $433 vs 现价隐含 -54%）。若稀缺定价是峰值而非新常态，则戴维斯双杀；若三引擎叠加使增长"高位钝化"，则 4.5/10 可上调。→ 覆盖 K2、K4。
  **薄拆解风险**：需 Reverse PE-DCF + 多年财务弧线 + 一致预期模型（consensus 是 hard 料）+ mid-cycle normalized EPS 估算。

- **命门 3 — 增长引擎兑现节奏（OCS/CPO 期权 vs NVIDIA/客户集中）**（置信度：**低 / uncertain**）
  股价计入了 OCS（CY27 $1B）+ CPO（H2 CY26 拐点）两个尚未规模兑现的引擎，且需求高度集中在 NVIDIA + 2-3 家 hyperscaler。命门是：**这些引擎是真实增量还是已被过度计价的期权；客户集中 + 不对称议价是否在产能释放后压制毛利**。NVIDIA $2B 双供应商（同投 Coherent）本身暗示 NVIDIA 不想给任一方定价权。→ 覆盖 K3、K5。
  **薄拆解风险**：OCS/CPO 多为 guidance+backlog，需逐季跟踪兑现；客户占比、NVIDIA 承诺条款 half_public/hard。

## 二、每环 B 靶点（A 合同地板之上的命门特化补充）

- **环① 生意/护城河/财务**：① Components(EML/激光) vs Systems(收发器/OCS) 的毛利分层与占比迁移（命门1/2）；② 多年财务弧线含 **FY22-25 周期下行的营收/毛利/FCF 回撤幅度**（命门2 normalized 锚——Lumentum 曾连续多季 GAAP 巨亏）；③ 自有 InP 晶圆/外延的垂直整合壁垒 vs Coherent 6 寸（命门1）。
- **环② 估值**：① Reverse PE-DCF 反推 ~$900 隐含 FY27-29 营收 CAGR + 终值倍数（命门2）；② EV/Sales + forward PE vs peer（Coherent/Innolight/Eoptolink/Ciena）水位（命门2）；③ 基本盘(EML)+期权(OCS/CPO)拆解，看市场给期权的定价 vs 独立 NPV（命门3）。
- **环③ WWHTBT**：列出"维持 4.5/10 谨慎"必须为真（Coherent 追平/毛利见顶/估值压缩）vs "上调看多"必须为真（稀缺延续+三引擎兑现+AI capex 续）的分界条件（绑命门1/3）。
- **环④ 多空/期望收益**：上行（稀缺延续+引擎兑现）× 下行（Coherent 追平+毛利回落+多重压缩）× 中性三情景概率加权；下行情景必须用 bear narrative($433) + 历史回撤校准（命门1/2）。
- **环⑤ 历史镜鉴**：光通信/光器件历史泡沫与崩塌剧本——① JDSU/dot-com 光通信泡沫（2000 顶→崩 99%，本体即 Lumentum 前身）② Lumentum/II-VI 自身 2021-2024 telecom+3D 下行（营收 $17.7→$13.6 亿、连续巨亏）③ 内存超级周期类比（稀缺定价→产能洪水）。本轮哪里相同/不同（命门1 产能拐点）。
- **环⑥ 行动/决策 kit**：明确"现价不追、回撤到 X 估值/价格档（如 forward PE <30x 或 bear 公允价附近）买入"的可执行触发器 + position_tier（黑箱高估→试探档）。

## 三、primer 入门目标 v0（门外人为投资读完应能做到的能力，种子非定稿）

1. 能解释光通信价值链：芯片(EML/CW/VCSEL)→模块(收发器)→系统(交换/传输)，Lumentum 卡在哪一环（高）
2. 能说明 **EML 是什么、为何是 800G/1.6T 收发器的核心瓶颈**、200G/lane 的意义（中，依赖 `[mat-5e2bd1]`）
3. 能区分 Lumentum 三身份变迁：JDSU 分拆的周期光器件商 → telecom+3D 感测 → AI 光学龙头（高）
4. 能说明 **InP 晶圆尺寸（3→4→6 寸）与良率为何决定成本/稀缺/定价权**（中，命门1 核心）
5. 能解释为什么 Lumentum 毛利率从 ~16% 跳到 ~48%、稀缺定价机制（中，依赖 `[mat-0d19cf]`）
6. 能识别四大增长引擎（EML / Cloud 收发器 / OCS / CPO）各是什么、处什么阶段（中）
7. 能说明 **NVIDIA $2B 入股的结构与意义**（优先股/采购承诺/双供应商），为何是双刃（中，依赖 `[mat-95ad42]`）
8. 能列出竞争格局：Coherent（头号）、日系 EML、中国模块厂（旭创/新易盛）、SiPho 替代各自位置（中）
9. 能说明 Lumentum **财年特殊性**（FY 截 6 月底）、Components vs Systems 分部该盯哪些指标（高）
10. 能解释 AI 光学股估值为何用 PS/EV-Sales/forward PE、~50x forward PE 计入了什么（中）
11. 能列出会改变 Lumentum 投资逻辑的 3-5 个可观测拐点信号（绑 K1-K5，尤其 Coherent 6 寸良率）（中）
12. 能说明 CPO/OCS 这类"路线之争"对可插拔光模块价值链的中长期重构（中）

> v0 粗清单；厚料浮现后由 I6 primer Step 1 精修。标"中/缺口"的 → 提示 I4 收对应背景料。

## 四、机械自检

- **K# → 命门覆盖**：K1→命门1 ✓；K2→命门1+2 ✓；K3→命门3 ✓；K4→命门2 ✓；K5→命门3 ✓。**5/5 全覆盖**。
- **A 合同必收类目（8 项，3 hard）是否排了收料优先级**：
  - `biz-moat-unit-econ` / `financial-arc` / `valuation-anchor` / `valuation-percentile` / `bull-bear` → roadmap L4 P0/P1 排（IR 财报/卖方/估值数据/Coherent 对比）。
  - **三项 hard**：`mgmt-capital-alloc`（Hurlston 资本配置 + NVIDIA 优先股结构 + 内部人减持）、`consensus`（一致预期/目标价模型，已部分由 prescan 拿到 PT $1,113）、`historical-mirror`（JDSU dot-com 崩塌 + LITE 自身 2022-24 下行）→ roadmap 显式留位（P1）。
- **命门置信度分布**：中偏低/中/低 各 1。**命门1（Coherent 6 寸 InP，置信度最低且承重最高）已标"最高优先级砸料"**，命门2（估值/normalized）次优先。均进 B 靶点优先收料 ✓。
- **primer 入门目标 → 背景料**：目标 2/4/5/7 标缺口已绑对应料源（EML 机制/InP 晶圆/毛利/NVIDIA）；其余训练知识可覆盖或由 IR/卖方料带出 ✓。
