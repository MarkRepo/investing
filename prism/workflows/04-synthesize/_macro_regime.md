# Macro 合成（理解先行 · 因果链驱动 · 三体制读数 · 自由发挥版）

> **调度提示**：本文件是 **macro 类型 topic 在 04-synthesize 阶段的完整规范**，是 `_arena_funnel.md`（arena 漏斗）/ `_company_case.md`（公司决策链）/ `_industry_funnel.md`（行业漏斗）的并列同胞。`company` 走 `_company_case.md`，`arena` 走 `_arena_funnel.md`，`industry` 走 `_industry_funnel.md`，**`macro` 走本文件**。
>
> **复用上游、不重写**：00-research → 01-roadmap → 02-materials → 03-findings 的 findings、`gap_detector`、增量重写判定、`thesis`、`00-primer.md`、sidecar schema/stub 创建机制全部沿用。本文件只重做 macro 的"合成"这一段。
>
> **设计依据**：本路径直接落地 `docs/superpowers/specs/2026-06-07-macro-rates-liquidity-layer-design.md`（宏观层方案 C）。链结构见该 spec **§3「核心架构：一条因果链，四层」**，本文件是它的可执行展开。

---

## 0. 定位与边界

macro 不是自下而上的个股/行业逻辑——它是**整个组合共用的贴现率与风险背景的拥有者**。prism 现有 topic（白酒、茅台、泡泡玛特、拼多多、富途等）的每个 case 都隐含一套利率/风险假设，但没有任何模块**拥有**这套假设；macro 层填的就是这个缺口：把"会移动我持仓价格的少数宏观变量"系统化研究出来，并显式连到每个持仓上。

用户是宏观门外汉，故本层有**双重目标**（spec §1）：① **学习载体**——用大白话把利率/流动性/汇率讲透；② **专业级集成**——以严谨因果链结构接入 prism，输出可消费的体制读数与传导决策。

两条根本规约（与 `_arena_funnel.md` 同构）：

1. **理解先行**：先出 `00_primer`（宏观理解地基，critic 校验"门外人真懂了"），活读数与传导地图**显式站在它之上**。
2. **按因果链组织**（不是并列指标罗列）：L1 输入 → L2 驱动变量 → L3 三体制读数 → L4 传导决策，每一层是上一层**逼出来的**。

- **不变的是骨架**（理解先行 + 四层因果链 + transmission_map sidecar schema）。
- **自由的是血肉**——每层讲什么、组织几节、详略，交给 LLM 针对当下宏观命门判断。

**与 arena/company 的刻意差异**：macro **没有 peer 漏斗、不选标的、不做 EV 加总**。它的定量终点是 ① regime_read 顶部的「综合判断 + 强度分 0-10」、② transmission_map 里每持仓的敏感度标签。决策落在"组合该怎么倾斜久期/利率β/美元暴露"，而非"买哪只票"。

---

## 1. 因果链总纲（这就是契约本身）

照 spec §3，macro 合同是**一条因果链、四层**：

```
[L1 输入源] → [L2 驱动变量]      → [L3 目标·三体制读数]     → [L4 传导·决策]
   数据          增长 / 通胀          利率 / 流动性 / 汇率         每持仓敏感度
              政策反应 / 财政        (各自小框架 + 大白话)        → 仓位/久期倾斜
```

**链条三段 = 用户最关心的三件事**（spec §3）：

- **左半段 = 输入**（L1 数据源 + L2 驱动变量：增长/通胀/政策反应/财政——它们不是并列目标，是利率/流动性的上游输入，央行盯着它们行动）。
- **中段 = 传导逻辑**（L3 三体制：利率/流动性/汇率，各自小框架把"输入怎么变成体制读数"讲透）。
- **右段 = 决策**（L4 transmission_map：三体制 → 四条传导渠道 → 每持仓敏感度 → 组合倾斜）。

prism 里的文件只是这条链的容器；逻辑在前、文件在后。本路径产出三份正文 + 一份 sidecar：`00_primer.md`（L1→L4 全链入门）/ `m_regime_read.md`（L3 三体制活读数）/ `transmission_map.yaml`（L4 传导地图 sidecar）/ 再落 thesis + decomposition。

**地理主线（spec §2 决策）**：**美国/全球为主线，中国第二块**——全球利率/流动性的总闸门在美国；汇率对几乎全为 A股/中概（含 ADR）的组合不可省，作为第三体制而非可选项。primer 与 regime_read **都先讲美/全球、再单列中国第二节**。

---

## 2. 执行 — 上游准备与 primer 先行

