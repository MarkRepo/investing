---
slug: global-quantum-computing
output_key: 04_implied_expectations
version: 1
generated: 2026-05-23T00:00:00+08:00
data_freshness: 2026-Q1
data_freshness_basis: findings_mat-902c40 (IonQ Q1 2026 10-Q) + findings_mat-2e82b4 (D-Wave Q1 2026) + findings_external_quantinuum_atom (Quantinuum IPO 2026 路演)
---

# 隐含预期与观点光谱（Industry 分支）

> 生成于 2026-05-23，训练知识占比约 50%（估值框架训练，当前数据资料）
> 这是 8 份产出中对投资决策最直接有用的一份

## I1. 行业估值数据提取

**美股纯硬件四傻（IONQ/RGTI/QBTS/QUBT）合计**（截至 2026-05-22 收盘）：

| 标的 | 股价/市值 | TTM 营收 | Trailing PS | Q1 2026 Ann. PS | 卖方 NTM PS | Q1 2026 收入 YoY |
|---|---|---|---|---|---|---|
| IONQ | ~$45 / ~$11B | $43M | **~256×** | **~960× (Q1 ann.)** | ~400× | -28% (估算) |
| RGTI | ~$15 / ~$4B | ~$11M | ~363× | ~250× | ~150× | -5% |
| QBTS | ~$10 / ~$3B | ~$9M | ~333× | -81% (实际下降) | ~200× | **-81%** |
| QUBT | ~$25 / ~$3B | ~$0.5M | ~6,000× | n/a | n/a | n/a |
| **合计市值/收入** | **~$21B / ~$64M** | | **平均 ~330×** | | **NTM 平均 ~250-400×** | **加权 -25 ~ -40%** |

**对比**：
- 2021 SPAC 顶 IONQ PS 峰值 ~180× → **当前 trailing PS 高于 2021 顶部 1.4-5×**
- 全球纯硬件半导体 SaaS（Snowflake/MongoDB 等）2021 估值顶 PS ~50-80× → **量子四傻是其 4-12×**
- 历史正常 PS 范围（成熟硬件 +30% YoY 增速）：5-15×

**私募对比**：
- Quantinuum IPO 路演 target $20B / 估 FY2025 营收 ~$50M = **400×** PS
- PsiQuantum 上轮估值 $7B / 营收估 <$10M = **>700×** PS

## I2. 反推行业隐含预期

**核心问题：当前行业估值假设了什么必须为真？**

取美股纯硬件四傻合计 $21B 市值 / 当前 $64M TTM 营收 = trailing PS ~330×

**情景 A（叙事正确）**：3 年 CAGR 100%/年（量子优势叙事兑现），3 年后营收 = $64M × 8 = $512M；按成熟硬件 PS 10×，3 年后市值 = $5.1B。
→ 三年回报 = $5.1B / $21B - 1 = **-76%（即使叙事 100% 兑现）**

**情景 B（要"赚钱"）**：3 年后维持当前 PS 330×。三年后需要的营收增速 = max(100%, X)
→ 若 PS 维持 330×，则当前已是 fair value。当前 PS 假设 = "PS 永远 330×" → 历史所有硬件 SaaS 顶部估值都不能持续 → 这条本身就是不可能假设

**情景 C（卖方 NTM 一致）**：4 家合计 NTM 估营收 ~$150M（卖方一致预期 ~2× ~3× 增速），NTM PS = 21B/150M = 140×；按 NTM 10× 公允 PS → 公允市值 $1.5B
→ NTM 一年潜在跌幅 = **-93%**（极端）；按 NTM 30× 公允 PS → 公允市值 $4.5B → **-78%**

**反推结论**：

```
当前行业整体 trailing PS = 330×（远高于 2021 顶 180×）
隐含 3 年营收 CAGR ≥ 100%/年（按 NTM PS 30× 公允 + 当前不变情景反推）
历史均值（同类硬科技导入期）：30-50%
市场似乎在假设：未来 3 年是「叙事完美 + 收入跟得上 + 估值不收缩」三连击
这个假设属于：**极度乐观（顶部叙事溢价）**
```

**正向 K# 校验**：
- K1（2027 前经济价值量子优势）：当前估值假设 K1 命中概率 ≥ 50%，但 K1 实际命中概率 ~15-25%（v1 校准）→ **估值多算了 25-35 个百分点的概率**
- K2（2028 前 ≥100 LQ + ≤10^-9）：估值未直接定价 K2，但 K2 是 K1 必要条件 → K2 概率 ≤15% 进一步证伪 K1
- K5（2026 H1 末美股四傻 -50%）：这是当前论文研究的"反向命题"，命中即正确

## I3. 行业观点光谱（5 级）

### Super-bull（超级乐观）— 概率 5%

- **核心逻辑**：IBM 2026 Q4 拿出 advantage demo 真实经济价值 + Quantinuum IPO 顺利定价 $25B+ + 中美科技协同 + 美联储降息
- **关键假设**：
  1. 2026 Q4 IBM 兑现 advantage 承诺
  2. Quantinuum IPO 路演成功 ≥ $25B
  3. 2027 ≥ 3 家化学/材料公司公开经济价值 ROI 案例
- **如果正确，潜在回报**：sector **+50-80%**（IONQ → $60-80）
- **概率估计**：**5%**

### Bull（乐观）— 概率 15%

- **核心逻辑**：通用优势叙事 A 延续，至少 1 个商业 PoC 落地，IPO/IPO 后估值稳定
- **关键假设**：
  1. IBM advantage demo 部分兑现（不必达完美）
  2. Quantinuum IPO 顺利 ≥ $18B
  3. lock-up 解禁不引发踩踏
