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

**如果是 company 类型，必须确认 ticker**（格式：`{market}_{code}`，如 `SZSE_000426`、`SSE_600519`、`HKEX_09995`、`US_AAPL`）。ticker 用于生成行情/财务页面链接。**company 漏传 ticker 会被 `create_topic` 直接 raise**（修 H1）。

**display_name 与 short_name 分离**（修 H3 v2）：`display_name` 用于 UI 展示（可长，含 ticker 和英文名）；`short_name` 用于 WebSearch 查询（≤12 字，纯主体名）。
- company 类型 **必填 `short_name`**（脚本 raise）；industry/arena 可选（不填走 display_name 兜底）
- 例：`display_name='荣昌生物 (RemeGen, SSE 688331)'` (30 字 UI 友好) → `short_name='荣昌生物'` (4 字 搜索友好)
- 例：`display_name='阿里巴巴 (BABA, HKEX 09988)'` → `short_name='阿里巴巴'`

**长 question 必须同步给 `search_terms`**（修 H3 v2）：当 `question` 超 25 字（典型如生物医药/科技/复合产业的 deep 类研究），**必填** `search_terms: list[str]` — 2-4 个 WebSearch 友好的核心关键词，每项 ≤15 字。
- 例：`question='荣昌生物作为中国领先的ADC+自免双管线创新药企业，全维度覆盖：商业化兑现节奏、海外授权回流'` → `search_terms=['ADC 商业化', 'BD 海外授权', 'IgAN 管线']`
- 脚本不做关键词提取（标点截断常切到非核心名词反而误导）—— 长 question 漏给 search_terms 会**直接 raise** 引导主 agent 显式提炼
- 这些关键词会进入 `build_search_queries` 的 `scope` / `l4-hunting` 覆盖槽 hint，作为主 agent 写 query 的核心原料（脚本只给 hint，不代写 query）

**多市场上市（AH 双重 / ADR / 多重上市）必须确认 `extra_tickers`**（list[str]，主代码以外的所有同公司代码）：
- 荣昌生物 A+H：`ticker='SSE_688331', extra_tickers=['HKEX_09995']`
- 阿里巴巴 H+ADR：`ticker='HKEX_09988', extra_tickers=['NYSE_BABA']`
- 中芯国际 A+H：`ticker='SSE_688981', extra_tickers=['HKEX_00981']`
- 漏填 = 后续 06-daily-monitor 拿不到第二市场资金/估值/公告 → thesis 写"AH 折溢价"时无结构化字段（修 M1）

---

## Step 2：生成 slug

slug 规则：
- 全小写，连字符分隔
- 格式：`{geo}-{keywords}`
- 示例：`cn-pet-industry`、`cn-commercial-space`、`cn-catl`
- 不超过 30 字符

在对话里显示 slug，等用户确认或修改。

---

## Step 3：检查是否已存在（结构化查重，勿凭 `ls` 肉眼判断）

```bash
python3 -c "from prism.scripts.topic import list_variants; print(list_variants('{slug}'))"
```

- 返回 `[]` → 全新 slug，直接进 Step 4。
- 返回非空（如 `['claude-opus-4-7']`）→ slug 已存在其他变体，**这是一个意图分叉点，必须停下问用户**（不能自行默认走某条）：
  - **续做**旧变体：不 create，读对应 `topic.yaml` 判 stage → 跳转对应 workflow 推进。
  - **换模型/换架构重研**（新变体）：进 Step 4 用新 variant 名创建（**变体名以 `model_registry` 规范名为准**——opus 4.8 规范名是短名 `opus4.8`，其余模型用全 model-id 式如 `claude-opus-4-7`；传别名脚本会自动归一；历史分裂目录不迁移，靠 `model_registry` 别名表运行时识别）。建后按"新变体复用旧料"流程：
    - **重注册 materials**——机械抽取层（年报 `_extracted.md` / 研报 `_vlm/`）是 slug 级共享、命中即跳过，**不重转 PDF**。复用**排除 prescan 校准层**（`addresses==['scope']` 或 `triggered_by` 为 `*-prescan*` 的 web-search 料：价/量/事件快照，时效性强，机械搬运会把过时事实当新赌注，违 `feedback_thesis_after_prescan`）；带 `K#` addresses 的**耐久文档**（财报/研报/drilldown/findings 源 + web-search 挖到的实质文档，validity 锚在出版日）照复用。**新变体一律自跑 prescan**（Step 4.5；复用模式会因本轮 0 注册误报 + prescan URL 不可构造，见 `project_variant_reuse_gotchas` 坑③④）。
    - **findings 必须本变体重抽（走 03）**，禁止复制旧变体的 `findings_mat-*.md`。findings 是"本变体 thesis 的 K# 解读"，按变体隔离；复制旧变体 findings 会①污染"苹果对苹果"模型对比（等于让新模型抄旧模型的解读）、②引发 mat_id churn（编号脱钩）。换模型的价值正在于让新模型自己读料、自己解读。
    - **`set_parent_materials` 引父级 findings** 仍合法——那是**跨 topic 父子复用**（行业父→竞技场子），与"同 slug 跨变体复制"是两回事。省略 `parent_variant` 时脚本按 `model_registry` 兜底解析（同模型/唯一/全登记自动选，多个异模型含未登记则 raise 让你问用户）。
    - 复用同一批 materials 可隔离变量、让模型/架构差异苹果对苹果对比（详见 memory `project_variant_reuse_gotchas`）。
  - **另一个 topic 撞名**：slug 加后缀（如 `cn-pet-industry-2`）另起。

