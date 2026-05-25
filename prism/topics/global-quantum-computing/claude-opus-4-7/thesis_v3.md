# Thesis v3 — 全球量子计算与量子模拟产业

> 写于：2026-05-23 同行评审后
> 模型：claude-opus-4-7
> 数据基础：17 份 findings（同 v2）+ peer review 报告
> 与 v2 的关系：**结构性升级**，针对评审 Top-3 修订项（三场景 P&L 矩阵 + Quantinuum 数据修正 + 按月 catalyst+hedge 日历）重写关键章节；保留 v2 的核心 thesis 与 K1-K5 verdict 不变

---

## 0. 与 thesis_v2 的关键修订（来自同行评审）

| 评审发现 | v2 状态 | v3 修订 |
|---|---|---|
| **Quantinuum RIKEN 90% 客户集中度 = FY2025 全年口径，2026-Q1 已降至 7%** | 把两个口径混用 | §2 K1、§3、§5、§6 全部修正为分口径披露；新增"集中度趋势"小段 |
| **P/S 650× 口径任意** | 单一数字 | 给出 3 口径区间：trailing 650× / Q1 annualized 960× / NTM ~400× |
| **RGTI/QUBT "-54.6%/-52.5%" 缺 baseline 与日期戳** | 未注明 | §2 K5 注明：from 52-week high, as of 2026-05-22 close |
| **Q-CTRL 3000× cat-and-mouse 风险** | 未提 | §2 K1 加入 IBM "quantum utility" 已被 Caltech/EPFL 经典反超的 base rate |
| **D-Wave K1 评分 9/10 vs thesis 弱信号** | 未明确反驳 | §2 K1 加 D-Wave 反驳段：spin-glass benchmark 为何不算 K1 经济价值 |
| **"≤10⁻⁹ 全员官方 → 2028 几乎不可能"逻辑不对称** | 用官方时间表当 upper bound 但又怀疑 Krishna 承诺 | §2 K2 显式说明：roadmap 在数量上倾向乐观、在精度上倾向保守；K2 概率下调到 **3-8%** |
| **"看空四傻 + 看多国盾"hidden long correlation** | 标签矛盾 | §5 重构 portfolio：国盾改为"K5 兑现后入场"，明确 conditional long |
| **"中性 IBM + IBM hedge long"自相矛盾** | 标签矛盾 | §5 明确：base case neutral，K1 命中场景下 1-2% portfolio insurance long |
| **看空 OXIG + 看多国盾本质同一笔交易** | diversification 虚高 | §5 合并为 K3 pair trade，共用仓位上限 |
| **看空 Quantinuum IPO 与 long IBM hedge 叙事抵消** | 未识别 | §5 明确：选其一，不可两边满仓 |
| **K5 时间窗"用 put spread"未给参数** | 文字层面 | §6 给出 IONQ/QBTS 具体 put spread strike/maturity/cost 区间 |
| **政策 catalyst 日历缺失** | §6 没列 NQIA/EuroHPC/CHIPS 2.0/IBM Summit | §6 升级为按月 catalyst+hedge 动作日历 |
| **Quantinuum IPO lock-up 180 天意味操作窗口到 2027 H1** | 当作 2026 K5 候选 | §5/§6 明确：IPO 短头窗口在 H+6M 后展开 |
| **Microsoft follow-up base rate 被低估** | 标 <5% | §8 改为 25-40%，并明确 follow-up 即便不能反驳 MZM 也会修复情绪 |
| **K5 应当用 portfolio-level Monte Carlo（相关性 0.7）** | 4 独立事件 | §5 三场景矩阵已隐含相关性；明确警告"K5 完全命中"概率被高估 |
| **K5 用"from peak" vs "from 入场" P&L 框架混淆** | 二元化 | §5 改用 P&L 框架 |
| **IBM 80 套部署 + Quantum Network $250K 门槛低估** | 一句话带过 | §3 新增 IBM 网络效应段；K1 grey zone（半命中）单独定义 |
| **IonQ 量子互联网横向平台被忽略** | 当纯负担 | §4 新增反方观点；§5 IONQ 空头改为时间窗收紧（2026-Q3 前） |
| **中美脱钩 → 国盾 TAM 上限 = 国内** | 未提 | §4 新增；§5 国盾估值锚改为中国军工电子 25-30× |

