# Workflow 00 — 开启新研究主题

**触发**：用户说「研究 X」或「开始研究 X」  
**产出**：创建 `prism/topics/{slug}/topic.yaml` + `manifest.yaml`，Web 页面 /prism/{slug} 可访问

---

## 00 速览（先读这块，再看细节步骤）

**4 幕 / 3 思考产物**（步骤号是落地细节，幕是心智模型）：

| 幕    | 步骤             | 产出                          | 一句话                                                     |
| ---- | -------------- | --------------------------- | ------------------------------------------------------- |
| ① 立框 | Step 1-4       | topic.yaml + manifest       | type→终局倒推 + question 押注 + slug + 早期 ingest              |
| ② 认知 | Step 4.3       | `baseline_knowledge.md`     | 训练知识先验（fact 账本 + 置信度 + 时效标签）+ 盲点→query                  |
| ② 校准 | Step 4.5 a/b/c | 入库 web-search + baseline §6 | prescan 把时敏 fact 对齐最新现实（防把过期事实当赌注）                      |
| ③ 下注 | Step 5.0       | `thesis_v0.md`              | 落在 type 终局上的赌注 + K#（可证伪）+ 反方                            |
| ③ 拆解 | Step 5.4       | `decomposition_v0.md`       | 从终局拆命门（机理/兑现路径）+ 每环 B 靶点 + primer 入门目标种子                |
| ④ 收料 | Step 6 / 6.5   | user_todos + 抓料入库           | K# + A 合同 派 todo → 产即收 eager-fetch → no-unattempted 硬闸门 |

**三个思考产物是三条不同轴、互不替代、且都喂下游——不要合并 / 删除 / 下放**（已核实下游消费）：

| 产物                                                  | 轴        | 下游消费者                                                                                                                                                                    |
| --------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `baseline_knowledge.md`                             | 训练知识先验   | 03-extract（findings cite `[fact-NN]`）、05-critic（列未校准 fact 清单）、04 primer                                                                                                  |
| `thesis_v{N}.md` 的 **K#**                           | 论点 / 覆盖轴 | gap_detector 算 K# 覆盖率、01-roadmap、05-critic                                                                                                                               |
| `decomposition_v{N}.md` 的 **命门 / B 靶点 / primer 目标** | 终局拆解轴    | **04 `_shared.md` 的「B 轴有界 delta 重拆」以 v0 为基线逐条 diff** → v1；04 各 funnel/case 决策环；05-critic；未收敛命门 capped→07-drilldown。primer 入门目标是 04 primer 的种子，"入门目标 delta 空"是 04 收敛的必要条件 |

> **命门 ≠ K# 换个说法**：K# 是可证伪的"会改变看法的事件"（覆盖轴，喂 gap_detector）；命门是"机理/兑现路径上方向错了就翻盘"的特化问题（终局拆解轴，映射到决策环）。写 `decomposition_v0` 时**不要把命门写成"覆盖 K1/K3"的复述**——那是把终局拆解轴退化成 K# 的影子，会让 04 的 delta 重拆失去真实基线。

---

## 幕① 立框 — `topic.yaml` + `manifest.yaml`

**目标**：type→终局倒推 + question 押注 + slug + 早期 ingest（家底元数据）
**产物**：`topic.yaml`（含 ticker/short_name/search_terms/scope）+ `manifest.yaml`
**✅ 验收断言**：`create_topic` 对 company 漏 ticker/short_name、长 question 漏 search_terms **直接 raise**（见 Step 1b / Step 4，脚本硬闸门）

### Step 1：确认研究对象

向用户确认以下信息（如果用户没说清楚则 AskUserQuestion）：

1. **研究对象名称**（中文，例如「中国宠物行业」「中国商业航天」「宁德时代」）
2. **研究类型**（industry / arena / company）
   - industry：整个行业（宠物、储能、机器人）
   - arena：细分竞技场（宠物食品、人形机器人执行器）
   - company：单家公司
3. **研究深度**（quick = 1-2 天 / standard = 1 周 / deep = 持续跟踪）
4. **地理范围**（CN / US / GLOBAL）

如果用户直接说「研究中国宠物行业」，可以推断：type=industry, geo=CN，然后只确认研究深度。

---

### Step 1a：type→终局倒推（确认 type 后立刻做 · 终局归 type 独占）

**确认 type 后，主 agent 必须显式读出本 type 的合同终局**（`terminal_for_type`），并在对话中向用户声明：

```bash
python3 -c "from prism.scripts.topic import terminal_for_type; print(terminal_for_type('{type}'))"
```

