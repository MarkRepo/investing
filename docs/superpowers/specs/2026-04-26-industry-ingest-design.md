# 行业研报 ingest 子系统 · 设计

**Status**: 设计已定，待 writing-plans 出实施计划
**Date**: 2026-04-26
**Supersedes**: `docs/PLAN-INDUSTRY-INGEST.md`（v0，已废弃）

---

## 1. 背景与动机

现有系统只处理聚焦单家公司的财报与卖方研报，行业研报（一份文件跨 ≥2 家公司的"行业深度/专题/策略"）被拒收。当下把一份行业研报硬塞进现有结构会把**行业事实错位寄生到公司层**——这不是假设，是现状：

- `companies/BSE_920118/claims.jsonl` 前 5 条中有 4 条是纯行业事实（十四五电网投资 3 万亿、2026 电缆市场 1.5 万亿、5G 基站光缆 CAGR 14.5%、特高压装机），跟太湖远大本身无关，但没处放只好塞进 ticker=920118 的 claims
- `arenas/cn-power-cable-polymer-material/competence-notes.md` 里 `q_power_grid_tam / q_policy_subsidies_barriers / q_domestic_consolidation` 这几条，问的是行业事实却挂在"太湖远大"公司名下，下次导万马股份就得再抄一遍
- 现有 `industries/{sector}/` 走 5 桶白名单（consumer/saas/cyclical/bank/biotech），粒度太粗、与 arena 不对齐、新建行业要改代码

根因：系统里没有"产业"这个一等公民。需要把产业事实层独立出来，并重构 arena/company 的职责边界，使三层各司其职、不重复复写同一事实。同时行业研报导入需要**跨报告交叉验证**能力（不同卖方对同一产业的 TAM/CAGR/竞争格局会给不同数字）。

## 2. 产出目标（11 维度）

一份行业研报 ingest 后，系统要能回答该产业的 11 个核心维度（CFA Level 1 + Porter + Damodaran 综合）：

| # | 维度 | 核心内容 | 数据形态 |
|---|---|---|---|
| 1 | 定义与边界 | 行业做什么、子行业/品类划分、与相邻行业边界 | narrative |
| 2 | 市场规模与增长 | 全球/分地域 TAM、历史/未来 CAGR、分品类拆解 | structured observations |
| 3 | 生命周期阶段 | Embryonic/Growth/Shakeout/Mature/Decline + 判据 | enum observation + narrative |
| 4 | 产业链分析 | 上/中/下游 + 各环节成本占比 + 议价权分布 | narrative + segment observations |
| 5 | 竞争结构 | Porter 五力 + 集中度 HHI/CR5 + 头部公司市占 | structured observations |
| 6 | 增长驱动与催化 | 技术/需求/政策/宏观；短期 catalysts | narrative |
| 7 | 技术与产品 | 工艺原理、产品品类、技术演进路径、关键指标 | narrative |
| 8 | 监管与政策 | 监管框架、行业标准、补贴/税收、贸易政策、环保合规 | narrative |
| 9 | 关键经营指标基准值 | 行业特有指标 + 优秀/平均/差基线 | structured observations |
| 10 | 主要风险 | 周期/政策/技术替代/客户集中/上游依赖/合规/汇率 | narrative |
| 11 | 投资视角与估值锚 | Damodaran 三元 + 历史 PE/PB/EV 中枢 + 选股逻辑 | narrative + structured observations |

"结构化"意味着可跨报告字段级聚合（自动算 median/range/spread、outlier 标记）；"narrative"意味着按 source 分块并列，不强行合并。

## 3. 核心设计决策（14 条）

