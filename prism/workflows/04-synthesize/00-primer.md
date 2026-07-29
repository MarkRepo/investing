# 产出 00 — 领域入门 (Domain Primer)

> **调度提示**：本文件是 04-synthesize 的内容规范。产出文件名 `00_primer`（排最前、读者最先读）。**primer 一律先行（全类型统一）**：在 case/决策链之前生成，作为理解地基，case 站其上。
> - **三类路径统一 primer-first**：company 走 `_company_case.md` Step 2、industry 走 `_industry_funnel.md` Step 2、arena 走 `_arena_funnel.md` Step 2，都在 Step 2 调用本文件。
> - **原材料统一为** findings + `thesis_v0` + K#（+ 按类型的财务数据 / 父级 primer 等亲属产出）。**不依赖 01-08 / thesis_v1**（旧 primer-last 路径已退休）。
>
> 可单独触发（「生成入门 {slug}」/「primer {slug}」）——若该 topic 已有 01-08/thesis_v1（旧数据），可一并作参考，但不作硬前置。

**定位**：给**完全外行**（懂股票/投资常识，但没碰过本 topic 所属领域）写一份深度领域入门——读完能对"研究对象本身"建立完整心智模型，足以跟从业者聊半小时不露怯，也足以拿起下游 case/决策链产出不被术语墙挡住。
**本质区别**：case（`c_investment_case` / `i_industry_case` / `a_arena_case`）是"研究产出/决策"（给已入门者的结构化分析与下注）；00_primer 是"领域教科书第一章"（给门外人补齐背景）。两者读者不同、深度递进方向不同，不要写重。
**产出文件**：`prism/topics/{slug}/{variant}/outputs/00_primer.md` + 配套 `_prism_reading_guide.md`

---

## 核心方法：元目标 + 目标生成 + 自由发挥 + critic 校验

本产出**不用固定章节模板**（不同 topic 类型——硬科技 / 单家公司 / 消费 / 创新药 / 资源——"好入门"的形态完全不同，模板会僵化）。改用"给目标 + LLM 自由发挥 + 独立 critic 校验目标达成"的闭环。已验证：硬科技 arena（固态电解质）、单家金融公司（Robinhood）、science-heavy 单家公司（荣昌生物）三类均可复现深度。

### 不变的元目标（所有 topic 共用，逐字不改）

> **门外人为了投资，正在研究这个 topic，他需要知道什么——以让他读完一篇就能入门该领域本身。先不限制内容长度。**

注："为了投资"这条隐含了内容取舍权重——**该讲**商业模式 / 单位经济 / 估值锚 / 竞争格局 / 风险 / 催化剂；**可省**与投资判断无关的纯学术细节、历史趣闻、人物八卦。LLM 在 Step 1 应自然吸收这条权重。

---

## Step 0：前置检查

参见 `_shared.md` 前置检查。**primer-first 统一原材料**：findings + `thesis_v0` + K#（+ 按类型的财务/亲属产出）。**不硬前置 01-08 / thesis_v1**——它们由本 topic 的合成路径在 case 阶段才产出，primer 站在它们之前。

```bash
python3 -c "
from prism.scripts.topic import read_topic
from prism.scripts.manifest import material_count
t = read_topic('{slug}', '{variant}')
print('type:', t['type']); print('question:', t['scope']['question'])
print('materials:', material_count('{slug}', '{variant}'))   # ≥3 才合成（同 _shared 前置）
print('thesis_v0:', (t.get('thesis') or {}).get('current_version'))
"
```

---

## Step 1：目标精修（读 decomposition 种子 + 厚料 delta，不凭空生成）

> **目标不从零拍脑袋**（与命门"以 v0 为种子"完全同构）：00 Step 5.4 的 `decomposition_v0.md` 已含一块 **「primer 入门目标 v0」**（薄知识起草的种子）。本步**读种子 → 厚料 delta 精修 → 出定稿**，而不是现场凭空生成。旧 topic 无 decomposition 种子 → 退化为凭空生成（零特判）。