**终局由 type 独占**——这是 a priori 不可协商的交付结构，研究任何标的之前已知：
- `industry` → 把资本/注意力分配给哪几个细分 arena（深挖/观察/淘汰三档分流）
- `arena` → 在候选标的里选出 shortlist——谁是赢家、介入纪律
- `company` → 买/卖/持有 + 期望收益(EV) + 目标价/介入纪律
- `macro` → 体制定位 + 传导地图下的资产含义

> 📎 *→ `_00_reference.md` §A1a（执行时可跳过）*

### Step 1b：核心研究问题 — 终局上的赌注（三段式收集）

**question 不再是自由散文**——它是「对 type 终局的先验赌注 + scope 切片」：

> 📎 *示例 / 软警告规约 → `_00_reference.md` §A1b（执行时可跳过）*

**主 agent 必须按三段式收集并写出 question**：

1. **标的身份 + scope 切片**（geo/depth/研究哪一刀）：
   - 例：「中国商业航天行业，deep 深度，不含军工邻接/一级 pre-IPO」
2. **对终局的先验赌注**（核心提问，按 type 改写——这是 alpha 本身）：
   - industry → 「你预判利润池会落到哪几个 arena？押哪条迁移路径？共识押哪条、你和它哪里分歧？」
   - arena → 「候选里你赌谁是赢家、凭哪个胜负变量？」
   - company → 「你赌买还是卖？核心命门是什么？目标价区间的赌注？」
3. **红线（不可违反）**：
   - question **不得**重新枚举/降格终局（如 industry 写「全维度…赛道筛选作其一」即违规——终局已由 type 独占、永远在场，question 只能往这个固定终局里灌赌注）
   - question **不得**用「全维度/百科式」一词——这是 thesis-driven 设计明令禁止的百科框法（00 Step 5.0 原文：先押赌注「避免研究变成百科全书式覆盖」）

> 若用户给「全维度/百科式」question：不硬收窄，改写成「终局赌注主轴 + 宽覆盖作 scope 备注」并回述确认（详例 → `_00_reference.md` §A1b）。

**重要**：如果用户没有明确说地域（如「研究AI算力基础设施行业」），不得默认 CN，必须将地理范围列入 AskUserQuestion 让用户选择。

同时需要确认当前使用的 LLM 模型变体名称（如 `gemini`、`gpt-4o` 等），后续将作为 `variant` 参数使用。默认可使用当前调用的模型名称。

**如果是 company 类型，必须确认 ticker**（格式：`{market}_{code}`，如 `SZSE_000426`、`SSE_600519`、`HKEX_09995`、`US_AAPL`）。ticker 用于生成行情/财务页面链接。**company 漏传 ticker 会被 `create_topic` 直接 raise**。

**display_name 与 short_name 分离**：`display_name` 用于 UI 展示（可长，含 ticker 和英文名）；`short_name` 用于 WebSearch 查询（≤12 字，纯主体名）。
- company 类型 **必填 `short_name`**（脚本 raise）；industry/arena 可选（不填走 display_name 兜底）

**长 question 必须同步给 `search_terms`**：当 `question` 超 25 字（典型如生物医药/科技/复合产业的 deep 类研究），**必填** `search_terms: list[str]` — 2-4 个 WebSearch 友好的核心关键词，每项 ≤15 字。**漏填会被 `create_topic` 直接 raise**（`topic.py:333`）——脚本不做关键词提取，标点截断常切到非核心名词反而误导，由主 agent 显式提炼。

**多市场上市（AH 双重 / ADR / 多重上市）必须确认 `extra_tickers`**（list[str]，主代码以外的所有同公司代码）。

> 📎 *short_name / search_terms / extra_tickers inline 示例 → `_00_reference.md` §A1b*

---

### Step 2：生成 slug

slug 规则：
- 全小写，连字符分隔
- 格式：`{geo}-{keywords}`
- 示例：`cn-pet-industry`、`cn-commercial-space`、`cn-catl`
- 不超过 30 字符

在对话里显示 slug，等用户确认或修改。

---

### Step 3：检查是否已存在（结构化查重，勿凭 `ls` 肉眼判断）

```bash
python3 -c "from prism.scripts.topic import list_variants; print(list_variants('{slug}'))"
```

- 返回 `[]` → 全新 slug，直接进 Step 4。
- 返回非空（如 `['claude-opus-4-7']`）→ slug 已存在其他变体，**这是一个意图分叉点，必须停下问用户**（不能自行默认走某条）：
  - **续做**旧变体：不 create，读对应 `topic.yaml` 判 stage → 跳转对应 workflow 推进。
  - **换模型/换架构重研**（新变体）：进 Step 4 用新 variant 名创建（变体名以 `model_registry` 规范名为准）。建后按"新变体复用旧料"流程（详 → `_00_reference.md` §A3）。
  - **另一个 topic 撞名**：slug 加后缀（如 `cn-pet-industry-2`）另起。
  - **本变体已存在但只是父级 init 种的空壳 stub** → **不是另起变体，而是续做本变体**：在现有 stub 上正常跑 Step 4.3→6.5（详 → `_00_reference.md` §A3）。