### Step 0：前置检查 + gap 体检 + 增量判定（**引用 `_shared.md`，不重抄**）

进 04 第一件事，照 `_shared.md` 跑三段，结果完整贴对话：

1. **前置检查**（资料 ≥3 份，否则停；MVP 下宏观料含手工快照亦计入，见 §8）。
2. **gap 体检**（`detect_gaps` 三项任一非空 → 不要硬合成，先补救）。
3. **增量重写判定**（`list_affected_outputs` 判 new/stale/fresh；`fresh` 跳过）。macro 路径 output_key = `00_primer` / `m_regime_read`（+ sidecar `transmission_map`）。

> Web 搜索路径见 `_shared.md` § 即兴 web-search 规约；数据源约定见本文件 §8。

### Step 1：加载 findings + thesis_v0 + **亲属 hook（图谱层）**

1. 照 `_shared.md` § 调度模式：`format_findings_for_prompt` 列 findings → 主 agent 并行 Read；`build_findings_index` 落盘 `_findings_index.md`；读 `thesis_v0.md`。
2. **亲属 hook（标准调用，macro 多数时候退化为独立合成）**：

   ```bash
   python3 -c "
   from prism.scripts.topic import get_relative_outputs
   rel = get_relative_outputs('{slug}', '{variant}')
   print('parent:', rel['parent'])
   print('children:', rel['children'])
   "
   ```

   - 函数**只返路径、绝不读内容、不做判断**——借用永远是输入/参照，受 `_arena_funnel.md` §1.3 跨层复用护栏约束（借来必标来源、质量按本维度自跑、冲突时本 topic 赢）。
   - **macro 在 tier 漏斗之外**：它通常既无 `parent_topic` 也无子 topic（持仓不是 macro 的 child，是平行的 company/arena topic）。故 `get_relative_outputs` 返回 `parent=None, children=[]` 是**正常退化**，直接走独立合成，**零特判、不阻塞**。
   - 若确有亲属（极少见，如未来挂了上层 macro-regime 父）→ 按护栏标来源、本维度自跑，不照搬结论。

> **调度模式**：macro 合成默认**主 agent 直做 + 并行 Write**。唯一 subagent 是 critic（只读不写）。

### Step 2：**先出 `00_primer`（入门读本 / 理解地基）**

按 `00-primer.md` Step 1-5 执行，产 `outputs/00_primer.md`（+ `_prism_reading_guide.md`，照该文件惯例）。本路径走 **primer-first**：primer 写完、critic 收敛后才进 Step 3 写 regime_read。

**frontmatter 必须 `depth: deep`**（本层的核心目标之一就是"用大白话把框架讲透"，浅 primer 不达学习载体目标）。

**入门读本必带子节（每节给"必须落地什么"，组织自由）**：

1. **术语表（大白话 / plain-language glossary）**：把利率/流动性/汇率最核心的术语用门外话讲清（如"久期 = 利率动 1% 你的价格动几个 %"、"净流动性 = 央行放的钱减掉财政/逆回购抽走的钱"、"carry = 借便宜的钱买贵收益的差价"）。这是后续 regime_read 每指标三句注解的词汇地基。
2. **L1→L4 因果链讲解**：照 §1 把四层串成一个故事——数据从哪来 → 驱动变量怎么动 → 三体制读数怎么形成 → 怎么传到持仓。读者顺着读就懂了整条链。
3. **三体制各自的小框架（each regime's mini-framework）**：
   - **利率体制**：费雪分解（名义=实际+通胀预期）；短端看央行、长端看预期+期限溢价；曲线四形态（牛陡/熊陡/牛平/熊平）。大白话 = 钱的**价格**往上还是往下。
   - **流动性体制**：央行→银行→市场三层传导；宽货币×宽信用四象限；净流动性 + 信用利差。大白话 = 钱**多不多、愿不愿冒险**。
   - **汇率体制**：利差→汇率→资本流动套利链；中美 10Y 利差 / DXY / USDCNY / 北向资金。大白话 = 钱往**中国流还是往外跑**。
4. **四条传导渠道（four transmission channels）**（spec §3 L4）：贴现率渠道 / 风险偏好渠道 / carry-久期渠道 / 汇率渠道——讲清每条渠道"宏观一变，持仓价格经哪条路被推动"。
5. **「根本争议」节（5-7 条）**：宏观判断从来不是共识（如"长端利率是被通胀预期还是期限溢价主导""净流动性指标是否还有效""中美利差对汇率的解释力是否在下降""降息究竟利好成长还是预示衰退"……）。逐条点出分歧两端 + 当前证据偏向。**这是 primer 深度门禁的硬检查项之一**。
6. **「自检清单」节**：给读者一份"我真懂了吗"的自测题（如"你能用一句话说清当前利率体制是四形态里哪个吗？""组合里哪只票的美元暴露最高？"）。**这是深度门禁的硬检查项之一**。