> 兜底（[skill-routing]）：即便跳过本步直奔 Step 4，`create_topic` 在 slug 已有其他变体时会打 stderr 提示——但那是最后一道防线，本步的"停下问用户"才是正解，勿依赖兜底跳步。

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
    # company 类型必填 ticker（H1）；industry / arena / concept 不填
    ticker='{ticker_or_None}',          # e.g. 'SSE_688331' / 'HKEX_09995' / 'US_AAPL'
    # AH 双重 / ADR / 多重上市必填（M1）；单市场或非 company 留 None
    extra_tickers={extra_tickers_or_None},  # e.g. ['HKEX_09995'] / ['NYSE_BABA'] / None
    # company 必填 / industry/arena 可选（H3 v2）；≤12 字，纯主体名（搜索查询用）
    short_name='{short_name}',  # e.g. '荣昌生物'（display_name 通常含 ticker/英文名 不能直接搜）
    # question 超 25 字时必填（H3 v2）；脚本不做关键词提取，长 question 漏填会 raise
    search_terms={search_terms_or_None},  # e.g. ['ADC 商业化', 'BD 海外授权', 'IgAN 管线'] / None
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

### Step 4.0：早期 ingest — 登记 topic 家底元数据（**新增 — 必跑**）

**为什么**：用户常在开研前把已有料（年报/研报/笔记）放进 `prism/topics/{slug}/inbox/`。若不在这里先登记，manifest 一直是空壳 → 00/01「建 todo 前查重」无家底可查 → 重复建已满足的 todo、重复 web-search。早期 ingest 让"建前查重"从 00 即生效。资料只在 topic 层（无全局 inbox）。

```bash
python3 -c "
from prism.scripts.manifest import register_inbox_materials
reg = register_inbox_materials('{slug}', '{variant}')
print(f'早期 ingest 登记 {len(reg)} 份家底：')
for r in reg: print(' ', r['filename'], '->', r['source_type'])
"
```

> **红线（保 bet-first）**：本步**只登记元数据**（文件名/扩展名粗判 source_type，零正文读取），**不读正文、不进 thesis_v0**——thesis 仍是读深度材料前的赌注，正文抽取留 03。
> **复核**：扫一眼返回清单，若年报/财报被误判（如某 PDF 标成 `sell-side-note` 实为年报），主 agent 用 `remove_material` + `add_material` 改 `source_type='annual-report'`（走 annual_report_extractor 不走 mineru）。
> **增量幂等**：本步是第一遍；用户本轮中途交付的料仍会在 02 / "推进 {slug}" 时被同一 helper 重扫登记（已登记的跳过）。

---

## Step 4.3：写训练知识 baseline（**新增 — 必跑**）

**为什么必须做**：训练知识是研究的第一层数据源（web-search 第二层、用户兜底第三层）。先把"训练时记得什么"显式写下来，后续每条 web-search hit 都能对照"我有的 vs 新拿到的差在哪"。同时这份 baseline 是 Step 4.5a 优先 query 的来源——第四节盲点 → 第五节精准 query → Step 4.5a 主 agent 逐条 WebSearch 入库。

**执行**：参 `prism/workflows/_baseline_knowledge.md` 模版，让 LLM（即当前主 agent）写一份 `prism/topics/{slug}/{variant}/baseline_knowledge.md`，五段结构（第六节 4.5c 回写时再加）：

1. 关键事实记忆（含数字/时间/主体 + 置信度 高/中/低/uncertain）
2. 关键人物 / 公司 / 产品
3. 产业链 / 竞争格局认知
4. **训练知识盲点（自我承认）** — 第五节 query 的种子
5. **需要 web-search 校准的优先项** — 必须是精准、可执行的 query 串（不是话题），Step 4.5a 会逐条跑

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
- 第四节盲点 → 第五节精准 query（如"特斯拉 4680 电池 2026Q1 量产爬坡进度"，不是"电池技术进展"这种话题描述）
- Step 4.5a 会**逐条**把第五节 query 跑 WebSearch + 入库——第五节漏写优先项 = prescan 漏校准 → thesis_v0 押过时赌注
- 后续 03/04 引用训练知识时 cite `baseline_knowledge.md` 的 `[fact-NN]` 编号
- 引用第六节标"被推翻"的 fact 时**必须改 cite 新 mat_id**

---

## Step 4.5：Web Pre-scan（必跑 — 校准训练知识与最新现实）

> **Web 搜索路径**：本步走 **adapter**（详见 [[_web_search_routing]]）。
>
> ```bash
> python3 -m prism.scripts.web_search search "<query>" \
>     --intent news --days 90 \
>     --max-results 5 --output sidecar \
>     --slug <slug> --variant <variant> \
>     --triggered-by 00-prescan-baseline \
>     --addresses scope
> ```
>
> **sidecar 模式只写 raw 不入库**（2026-05-28 修法）：上面命令会把 raw hit 写到 `prism/topics/{slug}/inbox/_websearch_raw/{ts}_{qhash}.json`，**不**调 register。主 agent 用 `review-digest` 看 index 判 tier（勿 Read 整 json，见 `_web_prescan_shared.md` Step C）→ 调 `register_web_search_batch` 入库。
> 退出码 40（all_exhausted）→ WebSearch tool fallback，再用 `postprocess` 子命令兜回 sidecar（postprocess 自动调 register），详见 [[_web_search_routing]] §双向 Fallback。
>
> domain_tier 由主 agent 在 H2 救回流程里判（参 `_web_prescan_shared.md` Step C），adapter 不预判权威源。