> 📎 *分支细节 / 兜底说明 → `_00_reference.md` §A3（执行时可跳过）*

---

### Step 4：创建 topic

```bash
python3 -c "from prism.scripts.topic import create_topic; create_topic(slug='{slug}', display_name='{display_name}', topic_type='{type}', question='{question}', geo='{geo}', depth='{depth}', variant='{variant}', ticker='{ticker_or_None}', extra_tickers={extra_tickers_or_None}, short_name='{short_name}', search_terms={search_terms_or_None}); print('创建成功')"
```
> 📎 *全参注释 / company 漏 ticker·short_name raise / 长 question 漏 search_terms raise（`topic.py:333`）/ extra_tickers 用途 → `_00_reference.md` §Step4*

```bash
python3 -c "
from prism.scripts.manifest import create_manifest
create_manifest('{slug}', '{variant}')
print('manifest 创建成功')
"
```

### Step 4.0：早期 ingest — 登记 topic 家底元数据（**新增 — 必跑**）

> 📎 *为什么 / 幂等说明 → `_00_reference.md` §A4.0（执行时可跳过）*

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

---

## 幕② 认知 + 校准 — `baseline_knowledge.md`

**目标**：先落训练知识先验（fact 账本 + 置信度 + 时效标签），再用 prescan 把时敏 fact 对齐最新现实（防把过期事实当赌注）
**产物**：`baseline_knowledge.md`（五段 + 4.5c 回写第六节）+ 入库 web-search material
**✅ 验收断言**：`check_prescan_health` 三态（`full`/`partial`/`failed`）在幕③登记 thesis 时校验；`failed`（入库率<50%）必须 `force_failed=True`

### Step 4.3：写训练知识 baseline（**新增 — 必跑**）

> 📎 *为什么必须做 → `_00_reference.md` §A4.3（执行时可跳过）*

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

**纪律**：自评置信度保守（uncertain 优于编造）；第四节盲点 → 第五节**精准可执行 query**（"特斯拉 4680 电池 2026Q1 量产爬坡进度"，非"电池技术进展"话题式）——4.5a 逐条跑入库，漏写=prescan 漏校准=thesis_v0 押过时赌注；03/04 引用训练知识 cite `baseline_knowledge.md` 的 `[fact-NN]`，引用第六节"被推翻"的 fact 必改 cite 新 mat_id。

---

### Step 4.5：Web Pre-scan（必跑 — 校准训练知识与最新现实）

> 📎 *为什么必须做 → `_00_reference.md` §A4.5（执行时可跳过）*

> **Web 搜索路径**：本步走 **adapter**（详 [[_web_search_routing]]），`--output sidecar` 只写 raw 不入库；主 agent 用 `review-digest` 判 tier 后调 `register_web_search_batch` 入库（勿 Read 整 json）。退出码 40（all_exhausted）→ WebSearch tool fallback + `postprocess` 兜回。
> 📎 *完整命令 / 2026-05-28 sidecar 修法 / domain_tier 判定 → `_00_reference.md` §Step4.5*

### Step 4.5a：先跑 baseline 第五节的优先 query

> 📎 *为什么手动落地（build_search_queries 不读 baseline）→ `_00_reference.md` §A4.5a（执行时可跳过）*

```bash
sed -n '/## 五、需要 web-search 校准的优先项/,/^##/p' prism/topics/{slug}/{variant}/baseline_knowledge.md
```

主 agent 对每条优先 query 按 `_web_prescan_shared.md` Step B.1 **并发限流**（5 并发/批 + 批间 10s，防静默限流）逐条跑 → `register_web_search_batch(triggered_by='00-prescan-baseline', addresses=['scope'], ...)`，**显式读 `failure_mode`**：`upstream_empty` 等 30s 串行重试（连 3 个转 B.2 兜底）/ `all_low_band` 走 H2 救回（非重试）。
> 📎 *register 完整范例 / failure_mode 分支处理 / 4 点限流细则 → `_00_reference.md` §Step4.5a*

**纪律**：第五节 5-10 条优先 query 全部尝试完才进 4.5b。漏跑等于主 agent 自评的盲点没补，thesis_v0 会基于过时认知做赌注。WebSearch 长时不可用时按 B.2 降级，**不允许默默跳过**——脚本会通过 Step 5.0 的 `check_prescan_health` 自动检测并触发 `prescan_status='failed'`。

### Step 4.5b：跑覆盖槽 prescan

> 📎 *为什么 / 反例 / 历史教训 → `_00_reference.md` §A4.5b（执行时可跳过）*

