# Workflow 00 — 开启新研究主题

**触发**：用户说「研究 X」或「开始研究 X」  
**产出**：创建 `prism/topics/{slug}/topic.yaml` + `manifest.yaml`，Web 页面 /prism/{slug} 可访问

---

## Step 1：确认研究对象

向用户确认以下信息（如果用户没说清楚则 AskUserQuestion）：

1. **研究对象名称**（中文，例如「中国宠物行业」「中国商业航天」「宁德时代」）
2. **研究类型**（industry / arena / company）
   - industry：整个行业（宠物、储能、机器人）
   - arena：细分竞技场（宠物食品、人形机器人执行器）
   - company：单家公司
3. **核心研究问题**（例如「中国宠物行业哪些细分赛道值得投资」）
4. **研究深度**（quick = 1-2 天 / standard = 1 周 / deep = 持续跟踪）
5. **地理范围**（CN / US / GLOBAL）

如果用户直接说「研究中国宠物行业」，可以推断：type=industry, geo=CN，然后只确认研究问题和深度。

**重要**：如果用户没有明确说地域（如「研究AI算力基础设施行业」），不得默认 CN，必须将地理范围列入 AskUserQuestion 让用户选择。

同时需要确认当前使用的 LLM 模型变体名称（如 `gemini`、`gpt-4o` 等），后续将作为 `variant` 参数使用。默认可使用当前调用的模型名称。

**如果是 company 类型，必须确认 ticker**（格式：`{market}_{code}`，如 `SZSE_000426`、`SSE_600519`、`US_AAPL`）。ticker 用于生成行情/财务页面链接。

---

## Step 2：生成 slug

slug 规则：
- 全小写，连字符分隔
- 格式：`{geo}-{keywords}`
- 示例：`cn-pet-industry`、`cn-commercial-space`、`cn-catl`
- 不超过 30 字符

在对话里显示 slug，等用户确认或修改。

---

## Step 3：检查是否已存在

```bash
ls prism/topics/ 2>/dev/null
```

如果已有同名 slug，告知用户并询问：
- 继续已有研究并在原变体目录下推进（运行 workflow 推进）
- 在当前 slug 下使用不同模型创建一个新变体目录（如 `gemini`、`qwen3.6-plus`）
- 还是创建全新研究（slug 加后缀，如 `cn-pet-industry-2`）

---

## Step 4：创建 topic

```bash
python3 -c "
from prism.scripts.topic import create_topic
create_topic(
    slug='{slug}',
    display_name='{display_name}',
    topic_type='{type}',
    question='{question}',
    geo='{geo}',
    depth='{depth}',
    variant='{variant}',
)
print('创建成功')
"
```

```bash
python3 -c "
from prism.scripts.manifest import create_manifest
create_manifest('{slug}', '{variant}')
print('manifest 创建成功')
"
```

---

## Step 4.3：写训练知识 baseline（**新增 — 必跑**）

**为什么必须做**：训练知识是研究的第一层数据源（web-search 第二层、用户兜底第三层）。先把"训练时记得什么"显式写下来，后续每条 web-search hit 都能对照"我有的 vs 新拿到的差在哪"。同时这份 baseline 是 Step 4.5 prescan 的种子——盲点列表直接转成 prescan 优先 query。

**执行**：参 `prism/workflows/_baseline_knowledge.md` 模版，让 LLM（即当前主 agent）写一份 `prism/topics/{slug}/{variant}/baseline_knowledge.md`，五段结构：

1. 关键事实记忆（含数字/时间/主体 + 置信度 高/中/低/uncertain）
2. 关键人物 / 公司 / 产品
3. 产业链 / 竞争格局认知
4. **训练知识盲点（自我承认）** — 直接喂 Step 4.5 prescan
5. 需要 web-search 校准的优先项

```bash
# 主 agent 用 Write 工具落盘 baseline_knowledge.md
# 落盘后调脚本核实
python3 -c "
from prism.scripts.topic import has_baseline_knowledge
print('baseline 已落盘:', has_baseline_knowledge('{slug}', '{variant}'))
"
```

**例外可跳过**：concept 类 topic（纯方法论）；用户明确说"不需要 baseline"。company / industry / arena 默认必跑。

**纪律**：
- 自评置信度保守（uncertain 优于编造）
- 第四节的盲点列表直接喂给 Step 4.5 prescan 作为优先 query
- 后续 03/04 引用训练知识时 cite `baseline_knowledge.md` 的 `[fact-NN]` 编号