**为什么必须做**：LLM 训练截止与当前时间往往有几个月到一年的差距，对**时效性强的标的**（公司财报/政策动态/股价估值/突发事件），跳过 prescan 直接靠训练知识写 thesis_v0 会把过时事实当成"初判赌注"，导致 K# 设错、user_todos 攻打错方向、后续整轮研究偏航。

**执行三段：先跑 baseline 优先 query → 再跑覆盖槽 prescan（`build_search_queries` 清单逐槽写 query）→ 回写 baseline 校准结果。三段都做完才进 Step 5。**

### Step 4.5a：先跑 baseline 第五节的优先 query（**修 M4 + ISSUE-001**）

`build_search_queries` 只枚举 scope + 事件 + L4 的**覆盖槽**（给 hint，不代写 query），**且不读 baseline_knowledge.md**——主 agent 在 Step 4.3 baseline 第五节写的"自评盲点 → 想精准查的 query"必须在这一步手动落地，否则等于白写。

```bash
# 1. 读 baseline 第五节
sed -n '/## 五、需要 web-search 校准的优先项/,/^##/p' prism/topics/{slug}/{variant}/baseline_knowledge.md
```

主 agent 对每条优先 query 按 `_web_prescan_shared.md` Step B.1 并发限流规约跑：
1. **5 并发一批 + 批间 10s**（不要一次 message 里塞 10 个 WebSearch 并行，会触发**静默**限流）
2. 调 `register_web_search_batch(triggered_by='00-prescan-baseline', ...)`，**显式读返回的 `failure_mode`**（'upstream_empty' / 'all_low_band' / 'none'）
3. ≥3 条 `failure_mode='upstream_empty'` → 等 30s 串行重试这些 query（30s 一条）；`'all_low_band'` 走 H2 救回不是重试
4. 串行重试仍多数 upstream_empty → 转 _web_prescan_shared.md Step B.2 兜底（WebFetch 已知权威 URL）

```python
from prism.scripts.web_prescan import register_web_search_batch
r = register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='baseline 第五节优先项的具体 query',
    addresses=['scope'],  # 此阶段还无 K#，先用 scope 占位
    triggered_by='00-prescan-baseline',
    hits=[...],
)
if r['failure_mode'] == 'upstream_empty':
    # 真的限流——等 30s 串行重试本 query；连 3 个转 B.2 兜底
    ...
elif r['failure_mode'] == 'all_low_band':
    # 非限流，H2 救回未启动——extract_url_features + LLM 判 tier + 二次 register
    ...
```

**纪律**：第五节 5-10 条优先 query 全部尝试完才进 4.5b。漏跑等于主 agent 自评的盲点没补，thesis_v0 会基于过时认知做赌注。WebSearch 长时不可用时按 B.2 降级，**不允许默默跳过**——脚本会通过 Step 5.0 的 `check_prescan_health` 自动检测并触发 `prescan_status='failed'`。

### Step 4.5b：跑覆盖槽 prescan

调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。

注意：此时 thesis 还不存在、roadmap 尚无 L4，`build_search_queries` 仅会枚举 **scope + company-event / industry-event / concept-update** 覆盖槽（无 l4-hunting 槽），这是预期的——本轮目的是为"写出靠谱的 thesis_v0"打地基，K# 类覆盖留给 workflow 01 prescan。逐槽 query 措辞按 `_web_prescan_shared.md` Step A 由主 agent 写。

跑完后输出汇报模板：
```
✅ 00-prescan 完成：
  - 4.5a baseline 优先 query：M 条 → 入库 M' 份
  - 4.5b 默认模板 prescan：N 条 → 高/中/低 X/Y/Z → 入库 X+Y 份
关键事实更新：
  - {对 thesis 影响最大的 2-3 条新事实}
```

### Step 4.5c：回写 baseline 校准结果（**修 M4**）

跑完 4.5a + 4.5b 后，主 agent 扫一遍刚入库的 web-search material，对照 baseline 第一节的 fact-NN，把被推翻 / 被验证的条目记下来，**追加到 baseline_knowledge.md 末尾**（Edit 工具）：

```markdown
## 六、prescan 校准结果（{iso_ts} 回写）

> Step 4.5 prescan 入库 N 份 web-search material 后，对照第一节 fact-NN 的更新：

### 被推翻（高优先级——thesis_v0 不要再引用原 fact）
- `[fact-03]` 训练时"2024 EV 销量 1450 万"，被 `[mat-xxxx]` 推翻：实际 1520 万 → 误差 4.8%
- `[fact-07]` 训练时"公司 PE 18x"，被 `[mat-yyyy]` 更新：当前 28x → 估值认知必须重置

### 被验证（可继续引用，置信度提升）
- `[fact-01]` 2024 全球 EV 1450 万 → `[mat-zzzz]` 一致，置信度 高 → 高+

### 仍未校准（thesis_v0 引用时标 uncertain）
- `[fact-NN]` ...
```