| # | 决策 | 取舍 |
|---|---|---|
| D1 | industry 作为一等公民，与 arena/company 并列三层 | 不做两层嵌套（topic > arena），概念干净而实现轻 |
| D2 | industry slug 中粒度，跟随报告主题（如 `cn-cmp-material`），**无白名单** | 卖方切分单位即默认 industry 单位；不做 sector 宽切（TAM 交叉验证无意义） |
| D3 | industry 存"市场格局"，arena 存"战场参与者" | 两层 players 语义不同，不重复 |
| D4 | 双模式存储：`observations.jsonl`（结构化字段） + 按维度拆的 `*.md`（叙事） | 单 JSONL 渲染难、单 markdown 无法字段级聚合，都不可取 |
| D5 | 交叉验证 lazy：写入不检测冲突，页面层按 field 聚合渲染 diff/outlier | ingest 流程简单；用户一定会打开页面 |
| D6 | 旧错位数据（BSE_920118 等）不迁移，新规则只对新导入生效 | 迁移脚本难写得可靠；历史数据原地保留有溯源价值 |
| D7 | subagent 按预处理 section 粒度派发（而非按 11 维度） | 并发度可控（每份报告 3-8 个 section），subagent prompt 统一，维度跨 section 时在聚合阶段合并 |
| D8 | 分流识别：文件名关键词 + 预处理扫 ≥2 独立 ticker → AskUser 确认 | 半自动；纯关键词误判率高，纯 flag 太麻烦 |
| D9 | **sector 概念完全删除**：`VALID_SECTORS` 白名单、`competence-sector/` 能力圈模板、`app/io/competence.py` 、`companies/*/competence-check.md` 全部废 | 用户明确指令；能力圈概念搬到 industry 层（见 D10） |
| D10 | industry 级别新增 checklist（类 arena checklist），承担"行业认知完整度引导"角色 | 替代旧 sector 能力圈；arena checklist 继续存在但收窄到"公司×战场交互" |
| D11 | company meta frontmatter `industry_primary` 字段改名为 `industry_slugs: [list]`，freeform 不卡白名单 | 一家公司可属多 industry；迁移零成本 |
| D12 | industry checklist bootstrap：agent 读报告 + 11 维度生成草稿 → 用户 AskUser 审改 | 同 arena bootstrap pattern，冷启动有内容 |
| D13 | ingest 行业研报时同时扫 industry checklist + 所有 linked arena 的 checklist（未答/vague 的 items） | 研报顺手回答 arena 问题，避免重复劳动 |
| D14 | 阅读体验 v1 先做"数据 backlink + 页面 cross-ref"；brief 聚合视图单独拆后续 plan | 本次 scope 可控；brief 是"阅读体验根治"重点，独立评估 |

## 4. 数据模型

### 4.1 三层目录布局

```
industries/{slug}/                  # 新一等公民。废旧 industries/{sector}/，slug 无白名单
├── meta.yaml                       # slug / name / scope / lifecycle_stage / linked_arenas / linked_tickers / created / last_updated
├── observations.jsonl              # 结构化字段事实（每行一条，见 §4.2）
├── checklist.yaml                  # 认知引导问题（见 §4.3）
├── checklist-answers.md            # checklist 回答（按 q_id × source_id 分段，见 §4.3）
├── definition.md                   # §1 维度 narrative
├── value-chain.md                  # §4
├── technology.md                   # §7
├── drivers.md                      # §6
├── regulation.md                   # §8
├── risks.md                        # §10
├── valuation.md                    # §11
└── sources/                        # 原研报 PDF 存档

arenas/{slug}/                      # 位置不变
├── definition.md                   # frontmatter 新增字段: industry: {slug}（多对一）
├── checklist.yaml                  # 收窄：只问"公司×战场交互"，不再问纯行业问题
└── competence-notes.md

companies/{key}/                    # 位置不变
├── meta.md                         # frontmatter 字段改：industry_primary → industry_slugs: [list]
│                                   # competence-check.md 文件删
├── profile-YYYY.md
├── claims.jsonl                    # 收窄：不再混入行业 TAM/政策（通过 prompt 约束，不做 schema 强制）
└── ...
```

### 4.2 observation schema（`industries/{slug}/observations.jsonl` 行格式）

```json
{
  "id": "cmp-material-0001",
  "dimension": "market_size",
  "field": "tam_global",
  "value": 33.8,
  "unit": "usd_bn",
  "timeframe": "2025",
  "segment": null,
  "metric_type": "atomic",
  "time_type": "actual",
  "source_id": "行研-国金证券-2026-03-10-abc12345",
  "source_file": "2026-03-10_国金_半导体材料CMP行业.pdf",
  "source_note": "研报引用 Market Growth Reports",
  "confidence": "high",
  "claim_text": "2025 年全球 CMP 抛光液和抛光垫市场规模约为 33.8 亿美元",
  "evidence": "根据 Market Growth Reports 统计，2025 年全球 CMP 抛光液和抛光垫的市场规模约为 33.8 亿美元",
  "extracted_by": "claude-opus-4-7",
  "extracted_at": "2026-04-26T..."
}
```

字段说明：