调用 `prism/workflows/_web_prescan_shared.md`，参数 `recency_days=90`，`triggered_by='00-prescan'`。

跑完后输出汇报模板：
```
✅ 00-prescan 完成：
  - 4.5a baseline 优先 query：M 条 → 入库 M' 份
  - 4.5b 默认模板 prescan：N 条 → 高/中/低 X/Y/Z → 入库 X+Y 份
关键事实更新：
  - {对 thesis 影响最大的 2-3 条新事实}
```

### Step 4.5c：回写 baseline 校准结果

跑完 4.5a + 4.5b 后，主 agent 扫一遍刚入库的 web-search material，对照 baseline 第一节的 fact-NN，把被推翻 / 被验证的条目记下来，**追加到 baseline_knowledge.md 末尾**（Edit 工具）：

> 📎 *第六节「被推翻/被验证/仍未校准」三分类回写模板 → `_00_reference.md` §Step4.5c*

**纪律**：
- 这一步是 LLM 判断（不是脚本能做的），主 agent 必须**逐条扫**，不要漏
- 若某 fact 在第六节标"被推翻" → Step 5.0 写 thesis_v0 时**不准**继续 cite 原 fact，必须改 cite 新 mat_id
- 该回写让 03/04/05 后续 cite baseline 时一眼看到哪些 fact 已经过时

---

**例外可以跳过 prescan**：concept 类 topic（纯方法论/历史回顾，与近期事件无关）；用户明确说"用你脑子里的知识就行"。**company / industry / arena 默认必跑**。

---

## 幕③ 下注 + 拆解 — `thesis_v0.md` + `decomposition_v0.md`

**目标**：把赌注押在 type 终局上（thesis_v0 + 可证伪 K# + 反方）；从终局拆命门（机理/兑现路径）+ 每环 B 靶点 + primer 入门目标种子
**产物**：`thesis_v0.md`（四段）+ `decomposition_v0.md`（命门带置信度 tag）+ `user_todos`
**✅ 验收断言**：`set_thesis(force_failed=…)` prescan failed 时强制；thesis K# 可观测可证伪（非"如果失败"式）；decomposition 命门带**置信度 tag**；K# 覆盖 self-check + 终局命门自检

### Step 5：基于训练知识 + prescan 数据做初步定向

**注意**：相较旧版"100% 训练知识"，本步要求把 Step 4.5 入库的 web-search 资料（manifest 里的 web-search source_type 条目）作为事实校准源；训练知识做"框架/逻辑/远期判断"，prescan 数据做"近 90 天事实/财务/监管/价格"。

产出以下**四部分**：5.0 thesis 表态写文件，5.1/5.2/5.3 直接在对话里输出。

### 5.0 LLM 初判 thesis（强制 — thesis-driven 研究的起点）

> 📎 *目的 / V# 降级 / 后续何时更新 → `_00_reference.md` §A5.0（执行时可跳过）*

**硬约束**：
- thesis 里的财务数字（收入/EPS/PE/股价/AUM）必须引用 Step 4.5 入库的 web-search 资料中的数据，不得用训练时记忆数字
- 在 frontmatter 加 `revised_after_prescan: true` 标记
- `data_freshness` 字段写明"训练知识截止 YYYY-MM + workflow 00 web-prescan（含 XX 数据）"

**要求**：写一份 `prism/topics/{slug}/{variant}/thesis_v0.md`，必须包含以下四段（每段都要写，不能跳过）：

1. **核心 thesis**：一句话（≤80 字）+ 强度评分（0-10 分，0=完全看空，10=All-in 看好）
   - 必须有方向（看多 / 看空 / 中性 / 分化看法），不能写"取决于"
   - 如果是分化看法，明确说"看好 X，看空 Y"
   - **thesis 必须是「终局上的立场」**——落在 type 终局上：
     - industry → 倾向哪几个 arena / 哪条迁移路径（不能只写「看多行业」）
     - arena → 赌谁是赢家、凭哪个胜负变量
     - company → 赌买还是卖、核心命门 + 目标价区间
     - macro → 体制定位 + 资产含义
2. **支持理由**（3-5 条）：每条一句话，给出 LLM 现在最相信的判断依据
3. **最大反方观点**（2-3 条）：诚实列出最有力的反方逻辑——不是稻草人
4. **会改变看法的事件 / Killer Question**（3-5 条）：必须是**可观测、可证伪**的具体事件
   - 反例："如果技术失败" ✗
   - 正例："任一头部车厂将全固态 SOP 时间从 2027-2028 推迟到 2030+" ✓

写完 `thesis_v0.md` 后，**先跑 prescan 健康度检查**再登记 thesis：

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