1. **读种子**：Read `decomposition_v{latest}.md` 的「primer 入门目标」section（连同命门，便于看盲点同源）。**抽出所有挂 `[训练知识展开]` tag 的目标 → 这是一份"必主动展开专节"清单**：decomposition 已判定它们无 findings 喂、靠训练知识兜底；本 primer 是 findings-first，最易把它们薄化漏掉，故须在此显式认领，Step 2.2 逐条给独立小节写到教学满深（旧 topic 无 tag → 退化：自行按"哪些目标 findings 覆盖不到"识别同一批，零特判）。
2. **delta 校验（= primer 目标的"体检"）**：读元目标 + `topic.yaml`（`type` / `scope.question` / `thesis` summary）+ `thesis_v0.md`（或最新 thesis）+ **`baseline_knowledge.md`（训练知识种子 · 见下）** + `_findings_index.md` / findings 本身，对照种子逐条问厚料：**该补的新入门目标**（findings 揭示门外人会卡、种子没列的）？**多余/可坍缩的目标**（种子列了但其实非入门必需）？因 primer 本就消费 findings，这步 delta 在动笔前自然发生。
3. **性质校验（primer 回归 · 必守）**：逐条审入门目标性质——**理解性/教学性**（说清/解释/区分/教方法 X 是什么、理解双面性、列出可观测信号）保留；**决策性**（复述 arena 分流结论/判断投资含义/给 stance/定 tier）**改写为理解性或剔除**。入门目标是"读懂这门生意"的能力，不是"做终局决策"的能力——终局贯穿到 K#/命门/case，但**不贯穿到 primer 入门目标**（终局豁免）。
4. **出定稿**：得到精修后的 **"本 topic 读完应能做到 N 条"清单**（N 通常 8-13，按领域复杂度）。把目标增删（added/dropped）记下，交 Step 4 / case 路径在 `decomposition_v1` 持久化 + 进 changelog（见 `_shared.md` §B 轴有界 delta 重拆——primer 目标 delta 与命门 delta 同一螺旋、同一收敛判定）。

> **O2 接线 · baseline_knowledge.md 是 primer 的训练知识种子**：00-research-topic Step 4.3 写的 baseline 是本 topic 第一层数据源（行业稳定知识 + 自评盲点）。primer 的"行业原理/技术分类/工艺/估值方法"等稳定知识层应**直接复用 baseline 第一节**，避免重新凭空回忆导致前后不一致。**但必须读 baseline §六 校准结果**（Step 4.5c 回写）——被 prescan 推翻的 fact **不准**再写进 primer，必须用校准后的新事实；被验证的可放心用。baseline 缺失（旧 topic）→ 退化为纯训练知识+findings，零特判。

每条必须是**门外人可观察的具体能力**（"能跟人解释 X / 能区分 Y 和 Z / 听到术语 W 知道在说什么 / 能读懂 V 的估值倍数含义"），不是知识罗列，**也不是决策**（"能判断 V 贵不贵/该不该投"是 case 的活，不入入门目标——见 Step 1 性质校验）。

**LLM 自行按 type 适配视角**（不要硬套，让模型读 type+scope 自己判断）：
- `industry` / `arena`（领域型）→ 目标偏"层层递进理解这门生意/技术/赛道本身"（科学原理 → 路线 → 产业链 → 玩家 → 争议）
- `company`（主体型）→ 目标偏"主体画像"（所处领域速写 → 是什么/做什么 → 怎么赚钱 → 竞争 → 财务 → 估值 → 争议 → 时点）
- **science-heavy company**（如创新药/硬科技单股）→ **混合**：先 industry 式铺科学背景，再 company 式讲主体（已验证：荣昌 primer 必须先讲清 ADC/双抗/审批流程才能讲公司）

把这份目标清单**贴到对话**（用户可判断"目标合理吗"），它同时是 Step 3 critic 的校验依据。

---

## Step 2：起点诊断 + 自由发挥撰写

### 2.1 起点诊断（写正文前必做，半模板，唯一强约束）

LLM 单轮自由发挥最易犯的错是**跳过"读者已知的最近概念"直接进主题**（如固态电池不从锂电池起手、直接讲 LPSC 离子电导率）。起点选错全篇崩，且 critic 救不回（要整篇重写）。所以写正文前**先输出一份 outline**：