- `dimension` ∈ `INDUSTRY_DIMENSIONS`（见 §4.4）。固定 11 个值，闭集
- `field` 开放词表。`INDUSTRY_FIELDS` 给初版建议清单，用户可扩展
- `value` 数值 / `unit` 单位。enum 字段 value 是字符串（如 lifecycle.stage = `"growth"`）
- `metric_type`: `atomic` (单一数) | `enum` (枚举判断) | `segment` (分品类/分 ticker 拆解)
- `time_type`: `actual` (历史/当前) | `forecast` (未来预测)。交叉验证 UI 按此分组，`forecast` 不和 `actual` 混算
- `segment`: 若 metric_type=segment，填子类别（如 slurry/pad，或 ticker）
- `source_id`: 行业研报格式 `行研-{institution}-{date}-{sha8}`；同份报告所有 observation 共用
- `confidence`: `high` | `medium` | `low`（由 subagent 判定，原文明确量化=high，引用间接数据=medium，表述模糊=low）

### 4.3 checklist schema（`industries/{slug}/checklist.yaml`）

```yaml
slug: cn-cmp-material
version: 1
last_updated: '2026-04-26'
changelog:
  - version: 1
    date: '2026-04-26'
    source_id: 行研-国金证券-2026-03-10-abc12345
    changes: initial bootstrap from 国金 CMP 行研
items:
  - id: q_cmp_tam_cross_source
    question: 不同数据源对全球与中国 CMP 材料市场规模的测算是否一致，差异来自什么
    why_matters: TAM 量级不一致意味着赛道大小判断有分歧，直接影响估值锚
    maps_to:
      dimension: market_size
      fields: [tam_global, tam_china, cagr_global, cagr_china]
    tags: [market_size, cross_source]
  - id: q_slurry_pad_value_chain
    question: CMP 抛光液和抛光垫的上游关键原料（磨料 SiO2/CeO2/Al2O3、聚氨酯）集中度和国产化进度
    why_matters: 上游卡脖子会压制国产替代逻辑
    maps_to:
      dimension: value_chain
      fields: null
    tags: [value_chain, technology]
  - id: q_cmp_concentration_trend
    question: CMP 抛光液/抛光垫全球头部格局（Dupont / 安集 / 鼎龙 / Fujibo 等）在过去 5 年的变化方向
    why_matters: 头部份额稳不稳决定国产替代的空间天花板
    maps_to:
      dimension: concentration
      fields: [hhi, cr5, share_by_player]
    tags: [concentration, competitive_position]
```

answers 文件 `checklist-answers.md`（与 arena competence-notes 同构，按 q_id × source_id 分段）：

```markdown
---
slug: cn-cmp-material
---

# 认知库 · cn-cmp-material

## q_cmp_tam_cross_source · level=specific
来源：行研-国金证券-2026-03-10-abc12345 · checklist v1 · 2026-04-26

国金报告内部就给出了两个冲突数字：华经统计 2024 年中国 CMP 抛光液 29.6 亿元，弗若斯特沙利文测算 23 亿元，差 28%。全球 TAM 33.8 亿美元（Market Growth Reports）与中国单品类 TAM 放在一起推算，隐含中国占比约 40-50%，与头部份额集中在国内（安集 10%）逻辑一致。

> 根据 Market Growth Reports 统计，2025 年全球 CMP 抛光液和抛光垫的市场规模约为 33.8 亿美元...根据华经产业研究院统计，2023 年中国 CMP 抛光液市场规模约为 29.6 亿元；根据弗若斯特沙利文测算，2024 年中国 CMP 抛光垫市场规模约 23 亿元。
```

### 4.4 维度固定清单 + 字段初版

`app/config.INDUSTRY_DIMENSIONS`（元组，闭集）：

```python
INDUSTRY_DIMENSIONS = (
    "definition", "market_size", "lifecycle", "value_chain",
    "concentration", "drivers", "technology", "regulation",
    "benchmark", "risks", "valuation",
)
```

`app/config.INDUSTRY_FIELDS`（字段初版建议，开放扩展，不做强白名单）：

```python
INDUSTRY_FIELDS = {
    "market_size":  ["tam_global", "tam_china", "tam_by_segment"],
    "lifecycle":    ["stage", "stage_evidence"],                  # stage: enum embryonic/growth/shakeout/mature/decline
    "concentration": ["hhi", "cr5", "cr10", "share_by_player"],
    "benchmark":    ["gross_margin_leader", "gross_margin_avg",
                     "capex_intensity_avg", "rd_ratio_leader"],
    "valuation":    ["pe_ttm_median", "pb_median", "ev_ebitda_median"],
    # porter 五力作为 concentration 的子组（每力一个 field，metric_type=enum，value 为 1-5 评分）
    # 其余维度（definition/value_chain/drivers/technology/regulation/risks）默认走 narrative，
    # 用户可在需要量化的场景自行新增 field，不卡白名单
}
```