> **默认 scope 约定下本步是 no-op，直接跳过**（仅当 prescan 材料用 `fact-NN` 标 addresses 时才跑；详 → `_00_reference.md` §A5.0a）。

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
- **终局命门自检（新增 · 终局对齐）**：thesis 的 K# 谱系 **或** decomposition 命门里，必须有**至少一条直接服务于 type 终局决策**；否则在对话报警并补。（语义判断归 LLM；`terminal_for_type` 作核对锚。）
  - industry 需有 arena 倾向/迁移路径相关 K# 或命门
  - arena 需有 shortlist/赢家判定相关 K# 或命门
  - company 需有买/卖 + 目标价相关 K# 或命门

Web 端会在详情页 thesis 卡片下显示 `K1✓ K2✓ K3✗ K4✓ K5✗` coverage strip，红色 = 未覆盖。看到红色就必须处理，不能假装看不见。

**v1 起的写作约定（方案 C 全快照）**：thesis_v0 是天然全快照（四段式，无 parent）；从 v1 起所有 thesis 必须是"全快照 + 顶部 changelog"格式，本版自包含、不依赖历代章节。详见 `prism/workflows/04-synthesize/_shared.md` § "Scheme C 写作约定"。

### 5.1 领域概览（3-5 句话）
- 这个行业/赛道/公司是什么
- 当前处于什么发展阶段
- 市场规模量级

### 5.2 关键研究维度（→ 升 K# 或坍缩进 primer scope · S1 简化）

> 📎 *Q# 降级来龙去脉 → `_00_reference.md` §A5.2（执行时可跳过）*

在对话里输出：① 哪些维度升成了 K#（指回 5.0）；② 一行 primer scope 备注（primer 该覆盖的背景范围）。

### 5.3 资料获取建议（用户需要收集什么）

按 **优先级（P0/P1/P2）+ 信息差等级（public/half_public/hard）** 列出 5-10 份关键资料。**每条 todo 都必须标注 addresses**——指向 5.0 thesis 的 Killer Question 号（K1-K5）（Q# 已降级，新 topic 不再用 Q# 作 addresses）——否则失去 thesis-driven 意义。

> **A 合同视角（收料地板）**：除了攻打 K# 的 todo，还要照 `_input_contract.md` 本 type 的**必收类目**排 todo——尤其三项真·欠供：`mgmt-capital-alloc`（管理层/资本配置史）、`consensus`（一致预期/估值锚）、`historical-mirror`（历史失败镜鉴）。这些不一定挂某个 K#，但决策链环①②⑤要落地就必须收。详细排期在 workflow 01 Step 3，此处先在 todo 里显式留位。

每条 todo 必填字段：`task` / `priority` / `info_tier` / `addresses`，选填 `source_hint`。（info_tier / P0-P2 定义 → 📎 `_00_reference.md` §Step5.3）

> **建 todo 前查重（纪律，复用 `read_manifest`）**：每写一条 todo 前，主 agent 先 `read_manifest('{slug}','{variant}')` 扫已有料，按文档身份判：已有料 → 建成 `status='done'` 填 `covered_by=[已有mat]`，或干脆不建；没有 → 建 `pending`。

> 📎 *闭环语义 / 产即收衔接 / 查重展开 → `_00_reference.md` §A5.3（执行时可跳过）*

---

### Step 5.4：产 decomposition_v0（命门拆解前移 · 驱动收料）

> 📎 *为什么前移 / 冷启动可靠性原理 → `_00_reference.md` §A5.4（执行时可跳过）*

**产出 `prism/topics/{slug}/{variant}/decomposition_v0.md`**，含四块（**B 轴 = 命门拆解（喂 case）+ 入门目标拆解（喂 primer）**，两者同属知识驱动、盲点同源，共住一份文件）：

1. **命门 1-3**（每个命门一句话 + **置信度 tag** 高/中/低/uncertain）：
   - 命门 = "若这件事的方向错了，整个 thesis 翻盘"的特化问题（比 K# 更聚焦于**机理/兑现路径**）。
   - 置信度低/uncertain 的命门 → 提示 01/02 **优先砸料验证**（对冲薄拆解风险）。
2. **每环 B 靶点**（决策链 6 环各 1-2 条"为支撑命门，该环特别要挖什么"）——这是 A 合同（type 地板）之上的**命门特化补充**，指导 01 收料 priority。
   - **终局环 B 靶点强制非空**（终局对齐 · 新增）：type 终局指向的环必须写出并排进 5.3/01 收料优先级（不能空着等环⑥「必产」硬挤）：
     - industry → 环⑥ arena 比较料靶点（跨 arena 同口径可比，用于分流）
     - arena → 环⑥ shortlist 料靶点（候选标的横向比较，用于选出赢家）
     - company → 环④ EV 输入料靶点（估值锚 + 一致预期 + 目标价支撑）
