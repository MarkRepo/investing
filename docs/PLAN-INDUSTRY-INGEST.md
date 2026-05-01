# 行业研报 ingest 设计 (v0)

> 状态：2026-04-26 3 个决策已拍板（见文末"已决策"段）。下一步 writing-plans 出可执行 plan。
>
> **注意：本文档描述的 digest-era 行业研报路径已被 endgame pipeline 替代。** 当前实现走 `review-bundle → ClaimRegistry → narrative` 路径；`companies/{ticker}/claims.jsonl` 和 `observations.jsonl` 均已废弃。本文档仅保留作历史设计参考。

## 范围

**覆盖**：一份文件跨 ≥2 家公司的卖方行业研报（"行业深度 / 专题 / 策略"），典型结构：行业总览 → 产业链 → 竞争格局 → 驱动因素 → 政策 → 周期位置 → 公司速览 → 重点推荐。

**不覆盖**：纯宏观策略、行业新闻、电话会纪要、公司公告。遇到继续拒绝。

## 核心观察

行业研报天然横跨三层知识库，不是单纯的"多公司 claim 通道"：

- **sector 层**（`industries/{sector}/`）— 已存在，`app/io/industry.py` 提供 read/write。章节结构（供需/成本曲线/监管/上下游/关键指标）原生匹配行业研报内容。
- **arena 层**（`arenas/{slug}/`）— 已存在，有 checklist + notes + participants。行业研报是 arena bootstrap 的主要场合。
- **company 层**（`companies/{ticker}/claims.jsonl`）— 仅对用户关心的 ticker 子集落 claim。

这三层各司其职，不重叠复写同一事实。

## 三路落盘映射

| section 语义 | 去向 | 写法 |
|---|---|---|
| 行业总览 / 产业链 / 驱动 / 政策 / 周期 | `industries/{sector}/landscape.md` | subagent 产增量，patch 对应章节（§供需 / §成本曲线 / §监管 / §上下游 / §关键指标），用户审 diff |
| 头部公司排名 / 市占率表 | `industries/{sector}/players.md` | 追加或更新表格行 |
| 细分竞争格局（护城河、替代威胁、客户结构） | `arenas/{slug}/checklist-v*.yaml` + `competence-notes.md` | subagent 填答 checklist（走 `consolidate_answers`）+ 追加 notes 段 |
| 公司速览 / 重点推荐 | `companies/{ticker}/claims.jsonl`（仅勾选的 ticker） | 按 sell-side 的 `prompts/sell-side/thesis.md` 抽 claim |

**不写**：profile / financials / meta（除非勾选的 ticker 对应 company 不存在 → 按 sell-side 的 auto-create 骨架 meta 一致走法）。

## 流程骨架

1. **入口判定**（`SKILL.md` Step 1）：文件名命中 `行业 / 专题 / industry / strategy / sector` 等关键词，或预处理扫出 ≥2 家公司候选 ticker → 走 industry 通道
2. **预处理**：`scripts.preprocess_report --type industry`，新模板 `templates/{a-share,us}-industry.yaml`
3. **sector 确认**：研报封面/前言通常能明确定位到 5 个 sector 之一；AskUserQuestion 让用户选 `VALID_SECTORS`
4. **arena 识别 / bootstrap**：复用现有 `prompts/arena/bootstrap-definition.md` 流程
5. **ticker 全扫**（决策 Q1=C）：主 agent 扫研报里出现的全部 ticker，**每家都派 subagent 抽 claim**。不做勾选交互。未在 `companies/` 下的 ticker 按 sell-side 规则 auto-create 骨架 meta
6. **派 subagent**（并发，按类型分组）：
   - sector-level section → `prompts/industry/sector-patch.md` subagent，产 `industries_append: {landscape_sections: {章节名 → 追加文本}, players_rows: [...]}`
   - arena-level section → `prompts/industry/arena-feed.md` subagent，产 `arena_answers: {q_id → answer}` + `arena_notes_append: str`（若 arena 降级跳过则该组不派）
   - 公司速览 / 重点推荐 → 对扫出的**每个** ticker 各派一个 `prompts/sell-side/thesis.md`（复用），产 per-ticker claims
7. **用户审 3 处**（按顺序）：
   - `industries/{sector}/landscape.md` 的**新增补充段预览**（非 diff——决策 Q2=append，只有追加没有替换，展示将要插入的文本）
   - arena checklist 新答案 + notes 新段（若跳过则无此步）
   - 每家 ticker 的 claim batch（数量多时按 ticker 分段确认）
8. **写入**：用户批准后一次性写四处（landscape append / players / arena checklist+notes / 各 ticker claims）
9. **QA checkpoint**：跑 `scripts.ingest_qa warn --write` + `gap --write`，同所有 workflow 标配

## source_id 规则