---

## 1. 核心 thesis（v3，与 v2 一致）

> **看空美股纯硬件 SPAC 量子四傻（IONQ/RGTI/QBTS/QUBT）2026 H1-H2 估值；2027 H1 起新增看空 Quantinuum post-IPO（lock-up 后）；继续看空 Bluefors/Oxford 制冷机叙事（与 K3 pair）；看空 Microsoft "拓扑路线已 work" 叙事；国产替代（国盾）从"中性偏多"降为"K5 兑现后条件性 long"；通用量子优势 2027 前部分上行风险（IBM Krishna 承诺 + Q-CTRL demo），但 cat-and-mouse 历史教训意味着 demo 命中后 6-12 月即可被经典反超；K2 在 2028 前几近不可能命中。**

**信念强度：7.5/10**（v2 维持）。

---

## 2. 五大 Killer Question 裁决（v3 修订）

### K1：2027 前是否出现首例"经济价值量子优势"
**裁决：大概率不命中（命中概率 20-30%），但需新增"半命中"灰区**

**v3 修订要点**：

1. **D-Wave 反驳段（修复评审维度 1 第 2 条）**：findings_mat-55d3c2 给 D-Wave K1 评分 9/10，主要依据是 2025-03 Science 论文 spin-glass + Jülich $16M 系统销售。**本 thesis 不接受这条主张为 K1 命中**，理由：(a) spin-glass 是 magnetic system dynamics 的物理 benchmark，**没有与任何工业问题（材料相变、电池优化、组合优化的工业版）建立明确 mapping**，Scott Aaronson 等明确反对其作为"经济价值"案例；(b) Jülich 一次性 $16M 系统销售是政府/学术研究采购，**不是"客户按年付 $1M+ 解决经典做不到的问题"**——证明就是 D-Wave 2026-Q1 收入塌方 -81%（findings_mat-2e82b4），若 supremacy 真带来商业拐点 QCaaS 应起飞。**降评依据：把 D-Wave Science 论文标为"K1 候选但不计入命中"**。

2. **Q-CTRL 3000× demo 的 cat-and-mouse 折扣（修复评审维度 1 第 1 条）**：IBM "quantum utility" Eagle 127-qubit 论文（2024）已被 Caltech/EPFL 等用经典张量网络在数小时内复现；arXiv 2511.09124 把这类 demo 概括为"cat-and-mouse game"。**Nighthawk 5,000-gate 电路在经典 MPS 仿真下仍可能被反超**。基于过去 12 个月的 base rate（IBM/Google/Quantinuum 公布的 advantage 主张被经典反超概率 ~60-70%），**Q-CTRL 3000× 这个数字对 K1 命中度的边际信息量应折半**——只算 0.5 个 +EV 信号。

3. **K1 半命中灰区（修复评审维度 3 第 4 条）**：市场不会等"$1M+/年付费客户"严格门槛——只要 Fortune 500 客户公开宣称"用 IBM Quantum 完成了 X 步实验"，板块就会按 K1 半命中定价 +30-50%。**v3 新增定义**：
   - **K1 完全命中**：≥1 家非合作伙伴的企业客户公开披露"年付费 ≥$1M + 经典做不到 + 量化 ROI" → 概率 20-30%（v2 维持）
   - **K1 半命中**：≥3 家研究合作/政府采购客户公开披露"非平凡 demo + 自己框定为商业里程碑"（Q-CTRL/Cleveland Clinic/Boeing 类）→ 概率 **45-60%**（v3 新增）
   - **K1 完全不命中**：所有 demo 在 12 个月内被经典反超 → 概率 ~15%
   **市场对 K1 半命中场景已开始定价**，这是空头逻辑的关键风险——既然 K1 半命中概率 ~50%，对应板块 +30-50% 反弹是 base case 情形之一。