**地理排布**：**美/全球为主线写在前、中国作第二节**（spec §2）。每个体制小框架与争议都先讲美/全球、再单列中国对应块。

**硬门禁（机械，零 LLM；由 `primer_quality_gate` 强制）**：`depth: deep` 的 primer 必须满足 **正文 ≥6000 字** + **含「争议」** + **含「自检」**（`primer_quality_gate` 检查 `char_count ≥ 6000` / `has_controversy`（正文含"争议"）/ `has_selfcheck`（含"自检"或"自测"）/ `critic_passed`）。任一不过 → `set_output_status('00_primer','fresh')` 会被**自动降级为 `draft`** 并把原因记进 `outputs_state.00_primer.primer_gate.warnings`。

primer 其余流程（目标生成 / 起点诊断 / 自由发挥 / 来源分层 / **独立 critic 校验**）照 `00-primer.md` 走，critic 不可省。

**收尾注册（顺序硬要求 · 照 `00-primer.md` Step 注册块）**：critic 收敛后**先调 `set_output_critic_passed`**（deep 的机械凭证），**再调 `set_output_status(..., 'fresh', ..., version=...)`**——否则 deep 软门禁把它降级 `draft`：

```bash
python3 -c "
from prism.scripts.topic import (set_output_critic_passed, set_output_status,
                                  set_output_referenced_mats, primer_quality_gate, read_topic)
# 1. critic 已收敛 → 先置机械凭证（deep 必需）
set_output_critic_passed('{slug}', '{variant}', '00_primer')
# 2. 注册 fresh（depth=deep 但门禁不过会被自动降 draft）
t = read_topic('{slug}', '{variant}')
cur = t['outputs_state'].get('00_primer', {}).get('version', 0)
set_output_status('{slug}', '00_primer', 'fresh', '{variant}', version=cur+1)
set_output_referenced_mats('{slug}', '00_primer', {mat_ids_list}, '{variant}')
# 3. 核门禁结果（被降级则按 warnings 补争议节/自检节/补长再重注册）
g = primer_quality_gate('{slug}', '{variant}')
final = read_topic('{slug}', '{variant}')['outputs_state']['00_primer']['status']
print(f'00_primer 注册：status={final}（depth={g[\"depth\"]}，gate ok={g[\"ok\"]}）')
if final == 'draft':
    print('⚠️ 被门禁降级，原因：', g['warnings'])
"
```

> ⚠️ 第一份产出（首次写 `00_primer`）走 `set_output_status` 的 `setdefault` 自动注册，**不用改 topic.py**。

---

## 3. 执行 — L3 三体制活读数（站在 primer 上）

### Step 3：写 `m_regime_read.md`（三体制活读数 / living regime read）

这是 macro 的 L3 主体——把 primer 教的静态框架，套到**当下的真实读数**上。"活"在两处：① 每指标带**三句注解**随用随巩固词汇；② regime_read 会随宏观变化重写（增量判定走 `list_affected_outputs`）。

**起点诊断（写正文前必做 · 借 `00-primer.md` §2.1，轻量化）**：primer 已建好框架，故只需确认 (a) 当前最该盯的 1-3 个体制命门（如"市场在赌降息但通胀粘性未消"）；(b) 哪些背景甩给 primer。命门以 00 的 `decomposition_v0` 为种子，读完 findings 按 `_shared.md` §"B 轴有界 delta 重拆"做 delta 校验 → 落 `decomposition_v1`。

**顶部（先于三节）**：写「**综合判断 + 强度分（0-10）**」——一句话总判（如"利率高位企稳、流动性边际转松、人民币贬压未解 → 组合整体偏防御、压久期"）+ 0-10 强度分（沿用 prism thesis 强度惯例：0=极弱信号，10=极强信号）。

**三节，一节一个体制（利率 / 流动性 / 汇率）**，每节统一三段式 + 每指标三句注解：

1. **关键输入指标**：列该体制的核心指标（利率：美 2Y/10Y、10Y 实际利率(TIPS)、期限溢价、政策利率；中 10Y 国债、DR007、LPR。流动性：美 净流动性(美联储资产−TGA−RRP)、信用利差(HY/IG OAS)；中 社融同比、M1、M1-M2 剪刀差、信贷脉冲。汇率：中美 10Y 利差、DXY、USDCNY、跨币种基差、北向资金。——以 spec §3 L3 表为锚，可增减）。**每指标必带三句注解**：
   - `这是什么`（大白话定义，呼应 primer 术语表）；
   - `为什么看它`（它在这条因果链里卡哪一环）；
   - `现在说明什么`（当前读数 + 它此刻在告诉我们什么）。