1. **读者已知的最近概念**是什么？（固态电池→锂电池；Robinhood→零售券商；荣昌→"创新药是热门赛道"）
2. 从这个起点到 topic 主题，需要哪几步**知识阶梯**？（每步一句话，5-8 步）
3. 起点是大学通识级 / 行业入门级 / 更专？
4. 从 `display_name` + `scope.question` + `thesis` 抽出 **1-3 个本 topic 的"特色点"**，强制给独立章节（如荣昌"+锂金属"→金属锂独立章；荣昌横跨 ADC+自免→两条线分别讲）

outline 不用贴对话，但必须先在上下文成形再展开正文。

### 2.2 自由发挥（无章节模板）

按 Step 1 目标 + 2.1 outline 自由组织。长度不设上限，由"门外人应该知道什么"驱动（已验证样例 11000-15000 字，但**不是字数指标**——短而够也行，长而注水不行）。

参考已验证样例（few-shot，读其结构与深度，**不是抄章节**）：
- 硬科技 arena：`prism/topics/global-ssb-electrolyte/{variant}/outputs/00_primer.md`
- 单家金融公司：`prism/topics/us-robinhood/{variant}/outputs/00_primer.md`
- science-heavy 单股：`prism/topics/cn-rongchang-bio-688331/{variant}/outputs/00_primer.md`

写作硬规约（这几条是质量来源，不是章节）：
- **预设读者**：理工/金融背景但完全没碰过本领域。讲解语气，不是同行速记
- **首次出现锚定**：任何术语 / 缩写 / 化学式 / 化合物 / 病名 / 法案首次出现 = 中英全名 + 一句定义 + 类型归属。门外人 google 不到的内部黑话尤其要就地解释
- **类比**：核心概念尽量给具体类比（硫化锂≈光刻胶 / ADC≈生物导弹 / PFOF≈浏览器卖搜索流量）。类比是能力不是规则——写不出好类比时宁可多讲两句机制，不要硬塞牵强类比
- **横向对比表**：2 项以上并列概念（技术路线/竞品/产品线）尽量给表
- **`[训练知识展开]` 维度必给独立小节主动展开**：Step 1 认领的 `[训练知识展开]` 目标（无 findings、靠训练知识的机理/技术/估值方法），**每条一节写到教学满深**（机制怎么运转 + 类比 + 必要对比表），**不许因"无 findings"压成一句或塞进争议节脚注**——这是 findings-first primer 最常见的偏薄漏网口（现象：期权/估值/催化这类 findings 厚的节又厚又好，而技术原理/业务机制/竞争格局这类纯训练知识节薄带一句）
- **争议必现**：必有一节列 5-7 条尚未消解的根本争议 + 各方理由（不能假装确定）
- **自检清单结尾**：列"读完后读者应能做到的 N 条"（对应 Step 1 目标）

### 2.3 来源分层（强约束——忠实 prism 溯源规约）

primer 混合三种来源，**必须分层标注**，否则门外人会把"研究新发现"误当"行业常识"：

| 来源 | 标注方式 |
|------|---------|
| **LLM 训练知识**（行业原理/技术分类/工艺/审批流程/估值方法/政策框架/行业级玩家背景） | 不标单条出处；文末来源说明统一声明"行业稳定知识" |
| **本研究 findings**（具体数字/时间表/公司动态/价格/产能/财务/BD 条款） | 凡引用必标 `[mat-XXX]` 或 `(mat-XXX)` |
| **本研究特色判断**（thesis take、强度、特色叙事） | 文末点到 + 指向 thesis_v1 / case sidecar（07_decision_kit / 09 / 10），正文不展开重述 |

文末 `## 来源说明` 给三者大致占比 + 引用的 mat 列表（表格）。

### 2.4 depth 降级（稀有领域诚实标注，不假装深）

从 findings 覆盖度 + 你自己撰写时的把握判断 LLM 训练知识在本领域的厚度（primer-first 下 `01_business_panorama` 尚不存在，改据 findings 与训练知识自评）：