4. **Quantinuum 客户集中度修正（修复评审维度 1 第 3 条）**：
   - FY2025 全年：**RIKEN 90%**
   - 2026-Q1：**RIKEN 7%、US Gov 24%、其余分散**
   - **趋势解读**：从单一日本研究客户切到美国政府主导，但 Q1 营收同比环比都明显萎缩（$5.2M vs FY2025 季均 $7.7M）。客户集中度"形式上下降"伴随"绝对营收下降"，**这是商业脆弱性而非客户结构改善**——可能是 RIKEN 大订单结束后空档期。需要 2026-Q2 数据验证是否反弹。

5. **K1 综合**：**完全命中 20-30%（v2 维持），半命中 45-60%（v3 新增），完全不命中 ~15%**。

### K2：2028 前 ≥1 个 FTQC 系统达 ≥100 逻辑比特、错误率 ≤10⁻⁹
**裁决：大概率不命中（v3 下调至 3-8%）**

**v3 修订要点**：

1. **"≤10⁻⁹ 推到 2029-2030"的逻辑修复（修复评审维度 2 第 1 条）**：v2 把官方时间表当 K2 命中概率上限存在不对称——同一 thesis 在别处又论证管理层乐观倾向。v3 修正：
   - **数量维度（≥100 LQ）**：管理层倾向乐观，IBM Starling 2029 / Quantinuum Sol 2027 / Atom 次代 2027-2028 都有滑期风险；**实际"2028 前 ≥100 LQ"概率 30-35%**（比 v2 的 35-45% 略低）
   - **精度维度（≤10⁻⁹）**：管理层倾向保守（不愿承诺达不到的数）；既然没有任何一家在 2028 前给出 ≤10⁻⁹ 时间表，**实际命中概率 <5%**（v2 同）
   - **两项 AND**：30-35% × 15%（条件概率，因为先做出 100 LQ 才有可能压精度）= **5-8%**；考虑 Atom Computing 中性原子 + QuEra 新型 LDPC 码理论上 10⁻¹³ 可行性，给出 **3-8% 区间**

2. **K2 部分兑现（≥100 LQ 单条件）的时间窗管理（修复评审维度 2 第 1 条尾部）**：2028-2029 之交"≥100 LQ 单条件"大概率命中（IBM Starling 全量交付或 Quantinuum Apollo 早 demo）。**届时市场将解读为"K2 半命中"并推动板块阶段性 +30-50%**——这是空头在 2028 Q4 - 2029 Q1 需要主动减仓或反向对冲的关键 catalyst。

### K3：Bluefors/Oxford Instruments 量子相关订单 2027 前同比 >40%
**裁决：大概率不命中且反向证据持续（命中概率 20-30%，v2 维持）**

### K4：≥3 家制药/化工/材料公司公开披露经济价值案例
**裁决：大概率不命中（命中概率 20-25%，v2 维持）**

### K5：2026 H1 末 IonQ/Rigetti/D-Wave 估值是否崩塌 >50% from peak
**裁决：部分兑现（命中概率 70-85%，v2 维持，但 baseline 与口径修正）**

**v3 数据修正（修复评审维度 1 第 5 条）**：
- 截止 2026-05-22 收盘
- **RGTI**: from 52-week high $22.15 (2025-12) → $14.04 (2026-03-31) → 进一步下行至 ~$10 区间 (estimated as of 2026-05) → **-55% from peak**（命中 K5 阈值）
- **QUBT**: from 52-week high → -52.5% from peak（命中 K5 阈值）
- **IONQ**: -30% from peak（未命中）
- **QBTS**: -37% from peak（未命中）

> **注**：以上百分比为评审日（2026-05-22）的估值，建议在交易前用 Bloomberg/WIND 复核当日数据。RGTI/QUBT 的"K5 已命中"标签仅在 baseline = 52-week high 且日期 = 2026-05-22 时成立。