**纪律**：
- 这一步是 LLM 判断（不是脚本能做的），主 agent 必须**逐条扫**，不要漏
- 若某 fact 在第六节标"被推翻" → Step 5.0 写 thesis_v0 时**不准**继续 cite 原 fact，必须改 cite 新 mat_id
- 该回写让 03/04/05 后续 cite baseline 时一眼看到哪些 fact 已经过时

---

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

**要求**：写一份 `prism/topics/{slug}/{variant}/thesis_v0.md`，必须包含以下四段（每段都要写，不能跳过）：

1. **核心 thesis**：一句话（≤80 字）+ 强度评分（0-10 分，0=完全看空，10=All-in 看好）
   - 必须有方向（看多 / 看空 / 中性 / 分化看法），不能写"取决于"
   - 如果是分化看法，明确说"看好 X，看空 Y"
2. **支持理由**（3-5 条）：每条一句话，给出 LLM 现在最相信的判断依据
3. **最大反方观点**（2-3 条）：诚实列出最有力的反方逻辑——不是稻草人
4. **会改变看法的事件 / Killer Question**（3-5 条）：必须是**可观测、可证伪**的具体事件
   - 反例："如果技术失败" ✗
   - 正例："任一头部车厂将全固态 SOP 时间从 2027-2028 推迟到 2030+" ✓

**不再单列"研究中重点验证项 V#" 段** —— V# 本质是 K#/Q# 的派生细化，作用是引导 workflow 01 路线图，但与 user_todos 重复。改为：**user_todos 直接承担验证项角色**，每条 todo 的 `addresses=[K#]` 标明它在攻打哪个论证目标（在 Step 5.3 体现；Q# 已降级，新 topic 不再用）。这样 thesis 收敛为 4 段，K# 覆盖闭环 self-check 矩阵保持二维（K × todo），不引入 V# 第三维。

写完 `thesis_v0.md` 后，**先跑 prescan 健康度检查**再登记 thesis（**修 ISSUE-001**）：

```bash
python3 << 'EOF'
from prism.scripts.web_prescan import check_prescan_health
from prism.scripts.topic import set_thesis

# 1. 检查 prescan 健康度：expected_queries = baseline 第五节优先 query 实际条数
h = check_prescan_health('{slug}', '{variant}',
                          expected_queries={n_priority_queries},
                          triggered_by_prefix='00-prescan')
print('prescan health:', h)
# {'status': 'full'/'partial'/'failed', 'queries_run': N, 'queries_with_hits': M,
#  'hit_rate': float, 'failure_reason': str|None}

# 2. 登记 thesis（脚本会按 status 自动校验）
set_thesis(
    slug='{slug}',
    variant='{variant}',
    version=0,
    summary='{一句话核心thesis，≤120字，用于yaml/web展示}',
    stage_set_at='01-roadmap-pending',
    prescan_status=h['status'],                    # 'full'/'partial'/'failed'
    prescan_failure_reason=h['failure_reason'],    # None 或一句话原因
    force_failed=(h['status'] == 'failed'),        # failed 必须显式 force（主 agent 承认接受赌注）
)
EOF
```

### 5.0a backfill（**仅当 prescan 材料用 fact-NN 标注时适用 —— 默认 scope 约定下跳过**）

> ⚠️ **适用前提（F2 订正）**：本步仅在 prescan 阶段（4.5a/adapter）把 web 材料 addresses 标成 baseline 事实编号 `fact-NN`（或 Q#）时才有意义。**当前默认约定（4.5a register 示例 + adapter `--addresses scope`）用的是 `scope`**——此时 `backfill_addresses_by_mapping` 没有 fact-NN 可重映，`updated_count` 恒为 0，本步是 no-op，**直接跳过**。
>
> 且 `scope` 本就不计入 K# 覆盖（addresses 三态表 scope=✗），所以漏跑**不会**让 gap_detector"误报 K# 全 0"——K# 覆盖实际来自 02/03 收的真材料（addresses 标 K#/Q#），与本步无关。
>
> **何时真要跑**：你显式改了 prescan 让命中按 `fact-NN` 标 addresses（想让 prescan 料也进 K# 覆盖），thesis 写完后才需要下面这段把 fact-NN → K# 重映。

```python
from prism.scripts.manifest import backfill_addresses_by_mapping

# 主 agent 写 thesis_v0 时已知道每个 K# 的论据来自哪些 fact-NN
# （baseline_knowledge.md 第二/三节列出了 fact-NN 内容，第六节有部分校准）
mapping = {
    # 'fact-04': ['K3'],          # 例：RC48 适应症 → K3 (RC48 终止/续)
    # 'fact-05': ['K3', 'K1'],    # 例：RC48-Seagen BD → K3 + K1 (RC148 BD 镜像)
    # 'fact-17': ['K4'],          # 例：财务数据 → K4 (业绩兑现)
    # ... 主 agent 列全 baseline 所有 fact-NN 与 K1..Kn 的映射
}
r = backfill_addresses_by_mapping(slug, variant, mapping)
print(f'backfill: {r["updated_count"]} 材料更新')
if r["unmapped_facts"]:
    print(f'⚠ 未覆盖的 fact: {r["unmapped_facts"]} — 补到 mapping 重跑或显式标注与本 thesis 无关')
```