维度 `definition` 只承载 narrative 不存 observation。`value_chain / drivers / technology / regulation / risks` 同理，但如果某份报告有量化事实（如"磨料占抛光液成本 54.6%"），subagent 可选填 segment observation。

## 5. ingest pipeline（行业研报 workflow）

```
1. /ingest <pdf>
2. 分流识别（SKILL.md Step 1）
   - 文件名命中 "行业/深度/industry/sector/strategy" 或预处理扫出 ≥2 独立 ticker
   - AskUserQuestion: [行业研报 / 公司深度研报 / 取消]
3. 预处理
   scripts.preprocess_report <file> --type industry --market {a-share,us} --out <json>
   templates/{a-share,us}-industry.yaml 剔除封面/免责/目录/风险提示套话
   输出: sections[] + detected_tickers[] + meta{institution, report_date, sha8}
4. industry slug 确认
   - 主 agent 基于报告标题 / 首段 / 目录推一个候选 slug (如 cn-cmp-material)
   - AskUserQuestion: [新建候选 slug / 选择已有 / 改名]
   - 新建 → auto-create industries/{slug}/meta.yaml 骨架（name / scope / linked_arenas=[] / linked_tickers=[]）
5. arena 识别（可选，v0 PLAN Q3=A 沿用）
   - 对 detected_tickers 调 arenas_io.find_by_company() 反查
   - 命中 → 加入 linked_arenas；未命中 → AskUser 是否 bootstrap；拒绝 → 降级跳过 arena
6. 首次新建 industry 的 checklist bootstrap（仅首次 ingest 该 industry 时执行）
   - 派 bootstrap-checklist subagent（Explore）：读报告 + 11 维度 + 字段初版清单
     → 产 10-15 题 initial checklist 草稿
   - AskUser 审/改/批准后写入 industries/{slug}/checklist.yaml v1
   - 注：此 subagent 只产问题，不产答案；Step 7b 的 industry-checklist-answer 再针对刚生成的问题产答案。
     这两个 subagent 对同一份报告读两遍，是刻意分工（prompt 各司其职），不合并。
7. 派发 3 类 subagent（Explore，并发上限 5 分批）
   a. section-extract：每个预处理 section 一个。prompts/industry/section-extract.md
      注入：section text + dimensions + field inventory + source_id + 11 维度产出 schema
      产出：{ observations: [...], narratives: { dimension → md_block }, per_ticker_claims: { ticker → [claim,...] } }
   b. industry-checklist-answer：1 个。prompts/industry/checklist-answer.md
      注入：report 全文 + industry checklist 未答/vague items + maps_to 提示
      产出：{ industry_answers: { q_id → {level, summary, evidence_quote} } }
   c. arena-checklist-answer：每个 linked arena 一个。同上 prompt，注入对应 arena checklist
      产出：{ arena_answers: { arena_slug: { q_id → {...} } } }
8. 主 agent 聚合（scripts.ingest_aggregate 新增 helper）
   - observations dedup（同 field + timeframe + source_id 保留 confidence 最高）
   - narratives 按 dimension 合并成单段 md block（顶部标 "### 来源 {institution} {date}"）
   - per_ticker_claims：经 subjects_io.validate_batch → claims schema 校验
   - checklist answers：consolidate（同 q_id 取 level 最高）
9. 用户审 4 处（按顺序）
   - industry observations（表格：新增 N 条）
   - industry narratives（每维度 md block 预览）
   - industry + arena checklist 新答案（按 q_id + arena 分段）
   - per-ticker claims（按 ticker 分段，数量多时分批）
10. 写入（用户批准后）
    - observations.jsonl append，source_id = `行研-{institution}-{date}-{sha8}`
    - 每维度 narrative .md 尾部插 "### 来源 {institution} {date} (sha8={sha8})" 段
    - industries/{slug}/meta.yaml 更新 linked_arenas / linked_tickers / last_updated
    - industries/{slug}/checklist-answers.md 按 q_id × source_id 追加段
    - arenas/{slug}/competence-notes.md 追加段（现有 arenas_io.append_notes）
    - 各 ticker claims.jsonl append（现有 claims_io.append_batch），
      source_id = `行研-{institution}-{date}-{sha8}-{ticker}` （附 `-{ticker}` 后缀，
      避免同份报告产生的 N 组 per-ticker claim 撞 id；sha8 关联回同一份 PDF）
    - sources/ 存档 PDF
11. QA checkpoint
    scripts.ingest_qa warn --write + gap --write（不跳过）
```