3. **primer 入门目标 v0（种子，非定稿）**——"门外人为投资读完本 topic 应能做到的 N 条具体能力"清单（N 通常 8-13，门外人可观察的能力，不是知识罗列；形态见 `04-synthesize/00-primer.md` Step 1）：
   - 用薄知识起草（thesis_v0 + K# + `baseline_knowledge.md`），**每条必挂一个收料去向 tag（三选一，禁止"其余"合并桶）**：
     - `[收料]` — 缺口/uncertain 且 findings 能补 → 排背景资料源进 5.3/01 todo；
     - `[训练知识展开]` — 无对应 findings、靠 LLM 训练知识兜底的**理解性/机理**目标（技术原理/工艺/估值方法/商业模式机制等）→ 不排收料，**但这是"免收料的对价"：04 primer 必须为它单列一节、用训练知识主动展开到教学满深，不许因 findings-first 而薄带一句**；
     - `[附带]` — 无需专门收料，攻打某 K# 的 findings 会顺带覆盖（须写明搭哪个 K#）。
   - **这是把 primer 目标前移、驱动背景收料**——与命门同属 B 轴，区别只是消费者（命门喂 case 决策环，入门目标喂 primer 理解地基）。
   - **性质约束（primer 回归 · 必守）**：入门目标必须是**理解性/教学性能力**（说清/解释/区分/教方法 X 是什么、理解双面性、列出可观测信号），**不得是决策性能力**（复述 arena 分流结论/判断投资含义/给 stance/定 tier）——后者归 case 决策环。
   - **终局豁免**：terminal-alignment 的终局贯穿到 K#/命门/case（正确），但**不贯穿到 primer 入门目标**。入门目标服务"门外人读懂这门生意"，不服务"做终局决策"——不得因 5.2 终局命门自检/5.4 终局环 B 靶点而把入门目标终局化（如"复述 arena 分流结论"是 case 环⑥的活，不是入门目标）。
   - **v0 只是种子**：粗清单即可，厚料浮现后的精修留 04 primer Step 1（同命门的有界 delta 重拆，见 `04-synthesize/_shared.md`）。
4. **机械自检**（无需 LLM 判断，照单核对）：
   - 每个 K# 是否都被某个命门覆盖（或显式标"非命门，背景项"）？
   - A 合同每个**必收类目**（尤其三项 hard）是否都在 5.3 / 01 排了收料优先级？
   - 命门置信度分布（几高几低）——低置信度命门是否都进了 B 靶点优先收料？
   - **每条 primer 入门目标是否都挂了 `[收料]`/`[训练知识展开]`/`[附带]` 三选一 tag 且逐条列名**（禁止"其余训练知识可覆盖或收料附带"这类合并桶——合并桶正是薄节漏网口）？`[收料]` 是否进 5.3/01 todo？**`[训练知识展开]` 是否逐条列进 decomposition，供 04 primer 认领为"必主动展开的专节"？**——避免 primer 目标只生成、不驱动收料，更避免"训练知识可覆盖"沦为免展开的逃生舱（教训：某目标被扫进"其余"合并桶 → 零收料 + 04 primer 薄带一句 → 整篇偏薄）。
   - **每条 primer 入门目标是否理解性/教学性（非决策性）？**（primer 回归 · 必守）——决策性条目（复述 arena 分流结论/判断投资含义/给 stance/定 tier）必须改写为理解性（"说清 X 是什么/解释 X 机理"）或剔除。终局决策归 case，不入入门目标（终局豁免见上）。
   - **「type 终局环的 B 靶点是否非空？」是否在 5.3/01 排了对应收料优先级？**（终局对齐 · 新增）——否则报警。形态对齐第 4 条「每条 primer 入门目标是否排了背景料」。

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

### Step 6：更新 topic 状态

**user_todos 必须用 dict 结构**（不能再写 list[str]）。

`set_next_actions` 须把 Step 5.0 拿到的 `h['status']` + `h['failure_reason']` 传进去，failed 时脚本会自动 prepend ⚠️ 警示 action 到 next_actions 第一条。

示例：