**纪律（仅在用 fact-NN 标注的前提下）**：
- 必须在 set_thesis(version=0) **之后**调（先有 thesis 再有 K#）
- mapping 必须覆盖 baseline 里出现过且仍与本 thesis 相关的 fact-NN（脚本返回 `unmapped_facts` 给诊断）
- 一个 fact 可对应多个 K#（如 BD 历史 ref 同时支撑 K1 镜像 + K3 历史）
- **scope 约定下无需关心本段**：prescan 料以 scope 入库、不计 K# 覆盖，K# 论据由 02/03 真材料提供
- 升 thesis（v1/v2）时同样调一次（K# 可能新增）

**三态语义**：
- `full`：prescan 入库率 100% → 正常推进 workflow 01
- `partial`：入库率 [50%, 100%) → 标 partial 但允许写入；workflow 05 critic 会列出"未校准 fact 清单"
- `failed`：入库率 <50% → 必须 `force_failed=True` + `prescan_failure_reason`；脚本会通过 `set_next_actions` 自动 prepend 警示，workflow 05 强制 block 04-synthesize 至用户复决

**failed 时 thesis_v0.md frontmatter 必须加红字横幅**（在 Coverage Strip 上方）：

```markdown
🔴 **PRESCAN FAILED** — 本 thesis 基于训练知识赌注；time_sensitivity=快变 的 fact 全部需用户复核
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

**v1 起的写作约定（方案 C 全快照）**：thesis_v0 是天然全快照（四段式，无 parent）；从 v1 起所有 thesis 必须是"全快照 + 顶部 changelog"格式，本版自包含、不依赖历代章节。详见 `prism/workflows/04-synthesize/_shared.md` § "Scheme C 写作约定"。

### 5.1 领域概览（3-5 句话）
- 这个行业/赛道/公司是什么
- 当前处于什么发展阶段
- 市场规模量级

### 5.2 关键研究维度（→ 升 K# 或坍缩进 primer scope · S1 简化）

> **S1 · Q# 降级**：旧版在此另生成一套 `Q1-Q8` 研究维度编号，与 thesis 的 K# 形成双轨、且与 user_todos 重复（与 5.0 删 V# 同源问题）。**新 topic 不再生成 Q#**：
> - **能押注、可证伪的维度** → 升格为 5.0 thesis 的 **K#**（Killer Question），进入 thesis 脊柱；
> - **纯背景/理解性维度**（"这是什么生意/技术分类/产业链长什么样"）→ **坍缩成一行 primer scope 备注**，交给 00_primer 处理，不单列编号、不进 todo addresses。
>
> 简言之：研究维度要么变成可下注的 K#，要么变成 primer 的讲解范围。中间态的 Q# 取消。
> （旧 topic 已有的 Q# addresses 仍有效，gap_detector 本就只认 K#；`extract_research_questions` 保留向后兼容。）

在对话里输出：① 哪些维度升成了 K#（指回 5.0）；② 一行 primer scope 备注（primer 该覆盖的背景范围）。

### 5.3 资料获取建议（用户需要收集什么）

按 **优先级（P0/P1/P2）+ 信息差等级（public/half_public/hard）** 列出 5-10 份关键资料。**每条 todo 都必须标注 addresses**——指向 5.0 thesis 的 Killer Question 号（K1-K5）（Q# 已降级，新 topic 不再用 Q# 作 addresses）——否则失去 thesis-driven 意义。

> **A 合同视角（收料地板）**：除了攻打 K# 的 todo，还要照 `_input_contract.md` 本 type 的**必收类目**排 todo——尤其三项真·欠供：`mgmt-capital-alloc`（管理层/资本配置史）、`consensus`（一致预期/估值锚）、`historical-mirror`（历史失败镜鉴）。这些不一定挂某个 K#，但决策链环①②⑤要落地就必须收。详细排期在 workflow 01 Step 3，此处先在 todo 里显式留位。

**信息差等级定义**：
- `public` 公开普及 — Google/Wind 一搜就有，价值低（但作为研究起点）
- `half_public` 半公开 — 需登录/付费/外文/拼凑，是 alpha 主要来源
- `hard` 难获取 — 专家访谈/产业链调研/圈内信息，价值最高但收集成本大

**优先级原则**：
- P0 = 缺了它整个研究无法推进的（约 3-5 项）
- P1 = 重要补充，影响 thesis 强度但不影响方向（约 3-5 项）
- P2 = 锦上添花，等核心研究完后补（不超过 3 项）

每条 todo 必填字段：`task` / `priority` / `info_tier` / `addresses`，选填 `source_hint`。

> **闭环语义（钉死）**：一条 todo = 「去收**某份具体文档**」的任务，`task` 描述那份文档。`addresses=[K#]` 只标「这份料喂哪个命门」，是**相关性标签**——多条不同 todo 可共享同一 K#（年报 / 卖方预期 / 二手价都可挂 K2），A 合同必收类目（consensus/mgmt-capital-alloc/historical-mirror）甚至**可以不挂任何 K#**。因此 todo 的闭环键是 **task/文档身份，不是 K#**：某 K# 有料 ≠ 攻打它的每条 todo 都收齐了。闭环只走 `mark_todo_fetch(task子串)` + `update_user_todo_status(task子串)`，**禁止用 K# 交集自动 done**（见 `_autofetch_protocol.md` 闭环键节 + memory `feedback_todo_closure_key`）。下面 5.3 的 Coverage self-check 是**反方向**校验（每个 K# 至少有 1 条 todo 瞄准），与「todo 收齐没」无关。

> **建 todo 前查重（纪律，复用 `read_manifest`）**：Step 4.0 早期 ingest 已把家底登记进 manifest。每写一条 todo 前，主 agent 先 `read_manifest('{slug}','{variant}')` 扫已有料，**按文档身份**判：
> - 已有料就是这条 todo 要的那份文档 → 建成 `status='done'` 并填 `covered_by=[已有mat]`，或干脆不建；
> - 没有 → 正常建 `pending`。
> 按文档身份判（不是 K# 撞 K#）——一份挂 K2 的旧价新闻不等于"年报全文"已收。
>
> **产即收衔接**：本阶段（00）产的 pending todo **由 00 自己在 Step 6.5 当场抓**（产即收总规约：谁产谁收、同段闭环）。关键时序——todo 产在 thesis_v0（5.0）**之后**、赌注已锁定，此时 eager-fetch **不污染 bet-first**：bet-first 由 Step 4.5 prescan 前置（只校准事实、`scope` 入库、永不碰 todo）担保，与"fetch 放哪一步"无关。01 Step 5.6 **只补抓 01 自己 Step 2/3 新增**的 L4/A合同 todo（并按 R3 重试 00 遗留的 `error`），不重抓 00 已 `fetched`/`empty` 的。

---

## Step 5.4：产 decomposition_v0（命门拆解前移 · 驱动收料）

> **为什么前移到这里**：拆解（把"赌注"拆成 1-3 个**命门**——最决定成败、最该砸资源验证的特化问题；**以及"门外人入门要掌握什么"的 primer 入门目标**）本是合成活动，但它**驱动收料方向**。前移到 00 用薄知识产一份 `decomposition_v0`，让 01/02 既照 A 合同地板收料、又照命门 B 靶点收料、还照 primer 入门目标补背景料。深度版（v1）留到 04 写作期做有界 delta 重拆（见 `04-synthesize/_shared.md`）。
>
> **冷启动断点 = 训练知识 + baseline + prescan**：此刻还没厚资料，命门基于 thesis_v0 + K# + `baseline_knowledge.md`（含 §六 prescan 校准）拆。**薄拆解可靠性原理上无法认证**（任何裁判也薄知识绑定）→ **v0 不做 LLM critic**，只做置信度 tag（收料对冲用）+ 机械自检。真正的可靠性闸门是 04 厚料 delta 重拆。

**产出 `prism/topics/{slug}/{variant}/decomposition_v0.md`**，含四块（**B 轴 = 命门拆解（喂 case）+ 入门目标拆解（喂 primer）**，两者同属知识驱动、盲点同源，共住一份文件）：

1. **命门 1-3**（每个命门一句话 + **置信度 tag** 高/中/低/uncertain）：
   - 命门 = "若这件事的方向错了，整个 thesis 翻盘"的特化问题（比 K# 更聚焦于**机理/兑现路径**）。
   - 置信度低/uncertain 的命门 → 提示 01/02 **优先砸料验证**（对冲薄拆解风险）。
2. **每环 B 靶点**（决策链 6 环各 1-2 条"为支撑命门，该环特别要挖什么"）——这是 A 合同（type 地板）之上的**命门特化补充**，指导 01 收料 priority。
3. **primer 入门目标 v0（种子，非定稿）**——"门外人为投资读完本 topic 应能做到的 N 条具体能力"清单（N 通常 8-13，门外人可观察的能力，不是知识罗列；形态见 `04-synthesize/00-primer.md` Step 1）：
   - 用薄知识起草（thesis_v0 + K# + `baseline_knowledge.md`），每条标置信度/缺口 tag（标 uncertain/缺口的 → 提示该条需收背景料）。
   - **这是把 primer 目标前移、驱动背景收料**——与命门同属 B 轴，区别只是消费者（命门喂 case 决策环，入门目标喂 primer 理解地基）。
   - **v0 只是种子**：粗清单即可，厚料浮现后的精修留 04 primer Step 1（同命门的有界 delta 重拆，见 `04-synthesize/_shared.md`）。
4. **机械自检**（无需 LLM 判断，照单核对）：
   - 每个 K# 是否都被某个命门覆盖（或显式标"非命门，背景项"）？
   - A 合同每个**必收类目**（尤其三项 hard）是否都在 5.3 / 01 排了收料优先级？
   - 命门置信度分布（几高几低）——低置信度命门是否都进了 B 靶点优先收料？
   - **每条 primer 入门目标**是否都在 5.3 / 01 排了对应背景资料源（或显式标"训练知识可覆盖，无需收料"）？——避免 primer 目标只生成、不驱动收料。

```python
from prism.scripts.topic import set_decomposition
set_decomposition(
    slug='{slug}', variant='{variant}', version=0,
    summary='{命门一句话概览，≤120字，如 "命门1=固态电解质量产良率(中); 命门2=车厂全固态认证节奏(低)"}',
    stage_set_at='00-research-pending',
    convergence_status='open',   # v0 默认 open（深度拆解留给 04）
)
```

> 旧 topic 无 decomposition → 缺省空壳，下游 graceful 退化；新 topic 此步必跑（gap ring 轴据 decomposition 存在性判定是否 active）。

---

## Step 6：更新 topic 状态

**user_todos 必须用 dict 结构**（不能再写 list[str]）。

**ISSUE-001**：`set_next_actions` 须把 Step 5.0 拿到的 `h['status']` + `h['failure_reason']` 传进去，failed 时脚本会自动 prepend ⚠️ 警示 action 到 next_actions 第一条。

示例：

```bash
python3 << 'EOF'
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
from prism.scripts.web_prescan import check_prescan_health

slug = '{slug}'
variant = '{variant}'
h = check_prescan_health(slug, variant, expected_queries={n_priority_queries})

set_stage(slug, '01-roadmap-pending', variant)
set_next_actions(slug, [
    '运行 workflow 01-build-roadmap：制定详细研究路线图',
    '收集 P0 资料后运行 workflow 02-gather-materials',
], variant,
    prescan_status=h['status'],
    prescan_failure_reason=h['failure_reason'],
)
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

## Step 6.5：post-thesis eager-fetch（产即收闭环 · 必跑）

> **为什么在这里**：Step 6 刚把 5.3 的 user_todos 写进 topic.yaml。按 `_autofetch_protocol.md` 总规约「谁产 todo 谁当场收」——**00 产的 todo 必须在 00 当场抓**，不甩给用户、不推给 01。本步在 thesis_v0（5.0）**之后**，赌注已锁定，eager-fetch **不污染 bet-first**（bet-first 由 4.5 prescan 前置 + prescan 不碰 todo 担保，与 fetch 置点无关）。
>
> 收料协议完全复用 `_autofetch_protocol.md`（R1 全覆盖 / R2 有效尝试 / R3 重试），与 workflow 01 Step 5.5/5.6 同源；闭环键 = **task/文档身份**（`mark_todo_fetch` + `update_user_todo_status`，**禁止 K# 交集自动 done**）。
>
> 作用域 = Step 6 写入的全部 `pending` todo（含 `hard`）。唯一与 01 的不同：00 此刻**还没有 roadmap**，收料对象是 `user_todos`（非 `roadmap.material_priority`），report 类 todo 的 ticker 由主 agent 按公司名现场映射。

### 6.5a：结构化报告（年报/季报）→ ticker 直下

todo 若指向可下载的上市公司年报/季报，主 agent **按公司名映射 ticker**（A股 `SSE_600519`/`SZSE_000858`；美股 `NVDA`；港股 `HKEX_02228`；韩 `KRX_006400`；日 `TSE_5019` 或 `EDINET_E00040`），调 `scripts.fetch_report_prism.fetch` / `fetch_many` 下载。一条 todo 含多家公司（如"茅五泸三家年报"）= 多个 ticker 循环 fetch。

```python
from scripts.fetch_report_prism import fetch
from prism.scripts.topic import mark_todo_fetch, update_user_todo_status

# 例：todo "下载茅五泸三家 2025 年报 + 2026Q1 季报"
tickers = {'茅台': 'SSE_600519', '五粮液': 'SZSE_000858', '泸州老窖': 'SZSE_000568'}
got = []
for name, tk in tickers.items():
    try:
        got.append(fetch(tk, report_type='annual', year=2025, slug=slug, variant=variant))
        got.append(fetch(tk, report_type='quarterly', year=2026, quarter=1, slug=slug, variant=variant))
    except Exception as e:
        print(f'{name} {tk} ✗ {e}')
# fetch() 自己登记 manifest + 盖 todo status；主 agent 仅在跨多 ticker / 部分到位时补判 done vs in_progress
mark_todo_fetch(slug, variant, '茅五泸三家 2025 年报', 'fetched', note=f'cninfo {len(got)} 份')
update_user_todo_status(slug, variant, '茅五泸三家 2025 年报', 'done', covered_by=[m for m in got])
```

### 6.5b：分析材料（卖方研报/行业数据/政策/科普）→ exa→semantic→WebFetch 阶梯

非报告类 todo（sell-side / industry-research / policy / data / 科普）走 workflow 01 Step 5.6 同一阶梯：

1. **exa 高级搜索** `mcp__exa__web_search_advanced_exa`（`numResults:5`、`enableHighlights:true`、`highlightsMaxCharacters:2000`、`textMaxCharacters:5000`），5 条一批并发；
2. exa 未满意 → **adapter semantic**：
   ```bash
   python3 -m prism.scripts.web_search search "<材料标题关键词>" \
       --intent semantic --days 365 --max-results 5 --output sidecar \
       --slug {slug} --variant {variant} \
       --triggered-by 00-deep-fetch --addresses K1,K2
   ```
3. 搜到的权威 URL（domain_tier=`llm-judged-official`）→ `mcp__exa__web_fetch_exa`（`maxCharacters:5000`，可批量）抓全文。

抓到 → 落 `prism/topics/{slug}/inbox/{descriptive_name}.md`（资料只在 topic 层）→ `add_material` 入库 → 按 task 子串 `mark_todo_fetch('fetched')` + `update_user_todo_status('done', covered_by=[mat])`。

### 6.5c：盖戳纪律（照 `_autofetch_protocol.md`，三态必显式盖）

- 抓到入库 → `fetched` → `done`；
- **有效尝试**确认公开无源 → `empty`（留 `pending` 交用户，触发 empty 硬闸门，**不静默写缺口**）；
- 工具/网络/限流失败 → `error`（**必须重试，绝不降级**；本轮等不了就先盖 `error` 交 01/R3 下轮重试）。
- `hard` 也要尝试一次（草根纪要/付费数据多半 `empty`，但 empty 要由**真实结果**证明，不由标签预判——付费卖方深度常有公开转载）。
- 闭环只走 task 子串（文档身份），**禁止用 K# 交集自动 done**。

### 6.5d：刷新 next_actions + 输出对照表

eager-fetch 跑完，**重设 next_actions**（覆盖 Step 6 的占位），让"你需要做的事"只剩真 `empty`：

```python
from prism.scripts.topic import set_next_actions, read_topic
t = read_topic(slug, variant)
remain = [td['task'] for td in t['user_todos'] if td.get('fetch_status') == 'empty']
set_next_actions(slug, [
    f'00 eager-fetch 已抓 N 份入库；剩 {len(remain)} 条公开无源待你决策（waived/will_collect）',
    '运行 workflow 01-build-roadmap（01 只补抓自己新增的 L4/A合同 todo + 按 R3 重试 00 的 error）',
], variant)
```

并在对话输出一张表（同 01 Step 5.6 格式），逐条标 `fetch_status`：

```
| todo | info_tier | 获取方式 | fetch_status |
|------|-----------|----------|--------------|
| 茅五泸 2025 年报+Q1 季报 | half_public | cninfo 直下 | fetched（mat-xxx…） |
| 卖方拐点研报×3 | public | exa→转载全文 | fetched（mat-xxx） |
| 飞天高频批价序列 | half_public | exa+semantic 0 命中 | empty（待你决策） |
```

> **纪律**：跑完 6.5 后，"你需要做的事"里**只应剩真·`empty`**（付费墙/App/草根纪要等有效尝试后确认公开无源的）。任何 `fetched`/能自动下的还躺在用户清单里 = 违产即收，回 6.5a/b 补抓。

---

## Step 6.5e：auto-fetch 全覆盖硬闸门（**未通过不得进 Step 7**）

> **为什么必须做**：Step 6.5b/c 的「产即收 + R1 全覆盖」如果只靠散文纪律（「不要跳过本步」），主 agent 容易在 prescan 已跑完 10+ query 后产生"已经够了"的 shortcut 偏见，凭 `info_tier` 先入为主跳过 half_public/hard todo、或只象征性抓 1 份就宣布完成——导致大量 unattempted todo 被包装成"剩 N 条待你"甩给用户。本闸门把 `pending_unfetched_todos` 接成进 Step 7 前的硬断言，精确拦截"从未尝试就推进"。
>
> **与 01 Step 5.8 同源**：01 已有等效闸门（unattempted → SystemExit(1)），00 之前缺失，导致 00 产的 todo 可以被跳过而无人卡口。本步补齐。

```bash
python3 -c "
from prism.scripts.topic import pending_unfetched_todos
p = pending_unfetched_todos('{slug}', '{variant}')
unattempted = [t for t in p if t.get('fetch_status') == 'unattempted']
errored     = [t for t in p if t.get('fetch_status') == 'error']
if unattempted:
    print('❌ 00 产即收违规：以下 todo 从未尝试过抓取（fetch_status=unattempted）——')
    print('   info_tier 只决定努力顺序，不是跳过门槛（auto-fetch 规约 R1）。回 Step 6.5b 逐条跑阶梯并 mark_todo_fetch：')
    for t in unattempted:
        print(f'   - [{t.get(\"info_tier\")}] {t[\"task\"][:60]}')
    raise SystemExit(1)
if errored:
    print('⚠ 以下 todo 抓取失败（fetch_status=error），按退避梯重试；本轮带过将由 01 的 R3 续抓：')
    for t in errored:
        print(f'   - {t[\"task\"][:60]}')
print('✓ 00 auto-fetch 全覆盖通过：无 unattempted（每条 todo 都已有效尝试过）')
"
```

如果非 0 退出（有 `unattempted`），**回 Step 6.5b 把它们逐条跑完阶梯 / 盖 `empty` / 盖 `error`**，再回来跑 Step 6.5e。**`unattempted` 清零是进 Step 7 的前置条件。**

---

## Step 7：告知用户

输出：
```
✅ 研究主题「{display_name}」已创建

Slug: {slug}
变体目录: prism/topics/{slug}/{variant}/
Web 地址: http://localhost:8000/prism/{slug}/{variant}/

00 eager-fetch（Step 6.5）：已抓 {N} 份入库 / 剩 {M} 条公开无源待你

下一步：
1. 在对话里说「prism 推进 {slug}」继续制定研究路线图（01 补抓自己新增的 todo）
2. 或者先收集资料放入 prism/topics/{slug}/inbox/ 后说「prism 推进 {slug}」

你需要做的事（仅剩真·公开无源 fetch_status=empty）：
{remaining_empty_todos}
```

> 若 {M}=0（00 eager-fetch 全抓到），"你需要做的事"应为空——直接进 01，不伪造待办。