---

## Step 4.5：Web Pre-scan（必跑 — 校准训练知识与最新现实）

**为什么必须做**：LLM 训练截止与当前时间往往有几个月到一年的差距，对**时效性强的标的**（公司财报/政策动态/股价估值/突发事件），跳过 prescan 直接靠训练知识写 thesis_v0 会把过时事实当成"初判赌注"，导致 K# 设错、user_todos 攻打错方向、后续整轮研究偏航。

**执行**：调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。

注意：此时 thesis 还不存在，`build_search_queries` 仅会生成 **scope + company-event / industry-event / concept-update** 系列查询（不含 K#-derived），这是预期的——本轮目的是为"写出靠谱的 thesis_v0"打地基，K# 类查询留给 workflow 01 prescan。

跑完后输出汇报模板：
```
✅ 00-prescan 完成：N 条查询 → 高/中/低 X/Y/Z → 入库 X+Y 份
关键事实更新：
  - {对 thesis 影响最大的 2-3 条新事实}
```

**例外可以跳过 prescan**：concept 类 topic（纯方法论/历史回顾，与近期事件无关）；用户明确说"用你脑子里的知识就行"。**company / industry / arena 默认必跑**。

---

## Step 5：基于训练知识 + prescan 数据做初步定向

**注意**：相较旧版"100% 训练知识"，本步要求把 Step 4.5 入库的 web-search 资料（manifest 里的 web-search source_type 条目）作为事实校准源；训练知识做"框架/逻辑/远期判断"，prescan 数据做"近 90 天事实/财务/监管/价格"。

产出以下**四部分**：5.0 thesis 表态写文件，5.1/5.2/5.3 直接在对话里输出。

### 5.0 LLM 初判 thesis（强制 — thesis-driven 研究的起点）

**目的**：让 LLM 在 Step 4.5 prescan 数据校准之后、阅读卖方深度研报之前先把"赌注"押下，后续所有研究都是去验证或推翻这个 thesis。
避免研究变成"百科全书式覆盖"，强制每条资料都要回答"这支持还是推翻我的初判？"

**硬约束**：
- thesis 里的财务数字（收入/EPS/PE/股价/AUM）必须引用 Step 4.5 入库的 web-search 资料中的数据，不得用训练时记忆数字
- 在 frontmatter 加 `revised_after_prescan: true` 标记
- `data_freshness` 字段写明"训练知识截止 YYYY-MM + workflow 00 web-prescan（含 XX 数据）"

**要求**：写一份 `prism/topics/{slug}/{variant}/thesis_v0.md`，必须包含以下五段（每段都要写，不能跳过）：

1. **核心 thesis**：一句话（≤80 字）+ 强度评分（0-10 分，0=完全看空，10=All-in 看好）
   - 必须有方向（看多 / 看空 / 中性 / 分化看法），不能写"取决于"
   - 如果是分化看法，明确说"看好 X，看空 Y"
2. **支持理由**（3-5 条）：每条一句话，给出 LLM 现在最相信的判断依据
3. **最大反方观点**（2-3 条）：诚实列出最有力的反方逻辑——不是稻草人
4. **会改变看法的事件 / Killer Question**（3-5 条）：必须是**可观测、可证伪**的具体事件
   - 反例："如果技术失败" ✗
   - 正例："任一头部车厂将全固态 SOP 时间从 2027-2028 推迟到 2030+" ✓
5. **研究中重点验证项**（3-5 条）：把支持理由 + 反方观点 + Killer Question 转成具体待查清单，引导后续 workflow 01 的路线图

写完 `thesis_v0.md` 后，调脚本登记到 topic.yaml：

```bash
python3 -c "
from prism.scripts.topic import set_thesis
set_thesis(
    slug='{slug}',
    variant='{variant}',
    version=0,
    summary='{一句话核心thesis，≤120字，用于yaml/web展示}',
    stage_set_at='01-roadmap-pending',
)
"
```

**Coverage 闭环（必须做）**：写完 thesis_v0.md + todos 后，做一次 self-check：
- 列出 thesis 里所有 Killer Question（K1, K2, ...）
- 检查每个 K# 是否至少有一个 todo 的 `addresses` 引用了它
- 如果有 K# 无 todo 攻打（uncovered），二选一：
  1. **补一个 todo 攻打它**（推荐）
  2. **在 thesis 中显式标注 "本次研究不验证此 K，理由是 ..."**（节约精力，但要写出来）