- **潜在回报**：sector **+20-30%**（IONQ → $55）
- **概率估计**：**15%**

### Base（中性 / 基准）— 概率 30%

- **核心逻辑**：叙事降温但不崩塌，估值缓慢消化
- **关键假设**：
  1. IBM advantage demo 跳票但未否定路线
  2. Quantinuum IPO 估值 $15-18B
  3. lock-up 解禁后内部人轻度减持
- **潜在回报**：sector **-20 ~ -30%**（IONQ → $30）
- **概率估计**：**30%**

### Bear（悲观）— 概率 35%

- **核心逻辑**：H2 2026 catalyst 真空 + lock-up 解禁踩踏 + 至少 1 家 SPAC 财务危机
- **关键假设**：
  1. IBM advantage demo 跳票
  2. IonQ/Rigetti lock-up 后内部人抛售 ≥ 30% holdings
  3. Quantinuum IPO 定价 $12-15B 或推迟
- **潜在下跌**：sector **-50 ~ -65%**（IONQ → $15-20）
- **概率估计**：**35%**（最可能情景）

### Super-bear（超级悲观）— 概率 15%

- **核心逻辑**：宏观/地缘冲击 + 多家融资失败 + Aaronson 或 Preskill 公开质疑 → 叙事完全崩塌
- **关键假设**：
  1. 美联储再加息 + ITAR 收紧
  2. 至少 1 家美股四傻被强制 reverse split / 退市预警
  3. Nature 撤稿 Microsoft Majorana 论文
- **尾部风险幅度**：sector **-70 ~ -90%**（IONQ → $5-10，QBTS → 0-2）
- **概率估计**：**15%**

---

**期望值估算**：
- E[return] = 0.05×60% + 0.15×25% + 0.30×(-25%) + 0.35×(-58%) + 0.15×(-80%) ≈ **-31%**

**反 EV 验证**：即使把 super-bull/bull 概率上调到 25%/25%（即对叙事 A 极度乐观），EV 仍为 **+2%** — 也就是说，**只有在"叙事 A 必然兑现"假设下，sector 才大致 fair value，否则负 EV**。

## I4. 关键分歧点

**多空双方最核心的一个分歧**：**通用量子优势 2027 是否兑现**（K1）

| 方向 | 立场 | 核心论据 |
|---|---|---|
| 多方 | K1 命中概率 ≥ 50% | Willow Lambda=2.14 已跨阈、Q-CTRL 3000× Fermi-Hubbard、IBM Krishna 2026 承诺、Quantinuum 48-94 LQ |
| 空方 | K1 命中概率 ≤ 20% | Google 自承 Stage 3 未达、advantage 全部是 benchmark 非商业、所有 SPAC 标的 10-K Risk Factors 明文"may never occur"、D-Wave Q1 收入 -81% 反向证据 |

**解决分歧需要的信息**：
- **决定性节点**：**2026 Q4 IBM Nighthawk advantage demo** 是否真实兑现（含独立学术验证 + 商业客户付费）
- 次要节点：2027 H1 Quantinuum lock-up 解禁后 RIKEN 7% 客户集中度是否被市场重新定价

**我的当前判断**（信心度 7/10）：
- 看空美股四傻 2026-2027 估值（K5 命中概率 65-75%）
- 看空 Microsoft 拓扑路线（Nature editorial note 已是硬证据，市场未充分定价）
- 看空 Quantinuum 高估 IPO（RIKEN 客户集中度 = 第二个 D-Wave QCaaS 故事）
- 中性 IBM/Google（资产负债表雄厚，advantage 跳票也不会破产）
- 中性偏多 IBM 作为 super-bull 情景对冲（5% 仓位）

## 估值矩阵汇总（Industry 简化版）

> Industry 层不做单个公司估值模型，但给出 sector 级公允估值的多模型对比。

| 模型 | 核心假设 | Bull 公允 PS | Base 公允 PS | Bear 公允 PS |
|---|---|---|---|---|
| 历史 SaaS 顶部类比 | 比同期硬件 SaaS 顶 80× | 80× | 50× | 20× |
| 同类导入期硬科技 | 5 年内首批 ROI 兑现 | 50× | 25× | 10× |
| Aaronson 派"研发服务公司"估值 | 量子永远 10 年后 | 15× | 8× | 3× |

**当前 sector trailing PS**：~330× | **NTM PS**：~250-400×

**模型间主要分歧**：来自"量子优势何时兑现"的核心假设——SaaS 顶部类比也只能支撑 80× 上限，而当前 330× 即使按最乐观模型也已 **4× 高估**。

## 信息来源

- 训练知识（约 50%）—— PS/DCF 反推框架、SaaS/SPAC 顶部估值类比、Kelly 期望值框架
- findings_mat-fa4949 (IonQ 10-K FY2024)：$43M TTM 营收基准
- findings_mat-902c40 (IonQ Q1 2026 10-Q)：Q1 营收 + Y/Y 降速
- findings_mat-2e82b4 (D-Wave Q1 2026 10-Q)：QCaaS -81% 反向证据
- findings_mat-d83292 (Rigetti 10-K)：政府订单依赖度
- findings_mat-71e318 (QUBT 10-K)：$0.5M 极小收入基数
- findings_external_quantinuum_atom：Quantinuum IPO target $20B / 估营收 ~$50M
- findings_external_ibm：Q-CTRL 3000× demo + Krishna 2026 承诺
- findings_external_google：Stage 3 未达 + Quantum Echoes 不是商业 ROI