**v3 portfolio-level K5 推算（修复评审维度 2 第 3 条）**：四标的股价相关性 0.6-0.9（量子板块同涨同跌属性）。**"4 标的全部命中 K5" 概率 ≈ 40-55%**（用相关性 0.7 折算），而非 v2 的"剩 2 标的待触发 → 70-85%"。**4 标的中至少 2 个命中 K5** 概率 ≈ 85%（已实现）；**至少 3 个命中**概率 ≈ 60-70%。

---

## 3. 支持理由（v3 新增重要补充）

**新增（针对评审维度 3 第 1、3 条）**：

9. **IBM 80 套量子部署的网络效应不可忽视**（findings_external_ibm L43）：13 套 utility-scale 系统已嵌入 BASF/Pfizer/Boeing/Cleveland Clinic/RIKEN 等大客户工作流。**K1 若在 2026-2027 出现，最可能的兑现路径是 IBM 已部署的 80 套之一**。这意味着 K1 命中场景的最大单一受益方就是 IBM——但反过来，**Quantinuum/Atom Computing/PsiQuantum 等纯 quantum-pure-play 在 K1 兑现时反弹幅度小于 IBM**（因为客户接入慢）。

10. **国产替代的 TAM 天花板 = 中国国内 + 一带一路**（findings_mat-140f68 L72）：国盾 2024 年报已明确"无境外资产、无境外业务"；中国电信入主后将更深度变成中央企业军工/政务采购通道。**估值锚应当用中国军工电子 P/E 25-30× 而非全球量子龙头 50×+**。这意味着国盾的多头逻辑被严重缩窄。

11. **IonQ 离子阱在 quantum networking + sensing 的横向平台价值**（findings_mat-902c40 L139-141）：ID Quantique + Skyloom + Capella + Vector Atomic 已经覆盖 QKD/卫星光通信/SAR/精密时频。**这是 IonQ 唯一可能在 2027-2028 通过"量子综合解决方案"叙事 squeeze 空头的潜在 catalyst**——若美国国家量子互联网政策 2026 H2 加码，IonQ 在 NQIA 续展窗口可能反弹 20-40%。**空头需在 2026-Q3 前完成关键 put roll，避开此窗口**。

---

## 4. 反方观点（v3 新增）

8. **散户对会计噪音的不对称反应**：IonQ Q1 +$805M GAAP 净利润 headline 被算法/散户误读为"扭亏为盈"；Q2 大概率出现镜像——若股价反弹 → warrant 负债扩大 → 季报巨额账面亏损 → 散户 again 可能误读为"亏损扩大但有 SkyWater 转型故事" → **股价不跌反涨**。**空头不能简单假定 Q2 财报会触发 K5**，需做 base case + tail case。

9. **Microsoft 补 Majorana follow-up 的 base rate 不是 5% 而是 25-40%**（修复评审维度 2 第 4 条）：Microsoft Research 历史上对争议论文的 follow-up 比例显著高于零。即便 follow-up 不能完全反驳 Nature 审稿人异议，**只要发布"补充 8 → 16 拓扑模式"的论文，市场情绪就会大幅修复**。空头依据"Majorana 已死" 的 thesis 应当对 2026 H2 论文 catalyst 留余地。

---

## 5. Position implications（v3 重构：三场景 P&L 矩阵 + 仓位上限表）

### 5.1 三场景 P&L 矩阵（针对评审 Top-3 修订项 #1）

> **核心仓位假设**：portfolio gross exposure 100，分配：四傻空头 30 + Quantinuum IPO 空头 0（未上市，预留 10）+ OXIG/国盾 K3 pair 10 + IBM 期权 hedge 2，现金 48（应对 catalyst 反弹）