Web 端会在详情页 thesis 卡片下显示 `K1✓ K2✓ K3✗ K4✓ K5✗` coverage strip，红色 = 未覆盖。看到红色就必须处理，不能假装看不见。

**后续何时更新 thesis**：
- workflow 04 合成完成后写 `thesis_v1.md`（基于资料修正）
- workflow 05 critic 评审后若有重大反转写 `thesis_v2.md`
- workflow 07 drilldown 后或 workflow 99 决策记录前写新版本
- 每次 set_thesis 都 append 到 history，不删除旧版本——保留判断演化轨迹

**v1 起的写作约定（方案 C 全快照）**：thesis_v0 是天然全快照（五段式，无 parent）；从 v1 起所有 thesis 必须是"全快照 + 顶部 changelog"格式，本版自包含、不依赖历代章节。详见 `prism/workflows/04-synthesize/_shared.md` § "Scheme C 写作约定"。

### 5.1 领域概览（3-5 句话）
- 这个行业/赛道/公司是什么
- 当前处于什么发展阶段
- 市场规模量级

### 5.2 关键研究维度（5-8 个问题）
列出要深度研究这个主题，最关键的 5-8 个问题。例如：
- 谁是核心受益者，谁是受损方？
- 增长的核心驱动力是什么，是结构性还是周期性？
- 当前市场共识是什么，哪里可能有分歧？
- 风险清单里最容易被低估的是什么？
- 有哪些历史类比案例？

### 5.3 资料获取建议（用户需要收集什么）

按 **优先级（P0/P1/P2）+ 信息差等级（public/half_public/hard）** 列出 5-10 份关键资料。**每条 todo 都必须标注 addresses**——指向 5.2 的问题号（Q1-Q8）或 5.0 thesis 的 Killer Question 号（K1-K5）——否则失去 thesis-driven 意义。

**信息差等级定义**：
- `public` 公开普及 — Google/Wind 一搜就有，价值低（但作为研究起点）
- `half_public` 半公开 — 需登录/付费/外文/拼凑，是 alpha 主要来源
- `hard` 难获取 — 专家访谈/产业链调研/圈内信息，价值最高但收集成本大

**优先级原则**：
- P0 = 缺了它整个研究无法推进的（约 3-5 项）
- P1 = 重要补充，影响 thesis 强度但不影响方向（约 3-5 项）
- P2 = 锦上添花，等核心研究完后补（不超过 3 项）

每条 todo 必填字段：`task` / `priority` / `info_tier` / `addresses`，选填 `source_hint`。

---

## Step 6：更新 topic 状态

**user_todos 必须用 dict 结构**（不能再写 list[str]）。示例：

```bash
python3 << 'EOF'
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
slug = '{slug}'
variant = '{variant}'
set_stage(slug, '01-roadmap-pending', variant)
set_next_actions(slug, [
    '运行 workflow 01-build-roadmap：制定详细研究路线图',
    '收集 P0 资料后运行 workflow 02-gather-materials',
], variant)
set_user_todos(slug, [
    {
        'task': '下载头部车厂全固态 SOP 时间表声明（IR/技术发布会）',
        'priority': 'P0',
        'info_tier': 'half_public',
        'addresses': ['Q1', 'K1'],
        'source_hint': '公司 IR 网站，需英日文阅读',
    },
    {
        'task': '下载3份对比卖方深度报告（中信建投/中金/申万任选3家）',
        'priority': 'P0',
        'info_tier': 'public',
        'addresses': ['Q3', 'Q6'],
        'source_hint': '同花顺/Wind/卖方公众号',
    },
    # ... 更多 todo
], variant)
EOF
```

字段约束（由 `_normalize_todo` 校验，不合规会直接 raise）：
- `priority`: P0 / P1 / P2
- `info_tier`: public / half_public / hard
- `addresses`: list[str]，元素如 `Q1`（5.2 问题号）或 `K1`（thesis Killer Question 号）
- `status`: pending / in_progress / done（缺省 pending）

---

## Step 7：告知用户

输出：
```
✅ 研究主题「{display_name}」已创建

Slug: {slug}
变体目录: prism/topics/{slug}/{variant}/
Web 地址: http://localhost:8000/prism/{slug}/{variant}/

下一步：
1. 在对话里说「prism 推进 {slug}」继续制定研究路线图
2. 或者先收集资料放入 prism/inbox/manual/ 后说「prism 推进 {slug}」

你需要做的事：
{user_todos_list}
```