- **行业层训练知识厚**（固态电池、券商、创新药行业原理）→ 正常写，frontmatter `depth: deep`
- **行业层也薄**（训练截止后才热的领域 / 极冷门 arena）→ frontmatter 标 `depth: shallow` + 正文显式声明"本领域 LLM 训练知识有限，背景部分可靠性低，建议补充阅读 [外部资料]"，**不强行注水假装深**
- **已知模式：公司层薄但行业层厚是常态**（荣昌 primer：公司事实 ~10% 训练知识全靠 findings，但 ADC/审批/估值行业知识中等厚）→ 在来源说明里**显式说明这个分层可靠性结构**（行业背景可信 + 公司事实依赖 findings 标注）

> 📎 *稀有领域瓶颈在 findings 覆盖度（robinhood/荣昌验证）→ 附录 A2.4（执行时可跳过）*

### 2.5 配套生成 `_prism_reading_guide.md`（首次生成时）

prism 系统约定（mat-XXX / K# / R# / KILL / thesis 强度 / topic 类型 / 产出体系 / 阅读路径）是**跨 topic 通用**的，不混进 primer（primer 专注领域本身）。从 canonical 模板复制：

```bash
cp prism/workflows/_reading_guide_canonical.md prism/topics/{slug}/{variant}/outputs/_prism_reading_guide.md
```

若该 topic 有领域特有的 K# 含义想补，可在复制后追加一小节，但通用部分不改（保持一处维护）。

### 2.6 主 agent 直做，不 dispatch subagent 写

12000+ 字跨多产出整合，**主 agent 直接 Write**（同 _shared.md "主 agent 直做"原则 + feedback_subagent_bulk_synthesis）。唯一用 subagent 的地方是 Step 3 的 critic（只读不写、单份、有界）。

---

## Step 3：独立 critic 校验（核心质控，不可省）

primer 写完后**不能自检**（作者中心化偏见——验证里反复证明：作者看不到自己默认门外人懂的术语、看不到叙事失衡）。必须 dispatch 一个**独立 critic subagent 扮演门外人读者**，对照 Step 1 目标逐条判断。

### 3.1 dispatch critic（`subagent_type: general-purpose`，不传 model，只读不写）

critic prompt 模板（按 topic 填空）：

```
你被请来独立校验一份投资研究入门 primer 的质量。

## 你的角色
你是一个**完全门外的、为投资目的、正在研究 {display_name} 的读者**。知识画像：
- ✅ 懂股票/市值/PE 等投资常识
- ✅ 模糊听过 {topic 所属领域的大众认知}
- ❌ 完全不懂：{逐条列出本 topic 的核心术语/概念/缩写/玩家——从 Step 1 目标反推，列全}

你读这份 primer 的目的：搞清楚 {scope.question}

## 关键校验规则（必须严守）
严格基于 primer 文本本身判断"懂没懂"，**绝不能用 primer 之外的知识自行补上**。即便你（作为 LLM）知道答案，primer 没讲清就标"不够"。不做善意脑补。任务是捅破墙、找门外人会卡住的地方，不是粉饰。{若 science-heavy 领域，额外强调：术语极密，最容易"作者以为讲清了其实门外人懵了"，用最苛刻零基础标准}

## 你要校验的目标（逐条）
{粘贴 Step 1 生成的 N 条目标}

## 你要做的
1. 读 primer 全文：prism/topics/{slug}/{variant}/outputs/00_primer.md
2. 对每条目标逐条判断 [够] / [不够]；[不够] 必须具体引用哪段不清楚 / 漏讲什么 / 读完还有什么疑问，具体到段落或概念，不要笼统说"不够深"。**凡目标标 `[训练知识展开]` tag（应由训练知识写成独立小节、写到教学满深）——用最苛刻标准查它有没有真的独立成节展开；若只有一句话 / 塞在别节脚注 / 只在争议节露脸 = 直接判 [不够]，这是本系统偏薄的首要漏网口，务必点名**
3. 三段总评：① 总体能不能用（门外人读完能聊半小时不露怯吗？）② 最大 2-3 个问题（按严重度）③ 只能补一处该补什么

简洁直接不客气。够的 1 行说够，不够的说清。控制 1800 字内。
```