2. **内部逻辑**：把指标串成体制判断（利率用费雪分解 + 曲线四形态；流动性用三层传导 + 四象限；汇率用利差→汇率→资本流动套利链）。
3. **输出形态**：收口成该体制的标准读数（利率：曲线形态 + 方向；流动性：松/紧 + 四象限；汇率：人民币升贬压力 + 外资流向）。

**地理排布**：每节内**先美/全球、再中国第二块**（spec §2）。

**数据时效标注（硬要求）**：MVP 允许手工快照，但**必须**在 regime_read 顶部或每指标处明示数据截止日，并落机械标记（见 §8 `set_data_freshness`）。

**收尾注册**：

```bash
python3 -c "
from prism.scripts.topic import set_output_referenced_mats, set_output_status, read_topic
t = read_topic('{slug}', '{variant}')
cur = t['outputs_state'].get('m_regime_read', {}).get('version', 0)
set_output_status('{slug}', 'm_regime_read', 'fresh', '{variant}', version=cur+1)
set_output_referenced_mats('{slug}', 'm_regime_read', {mat_ids_list}, '{variant}')
print('m_regime_read 已注册 fresh')
"
```

> 新键 `m_regime_read` 靠 `set_output_status` 的 `setdefault` 自动注册，**不用改 topic.py**。

---

## 3.5 机制纠错与多维读数（合成必遵守）

> 来源：spec `2026-06-07-macro-dynamic-monitoring-and-maturation-design.md` §5（机制纠错）+ §6.1-6.2（多维读数 / fragility 罚分）。这是校准红队推翻/修正后的**硬约束**——写 `m_regime_read.md` 与 `transmission_map.yaml` 时逐条遵循，不得回退到被推翻的旧机制。

### 3.5.1 机制纠错八条（spec §5，逐条遵循）

校准红队对原断言的判定与处置，合成读数时必须照此落（§3 状态列已体现）：

1. **中美10Y利差 → 人民币贬（carry）**：现 regime 下该链路**断裂/反向因果**（高信）。**A→B**，由因果驱动降为**压力表**（只读不当成因）；人民币的真 A 级驱动是**中间价 / 逆周期因子 + 资本管制 + 贸易顺差**，而非利差。
2. **黄金 = 实际利率 + DXY 的产物**：机制过时（高信）。层级保留 **B**，但**机制改写**——2023–25 黄金已与实际利率/DXY **脱钩**（央行购金主导），是更好的**去美元化读数**，**不得再当实际利率代理**。
3. **信用利差 OAS**：原为重复登记且"领先股市"不成立（高信）。**收敛为单一 B**，删去"领先"标签，改标**同步**。
4. **净流动性 → 风险偏好**：属 regime 条件量、RRP 已基本耗尽（中高信）。A 级**保留但降权**；**SOFR−IORB** 升为 **binding driver**（资金面真正咬合处）。
5. **核心 PCE / CPI → 利率↑**：方向对、但漏期限（高信）。维持 A，须**分期限**读（短端正相关 / 长端可反向）；触发条件用**超预期**（surprise）而非绝对**水平**。
6. **日元 carry**：原 mis-scoped（高信）。A 级保留，但标为**条件 / 阈值的尾部触发**（拥挤平仓型），非常态驱动。
7. **DXY → 中国 FX**：工具错（DXY 约 57% 是欧元权重，中信）。中国侧改用 **CFETS / 广义美元**指数；**DXY 降为 B**。
8. **比特币 C**：红队**确认正确**（affirm）——**维持 C**（被利率驱动的相关资产，非独立因果）。

### 3.5.2 多维读数（spec §6.1）

不再"单一综合判断 + 1 个强度分"。读数要：

- 三体制（利率 / 流动性 / 汇率）**各自给读数 + 分维信心**（per-dimension confidence，0-10，落 `transmission_map.regime.*.confidence`）。
- 另设**增长/通胀象限**（复苏 / 过热 / 滞胀 / 衰退），**独立于三体制**单独判一个落点（落 `transmission_map.regime.quadrant`）——三体制说的是"市场体制"，象限说的是"宏观基本面在哪格"，二者可背离。

### 3.5.3 fragility 罚分（spec §6.2）