每家勾选的 ticker 各自一条：新增格式 `industry: "行研-{institution}-{date}-{sha8}-{ticker}"`。同一 PDF 产 N 组 claims，靠 sha8 关联回同一份文件。

sector-level 和 arena-level 产出不走 claims，不需要 source_id；但 patch 写入时要在文本里留来源注记 `> 来源：{institution} {date} (sha8={sha8})`，供后续追溯。

## 新增 / 改动文件

| 文件 | 动作 |
|---|---|
| `.claude/skills/ingest/workflows/industry-report.md` | **新** 主 workflow（约 sell-side-note 的 1.3 倍长） |
| `.claude/skills/ingest/templates/a-share-industry.yaml` | **新** A 股研报模板剔除规则 |
| `.claude/skills/ingest/templates/us-industry.yaml` | **新** 美股研报模板剔除规则 |
| `.claude/skills/ingest/section-routing.yaml` | 加 `industry-generic` 通道（industry_overview / value_chain / competitive / drivers / regulatory / cycle / company_snapshots / key_picks） |
| `.claude/skills/ingest/prompts/industry/sector-patch.md` | **新** subagent prompt |
| `.claude/skills/ingest/prompts/industry/arena-feed.md` | **新** subagent prompt |
| `.claude/skills/ingest/source-id-rules.yaml` | 加 `industry` 格式 |
| `scripts/preprocess_report.py` | 加 `--type industry` 分支 + 多 ticker 扫描 |
| `scripts/ingest_aggregate.py` | 加 `write_industries_patch` / `write_arena_feed` helper |
| `.claude/skills/ingest/workflows/sell-side-note.md` | Step 4a：多公司判定 → **转派** industry 通道（不再拒绝） |
| `.claude/skills/ingest/SKILL.md` | 支持范围更新 |

## 不改的东西

- `app/io/industry.py` / `app/io/arenas.py` / `app/io/claims.py`（现有 API 够用）
- 预处理主干代码
- 受控词表 `subjects.yaml`（暂不加 industry_* tags；首批跑完再看缺什么）
- QA 管道

## 风险 & 已知坑

- **landscape.md 膨胀**（Q2=append 的直接后果）：每份研报都在 5 个章节下追加"补充（来源 X 日期 Y）"段，landscape 会长成"日志流"。缓解：subagent prompt 约束"每章节追加 ≤200 字浓缩要点，不得复制原文段落"；定期由用户手动做一次"合并精简"（不在 ingest 流程内）。
- **ticker 全扫的 claim 噪声**（Q1=全扫的直接后果）：一份研报里被顺带提及的公司（如"XX 也在布局"1 句话）也会产 claim。缓解：subagent prompt 要求"证据 <2 句话的 ticker 直接返回空 claim list"，从 subagent 侧过滤；aggregate 层若某 ticker 产出 0 claim，自动跳过 `auto_create_meta`（避免为一笔带过的公司建骨架 meta）。
- **研报里的未来预测数字**（如"2027 年 TAM 将达 5000 亿"）会试图混进 landscape.md。subagent prompt 明确规定：只抽**历史/当前**事实到 landscape，未来预测**只能进 arena notes** 或 **标的公司 claim**，绝不进 industries/。

---

## 已决策（2026-04-26）

### Q1=C：ticker 全扫

- 扫出的**每个** ticker 都派 subagent 抽 claim。不做勾选交互。
- **降噪**：subagent prompt 规定"证据 <2 句话的 ticker 返回空 claim list"；aggregate 层对 0-claim 的 ticker 跳过 auto_create_meta。
- 不存在的 ticker 公司，按 sell-side 那套 auto-create 骨架 meta（推过 ≥1 条 claim 的才建）。

### Q2=B：landscape.md 一律 append 补充段

- subagent 按 5 个章节（§供需 / §成本曲线 / §监管 / §上下游 / §关键指标）各产一段浓缩要点（≤200 字）。
- patch 写入模式：在对应章节末尾插入 `### 补充 — {institution} {date} (sha8={sha8})` 二级块，**永不修改原有内容**。
- landscape.md 随时间长成"日志流"是已知代价；需要精简时用户手工做，不在 ingest 流程内。

### Q3=A：arena 识别失败降级跳过

- 若 arena 识别失败、用户也不愿 bootstrap：**跳过** arena-level section 的 subagent 派发，继续跑 sector-level + ticker claims。
- 写入完成后在产出清单里明确标注"本次未写入 arena"，提示用户后续可 `/arenas/new` 手动 bootstrap。

---

## 工期估算

批准后：

- preprocess + templates + section-routing：约 0.5 天
- 两个新 subagent prompt：约 0.5 天
- workflow 文件：约 1 天
- aggregate helper + source-id 规则：约 0.5 天
- sell-side Step 4a 改造 + SKILL.md 更新：约 0.3 天
- 端到端测试（找一份真实行业研报跑）：约 0.5 天

合计约 3.3 个工作日。