source_id 格式：`行研-{institution}-{date}-{sha8}`（industry observations / narrative / checklist-answers 共用；per-ticker claims 额外附加 `-{ticker}` 后缀保持跨 claim 层的唯一性）。

## 6. arena / company 的配合改造

### arena 收窄

- `arenas/{slug}/definition.md` frontmatter 加 `industry: {slug}` 字段（多对一），bootstrap 时主 agent 推 industry → AskUser 确认。旧 arena 补齐 `industry: null` 后由下一次 ingest 自动回填
- `arenas/{slug}/checklist.yaml` 的 bootstrap prompt（`prompts/arena/bootstrap-checklist.md`）更新：规定"不生成 TAM/CAGR/HHI/产业政策 这类纯行业问题，那类走 industry checklist；只生成公司×战场交互问题"
- 现有 arena checklist 的纯行业 items（如 `q_power_grid_tam` `q_domestic_consolidation` `q_policy_subsidies_barriers`）**不主动迁**，在 arena 下注解但保留（D6：历史不动）

### company 收窄

- `companies/{key}/meta.md` frontmatter 字段改：`industry_primary: {value}` → `industry_slugs: [list]`
  - `app/io/company.py` 不再校验白名单，freeform slug 数组
  - 旧 3 份 meta 迁移：`cyclical` → `industry_slugs: []`（置空，下次 ingest 回填），保留 `arenas: [...]` 字段
- `companies/{key}/competence-check.md` 文件删除
- claims extraction prompt（per-ticker subagent）规定："只抽与本公司直接相关的事实；研报引用的行业 TAM/政策/同业市占不抽成 claim"
- 跨层反查：新增 `industry_io.find_by_company(ticker, market)` 扫所有 `industries/*/meta.yaml` 的 `linked_tickers` 字段

## 7. 阅读视图（v1：跨层 cross-ref）

**数据层 backlinks**（§4 已埋好）：
- `industries/{slug}/meta.yaml`: `linked_arenas`, `linked_tickers`
- `arenas/{slug}/` frontmatter: `industry: {slug}`
- `companies/{key}/meta.md`: `industry_slugs: [list]`, `arenas: [list]`

**页面层 cross-ref**（v1 本次 scope）：

| 页面 | 顶部面包屑 | 侧边/底部关联区 | 维度内交叉展示 |
|---|---|---|---|
| `/industries/{slug}` | industry 名 | 参与者列表（→ `/companies/{key}`）、关联 arena（→ `/arenas/{slug}`）、原文 `/sources/{file}` | 每个结构化 dim 表格：observations 按 source 折叠；spread>30% 高亮；forecast/actual 分组；每 observation 的 source 可点 |
| `/arenas/{slug}` | 所属 industry（→）→ arena 名 | 参与者（→ company）、checklist item 的 `maps_to.dimension` → industry 对应 section | checklist item 旁显示 industry 对应 dim 的 observation 片段 |
| `/companies/{key}` | industry_slugs tag（→） + arenas tag（→） | 所属 arena checklist 完成度 + industry checklist 完成度 | claim 按 subject_tag 分组（现状保留） |

**跨层分歧渲染规则**（只在 industry 页做）：

- atomic 数值字段：`table {source | timeframe | value | unit}` + 顶部 `median / range / spread` + `spread>30%` 红色 🚨
- enum 字段：各 source 判断并列；一致 → 🟢；分歧 → 🟡 展开对比
- narrative .md：默认展开最新一份 + 折叠其他；用户可勾选多份侧边栏对照

**不在本次 scope（拆后续 plan）**：`/brief/{slug}` 按决策问题聚合视图、首页决策仪表盘。

## 8. 代码改动清单

### 删除

- `app/config.VALID_SECTORS` 白名单整条
- `app/io/industry.py`（旧 sector 承载，重写）
- `app/io/competence.py`（旧能力圈）
- `app/routes/competence.py`
- `controlled-vocab/competence-sector/*.yaml`（5 个）
- `templates/competence-check.md.tmpl`
- 所有 `companies/*/competence-check.md` 旧文件（已核对 3 份均为 0 分空骨架，无用户手写内容，删除安全）
- 所有 import `VALID_SECTORS` 的代码点（`company.py` / `routes/companies.py` / 等）

### 迁移（一次性，含在本次 PR）