强度分与突变风险**反相关**（越"干净"越临近崩）。综合信心须被**脆弱度**折减——脆弱度由 **利差极窄 + 低波动 + carry 拥挤 + 承重假设数** 构成；high 时即便 conviction 高，也要明示输出"**信心X / 脆弱度高**"（落 `transmission_map.regime.fragility` = low/mid/high）。

---

## 4. 执行 — L4 传导地图 sidecar（硬契约 · schema 原样不动）

### Step 4：写 `transmission_map.yaml`（传导地图 / dashboard banner 消费契约）

> **承上（§3.5）**：`transmission_map` 的 `regime` 块必须落 `confidence`（三体制分维信心）/ `quadrant`（增长/通胀象限）/ `fragility`（脆弱度），schema 已具这三字段，照 §3.5.2-3.5.3 填。

⚠️ dashboard 的宏观横幅（banner）**只读 `transmission_map.yaml`、只认这套字段名**。**禁自创/改名/漏字段**。三体制读数（L3）经四条传导渠道映射成每持仓敏感度标签（L4），逐字照下面 schema 落盘：

```yaml
slug: <slug>
variant: <variant>
generated: "<ISO8601>"            # 用 datetime.now(timezone.utc).isoformat()
regime:
  rates:     {state: ..., note: ..., confidence: <0-10>}   # 新增分维信心
  liquidity: {state: ..., note: ..., confidence: <0-10>}
  fx:        {state: ..., note: ..., confidence: <0-10>}
  composite: ...                       # 顶部综合判断一句话(= regime_read 顶部综合判断)
  conviction: <0-10>                   # 强度分(= regime_read 顶部 0-10，数字不加引号)
  quadrant: ...        # 新增：增长/通胀象限（复苏/过热/滞胀/衰退），独立于三体制（spec §6.1）
  fragility: ...       # 新增：脆弱度（low/mid/high）——强度越"干净"越临近崩，折减信心（spec §6.2）
holdings:
  - {slug: ..., display_name: ..., duration: long|short, rate_beta: high|mid|low,
     usd_exposure: high|mid|low, liquidity_beta: high|mid|low, exposure_score: high|mid|low,
     regime_favor: [...], regime_hurt: [...], plain: "一句大白话传导链",
     source: macro_synth, provisional: false, as_of_regime: vN}   # 新增三字段(3a)
categorical_tail:       # 新增：spec §3.10 类别尾部 always-alert 状态快照（无市场序列可 diff）
  - {name: ..., state: 平静|警示|触发, note: "一句话"}
```

> **新增字段语义**：`confidence`=该体制单独的判读信心 0-10；`quadrant`=增长/通胀象限（复苏/过热/滞胀/衰退）；`fragility`=脆弱度（low/mid/high），high 时即便 conviction 高也要在 dashboard 标"信心X/脆弱度高"。

字段语义（沿 spec §3 L4 四渠道 + 每持仓标签）：

- `duration`：久期长短（成长股/长资产=long，价值/短现金流=short）。
- `rate_beta` / `liquidity_beta` / `usd_exposure`：对利率 / 流动性 / 美元的敏感度（high/mid/low）。
- `exposure_score`：综合暴露分（high/mid/low）。**`exposure_score: high` → 该持仓进 banner 的「最受影响」列表**（dashboard 直接消费这条规则）。
- `regime_favor` / `regime_hurt`：当前哪些体制利好 / 利空它（list，元素如 `rates_down`、`liquidity_tight`、`cny_weak`）。
- `plain`：一句大白话传导链（如"美元走强 → 中概外资流出 → 拼多多承压"）。
- `source`=`macro_synth`（macro 合成判）/ `self_registered`（company 自注册待复核）；`provisional`=self_registered 未复核；`as_of_regime`=依据哪版 regime eval。**macro 合成时必复核 provisional 行：确认/改写标签 → 清 provisional → 更新 as_of_regime**。

**覆盖范围（硬要求）**：`holdings` 数组**必须覆盖每一个现存 company 持仓**。先枚举当前所有 company-type topic 再逐个填，别漏：

```bash
python3 -c "
from prism.scripts.topic import list_topics
for t in list_topics():
    if t.get('type') == 'company':
        sc = t.get('scope', {})
        print(t['slug'], t.get('variant'), '|', t.get('display_name'), '|', sc.get('ticker'))
"
```

> ⚠️ 缺料导致某持仓敏感度判不准时，**标注"训练知识估算"或"数据缺失"，不编造、不静默漏行**（照 `00-primer.md` §2.4 depth 降级惯例）。数字不加引号，缺失 null。文件用 `Path(...).write_text(...)` 落盘到 `topics/{slug}/{variant}/outputs/transmission_map.yaml`。

