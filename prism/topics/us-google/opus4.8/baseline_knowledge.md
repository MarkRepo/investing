---
slug: us-google
variant: opus4.8
written_at: 2026-07-23
training_cutoff_estimate: 2026-01
---

# 训练知识 Baseline — Alphabet 谷歌 (GOOGL, NASDAQ)

> 本文记录 LLM 在**训练截止时**对该 topic 的认知现状。
> 后续 web-search / 用户资料的事实校准必须 cite 本文记忆条目。

## 〇、基本信息（company）

- **主代码**：`US_GOOGL`（Class A，有投票权，1 票/股）
- **多市场上市**：同一实体双 class ——
  - `US_GOOG`（Class C，无投票权）——同一家 Alphabet Inc.，两个 class 都在 NASDAQ 交易，GOOG 通常略低价（无投票权），两者流动性都极高
  - Class B（Page/Brin 等创始人持有，10 票/股，不公开交易）——创始人借此保留控制权
  - 研究纪律：估值/市值用两 class 合计股本计（约 122 亿股），EPS 用稀释后合计；引用股价时标 GOOGL 还是 GOOG
- **市场属性**：美股 NASDAQ，9:30-16:00 ET；标普 500 + 纳指 100 权重股；ADR/时差对本标的不适用（本土股）

## 一、关键事实记忆（快变类标 ⚠️）

### 财务（多数快变，thesis 估值锚必校准）
- `[fact-01]` FY2024 总营收约 $350B，同比 +14% → 置信度：高 | time_sensitivity：**快变** ⚠️
- `[fact-02]` FY2024 净利润约 $100B，稀释 EPS 约 $8.0 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-03]` FY2024 Google 广告（Search+YouTube+Network）约 $265B，其中 Search 约 $198B、YouTube 广告约 $36B → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-04]` FY2024 Google Cloud 营收约 $43B，全年经营利润转正约 $6B（2023 首次全年盈利）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-05]` FY2024 资本开支约 $52.5B，2025 指引一度 ~$75B、年中上调（幅度记忆模糊）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-06]` Other Bets（含 Waymo）持续经营亏损，年亏约 $40-45 亿 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-07]` 现金及等价物 + 有价证券约 $95-110B → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-08]` 2024-04 首次派息 $0.20/季，同时批 $70B 回购；2025 股息小幅上调至约 $0.21 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-09]` 市值 2024 年内破 $2T；2025 大概率在 $2.5-3T 区间波动 → 置信度：低 | time_sensitivity：**快变** ⚠️
- `[fact-10]` GOOGL 股价 2024-2025 大致 $150-210 区间；2025-01 DeepSeek 冲击 + 关税恐慌一度回撤，后修复；当前价 uncertain → 置信度：uncertain | time_sensitivity：**快变** ⚠️

### 业务与竞争（慢变/快变混合）
- `[fact-11]` Google 搜索全球份额约 90%，是核心现金牛，广告是主要盈利来源 → 置信度：高 | time_sensitivity：**慢变**
- `[fact-12]` YouTube 是全球最大视频平台，广告 + Premium/订阅双轮 → 置信度：高 | time_sensitivity：**慢变**
- `[fact-13]` Google Cloud 是全球第三大公有云（AWS、Azure 之后），增速约 30%+，AI 工作负载驱动 backlog 上升 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-14]` Android 是全球最大移动 OS，Chrome 是最大桌面/移动浏览器 → 置信度：高 | time_sensitivity：**静态**

### AI 与技术（快变为主）
- `[fact-15]` Gemini 是 Alphabet 的 LLM 家族（1.0 于 2023-12、1.5、2.0 于 2024 末、2.5 于 2025）；对标 OpenAI GPT → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-16]` AI Overviews（原 SGE）2024 起嵌入搜索结果页，是搜索货币化的双刃剑（可能挤压点击/CPC）→ 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-17]` Google DeepMind（2023 Brain 与 DeepMind 合并）由 Demis Hassabis 领导，AlphaFold 等 → 置信度：高 | time_sensitivity：**慢变**
- `[fact-18]` 自研 TPU（v5e/v5p、Trillium/v6，后续 Ironwood）降低对 Nvidia 依赖、支撑云与自用推理 → 置信度：中 | time_sensitivity：**快变** ⚠️