- 现有 3 份 `companies/*/meta.md` frontmatter：`industry_primary: {value}` → `industry_slugs: []`（保留 arenas 字段）
- `app/io/company.py` 字段校验逻辑移除白名单分支
- `docs/USER-GUIDE.md` / `docs/DEVELOPER-GUIDE.md` 对应章节改写
- `.claude/skills/ingest/SKILL.md` 中 sector 提示行移除 + 支持范围更新
- `.claude/skills/ingest/workflows/sell-side-note.md` Step "问 sector" 整段改为"问 industry slug"（freeform，AskUser 手填或选已有）
- 旧 `docs/PLAN-INDUSTRY-INGEST.md` 文件头部加 `Status: superseded by specs/2026-04-26-industry-ingest-design.md` 注记（保留历史，不删）

### 新增

**核心 IO 层**：

- `app/io/industry.py`（完全重写）
  - `list_industries() -> list[dict]`
  - `read_meta(slug)` / `write_meta(slug, fm)`
  - `read_observations(slug) -> list[dict]` / `append_observations(slug, rows)` / `dedup_observations(rows)`
  - `read_narrative(slug, dimension)` / `append_narrative_block(slug, dimension, block, source_meta)`
  - `read_checklist(slug)` / `write_checklist(slug, items, changelog_entry)` / `bump_version(slug)`
  - `consolidate_checklist_answers(raw)` / `append_checklist_answers(slug, q_id, body, source_id)`
  - `find_by_company(ticker, market) -> list[slug]`（扫 meta.yaml.linked_tickers）
- `app/io/arenas.py`：
  - `read_arena` 返回字段加 `industry`
  - `write_definition` 接受 `industry` 参数
  - `bootstrap` 相关函数更新

**config**：

- `app/config.INDUSTRY_DIMENSIONS`（11 元组，闭集）
- `app/config.INDUSTRY_FIELDS`（dict，初版建议清单，不做强校验）

**routes + templates**：

- `app/routes/industries.py`（完全重写为 slug 路由）
  - `/industries/` 列表
  - `/industries/{slug}` 详情（11 维度 + 跨源聚合 + 关联 arena/company）
  - `/industries/{slug}/checklist` 清单页 + 完成度
- `app/templates/industries/*.html`（slug 详情模板 + observation diff 表 + checklist 页）
- `app/routes/arenas.py` + 模板：加 industry 顶部链接
- `app/routes/companies.py` + 模板：industry_slugs tag 显示 + 跨层跳转

**预处理 + 聚合**：

- `scripts/preprocess_report.py`：加 `--type industry` 分支；`detected_tickers[]` 扫描；meta 提取 institution / report_date / sha8
- `.claude/skills/ingest/templates/a-share-industry.yaml`（新，剔除规则）
- `.claude/skills/ingest/templates/us-industry.yaml`（新）
- `scripts/ingest_aggregate.py`：新增
  - `write_industry_observations(slug, rows)` + dedup
  - `write_industry_narrative(slug, dim, block, source_meta)`
  - `write_industry_checklist_answers(slug, consolidated)`
  - `write_arena_checklist_answers(arena_slug, consolidated)`

**ingest skill**：

- `.claude/skills/ingest/SKILL.md`：支持范围放开到行业研报；补关键资源索引（industry 维度清单 / field inventory / bootstrap prompt 位置）
- `.claude/skills/ingest/workflows/industry-report.md`（新，完整 workflow）
- `.claude/skills/ingest/prompts/industry/section-extract.md`（新，统一 section subagent prompt）
- `.claude/skills/ingest/prompts/industry/checklist-answer.md`（新）
- `.claude/skills/ingest/prompts/industry/bootstrap-checklist.md`（新）
- `.claude/skills/ingest/section-routing.yaml`：加 `industry-generic` 通道
- `.claude/skills/ingest/source-id-rules.yaml`：加 `行研-` 格式

**tests**：

- `tests/test_industry_io.py`（slug CRUD / observations dedup / narrative append / checklist version bump / find_by_company）
- `tests/test_ingest_industry_aggregate.py`（observations schema / narrative formatting / checklist consolidation）
- `tests/test_preprocess_industry.py`（ticker 扫描 / meta 提取）

## 9. 跨验证呈现示例（CMP 用例）

假设先后 ingest 了国金 2026-03-10 和一份虚拟的华泰 2025-12-01 CMP 报告，industry 页 `市场规模` 维度渲染：