**落盘后注册引用（触发 dashboard 重建）**：

```bash
python3 -c "
from prism.scripts.topic import set_output_referenced_mats
set_output_referenced_mats('{slug}', 'transmission_map', {mat_ids_list}, '{variant}')
print('transmission_map 已注册并触发 dashboard 重建')
"
```

> `set_output_referenced_mats` 内部调 `_trigger_dashboard` → fire-and-forget 重建横幅。新键 `transmission_map` 靠 `setdefault` 自动注册，不用改 topic.py。

---

## 5. 执行 — 收尾（thesis / decomposition）

### Step 5：落 thesis_v1 + decomposition_v1（因果链跑完后才写）

**thesis_v1（三体制综合判断快照）**：把 regime_read 顶部的综合判断提炼成可追踪快照，完整 markdown 写到 `thesis_v1.md`，summary ≤120 字：

```bash
python3 -c "
from prism.scripts.topic import set_thesis
set_thesis(
    '{slug}', '{variant}',
    version=1,
    summary='利率高位企稳·流动性边际转松·人民币贬压未解 → 组合偏防御压久期，强度6/10',  # ≤120字
    stage_set_at='04-synthesizing',
)
print('thesis_v1 已记录')
"
```

> `set_thesis` version≥1 会自动跑 reverse-check（K# 在 roadmap 未闭环则写补 roadmap todo + 翻 stage 到 01-roadmap-reopen）；macro 若 roadmap 未建则跳过该副作用，正常返回。

**decomposition_v1（命门 = 当前最不确定的宏观岔口）**：把"现在最该盯、最可能翻盘"的宏观岔口落成命门，完整 markdown 写到 `decomposition_v1.md`，summary ≤120 字，**v1 必带 changelog**：

```bash
python3 -c "
from prism.scripts.topic import set_decomposition
set_decomposition(
    '{slug}', '{variant}',
    version=1,
    summary='命门1=通胀粘性是否压住降息节奏; 命门2=净流动性见顶后风险偏好转向; 命门3=中美利差走阔触发的资本外流',  # ≤120字
    stage_set_at='04-synthesizing',
    convergence_status='converged',   # 'open'/'converged'/'capped'，照 _shared.md B 轴判定
    changelog='v1 相对 v0：新增汇率岔口为命门、降级增长岔口（已被 L2 输入解释）',  # v1+ 必带
)
print('decomposition_v1 已记录')
"
```

**写评估快照（闭环重估 · 硬要求）**：regime_read/transmission_map 落地后，调 `eval_snapshot.record_evaluation` 把「输入→判断」写回 `regime_eval_log.yaml`——这是 web「发起重估」与 diff/简报基准的脊梁，**漏写则 `reeval_pending` 戳永不自动清、「上次合成时间」不更新、下次 diff 失基准**。`record_evaluation` 用 `snapshot_inputs` 自动列全所有输入、据 `based_on` 标 `used`、自增 version、写 `evaluated_at`、**自动清 `reeval_pending`**；不变量校验（input_snapshot 列全 + based_on 不悬空 + role 合法）全程不放松。

conclusions 覆盖本轮三体制读数与象限/脆弱度，每条带 `id` + 中文 `label` + `state` + `causal`（一句因果）+ `based_on:[{input, role}]`（`role` ∈ load_bearing/confirming/background；`input` 必须是 registry 里的真实输入名，否则校验报错）。本轮**有变化/越带的受影响结论必须重判**（见简报）；无变化的可沿用上版判读但仍要登记。

```bash
python3 -c "
from prism.scripts.eval_snapshot import record_evaluation
v = record_evaluation('{slug}', '{variant}', [
    {'id': 'overall',      'label': '综合判断',     'state': '偏防御·压久期', 'causal': '...', 'based_on': [{'input': '<名>', 'role': 'load_bearing', 'expected': 'up_or_flat'}]},
    {'id': 'rates_us',     'label': '美国利率体制', 'state': '高位企稳',     'causal': '...', 'based_on': [{'input': '<名>', 'role': 'load_bearing', 'expected': 'up_or_flat'}]},
    {'id': 'rates_cn',     'label': '中国利率体制', 'state': '...',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'confirming'}]},
    {'id': 'liquidity_us', 'label': '美国流动性体制','state': '...',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'load_bearing', 'expected': 'down_or_flat'}]},
    {'id': 'fx_cny',       'label': '人民币汇率体制','state': '...',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'confirming'}]},
    {'id': 'quadrant',     'label': '增长/通胀象限','state': '滞胀',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'background'}]},
    {'id': 'fragility',    'label': '脆弱度',       'state': 'high',          'causal': '...', 'based_on': [{'input': '<名>', 'role': 'background'}]},
], note='S5 合成/重估')
print(f'评估快照已写 v{v}，reeval_pending 已自动清')
"
```