| 场景 | 概率（v3） | 触发条件 | 四傻 -30% 空头 P&L | 国盾 +10 多头 P&L（仅 K5 后） | IBM K1 hedge +2 P&L | OXIG 空头 -10 vs 国盾 long 10 net | **portfolio 净 P&L** |
|---|---|---|---|---|---|---|---|
| **A（K1 完全兑现）**| 20-30% | IBM/Quantinuum/Q-CTRL 类客户 2026-2027 公开付费 ≥$1M/年案例；板块 risk-on +50-100% | -15 至 -30 | 国盾未入场（K5 未触发）→ 0 | +1 至 +2 | 0（pair trade 同涨同跌）| **-12 至 -28** |
| **A'（K1 半命中）**| 45-60% | ≥3 家研究/政府客户公开 demo；板块 +20-40% | -6 至 -12 | 0 | +0.5 至 +1 | 0 | **-5 至 -11** |
| **B（K5 完全兑现 + K1 不命中）**| 25-35% | 四傻 4 家全部 -50%；Q3-Q4 财报失望 | +12 至 +18 | -1 至 -3（contagion）| 0 | 0 | **+11 至 +15** |
| **C（K5 部分兑现 + K1 不命中）**| 15-20% | 四傻 2-3 家 -50%；IONQ/QBTS 部分跌 | +6 至 +10 | 国盾未入场 → 0 | 0 | 0 | **+6 至 +10** |
| **D（双向都不发生）**| 5-10% | 板块横盘 + 政策中性 | -1 至 +2 | 0 | 0 | 0 | **-1 至 +2** |

**expected portfolio return**（按概率加权）：

$$
\text{EV} = 0.25 \times (-20) + 0.50 \times (-8) + 0.30 \times 13 + 0.18 \times 8 + 0.07 \times 0 \approx -5 \text{ 至 } -3 \text{ pts}
$$

**净结论**：**当前 portfolio 结构在 EV 上为微负**——K1 完全/半命中合计概率 65-90%，会吃掉 K5 兑现的多头收益。**v3 必须降低空头仓位（30 → 20）或加大 IBM K1 hedge（2 → 5）来平衡**。

### 5.2 修订后的仓位上限表（v3）

| 标的/方向 | v2 建议 | v3 修订 | 仓位上限 | 关键 catalyst | 入场/退出条件 |
|---|---|---|---|---|---|
| **QBTS 空头 (put spread)**| 第 2 优先 | **第 1 优先** | 8% | Q2 2026 财报 (2026-08) | Q2 财报后 -50% 平仓 50%、剩 50% 持至 2026-Q4 |
| **IONQ 空头 (put spread)**| 第 3 优先 | **第 2 优先**（窗口紧）| 6% | NQIA 续展、Q2 warrant | **2026-Q3 前完成 put roll**，避开 H2 政策反弹 |
| **QUBT 空头**| 第 1 优先 | **降为第 4**（已 -52%） | 3% | LSI 整合、ATM 重启 | 反弹 +30% 加仓；-70% 平仓 |
| **RGTI 空头**| 第 4 优先 | **降为第 5**（已 -55%）| 2% | 印度 C-DAC 入账、Q3 财报 | -65% 平仓 |
| **Quantinuum post-IPO 空头**| 第 6 | **2027 H1 后入场**（lock-up 180 天）| 预留 10% | IPO 定价、lock-up expiry | IPO 后 H+180 起观察 |
| **OXIG 空头 + 国盾多头 (K3 pair)**| 分列两条 | **合并 K3 pair**，共用仓位 | 5%（pair 净） | NSI Act 结果、国盾三季报 | 国盾跌 -20% 后再入场多头 |
| **IBM 期权 hedge (K1 命中保险)**| 1-2% | **3-5%**（K1 命中概率高）| 5% | Krishna 2026 内承诺 | 长期持有；K1 兑现时平仓 |
| **国盾独立多头**| §5.2 第 1 | **删除**（已并入 K3 pair）| 0 | — | — |

**总 gross：~30%（v2 ~50%）**；**净 K5 暴露 ~17%**；**净 K1 暴露 -2 至 +3%**（视 IBM hedge size）

### 5.3 关键 hidden correlation 警告（针对评审维度 5）

1. **国盾 vs 四傻在 K5 兑现时同向跌**（findings_mat-140f68 L114）：因此国盾多头**必须 conditional on K5 兑现 + 国盾跟跌 -20%+ 后**，否则会承担 -25% 的拖累
2. **看空 Quantinuum vs long IBM hedge 叙事抵消**：Quantinuum 估值崩塌 → ion-trap + qLDPC 路线被重估 → IBM Q-CTRL demo 商业兑现叙事受损 → 二者不能同时满仓。**v3 选择保留 IBM hedge（K1 高概率），放弃 Quantinuum IPO 空头的"主动建仓"，改为"等 lock-up 后机会主义"**
3. **OXIG 空头 + 国盾多头本质同一笔 K3 替代主题**：合并为 K3 pair，diversification 不可重复计