### 反垄断（关键命门，静态案件 + 快变裁决）
- `[fact-19]` DOJ v. Google 搜索案：Judge Mehta 于 2024-08 裁定 Google 在搜索构成非法垄断（liability 成立）→ 置信度：高 | time_sensitivity：**静态**（liability 已成立）
- `[fact-20]` 搜索案 remedy 阶段：DOJ 曾提议剥离 Chrome、终止默认协议（含向 Apple 年付约 $20B）；最终 remedy 裁决记忆约 2025 年内落地，但**具体内容/是否剥离 Chrome 我不确定** → 置信度：uncertain | time_sensitivity：**快变** ⚠️
- `[fact-21]` DOJ 广告技术（ad-tech）案：Judge Brinkema 于 2025-04 裁定 Google 在发布商广告服务器 + 广告交易所构成垄断；remedy 待定 → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-22]` EU 对 Google 有多起反垄断罚款（Android/Shopping/AdSense 历史案）→ 置信度：中 | time_sensitivity：**慢变**

### Waymo（期权价值命门）
- `[fact-23]` Waymo 是自动驾驶 Robotaxi，运营于凤凰城/旧金山/洛杉矶/奥斯汀等，2025 付费单量快速爬坡（周单量记忆约十万级+，具体数字不确定）→ 置信度：低 | time_sensitivity：**快变** ⚠️

### 竞争威胁
- `[fact-24]` OpenAI ChatGPT、Perplexity、微软 Copilot/Bing 构成对通用搜索的 AI 替代威胁——市场核心担忧是"AI 助手分流搜索查询" → 置信度：中 | time_sensitivity：**快变** ⚠️
- `[fact-25]` DeepSeek（2025-01）低成本模型冲击引发 AI 资本开支效率质疑，波及大型科技股估值 → 置信度：中 | time_sensitivity：**静态**（事件已发生）

**第一节统计**：静态 4 条 / 慢变 5 条 / 快变 16 条。快变+高/中置信 = 约 12 条，必须在第五节各有对应 query。

## 二、关键人物 / 公司 / 产品

- **Sundar Pichai**：Alphabet & Google CEO，主导 AI-first 战略与"Code Red"应对 ChatGPT
- **Anat Ashkenazi**：CFO（2024 年接替 Ruth Porat 的 CFO 职；Porat 转任 President & Chief Investment Officer）
- **Larry Page / Sergey Brin**：联合创始人，通过 Class B 保留控制权，近年据报重回 AI 一线参与
- **Demis Hassabis**：Google DeepMind CEO，2024 诺贝尔化学奖（AlphaFold）
- **产品线**：Search、AI Overviews、Gemini（App + API + Workspace 集成）、YouTube、Google Cloud（Vertex AI、BigQuery）、Android、Chrome、Pixel、Waymo、TPU

## 三、产业链 / 竞争格局认知

1. **搜索广告主战场**：Google 全球搜索份额 ~90%，广告是绝对现金牛。护城河 = 默认协议（Apple/三星）+ 用户习惯 + 广告主生态 + 数据飞轮。当前最大结构性威胁是生成式 AI 助手改变信息获取方式（用户在 ChatGPT/Gemini 里问答而非在搜索框点广告链接）。反垄断 remedy 又威胁默认协议这条护城河。

2. **云 + AI 基础设施**：三足鼎立 AWS/Azure/GCP，Google 第三但增速与盈利同步改善，靠自研 TPU + Gemini + Vertex 差异化。AI 训练/推理需求推动 backlog，但也是资本开支暴增来源。

3. **AI 模型军备竞赛**：Gemini vs OpenAI GPT vs Anthropic Claude vs Meta Llama。Google 优势 = 全栈（自研芯片 TPU + 数据 + 分发渠道 Search/Android/Chrome/YouTube/Workspace 数十亿用户）。劣势 = 消费者心智上 ChatGPT 先发。

4. **自动驾驶/其他押注**：Waymo 是 Robotaxi 领跑者（相对特斯拉 FSD、Cruise 已收缩），商业化爬坡中但仍亏损，属长期期权。

5. **监管压顶**：美国两起 DOJ 垄断案（搜索 + ad-tech）均已 liability 成立，remedy 是最大不确定性——极端情形涉及剥离（Chrome/ad-tech 业务）或终止默认协议，直接冲击护城河与盈利结构。

## 四、训练知识盲点（自我承认）

- **搜索案 remedy 最终裁决内容**：2025 年 Mehta 的 remedy 判决具体条款（是否剥离 Chrome、默认协议如何处理、数据共享要求）——我记忆模糊/不确定，这是**第一命门**
- **ad-tech 案 remedy 进展**：Brinkema 2025-04 liability 后的补救走向不清楚
- **FY2025 完整财务 + 2026 最新季度**：营收/云增速/资本开支实际值、2026 capex 指引——训练后数据缺失
- **当前股价/估值倍数**：GOOGL 现价、P/E、市值——完全 uncertain
- **AI Overviews 对搜索货币化的实际影响**：是否已见查询量/CPC 侵蚀的硬数据——只有定性认知
- **Gemini 最新版本与市场地位**：Gemini 3？相对 ChatGPT 的用户/份额进展
- **Waymo 最新运营规模**：周单量、城市扩张、单位经济
- **AI 资本开支的最新指引与市场对其 ROI 的态度**（DeepSeek 之后的叙事演变）
- **2025 股东回报**：最新股息率、回购执行、是否加码

## 五、需要 web-search 校准的优先项

> 强制：第一节所有"快变 + 高/中置信"fact 都要有对应 query。

1. `Google DOJ search antitrust remedy ruling 2025 Chrome divestiture Mehta decision`（fact-19/20，第一命门）
2. `Google ad-tech antitrust remedy 2025 Brinkema Judge decision ad exchange`（fact-21）
3. `Alphabet FY2025 full year revenue earnings Google Cloud growth`（fact-01/02/04/13）
4. `Alphabet Q1 2026 Q2 2026 earnings results Search advertising revenue`（fact-03）
5. `Alphabet capex 2025 actual 2026 guidance AI infrastructure spending`（fact-05）
6. `Google Gemini 3 latest model 2026 vs ChatGPT market share usage`（fact-15/24）
7. `Google AI Overviews search monetization impact query volume CPC 2025 2026`（fact-16）
8. `Alphabet GOOGL stock price valuation PE market cap July 2026`（fact-09/10）
9. `Waymo weekly rides 2026 cities expansion robotaxi scale`（fact-23）
10. `Alphabet dividend buyback 2025 2026 shareholder return`（fact-08）
11. `Google TPU Ironwood 2026 Nvidia dependence cloud AI chip`（fact-18）
12. `Google Cloud backlog remaining performance obligation 2025 AI revenue`（fact-13）

**质检**：第五节 12 条 query ≥ 第一节"快变+高/中"fact（~12 条），每条快变 fact 已被覆盖。✓

## 六、prescan 校准结果（2026-07-23 回写）

> Step 4.5 prescan 入库 30 份 web-search material + FY2025A 财务（yfinance）后，对照第一节 fact-NN 更新。
> ⚠️ **本轮时点极关键**：Q2 2026 财报于 **2026-07-22（昨天）** 发布，本研究恰在最新财报次日。

### 被推翻 / 大幅更新（高优先级——thesis_v0 不要再引用原 fact）
- `[fact-01]` 训练"FY2024 营收 $350B"→ 实际 **FY2025A 营收 $402.8B**（+15%），Q2 2026 单季 **$119.8B/+24%**（`[mat-cf946d]`/`[mat-863fff]`/财务ctx）
- `[fact-02]` 训练"FY2024 净利 $100B"→ **FY2025A 净利 $132.2B**；Q2 2026 净利 **$112.1B**（含 Anthropic/SpaceX 股权重估 **$99B other income** 一次性，需剔除看经营）（`[mat-cf946d]`/`[mat-aebbd4]`）
- `[fact-04]` 训练"Cloud FY2024 $43B / 增速 30%+"→ **Q2 2026 Cloud $24.77B 单季、YoY +82%**（增速大幅加速），backlog **$460-462B**（Q1 2026 翻倍），且**产能受限**（`[mat-e6b2aa]`/`[mat-eff6d4]`/`[mat-d2016a]`/`[mat-f86102]`）— Cloud 已占 Alphabet ~18%
- `[fact-05]` 训练"FY2024 capex $52.5B、2025 指引 ~$75B"→ **2025 实际 ~$91.4B**；**2026 指引一路上调：Feb $175-185B → Q1 $180-190B → Q2 2026 $195-205B**（`[mat-3cbb2c]`/`[mat-b94c8b]`/`[mat-96e664]`）— 这是最强反方的核心：capex 近乎翻倍
- `[fact-09]` 训练"市值破 $2T"→ **已破 $4T**（Fortune 称 "$4 trillion tech giant"）（`[mat-b94c8b]`）；尾随 P/E ~30x（$4T / $132B 净利）
- `[fact-20]` 【第一命门大幅利好】搜索案 remedy：**Judge Mehta 已终裁，Google 保住 Chrome（不剥离）**，仅要求搜索数据共享 + 限制（非禁止）默认协议（`[mat-69b262]`/`[mat-477943]`）— 最坏情形（剥离 Chrome）被排除，重大 de-risk
- `[fact-15]` Gemini：**662M 用户**（YoY +132%）；**ChatGPT 份额跌破 50% 至 46.4%，Gemini 27.7%，Claude 10.3%**（`[mat-8ba765]`）— Gemini 借 Search/Android/Workspace 分发快速追赶
- `[fact-16]` AI Overviews/**AI Mode 已达 ~1B 用户**，广告已进入 25% 的 AI 结果（`[mat-d68a3f]`/`[mat-d23b56]`）— 货币化侵蚀担忧被"AI Mode 已放广告"部分对冲
- `[fact-23]` Waymo：**周付费单量 ~45 万（2025-12）**，目标 **2026 年 100 万/周**（`[mat-336e91]`/`[mat-050380]`）

### 被验证（可继续引用，置信度提升）
- `[fact-08]` 首次派息 2024-04 + $70B 回购 → 2025-04 再上调股息 + 新回购授权（`[mat-3c6b29]`/`[mat-bbcb49]`）→ 高
- `[fact-18]` TPU 自研兑现：**Anthropic 扩大使用 Google Cloud TPU（传至百万级 TPU）**，Google 拟对 Anthropic 追投至 $40B；Ironwood 4X 性能（`[mat-950a14]`/`[mat-400487]`/`[mat-e01fac]`）→ TPU 从自用走向外部变现，中→高
- `[fact-19]` 搜索案 liability 成立（静态）→ 验证；remedy 见上
- `[fact-25]` DeepSeek 冲击（2025-01，静态事件）→ 验证

### 仍未校准 / 待深料（thesis_v0 引用时标 uncertain）
- `[fact-21]` ad-tech 案 remedy：phase 已收官，**divestiture（剥离广告交易所）仍在权衡、终裁待定**（`[mat-414252]`/`[mat-f2594f]`）— 第二命门，需 02/03 深料
- `[fact-03]` Search 广告单项拆分（Q2 2026 广告 +14.5%，但 Search vs YouTube 精确拆分）待年报/10-Q
- `[fact-07]` 最新现金/净现金头寸待 10-Q
- FCF：FY2025A **$73.3B**（几乎持平 2024 的 $72.8B）——capex 翻倍下 FCF 尚未崩，但 2026 capex $195-205B 将实质压缩 FCF，这是估值核心变量，待建模