```
§2 市场规模与增长                                              [2 sources]

atomic · market_size.tam_global                               median 34.7  range 33.8-35.6  spread 5%
┌──────────────────────┬──────────┬────────┬────────┬────────┐
│ source               │ timeframe│ value  │ unit   │ conf   │
├──────────────────────┼──────────┼────────┼────────┼────────┤
│ 国金 2026-03-10      │ 2025     │ 33.8   │ usd_bn │ high   │
│ 华泰 2025-12-01      │ 2025     │ 35.6   │ usd_bn │ high   │
└──────────────────────┴──────────┴────────┴────────┴────────┘

atomic · market_size.tam_china                                🚨 spread 28%
┌──────────────────────┬──────────┬────────┬────────┬────────┐
│ 国金 2026-03-10      │ 2024     │ 29.6   │ cny_bn │ high   │ (华经)
│ 国金 2026-03-10      │ 2024     │ 23.0   │ cny_bn │ high   │ (弗若斯特沙利文)
│ 华泰 2025-12-01      │ 2024     │ 27.2   │ cny_bn │ medium │
└──────────────────────┴──────────┴────────┴────────┴────────┘

atomic · market_size.cagr_global (forecast)                   2025-2034
┌──────────────────────┬──────────┬────────┬────────┬────────┐
│ 国金 2026-03-10      │ 2025-2034│ 4.5%   │ -      │ high   │
│ 华泰 2025-12-01      │ 2025-2030│ 5.0%   │ -      │ high   │
└──────────────────────┴──────────┴────────┴────────┴────────┘
```

用户看到 `tam_china` 同一份报告内部就有 2 条冲突（华经 29.6 vs 弗若斯特沙利文 23），外部再加华泰 27.2 —— 一眼看清有多少不确定性。

## 10. 破坏性变更与兼容策略

**破坏性（一次性完成，预期在 CI 验证下通过）**：

- `VALID_SECTORS` 相关引用从代码完全移除（import 失败点在 CI 会暴露）
- `company.meta.industry_primary` 字段迁移（3 份 meta 一次性改写）
- 旧 `app/io/industry.py` API 签名完全变（基于 sector 的 `read/write(sector, kind)` → 基于 slug 的完整新 API）；若有外部代码依赖旧签名需同步改，项目内扫过确认只有 `app/routes/industries.py` 引用
- `app/routes/competence.py` + 模板删，URL `/competence/*` 消失。历史 bookmark 会 404

**不破坏**：

- 现有 claims.jsonl / profile-*.md / financials.db 格式不变
- arena 文件格式不变（只加 frontmatter 字段 `industry`，解析旧文件向后兼容即可）
- ingest 现有 workflow（annual / quarterly / sell-side）不动

**已知遗留问题**（design 决策 D6 的代价）：

- `BSE_920118/claims.jsonl` 的 id=0001-0005 中 4 条属于行业事实错位，但保留以维持历史完整性；后续若用户手动整理可一次性迁移到对应 industry observations
- `cn-power-cable-polymer-material/competence-notes.md` 的 `q_power_grid_tam / q_policy_subsidies_barriers / q_domestic_consolidation / q_overcapacity_risk` 几条答案挂公司名下但实为行业事实；同上保留
- 新 ingest 按新规则写入，不会继续累积此类错位

## 11. 不做的事（显式排除）

- ❌ 自动冲突检测（D5）
- ❌ industry observation → company claim 自动联动（两个独立事实层）
- ❌ 迁移旧错位数据（D6）
- ❌ brief 聚合视图 /brief/{slug}（v1 scope 外，后续 plan）
- ❌ 首页决策仪表盘重做（scope 外）
- ❌ 将来预测进 `metric_type=atomic`（用 `time_type=forecast` 区分，渲染上与 actual 分组）
- ❌ 行业新闻 / 电话会纪要 / 社媒 ingest（本次只处理正式行业研报 PDF）
- ❌ 多份报告之间自动合并 narrative 段（只按 source 并列，合并靠用户手动）

## 12. 测试策略

- unit：所有新 IO 函数（industry.py / ingest_aggregate 新增 helpers）+ 预处理 ticker 扫描
- integration：用国金 `化学机械抛光行业.pdf` 走完整 pipeline，断言
  - `industries/cn-cmp-material/` 各文件生成且结构正确
  - observations.jsonl 含 `market_size.tam_global=33.8 usd_bn @ 2025` 和 `market_size.tam_china` 同 source 下 29.6 与 23.0 两条并列（`source_note` 分别为"华经统计"和"弗若斯特沙利文测算"）
  - checklist.yaml v1 生成且 maps_to 字段齐
  - per-ticker claims 至少为安集/鼎龙生成 ≥3 条公司事实 claim，且不含 `market_size.tam_global` / `concentration.cr5` 这类本属 industry observation 的行业级事实