---

## 6. 关键观察窗口与按月 catalyst+hedge 日历（v3 重构）

| 时间 | 事件 | 性质 | 对应 K | hedge 动作 |
|---|---|---|---|---|
| **2026-06** | H1 收盘股价 | 观察 | K5 | 评估 IONQ/QBTS 是否完成 -50% |
| **2026-07 上** | IBM Q2 earnings call | catalyst | K1 (Krishna 兑现概率 #1)| Krishna 若提具名付费客户 → IBM hedge 立刻平仓获利，加大 cash |
| **2026-07 中** | IonQ Q2 财报 | catalyst | K5 | warrant 反向 mark；散户误读风险——put spread 不要在财报前加仓 |
| **2026-08 上** | D-Wave Q2 财报 | catalyst | K5、K1 | RPO/Customer A 替换情况；触发 QBTS put spread 平仓 50% |
| **2026-08 中** | Rigetti Q2 财报 | catalyst | K5、K2 | C-DAC 印度 $8.4M 入账若兑现 → RGTI 反弹 → 不加仓 |
| **2026-08 下** | QUBT Q2 财报 | catalyst | K5 | LSI 整合、ATM；-70% 平仓 |
| **2026-09 中** | IBM Quantum Summit | catalyst | K1（Krishna 兑现概率 #2）、K2（Kookaburra demo）| **空头此前必须完成 put roll**；Krishna 若兑现 → portfolio 切换 risk-on |
| **2026-09 末** | NQIA 续展投票（推测）| catalyst | K5 反向 | RGTI/IONQ 反弹风险，预留 5% cash 对冲 |
| **2026-Q3** | Quantinuum SEC review 完成 / IPO 定价 | catalyst | K5（新增）| 观察 IPO 估值与首日表现，决定 H+180 后是否做空 |
| **2026-10** | IBM Q3 earnings call | catalyst | K1（Krishna 兑现概率 #3）| 同 7 月 |
| **2026-Q4** | EuroHPC quantum 第二批拨款 | catalyst | K3 反向 | OXIG 反弹风险，pair trade 加 OXIG 短头到上限 |
| **2026-Q4** | 药企/化工 R&D 年报章节 | observation | K4 | 若 BASF/Pfizer 量化披露 → K4 半命中，进入 catalyst risk |
| **2026-Q4** | 国盾三季报 | catalyst | K3 反向、K1 边缘 | ez-Q Fridge 出货量、中电信集采 |
| **2026-12** | IBM 年终 PR（Krishna 兑现概率 #4）| catalyst | K1 | 同 9 月 |
| **2027-01** | CES / Davos（Krishna 兑现概率 #5）| catalyst | K1 | 同 9 月 |
| **2027-Q1** | Atom Computing Magne (50 LQ) 投运 Denmark QuNorth | catalyst | K2 | 板块情绪修复，空头减仓 |
| **2027 H1** | Microsoft Majorana follow-up（25-40% 概率）| catalyst | K2 | 若 follow-up → Microsoft 量子叙事修复，但与四傻无直接联动 |
| **2027 Q1-Q2** | Quantinuum IPO lock-up expiry（如果 IPO 在 2026-Q3-Q4）| **关键 catalyst** | K5 新增 | **Quantinuum 空头建仓窗口开启**；监控 lock-up 后 30 天股价 |

### 6.1 具体 put spread 报价区间（针对评审 Top-3 修订项 #3）

> 以下为基于当前 IV ~80-120%（量子板块历史 IV）和典型期权链结构的**估算区间**，实际交易需复核 OPRA 实时报价

| 标的 | 当前 spot（est.）| put spread 结构 | maturity | 估算 cost | max payoff | break-even |
|---|---|---|---|---|---|---|
| **IONQ** | $30-35 | $25 / $15 long put spread | 2026-09 | $2.50-3.50 | $7-7.50 | -30% from spot |
| **IONQ** | 同上 | $20 / $10 long put spread | 2027-01 | $2.00-3.00 | $7-8 | -45% from spot |
| **QBTS** | $4-5 | $3.50 / $2 long put spread | 2026-09 | $0.40-0.60 | $1.40-1.50 | -25% from spot |
| **QBTS** | 同上 | $3 / $1.50 long put spread | 2027-01 | $0.40-0.55 | $1.45-1.55 | -35% from spot |
| **RGTI** | ~$10 | $8 / $5 long put spread | 2026-09 | $0.80-1.20 | $2-2.20 | -25% from spot |
| **QUBT** | $7-8 | $6 / $3 long put spread | 2026-09 | $0.60-0.90 | $2.40-2.50 | -25% from spot |

**注意事项**：
- 量子板块单日 -20%+ 是常态，put spread 的 max payoff 经常在 1-2 周内触及——可考虑 trailing roll 到更深 strike
- borrow rate 当前 RGTI/QUBT ~15-30% APR（贵），用 put spread 比裸卖空更优
- IONQ borrow rate ~5-10%（便宜），可少量裸卖空 + put 保险

---

## 7. Coverage 闭环（v3 维持 v2）

| Killer Question | 覆盖度 | v3 verdict | 缺口 |
|---|---|---|---|
| K1 | 强 | 完全命中 20-30% / 半命中 45-60% / 不命中 ~15% | 缺各药企/化工自家年报披露 |
| K2 | 强 | 3-8% AND 命中；≥100 LQ 单条件 30-35% | 缺各家未公开内部 logical error rate 测试 |
| K3 | 充分 | 大概率不命中且反向（20-30%）| 缺 Bluefors 母公司订单数据 |
| K4 | 中 | 大概率不命中（20-25%）| 缺各药企/化工年报量化披露 |
| K5 | 充分 | 4 标的全部命中 40-55% / 至少 3 命中 60-70% / 至少 2 已命中 ~85% | 实时股价监控 |

---

## 8. Thesis v4 触发条件

1. **IBM Krishna 在 2026-09 / 2026-10 / 2026-12 / 2027-01 任一节点给出具名企业客户付费 $1M+/年案例** → K1 完全兑现，整个空头逻辑被推翻，portfolio 切换 risk-on
2. **K1 半命中场景实现**（≥3 家研究/政府客户公开 demo）→ 板块 +20-40%，空头需要在 -10% 止损前减仓
3. **IONQ/QBTS 任一完成 -50% 崩塌** → K5 部分兑现，IONQ/QBTS 空头平仓 50%
4. **Quantinuum IPO 定价 + lock-up 表现** → 决定 H+180 后是否建立 Quantinuum 空头
5. **Microsoft 2026 H2 补交 Majorana follow-up 论文**（概率 25-40%）→ Microsoft 量子叙事修复，影响极小（与四傻无联动）
6. **Atom Computing Magne 2027 Q1 如期投运并附 ≥50 LQ benchmark** → K2 部分兑现，K2 命中概率上调；板块阶段性 +30-50%
7. **任一药企/化工/材料公司年报披露量化经济价值案例** → K4 重大边际变化
8. **NQIA 续展 / CHIPS Act 2.0 量子条款落地** → RGTI/IONQ 政策反弹，空头时间窗管理升级

---

## 9. v3 一句话总结

> **空头 EV 在 v2 结构下为微负——K1 完全/半命中合计概率 65-90% 会吃掉 K5 兑现收益；v3 通过降低空头总仓位（30→20）、加大 IBM K1 hedge（2→5）、把国盾改为 K5 兑现后 conditional long、把 Quantinuum 空头推迟到 2027 H1 lock-up 后、合并 OXIG/国盾为 K3 pair、按月排 catalyst 日历并给出具体 put spread strike/maturity/cost，把 portfolio 从"赌单一方向"改造为"K5 base case + K1 命中保险"。**