> 不确定某结论挂哪些输入时，宁可多挂 `confirming`/`background`，但**承重输入必须标 `load_bearing`**——表头「承重漏判」红字（load_bearing 却未参与）就是查这个。

> **可证伪预测（硬要求 · 仅承重边）**：每条结论的 `load_bearing` 边、且该输入有数值或立场基准时，**必须**带 `expected` 方向预测（缺则 `record_evaluation` 校验报错）。方向词表：数值型 `up / down / flat / up_or_flat / down_or_flat`；立场型用对应轴方向词（`更鹰/更鸽`、`更紧/更松`、`更收缩/更扩张`、`更下移/更上移`）。这是日后机器拿 FRED 序列机械裁决「判得对不对」的钉子——预测提前钉死、数据说话。confirming/background 边可不带。

**复核 provisional + 体制变扫失鲜（硬要求 · 写完评估快照后跑）**：record_evaluation 落新版后，跑横切回路——给依赖体制状态已变的持仓盖 stale 旗 + 写 `macro_regime` proposal（stage 不动）：

```bash
python3 -c "
from prism.scripts import macro_xcut as mx
res = mx.apply_holding_staleness('{slug}', '{variant}')
cov = mx.coverage_gaps('{slug}', '{variant}')
print(f'体制变扫失鲜：{res[\"applied\"]}/{res[\"scanned\"]} 持仓标 stale')
print(f'覆盖率：{cov[\"covered_count\"]}/{cov[\"total_company\"]} company 已入表；漏注册={cov[\"missing\"]}；待复核 provisional={cov[\"provisional\"]}')
"
```

> provisional 行的复核是 LLM 动作（在本合成对话里做）：对 `coverage_gaps` 报出的 provisional 持仓，逐行确认/改写四渠道标签、清 `provisional`、更新 `as_of_regime`，写回 transmission_map（照 §4 落盘惯例）。

**带上版战绩裁定（重估时 · 软要求）**：本轮若是**重估**（已有上一版评估），重判前先看上版机械战绩，据此对每条结论落 `prior_verdict`（held/partial/wrong），写在本（新）评估条目上（append-only、不改旧）：

```bash
python3 -c "
from prism.scripts import eval_score as sc
s = sc.score_evaluation('{slug}', '{variant}')   # 上版整版战绩卡
print('上版占对：', s.get('hits'), '/', (s.get('hits') or 0)+(s.get('misses') or 0), '·', s.get('days'), '天')
for c in s.get('conclusions') or []:
    print(' -', c['label'], c['hits'], 'hit /', c['misses'], 'miss', '· 占对', c['hit_rate'])
led = sc.edge_ledger('{slug}', '{variant}')        # 跨版边台账 → 降级候选
for r in led[:5]:
    print('   边', r['conclusion_id'], r['input'], r['track'], r['hits'], '/', r['hits']+r['misses'])
"
```

据此在 `record_evaluation(...)` 调用补 `prior_verdict=[{'conclusion_id': '<id>', 'verdict': 'held|partial|wrong', 'note': '...'}]`。**机制边降级**＝一次普通 registry 编辑：对 `edge_ledger` 报「降级候选」的边，按需调 `macro_registry.upsert_input` 改该输入 `tier`（A→B）或调它在 based_on 的 `role`（load_bearing→confirming）。不发明新台账文件。

### Step 6：critic 校验 + stage 推进

写完即跑一轮**内嵌 chain-critic**（模型同 `00-primer.md` Step 3，只读不写 subagent，`subagent_type: general-purpose` 不传 model），逐层校验因果链是否走通：

- **L1/L2**：输入源 + 驱动变量（增长/通胀/政策反应/财政）讲清了吗、有没有把它们误当成并列目标？
- **L3**：三体制各有"关键输入→内部逻辑→输出形态"、每指标三句注解齐、顶部综合判断+强度分在？
- **L4**：transmission_map 覆盖**全部** company 持仓、四渠道映射成敏感度标签、`exposure_score: high` 行的传导链 `plain` 立得住？
- **primer↔regime_read 是否重复**（背景该甩 primer 的甩了没）？
- **源分层**：findings 数字标 `[mat-XXX]`？手工快照标了数据截止日？
- 🎯 **目标达成核对（最重要）**：贴出本 topic `scope.question` 原文（`python3 -c "from prism.scripts.topic import read_topic; print(read_topic('{slug}','{variant}')['scope']['question'])"`），逐子句核对是否答到**可执行层**——macro 的"可执行"= 三体制读数 + 每持仓倾斜标签，停在"宏观怎么走"却没落到"组合该怎么倾斜"即判**致命缺口**。