```bash
python3 << 'EOF'
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
from prism.scripts.web_prescan import check_prescan_health
slug, variant = '{slug}', '{variant}'
h = check_prescan_health(slug, variant, expected_queries={n_priority_queries})
set_stage(slug, '01-roadmap-pending', variant)
set_next_actions(slug, ['运行 workflow 01-gather：制定路线图 + 自动收料 + 登记'], variant,
                 prescan_status=h['status'], prescan_failure_reason=h['failure_reason'])  # failed 时脚本自动 prepend ⚠️ 到第一条
set_user_todos(slug, [{'task': ..., 'priority': 'P0', 'info_tier': 'half_public', 'addresses': ['K1'], 'source_hint': ...}, ...], variant)
EOF
```
> 📎 *多 todo 完整范例 + `_normalize_todo` 字段约束枚举（priority P0/P1/P2 · info_tier public/half_public/hard · addresses list[K#] · status，不合规 raise）→ `_00_reference.md` §Step6*
---

## 幕④ 收料 — 产即收 eager-fetch + 全覆盖硬闸门

**目标**：K# + A 合同派的 todo，00 自己当场抓（产即收），no-unattempted
**产物**：材料入库 + todo 三态闭环（fetched/empty/error）
**✅ 验收断言**：Step 6.5e 双闸门 `pending_unfetched_todos`(拦 unattempted) + `verify_empty_todos_searched`(拦无痕 empty) — **未过不得进 Step 7**

### Step 6.5：post-thesis eager-fetch（产即收闭环 · 必跑）

> 📎 *为什么在这里 / 收料协议 / 作用域 → `_00_reference.md` §A6.5（执行时可跳过）*

### 6.5a：结构化报告（年报/季报）→ ticker 直下

todo 若指向可下载的上市公司年报/季报，主 agent **按公司名映射 ticker**（A股 `SSE_600519`/`SZSE_000858`；美股 `NVDA`；港股 `HKEX_02228`；韩 `KRX_006400`；日 `TSE_5019` 或 `EDINET_E00040`），调 `scripts.fetch_report_prism.fetch` / `fetch_many` 下载。一条 todo 含多家公司（如"茅五泸三家年报"）= 多个 ticker 循环 fetch。

> ⚠️ **本段必须用 `./.venv/bin/python` 跑**：`fetch_report_prism` 依赖 `requests`，仓库默认 `python3` 未装，裸跑会 `ModuleNotFoundError: No module named 'requests'`。纯 CRUD 脚本（`prism.scripts.topic` / `prism.scripts.manifest`）才可用裸 `python3`。

```python
# 主 agent 按公司名映射 ticker → fetch()，逐条闭环
from scripts.fetch_report_prism import fetch
from prism.scripts.topic import mark_todo_fetch, update_user_todo_status
from prism.scripts.manifest import read_manifest
# got=[fetch(tk, report_type='annual'/'quarterly', year=..., slug=slug, variant=variant) for tk in tickers]
mark_todo_fetch(slug, variant, '<task 子串>', 'fetched', note='...')
# covered_by 用 manifest 主键 id（不是 mat_id）：按 filename 反查 fetch() 返回的 Path
_idx={m['filename']: m['id'] for m in read_manifest(slug,variant)['materials']}
update_user_todo_status(slug, variant, '<task 子串>', 'done', covered_by=[_idx[p.name] for p in got if p.name in _idx])
```
> 📎 *茅五泸三家年报+季报完整循环范例 → `_00_reference.md` §Step6.5a*

### 6.5a-ann：A 股临时公告 → list → LLM 标题分诊 → 按选下载（**不要一把梭全拉**）

> `fetch()` 默认 `with_announcements=False`（不再隐式拉全年公告流），公告改走**显式三步**，由 LLM 看标题决定拉哪些。**本段用 `./.venv/bin/python`。**

1. `list_announcements_cn(ticker, days=180)` 只拿标题（不下载）；
2. 主 agent 按 thesis/K# 判 `selected`（判断留对话，不写脚本）——**拉**：临床读出/适应症获批/BLA·NDA 受理/BD·License/重大合作/业绩预告快报/命门相关自愿披露；**丢**：议事规则/薪酬制度/辞职换届/股东会通知/利润分配/回购进展/募投变更/独董提名等程序治理件；>50 条按日期窗口批量判；
3. `download_announcements_cn(ticker, slug, variant, selected)`（source_type='announcement'），照 `_autofetch_protocol.md` 盖戳闭环（task 子串/文档身份，不用 K# 求交）。
> 📎 *list/download 完整代码范例 → `_00_reference.md` §Step6.5a-ann*

### 6.5b：分析材料（卖方研报/行业数据/政策/科普）→ sidecar-first 惰性阶梯

非报告类 todo（sell-side / industry-research / policy / data / 科普）**照 workflow 01 Step 5.6 同一 sidecar-first 惰性阶梯逐字执行**——阶梯（① adapter sidecar 搜索默认首选、正文落盘不进 context → ② `web_fetch_exa` 精准取权威 URL 全文落盘、03 复用 → ③ exa 高级搜索仅补充、**默认不取 `text`** 省 token）、token 中性质量理由、snippet 兜底纪律**均见该步**，不在此重列。

> **本步作用域（00 特化）**：post-thesis 阶段只抓 00 自己产的非报告类 pending todo；命令透传 `--triggered-by 00-deep-fetch --addresses <K#>`。

抓到 → 落 `prism/topics/{slug}/inbox/{descriptive_name}.md`（资料只在 topic 层）→ `add_material` 入库 → 按 task 子串 `mark_todo_fetch('fetched')` + `update_user_todo_status('done', covered_by=[mat])`。

### 6.5c：盖戳纪律（照 `_autofetch_protocol.md`，三态必显式盖）

- 抓到入库 → `fetched` → `done`；
- **有效尝试**确认公开无源 → `empty`（留 `pending` 交用户，触发 empty 硬闸门，**不静默写缺口**）；
- 工具/网络/限流失败 → `error`（**必须重试，绝不降级**；本轮等不了就先盖 `error` 交 01/R3 下轮重试）。
- `hard` 也要尝试一次（草根纪要/付费数据多半 `empty`，但 empty 要由**真实结果**证明，不由标签预判——付费卖方深度常有公开转载）。
- 闭环只走 task 子串（文档身份），**禁止用 K# 交集自动 done**。
- **标 `empty` 前必须实际搜索**：adapter 搜 `--output sidecar`（自动写 `web_search_log`）或原生 WebSearch tool 搜完调 `log_native_websearch()`。**6.5e 闸门脚本会校验**——`web_search_log` 无痕的 `empty` 会被 `verify_empty_todos_searched` 拦截。

### 6.5d：刷新 next_actions + 输出对照表

eager-fetch 跑完，**重设 next_actions**（覆盖 Step 6 的占位），让"你需要做的事"只剩真 `empty`：

```python
# 重设 next_actions 覆盖 Step 6 占位；remain = [td['task'] for td in read_topic()['user_todos'] if td.get('fetch_status')=='empty']
set_next_actions(slug, [f'00 eager-fetch 已抓 N 份；剩 {len(remain)} 条公开无源待你决策', '运行 workflow 01-gather（只补抓自己新增 todo + R3 重试 error）'], variant)
```
并在对话输出一张逐条标 `fetch_status` 的对照表（同 01 Step 5.6 格式：todo | info_tier | 获取方式 | fetch_status）。
> 📎 *set_next_actions 范例 + 对照表样式 → `_00_reference.md` §Step6.5d*

> **纪律**：跑完 6.5 后，"你需要做的事"里**只应剩真·`empty`**（付费墙/App/草根纪要等有效尝试后确认公开无源的）。任何 `fetched`/能自动下的还躺在用户清单里 = 违产即收，回 6.5a/b 补抓。

---

### Step 6.5e：auto-fetch 全覆盖硬闸门（**未通过不得进 Step 7**）

> 📎 *为什么必须做 / 与 01 同源 → `_00_reference.md` §A6.5e（执行时可跳过）*

```bash
python3 << 'EOF'
from prism.scripts.topic import pending_unfetched_todos
from prism.scripts.web_prescan import verify_empty_todos_searched

p = pending_unfetched_todos('{slug}', '{variant}')
unattempted = [t for t in p if t.get('fetch_status') == 'unattempted']
errored     = [t for t in p if t.get('fetch_status') == 'error']

if unattempted:
    print('❌ 00 产即收违规：以下 todo 从未尝试过抓取（fetch_status=unattempted）——')
    print('   info_tier 只决定努力顺序，不是跳过门槛（auto-fetch 规约 R1）。回 Step 6.5b 逐条跑阶梯并 mark_todo_fetch：')
    for t in unattempted:
        print(f'   - [{t.get("info_tier")}] {t["task"][:60]}')
    raise SystemExit(1)

if errored:
    print('⚠ 以下 todo 抓取失败（fetch_status=error），按退避梯重试；本轮带过将由 01 的 R3 续抓：')
    for t in errored:
        print(f'   - {t["task"][:60]}')

# 搜索证据校验：empty 的 todo 必须在 web_search_log 中有对应记录
v = verify_empty_todos_searched('{slug}', '{variant}')
if v['unverified']:
    print(f'❌ empty 证据缺失：{len(v["unverified"])} 条 todo 标了 empty 但 web_search_log 中无对应搜索记录——')
    print('   adapter 搜索会自动留痕；用原生 WebSearch tool 搜完需调 log_native_websearch() 留痕。')
    for t in v['unverified']:
        print(f'   - {t["task"][:60]}')
    raise SystemExit(1)

if v['empty_todos']:
    print(f'✅ {len(v["empty_todos"])} 条 empty todo 已通过搜索证据校验')

print('✓ 00 auto-fetch 全覆盖通过：无 unattempted（每条 todo 都已有效尝试过）')
EOF
```

如果非 0 退出，回 Step 6.5b 补搜。**`unattempted`+`empty` 证据两条都通过才能进 Step 7。**

---

### Step 7：告知用户

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