### 3.2 按 critic 反馈修订（主 agent 直接 Edit）

- critic 标 [不够] 的逐条修。区分两类：
  - **写作问题**（术语没解释/起点错/叙事失衡/类比缺）→ 直接补写
  - **数据缺口**（市场规模/估值拆解 findings 没有）→ 能训练知识粗估则标注补，补不了则明写"数据缺失"（见 2.4）
- 修完**判断是否需要第二轮 critic**：已验证 2 轮内收敛（首轮多个 [不够] → 一轮修复后仅剩 1-2 个轻微/数据类）。若首轮问题多或涉及起点错，跑第二轮确认收敛；若首轮只剩轻微问题，可直接交付不再 critic。

> 📎 *critic 收敛速度实例 → 附录 A3.2（执行时可跳过）*

---

## Step 4：写入文件 + 状态注册

frontmatter 规范：

```markdown
---
slug: {slug}
output_key: 00_primer
version: {N}
type: domain-primer
audience: 完全外行（{一句话描述读者起点}）
generated: {timestamp}
depth: deep | shallow
sources_note: 主体（{领域原理范围}）来自 LLM 训练知识，截止 2025 年中；具体数据凡引用 findings 均标 [mat-XXX]
prereq: 无（本篇即前置）
companion: _prism_reading_guide.md
---
```

状态注册（同其他产出）：

> ⚠️ **顺序硬要求（F17 机械门禁）**：`depth: deep` 的 primer 注册前**必须先调 `set_output_critic_passed`**（Step 3 critic 收敛的机械凭证），且正文须含**争议节 + 自检清单节**、字数过 deep 地板。否则 `set_output_status('00_primer','fresh')` 会被门禁**自动降级为 `draft`** 并在 `outputs_state.00_primer.primer_gate.warnings` 记原因——dashboard 显示 draft 而非 fresh。这是把"critic 不可省 + 不许 outline 假冒 deep"从文档约定落成跑不过就降级的机械闸门。depth=shallow 不设字数地板（诚实标浅）。

```bash
python3 -c "
from prism.scripts.topic import (set_output_referenced_mats, set_output_status,
                                  set_output_critic_passed, primer_quality_gate, read_topic)
# 1. critic 已收敛 → 先置机械凭证（deep 必需；shallow 也建议置）
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

---

## Step 5：汇报

```
✅ 领域入门已生成 → 00_primer v{N}（depth={deep/shallow}）
   配套 _prism_reading_guide.md（prism 系统约定）

Web 查看：http://localhost:8000/prism/{slug}/{variant}/output/00_primer

Step 1 目标：{N} 条门外人能力清单
critic 校验：{轮数} 轮收敛，剩余 {0/轻微数据缺口}
{若 depth=shallow：⚠️ 本领域训练知识有限，背景部分可靠性低，已标注建议外部补读}
```

---

## 附录 A — rationale / 反例 / 历史教训（执行时可跳过，调试 / 维护时查）

> 本附录收纳从各步主流程搬出的"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"。**主流程逐字未删、只是移出执行动线**；要看某步的来龙去脉，按对应小节查。

### 附录 A2.4 — 稀有领域瓶颈在 findings 覆盖度（robinhood/荣昌验证）

> **关键洞察（来自 robinhood/荣昌验证）**：稀有领域的瓶颈往往**不在 LLM 写作能力，而在 findings 数据覆盖度**。critic 反馈里"市场规模缺/估值拆解黑箱"这类问题，多数是底层资料没挖到，不是 primer 写不出。遇到这种缺口：能用训练知识粗估的标注"训练知识估算、非 findings"补上；补不了的明写"此处数据缺失，研究产出未覆盖"，不编造。

### 附录 A3.2 — critic 收敛速度实例

> 已验证收敛速度：robinhood 首轮 4 [不够]+多个小问题 → 修一轮 → 二轮仅剩 1 中等（作者引入的口径 bug）+1 轻微。荣昌首轮即"高于平均"，3 个问题全是数据缺口类，修一轮即可。