四段总评（链通不通 / 最严重 2-3 个断点 / 🎯 目标达成判定 / 只补一处补哪），苛刻直接，1800 字内。按反馈修订（主 agent 直接 Edit）。首轮若判断链 OR 目标未达成，**必须跑第二轮**。

**stage 推进**：合成完照 `_shared.md` 出终态报告 + `append_user_todos` + 清 `next_actions`，stage 置 `05-critic-review`（第 6 阶段「评审」，与 company/arena 统一；macro 的 critic 非强制——可对话跑评审或 web 点「完成」直接 done）：

```bash
python3 -c "from prism.scripts.topic import set_stage; set_stage('{slug}', '05-critic-review', '{variant}'); print('→ 评审 {slug}')"
```

---

## 6. 数据来源约定（Data-source convention）

照 spec §3 L1+L2 数据获取现实 + `_shared.md` 来源分层惯例：

- **美国/全球指标（主线）**：优先 **FRED 免费 API / 公开发布**（CPI、核心 PCE、净流动性各分量、2Y/10Y、TIPS、HY/IG OAS、DXY 等几乎全覆盖）；FRED 取不到的（FOMC 点阵图、CME FedWatch、QRA、TGA）走 **web search** 抓官方/权威转述。**第二期可全自动抓 FRED；MVP 阶段允许手工快照**。
- **中国指标（第二块）**：数据较散——走 **web / exa** 抓统计局 / 央行（货币政策执行报告、OMO/MLF、社融、M1/M2、DR007、LPR）/ **Wind 转述**。MVP 半自动（人工或 web 搜索快照）。
- **来源分层（照 `00-primer.md` §2.3）**：训练知识不标单条 / findings 凡引必标 `[mat-XXX]` / 手工快照标数据截止日 + 来源。

- **时效机械标记（硬要求）**：regime_read 写完后用 `set_data_freshness` 落机械时效位，让 dashboard / 增量判定知道这份读数有多新：

```bash
python3 -c "
from prism.scripts.topic import set_data_freshness
# freshness 写人读得懂的时效串，如 'snapshot@2026-06-05'（手工快照截止日）或 'live'（自动抓）
set_data_freshness('{slug}', 'm_regime_read', 'snapshot@2026-06-05', '{variant}')
print('m_regime_read 数据时效已标记')
"
```

> MVP 手工快照不是降级借口——**标清截止日就是诚实**；过期读数靠这个字段 + 增量判定触发重写，胜过假装实时。

---

## 附：与 arena/company 路径的关系

> 📎 *与 arena/company 路径的对照表 → 附录 A附（执行时可跳过）*

---

## 附录 A — rationale / 反例 / 历史教训（执行时可跳过，调试 / 维护时查）

> 本附录收纳从各步主流程搬出的"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"。**主流程逐字未删、只是移出执行动线**；要看某步的来龙去脉，按对应小节查。

### 附录 A附 — 与 arena/company 路径对照表

| | arena `_arena_funnel.md` | company `_company_case.md` | **macro 本文件** |
|---|---|---|---|
| 组织原则 | 理解先行 + 6 环决策漏斗 | 理解先行 + 决策链 | **理解先行 + 四层因果链（L1→L4）** |
| 终点 | peer shortlist（押哪几个玩家） | 买/卖一只票 | **三体制读数 + 每持仓倾斜标签（不选标的、不做 EV）** |
| primer | 最先生成，case 站其上 | 最先生成 | **最先生成（depth=deep 硬门禁），regime_read 站其上** |
| 主产出 | `a_arena_case.md` | `c_investment_case.md` | **`m_regime_read.md`（L3 活读数）** |
| sidecar | `peer_matrix.yaml` | `07_decision_kit.yaml` | **`transmission_map.yaml`（L4 banner 契约，覆盖全部持仓）** |
| 亲属 hook | 向下站父 primer、向上拿子 case 当实证 | 父 arena K# 收窄 | **多数退化为独立合成（macro 在 tier 漏斗外，parent=None/children=[]）** |
| thesis / decomposition | 赛道判断 / 命门 | 标的判断 / 命门 | **三体制综合判断 / 当前最不确定的宏观岔口** |
| critic | 内嵌 chain-critic + 05（可选） | 内嵌 + 05（必跑） | **内嵌 chain-critic + 05（可选）** |