- regression：现有 sell-side-note / annual-report workflow 仍通过（保留 fixture）
- UI：industry 详情页渲染 spread>30% badge 的测试（需要 observations fixture 覆盖）

## 13. 未决 / 后续

- `/brief/{slug}` 聚合视图设计（下一个 spec）
- field inventory 初版是否够用：首批跑完 3-5 份行业研报后回头复盘，看哪些 dim 需要强结构化补字段
- industry checklist 问题质量：多次 bootstrap 后若用户频繁删改草稿，调整 `bootstrap-checklist.md` prompt
- arena checklist 的历史纯行业 items 是否主动清理（目前保留；首批新 ingest 跑完后评估）
- 跨 industry 的关系表达（如 `cn-cmp-material` 和 `cn-semiconductor-equipment` 存在上下游关系）：目前不表达，未来若需要可在 meta.yaml 加 `upstream_industries / downstream_industries` 字段

## 附录 A · 现有数据形态参考

- 行业研报样例：`~/Downloads/化学机械抛光行业.pdf`（国金证券 2026-03-10，12 页，封面"半导体材料行业研究：化学机械抛光行业"）
- 现有 arena checklist：`arenas/cn-power-cable-polymer-material/checklist.yaml`（含 15 items，tag 混用 industry_structure / competitive_position / growth_drivers 等 8 标签）
- 现有 arena notes：`arenas/cn-power-cable-polymer-material/competence-notes.md`（按 q_id × ticker 分段）
- 现有 claims 样例：`companies/BSE_920118/claims.jsonl`（混有行业错位 claim）/ `companies/SSE_600519/claims.jsonl`（纯公司事实）

## 附录 B · 废除 sector 级联影响 grep 清单

废 `VALID_SECTORS` 涉及文件（要同步改）：

```
app/config.py:23                      VALID_SECTORS 定义
app/io/company.py:11,51,52,162,164   import + sector 校验
app/io/industry.py:50,51,86          废 API 整体重写
app/io/competence.py:23,155,156      整个模块删
app/routes/companies.py:6,51,151     form 下拉去除
app/routes/industries.py:26,48,62    路由改为 slug
app/routes/competence.py:8,31,34     整个路由删
.claude/skills/ingest/SKILL.md:47              关键资源索引更新
.claude/skills/ingest/workflows/sell-side-note.md:38    Step "问 sector" 改写
docs/USER-GUIDE.md:63,102,297        章节改写
docs/DEVELOPER-GUIDE.md:123,251,299  同上
docs/PLAN-INDUSTRY-INGEST.md         整份标为 superseded
```

## 附录 C · 用例跟踪（CMP 端到端）

ingest `化学机械抛光行业.pdf` 预期产物：

1. `industries/cn-cmp-material/meta.yaml`（新建）
   - linked_tickers: `[{market: SSE, ticker: '688019', name: 安集科技}, {market: SZ, ticker: '300054', name: 鼎龙股份}, ...]`（报告提及且证据充分的）
   - linked_arenas: 如果 `cn-cmp-slurry` / `cn-cmp-pad` arena 已存在则加入；否则 empty + 提示用户 bootstrap
   - 注：cn-cmp-material 与现有 `cn-power-cable-polymer-material`（电缆料）是两个完全不同的 industry，没有交集，不会互相污染数据
2. `industries/cn-cmp-material/observations.jsonl` 约 15-25 条原子/segment/enum 事实
3. 7 份 narrative .md（definition / value_chain / technology / drivers / regulation / risks / valuation）
4. `industries/cn-cmp-material/checklist.yaml` v1 含 10-15 items
5. `industries/cn-cmp-material/checklist-answers.md` 针对被报告覆盖的 5-10 个 q_id 有答案
6. `companies/SSE_688019/claims.jsonl` 新增 3-5 条（安集 CMP 营收 / 全球份额 / 产能 / 研发）
7. `companies/SZ_300054/claims.jsonl` 新增 3-5 条（鼎龙抛光垫份额 / 武汉汉阳基地 60 万片/年 / 多品类布局）
8. 其他提及 ticker（上海新阳 / 时代新材等）若报告内容不足 2 句话则不建 meta 不产 claim（沿用 v0 PLAN 降噪规则）

---

**Next step**: 用 `superpowers:writing-plans` 出实施 plan（按代码改动清单 §8 的"删除 → 迁移 → 新增"三批拆 task，建议按 `app/io → scripts → .claude/skills/prompts → workflows → routes → templates → tests` 的依赖顺序实施）。
