# Plan 3: ingest workflow digest dispatch 升级

**日期：** 2026-04-26
**依赖：** Plan 1（三层 IO）+ Plan 2（preprocess + digest prompts + aggregate helpers）
**Scope：** 纯 markdown 文档升级。不改 Python，不加 IO，不改 schema。仅改写 `.claude/skills/ingest/SKILL.md` + 3 份 workflow + 新增 1 份 workflow。

**动机：**
Plan 2 已经把 digest prompt（一整份报告一个 subagent）+ aggregate helpers（`route_key_facts` / `write_industry_observations` / `write_industry_narrative` / `write_arena_narrative` / `write_company_narrative` / `facts_to_claims` / `ensure_industry_exists` / `ensure_company_exists` / `bootstrap_arena` 等）铺设完毕，但 Claude 在对话里读的"行动剧本"——`SKILL.md` 和 `workflows/*.md`——还停留在旧的 section-per-subagent 分派。Plan 3 把这些剧本升级到 digest dispatch 架构，同时补齐行业研报（industry-research）的完整 workflow，让 ingest skill 真正覆盖 Plan 2 打开的"三层 + 四类源"能力。升级完成后，所有 ingest 走"1 份报告 → 1 个 digest subagent → 主 agent 分拣三层落盘"的统一路径；旧的 7 种 section subagent + 3 种 sell-side subagent 归档，不再被调用。

**架构变化一览：**

- **旧 Step 7**：对每个 `action: extract` section 派一个 Explore subagent，并发 ≤ 5，每个 subagent 只看自己的 section 文本，返回 `{section, claims, profile_fragments, financial_rows, meta_updates, competence_findings, flags}`。
- **新 Step 7**：派 1 个 digest subagent，把整份报告（含 `figure_contexts` / `detected_tickers` / `known_arenas` / `dimension_ref` / `industry_fields_hint` / `subjects_whitelist`）一起喂给它；subagent 返回 `{key_facts[], narratives, proposed_arenas, flags}` 以及（仅 annual/quarterly）`financial_rows[]`。
- **旧 Step 8**：`agg.aggregate(outputs)` 按 section merge。
- **新 Step 8**：`agg.route_key_facts(key_facts)` 按 `target_layer` 分三桶（industry / arena / company），每桶独立走对应写入函数。
- **旧 Step 10**：写 `claims.jsonl` + `financials.db` + `profile-*.md` + `meta.md`。
- **新 Step 10**：写 `claims.jsonl`（company facts → `facts_to_claims`）+ `financials.db`（年/季报保留）+ 三层 narratives（`write_industry_narrative` / `write_arena_narrative` / `write_company_narrative`）+ 图表上下文（`write_figure_contexts`）+ industry observations（`write_industry_observations`）+ arena bootstrap（`bootstrap_arena`）+ `meta.md`（仅年报）；不再写 `profile-{year}.md`——事实层快照改为依赖 `companies/{key}/narratives/*.md`。

**核心约束（来自用户 feedback 文件 + Plan 2 遗留）：**

1. 不写 Python 脚本；aggregate 函数清单冻结在 Plan 2。Plan 3 全部是 markdown。
2. 旧 section-per-subagent 不保留为 fallback，直接切换到 digest 架构（旧 `prompts/sections/` 和 `prompts/sell-side/` 改名移到 `prompts/_v1_archived/`，保留历史做参考，但 workflow 不再引用）。
3. `industry-research.md` 是全新 workflow，不复用单公司 arena bootstrap（单公司 arena 是公司视角；行业研报的 arena 候选从 `proposed_arenas` 里来，逻辑不同）。
4. QA checkpoint（Step 10.5）：年/季/研报沿用当前 6 规则 `warn + gap`；行业研报只跑 `warn`（规则子集：`empty_evidence` / `self_contradict_specific` / `polarity_mismatch`），不跑 `gap`（`--company` 参数不适用，行业研报不绑定单一 company）。行研 QA 的规则精化留给 Plan 4。
5. autobuild 纪律（`feedback_ingest_autobuild_meta.md`）：industry / company 缺失 → `agg.ensure_industry_exists` / `agg.ensure_company_exists` 立刻建骨架，不中止。
6. fix-forward 纪律（`feedback_ingest_fix_forward.md`）：preprocess / dispatch 失败改 template / 正则 / 白名单；workflow 不给"主 agent 手工补"的一次性 workaround。
7. LLM workflow 纪律（`feedback_llm_workflow.md`）：Python 不调 LLM；LLM 判断由 Claude 在对话里做，aggregate helpers 只管校验 + 写入 + 查询。
8. base convention（Plan 2 遗留）：`industry_io` 的 `base` 是 `industries/` 目录本身；`arenas_io` / `company_io` 的 `base` 是项目根。workflow 一律不传 `base=`，让函数走默认值 (`cfg.INDUSTRIES_DIR` / `cfg.COMPANIES_DIR` / `cfg.ARENAS_DIR`）。**特例**：`agg.ensure_company_exists` 内部已做 base→project_root 转换，但 workflow 仍然不传 `base=`，走默认值即可。

---

## File Map

**Create (workflow):**
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/industry-research.md` — 全新 workflow（行业研报）

**Modify (workflow):**
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/annual-report.md` — 升级 Step 7/8/10（digest dispatch）
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/quarterly-report.md` — 同上
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/sell-side-note.md` — 同上

**Modify (skill root):**
- `/Users/yangqi/investing/.claude/skills/ingest/SKILL.md` — 加 industry 类型路由 + 三层知识系统说明 + 更新关键资源索引 + 更新"聚合/校验/写入库"章节

**Modify (routing config):**
- `/Users/yangqi/investing/.claude/skills/ingest/section-routing.yaml` — 简化：保留 `industry-generic`（digest 走 fallback）；`us-10k` / `us-10q` / `a-share-annual` / `a-share-quarterly` / `sell-side-generic` 降级成**只保留 `skip` 规则**（digest 无视 section-level subagent 字段；但 preprocess 仍然需要 `skip` 标记来丢弃样板章节）

**Archive (rename):**
- `/Users/yangqi/investing/.claude/skills/ingest/prompts/sections/` → `prompts/_v1_archived/sections/`
- `/Users/yangqi/investing/.claude/skills/ingest/prompts/sell-side/` → `prompts/_v1_archived/sell-side/`

**Do not modify in this plan (out of scope):**
- 任何 `app/**` 或 `scripts/**`（Plan 2 已冻结）
- 任何 `controlled-vocab/*.yaml`
- `app/routes/**`（Plan 4 scope）

---

## Phase A：industry-research.md 新 workflow

行业研报是 Plan 2 开通的新源类型，目前没有任何 workflow 覆盖它——必须先把它做出来，因为 Phase B/C 的升级会复用 Phase A 的 digest dispatch 骨架。

### Task 1: industry-research.md 骨架（Step 0-4：前置 + 输入 + autobuild industry + source_id + 原文落位）

**目标：** 产出 workflow 前半部分。覆盖从 `SKILL.md` 路由进来之后到"准备好派 digest subagent"之前的全部步骤。核心决策点：预处理 `--type industry`、industry slug 的 autobuild、行业研报 source_id 格式、原文字节落位到 `industries/{slug}/sources/`（**不是** `companies/{key}/sources/`）。

**文件改动：**
- Create: `/Users/yangqi/investing/.claude/skills/ingest/workflows/industry-research.md`（新文件，本 Task 产出 Step 0-4 共约 120 行）

**关键 markdown 骨架：**

```markdown
# workflow: industry-research

处理行业研报（非单公司聚焦）。主 agent（你）按步骤执行；digest subagent 只读整份报告，返回分层事实 + 叙事 + 候选 arena，由你统一校验、分拣、落盘。

**与其它 workflow 的核心差异：**

1. **主产物在 industry 层**：observations.jsonl（atomic 数值 / structured field / enum）+ narratives/*.md（11 维浓缩）+ figure_contexts.jsonl（图表上下文）。company / arena 层是附带产物。
2. **不写 financials**：行业研报谈公司通常 1-2 句，不是结构化财报。
3. **不写 profile**：profile 是单公司事实层快照，与行业无关。
4. **arena 是"主要来源"**：行研里的"国产替代 / 技术路线之争 / 龙头挑战"等章节是 arena 的最大催化源。`proposed_arenas` 由 digest 直接产出，主 agent 审用户后 `bootstrap_arena` 落盘，无需复用单公司 Step 4.5 的流程。
5. **company layer 是 opportunistic**：研报里每个被提到 ≥3 句话的 ticker 产 ≥1 条 company key_fact，公司缺失则 `ensure_company_exists` 自动建骨架。
6. **QA 只跑 warn，不跑 gap**：行研不绑单一 company，`ingest_qa gap --company` 无意义。

---

## 前置状态

- `SKILL.md` 已判定源类型为 `industry`（触发词：行业深度 / 行业研究 / 行业点评 / Sector Report / Industry Report）
- 已知：`file_path`；**未知**（由本 workflow 推导）：`industry_slug`（可能是已存在或需要 autobuild）、`market`（`a-share | us`，按机构语言和 ticker 前缀推）

---

## Step 1：输入校验

- 确认 `file_path` 存在且可读
- 推断 `market`：
  - 机构名在 `{国金/中信/中信建投/中金/华泰/...}` 之一 → `a-share`
  - 机构名在 `{Goldman/Morgan Stanley/JPM/Citi/BofA/...}` 或明显英文文件名 → `us`
  - 抽不到机构名 → 后续 Step 4b AskUserQuestion 补齐（复用 sell-side 的机构补齐流程）

---

## Step 2：预处理

```bash
.venv/bin/python -m scripts.preprocess_report "<file_path>" \
    --type industry \
    --market {a-share|us} \
    --out /tmp/ingest-<sha8>.sections.json
```

输出 JSON 关键字段：
- `meta.sha8` / `meta.institution` / `meta.publish_date` / `meta.detected_form`（值固定为 `industry-research-{market}`）
- `sections[*]`：action = skip（封面 / 免责 / 分析师 bio 等）或 extract（实际内容）
- `figure_contexts[]`：**本 workflow 主产物之一**；digest subagent 会读这些
- `detected_tickers[]`：研报出现的所有 ticker
- `report_abstract`（封面摘要）

---

## Step 3：解析预处理输出 + industry slug 判定 + autobuild

### 3a：institution + publish_date 补齐

若 preprocess 抽不到 `meta.institution` / `meta.publish_date` → AskUserQuestion（复用 sell-side Step 4b 的措辞）：
- **institution**：让用户给机构名（如"国金证券"/"Morgan Stanley"）
- **publish_date**：ISO `YYYY-MM-DD`

这两个字段决定 source_id，不能省。

### 3b：候选 industry slug 推导

**逻辑（主 agent 在对话里推，不派 subagent）：**

1. 读 preprocess 的 `report_abstract` + `sections[0:3]` 的 `text` 前 2K 字，提取核心行业术语（如"CMP 抛光材料"/"GLP-1"/"电力电缆"）。
2. 列已有 industries：
   ```python
   from app.io import industry as industry_io
   existing = industry_io.list_industries()   # [{slug, name, scope, ...}]
   ```
3. 根据核心术语匹配已有 industry：
   - 名称 / scope 含主关键词 → 候选
   - ≥1 候选 → 取匹配度最高的 1 个作 "match_candidate"；≥2 候选 → AskUserQuestion 让用户选
   - 0 候选 → 走 3c 新建

### 3c：industry slug 新建（若无已存在匹配）

AskUserQuestion 让用户给：
- **slug**（kebab-case，带地域前缀）：主 agent 给默认建议（如 `cn-cmp-material` / `us-glp1-therapy`）
- **name**（中文显示名）：主 agent 从报告标题推默认
- **scope**（1-2 句边界）：用户写或接受主 agent 草稿

```python
from scripts import ingest_aggregate as agg
result = agg.ensure_industry_exists(slug=user_slug, name=user_name, scope=user_scope)
if result["autobuilt"]:
    # 告知用户："已建 industries/{slug}/（含 11 份 narrative 骨架 + observations.jsonl）"
```

`ensure_industry_exists` 幂等：slug 已存在时 `autobuilt=False`，不抛错。

### 3d：industry_slug 最终确定

到本步结束，`industry_slug` 是一个已存在的 slug（要么是 3b 复用的，要么是 3c 刚建的）。后续步骤用这个 slug。

---

## Step 4：source_id 生成 + 原文落位

### 4a：source_id

```python
source_id = f"行研-{institution}-{publish_date}-{meta['sha8']}"
# 例：行研-国金证券-2026-03-10-abc12345
```

规则来自 `.claude/skills/ingest/source-id-rules.yaml` 的 `industry-research` 条目。

### 4b：碰撞检测

行研不写 `claims.jsonl`，所以不能用 `claims_io.read_claims` 做碰撞检测。改查 `industries/{industry_slug}/observations.jsonl`：

```python
existing_obs = industry_io.read_observations(industry_slug)
existing_ids = {o.get("source_id") for o in existing_obs}
if source_id in existing_ids:
    # AskUserQuestion: overwrite (= discard; jsonl is append-only) / discard / new_version (-v2)
    ...
```

### 4c：原文落位

行业研报的原文落到 **`industries/{slug}/sources/`**（不是 companies/）。由于 `app.io.industry` 当前没有 `save_source` helper，直接用标准库：

```python
from pathlib import Path
import shutil
from app import config as cfg

src_dir = cfg.INDUSTRIES_DIR / industry_slug / "sources"
src_dir.mkdir(parents=True, exist_ok=True)
dst = src_dir / Path(file_path).name
shutil.copyfile(file_path, dst)
# dst 现为 industries/{slug}/sources/{filename}
```

幂等：同名文件存在会被覆盖（同 `save_source_markdown` 行为）。
```

**验证：**
- 人工走读 Step 0→4，检查"从 `SKILL.md` 跳进来后我能不能一步步执行到 Step 4 结束"
- industry slug 的 autobuild 分支必须明确（现成 industry → 复用 vs 不存在 → `ensure_industry_exists`）
- 碰撞检测源从 `claims.jsonl` 改到 `observations.jsonl` —— 这一点在 annual/quarterly/sell-side 都不会有（它们都查 `read_claims`）

**commit message：** `add industry-research workflow skeleton (Step 0-4): preprocess, industry autobuild, source_id`

---

### Task 2: industry-research.md Step 5-8（digest dispatch + aggregate）

**目标：** 派 1 个 `industry-digest` subagent，读整份报告 + figure_contexts + detected_tickers + known_arenas 上下文，返回结构化 JSON；主 agent 落 `merged.json`，按 `target_layer` 分三桶。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/industry-research.md`（append Step 5-8，约 180 行）

**关键 markdown 骨架：**

```markdown
---

## Step 5：Digest dispatch（单 subagent，整份报告）

### 5a：准备 subagent context

主 agent 组装 digest subagent 的完整 prompt：

```python
import json
from app.io import arenas as arenas_io, industry as industry_io, claims as claims_io

# 5a.1 拼接整份报告文本（所有 action=extract 的 section 按 order 串起）
preprocess = json.loads(Path(f"/tmp/ingest-{sha8}.sections.json").read_text())
full_text_chunks = []
for s in preprocess["sections"]:
    if s.get("action") == "extract":
        full_text_chunks.append(f"### {s['heading_raw']}\n\n{s['text']}")
full_text = "\n\n".join(full_text_chunks)

# 5a.2 已知 arenas（同 industry 的 + 跨 industry 近义的）
known_arenas_same_industry = [
    arenas_io.read_definition(slug)
    for slug in arenas_io.find_by_industry(industry_slug)
]
known_arenas = [
    {
        "slug": a["slug"],
        "battleground_focus": a.get("battleground_focus", ""),
        "participants": [p.get("name") or p.get("ticker") for p in a.get("participants", [])],
        "industry": industry_slug,
    }
    for a in known_arenas_same_industry
]

# 5a.3 dimension_ref / industry_fields_hint（来自 app.config）
from app import config as cfg
dimension_ref = {
    "industry": list(cfg.INDUSTRY_DIMENSIONS),
    "arena":    list(cfg.ARENA_DIMENSIONS),
    "company":  list(cfg.COMPANY_DIMENSIONS),
}
industry_fields_hint = cfg.INDUSTRY_FIELDS  # Plan 1 定义

# 5a.4 figure_contexts（从 preprocess 出来就有）
figure_contexts = preprocess.get("figure_contexts", [])

# 5a.5 detected_tickers
detected_tickers = preprocess.get("detected_tickers", [])

# 5a.6 subjects_whitelist（给 company key_fact 的 subject_tag_hint 用）
subjects_whitelist = list(claims_io.load_subjects().keys())

# 5a.7 industry_context
industry_meta = industry_io.read_meta(industry_slug)
industry_context = {"slug": industry_slug, "name": industry_meta.get("name")}
```

### 5b：Dispatch

读 `.claude/skills/ingest/prompts/digest/_common.md` + `prompts/digest/industry-digest.md`，拼成最终 prompt：

```python
digest_common = Path(".claude/skills/ingest/prompts/digest/_common.md").read_text()
digest_industry = Path(".claude/skills/ingest/prompts/digest/industry-digest.md").read_text()

prompt = f"""
{digest_common}

---

{digest_industry}

---

## 你本次要处理的输入

file_meta:
  source_id: {source_id}
  institution: {institution}
  publish_date: {publish_date}
  sha8: {sha8}

industry_context: {json.dumps(industry_context, ensure_ascii=False)}

known_arenas: {json.dumps(known_arenas, ensure_ascii=False, indent=2)}

dimension_ref: {json.dumps(dimension_ref, ensure_ascii=False)}

industry_fields_hint: {json.dumps(industry_fields_hint, ensure_ascii=False, indent=2)}

subjects_whitelist: {json.dumps(subjects_whitelist, ensure_ascii=False)}

figure_contexts: {json.dumps(figure_contexts, ensure_ascii=False, indent=2)}

detected_tickers: {json.dumps(detected_tickers, ensure_ascii=False, indent=2)}

full_text: |
{_indent(full_text, "  ")}

---

现在请输出严格 JSON（顶层 keys: key_facts, narratives, proposed_arenas, flags；见 _common.md schema）。
"""
```

**派单**（用 Agent 工具，`subagent_type = "Explore"`；只读，无写权限；即便 prompt 很长 >50K 字也一次派，不分段——digest 的前提就是一次读完整份报告）：

```
tool: Agent
subagent_type: Explore
prompt: <上面拼好的 prompt>
```

**并发：** 行研只有一个 digest subagent，无并发问题。若 subagent 返回超时（>10min），AskUserQuestion 问是继续等 / 重派 / 中止。

### 5c：拒绝产出 section 级并行

**不要**回退到 section-per-subagent 模式（即使 digest 超时或报错）。研报总字数通常 30K-60K 字，远在 Opus 上下文范围内。失败 → 让用户用更窄的报告版本重 ingest，或手动切页数后重试。这是 fix-forward 的体现。

---

## Step 6：主 agent 汇总 + JSON 解析容错

```python
from scripts import ingest_aggregate as agg

raw_output = subagent_result   # str, subagent 返回的整段文字
digest = agg.load_json_tolerant(raw_output)
# load_json_tolerant 会剥掉 ```json fence、处理尾随逗号等容错
```

**健康检查**（失败 → pause）：

```python
required_keys = {"key_facts", "narratives", "proposed_arenas", "flags"}
missing = required_keys - set(digest.keys())
if missing:
    # AskUserQuestion: digest 返回 JSON 缺 {missing}。选项：重派 digest / 继续但跳过该字段 / 中止
    ...
```

**把 digest 落盘到 `/tmp/ingest-{sha8}.digest.json`**（Step 10.5 QA 消费）：

```python
Path(f"/tmp/ingest-{sha8}.digest.json").write_text(
    json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

---

## Step 7：按 target_layer 分三桶

```python
buckets = agg.route_key_facts(digest["key_facts"])
# buckets = {"industry": [...], "arena": [...], "company": [...]}
```

**预期分布**（行研）：
- `industry`：50-70% 的 key_facts（TAM / competition / drivers / ...）
- `arena`：15-25%
- `company`：10-25%
- 少量 `cross` 会被同时放进 `industry` 和 `company` 两桶

若某桶异常（如 `industry` 桶 0 条），在最终报告里打 flag；但不阻塞流程。

---

## Step 8：公司 layer 的 autobuild pass

digest 返回的 `company` 桶里每个 fact 带 `target_refs.ticker` + `target_refs.market`。对每个唯一 (ticker, market)：

```python
company_facts = agg.group_company_facts(digest["key_facts"])
# {(ticker, market): [facts]}

for (ticker, market), facts in company_facts.items():
    # 从 facts[0] 或 detected_tickers 里推 company 显示名
    ticker_info = next((t for t in detected_tickers
                        if t["ticker"] == ticker and t["market"] == market), {})
    name = ticker_info.get("name") or f"{market}_{ticker}"

    # industry_slugs 至少含本次的 industry_slug
    result = agg.ensure_company_exists(
        ticker=ticker, market=market, name=name,
        industry_slugs=[industry_slug],
        currency="CNY" if market in ("SSE", "SZSE", "BSE") else "USD",
    )
    if result["autobuilt"]:
        # 告知用户："已建 companies/{market}_{ticker}/（骨架）"；
        # name 不准可后续 /edit-meta 改
```

**注意**：`ensure_company_exists` 不问用户 sector（行研没有好的 sector 判据）。此时 meta.md 的 sector 字段留默认空或 "unknown"；等后续 ingest 年报 / 研报时再由那时的 workflow 用 AskUserQuestion 补。

若用户不希望静默建公司骨架，可在 autobuild 前 AskUserQuestion 列出候选公司 + 让用户批量选择 / 排除。默认行为是静默建（减少用户打扰）。
```

**验证：**
- 核对 prompt 拼接格式与 `_common.md` 的 "输入（主 agent 在你的 prompt 里会提供）" 段落完全对齐，不漏任何 key（industry_fields_hint / known_arenas / detected_tickers）
- `group_company_facts` / `route_key_facts` / `ensure_company_exists` 三个函数签名与 `scripts/ingest_aggregate.py` 一致

**commit message：** `add industry-research Step 5-8: digest dispatch, routing, company autobuild`

---

### Task 3: industry-research.md Step 9-10（交叉校验 + 统一写入）

**目标：** 按"已审"流程落盘三层数据（industry observations / narratives / figure_contexts；arena narratives + bootstrap；company narratives + claims）。写入顺序严格：原文 → figure_contexts → observations → narratives → arenas → companies。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/industry-research.md`（append Step 9-10，约 220 行）

**关键 markdown 骨架：**

```markdown
---

## Step 9：交叉校验（行研精简版）

行研的 cross-check 与 annual 不同：

- 不跑 `revenue_consistency`（行研没 total revenue 锚）
- 不跑 `period_consistency`（行研事实跨多 FY / 多 timeframe；众数概念无意义）
- **跑** `empty_section`（检查 digest 是否忘了某层）
- **新增** `industry_observation_sanity`（自建简单校验，见下）

```python
issues = []

# 9.1 empty layer check（手写，不调 agg；agg.check_empty_sections 是针对
# section-per-subagent 模式的，digest 模式下不适用）
if not buckets["industry"]:
    issues.append("industry 桶为空（行研核心产物缺失）")
if not digest.get("narratives", {}).get("industry"):
    issues.append("narratives.industry 为空（digest 未产出浓缩叙事）")

# 9.2 industry_observation_sanity：
# 对每条 industry fact，若 field_hint 非空，value_numeric 必须非 None；
# timeframe 必须非空；unit 必须非空
for f in buckets["industry"]:
    if f.get("field_hint") and f.get("value_numeric") is None:
        issues.append(f"industry fact idx={f['idx']} field={f['field_hint']} 缺 value_numeric")
    if not f.get("timeframe"):
        issues.append(f"industry fact idx={f['idx']} 缺 timeframe")
    if f.get("field_hint") and not f.get("unit"):
        issues.append(f"industry fact idx={f['idx']} field 有 value 但缺 unit")
```

**触发处理：** issues 非空 → AskUserQuestion 展示前 10 条，让用户选"接受差异（继续写入但标 flag） / 重派 digest（回到 Step 5b） / 中止"。

---

## Step 10：统一写入

**写入顺序**（前一步失败则中止；不回滚已写）：

### 10.1 原文（Step 4c 已做）

### 10.2 figure_contexts（行研主产物）

```python
source_meta = {
    "source_id": source_id,
    "institution": institution,
    "date": publish_date,
    "sha8": sha8,
    "source_file": Path(file_path).name,
}

n_fig = agg.write_figure_contexts(
    slug=industry_slug,
    contexts=figure_contexts,        # 来自 preprocess
    source_meta=source_meta,
)
# 注意：write_figure_contexts 的 slug 参数是 industry_slug（唯一绑定）
```

### 10.3 industry observations（atomic 数值）

```python
from datetime import datetime, timezone
extracted_by = "claude-opus-4-7"
extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

n_obs = agg.write_industry_observations(
    buckets["industry"],   # + cross layer 已被 route_key_facts 复制进来
    source_meta,
    extracted_by=extracted_by,
    extracted_at=extracted_at,
)
```

`write_industry_observations` 内部自动按 `target_refs.industry_slug` 分拣——一份行研可能涉及**多个** industry（如 "半导体材料行业深度" 触及 `cn-cmp-material` / `cn-photoresist` 两个）；write 层按 slug 独立 append 并 dedup。

### 10.4 industry narratives（11 维浓缩段）

`digest["narratives"]["industry"]` 的 shape 为 `{dim: md_block}`（单 slug 上下文）。但 IO 函数期望 `{slug: {dim: md_block}}`——主 agent 要 wrap 一层：

```python
industry_nar_payload = {industry_slug: digest["narratives"].get("industry", {})}
n_nar_ind = agg.write_industry_narrative(industry_nar_payload, source_meta)
```

**多 industry 的情况**：digest subagent 可能在 `narratives.industry` 里嵌套成 `{slug: {dim: ...}, slug2: {dim: ...}}` —— 主 agent 检测 `narratives.industry` 的第一层 key：
- 若 key 都在 `INDUSTRY_DIMENSIONS` 集合里 → 单 slug，wrap 一层
- 若 key 看起来是 slug（包含 "-" 或在 existing slugs 里）→ 已是 slug 维度，直接传

```python
first_keys = set(digest["narratives"].get("industry", {}).keys())
dim_set = set(cfg.INDUSTRY_DIMENSIONS)
if first_keys and first_keys.issubset(dim_set):
    industry_nar_payload = {industry_slug: digest["narratives"]["industry"]}
else:
    industry_nar_payload = digest["narratives"].get("industry", {})
```

### 10.5 arena narratives（若有）

```python
arena_nar = digest["narratives"].get("arena", {})
# arena_nar shape: {arena_slug: {dim: md_block}}
n_nar_arena = agg.write_arena_narrative(arena_nar, source_meta)
```

`write_arena_narrative` 在遇到 `arena_slug` 不存在（还没跑 `bootstrap_arena`）时会抛 FileNotFoundError。所以必须**先** 10.6 再 10.5——或者把 10.6 挪到 10.5 前面。**推荐顺序**：先 10.6 再 10.5。

### 10.6 proposed_arenas 审阅 + bootstrap

```python
proposals = agg.propose_arena_bootstrap(digest["proposed_arenas"])
# returns [{slug, name, industry, battleground_focus, participants}, ...]
```

**AskUserQuestion** 展示每个 proposal（slug / focus / participants），让用户批量选：
- approve 全部
- approve 部分（逐条勾选）
- approve 全部但 **逐条改 slug / focus**（用户编辑）
- 拒绝所有

**对每个 approved proposal**：

```python
for p in approved_proposals:
    agg.bootstrap_arena(p)
    # 此时 arenas/{slug}/ 下已有 definition.md + 5 份 narrative 骨架
```

bootstrap 完成后再跑 10.5（arena narrative append）。注意 digest 可能在 `narratives.arena` 里提到一个 `proposed_arenas[].tentative_slug` 对应的 narrative 段——用户如果 reject 了这个 proposal，要在 `arena_nar` 里删掉该 slug 后再 write。

### 10.7 company narratives

```python
comp_nar = digest["narratives"].get("company", {})
# shape: {MARKET_TICKER: {dim: md_block}}
n_nar_comp = agg.write_company_narrative(comp_nar, source_meta)
```

Step 8 已经做完 `ensure_company_exists` —— 所有 key 对应的目录都已存在。

### 10.8 company claims

行研的 company facts 数量通常很少（每个 ticker 1-3 条），但仍要写到 `companies/{key}/claims.jsonl`，因为 `facts_to_claims` 能把它们转成 claim schema：

```python
from datetime import datetime, timezone

for (ticker, market), facts in company_facts.items():
    claims_payload = agg.facts_to_claims(facts)
    if not claims_payload:
        continue
    n, errors = agg.write_claims(
        ticker, market, claims_payload,
        source_id=source_id,
        source_file=Path(file_path).name,
        extracted_by="claude-opus-4-7",
        extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    if errors:
        # 报给用户；不阻塞后续公司（行研是 opportunistic company layer，单家失败不中止）
        ...
```

**注意**：`facts_to_claims` 不填 `claim_type="quantitative"` 默认（除非 value_numeric 存在）。行研里大部分 company fact 是 qualitative（护城河 / 业务结构描述）。

### 10.9 industry meta 联动

若 bootstrap 了新 arena，需要让 `industries/{slug}/meta.yaml` 的 `linked_arenas` 字段追加：

```python
industry_meta = industry_io.read_meta(industry_slug)
existing_linked = set(industry_meta.get("linked_arenas") or [])
new_linked = set(p["slug"] for p in approved_proposals)
if new_linked - existing_linked:
    industry_meta["linked_arenas"] = sorted(existing_linked | new_linked)
    industry_io.write_meta(industry_slug, industry_meta)
```

若 autobuilt 了 company，需要追加 `linked_tickers`：

```python
existing_tickers = {(t["market"], t["ticker"])
                    for t in industry_meta.get("linked_tickers") or []}
new_tickers = [{"market": m, "ticker": t, "role": "mentioned"}
               for (t, m) in company_facts.keys()
               if (m, t) not in existing_tickers]
if new_tickers:
    industry_meta.setdefault("linked_tickers", []).extend(new_tickers)
    industry_io.write_meta(industry_slug, industry_meta)
```
```

**验证：**
- 写入顺序 10.6（arena bootstrap） → 10.5（arena narratives） 的依赖关系明确（没有先写 narrative 再建 definition 的死循环）
- 10.4 的单 slug vs 多 slug wrap 逻辑对齐 `write_industry_narrative` 的 shape 要求（`{slug: {dim: block}}`）
- 10.8 `facts_to_claims` 的 company fact 写入路径——失败不整体中止，因为行研 company layer 是 opportunistic

**commit message：** `add industry-research Step 9-10: cross-check, three-layer write with arena bootstrap`

---

### Task 4: industry-research.md Step 10.5-11 + 失败模式（QA + 收尾 + 失败树）

**目标：** QA checkpoint（行研专用精简版）+ 收尾报告模板 + 失败模式矩阵。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/industry-research.md`（append Step 10.5-11 + 失败模式表，约 80 行）

**关键 markdown 骨架：**

```markdown
---

## Step 10.5：QA checkpoint（行研精简版：仅 warn）

行研不绑单一 company，`ingest_qa gap --company` 无意义；只跑 `warn`，且规则子集限于 `empty_evidence` / `self_contradict_specific` / `polarity_mismatch`（这三条对 key_facts 也适用）。

**关键差异**：当前 `scripts.ingest_qa warn` 的 `--merged` 参数期望旧版 aggregate merge 格式（含 `claims` 顶层列表）。digest 模式下 `claims` 集中在 `company_facts` 里。解决办法：把 digest + `facts_to_claims` 的结果 **凑** 成一份"兼容" merged，喂给 `ingest_qa warn`：

```python
# 10.5.1 凑兼容的 merged.json
all_claims = []
for (ticker, market), facts in company_facts.items():
    all_claims.extend(agg.facts_to_claims(facts))

compat_merged = {
    "claims": all_claims,
    "flags_by_subagent": {"industry-digest": digest.get("flags", [])},
    "empty_subagents": [],
    "competence_findings": {"answered": [], "proposed_additions": []},
}
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(compat_merged, ensure_ascii=False, indent=2)
)
```

```bash
.venv/bin/python -m scripts.ingest_qa warn \
    --merged /tmp/ingest-{sha8}.merged.json \
    --preprocess /tmp/ingest-{sha8}.sections.json \
    --write --scope industry:{industry_slug}
```

**不跑 `gap`**。也**不用 `--arena`**（行研常触多 arena，挑一个没意义）。

**未来扩展**：行研专属 QA 规则（如 `figure_without_observation` / `arena_proposed_but_no_narrative` / `tam_unit_mismatch`）留到 Plan 4。

---

## Step 11：收尾报告

```
已 ingest 行业研报：industries/{industry_slug}/sources/{filename}
✓ industries/{industry_slug}/figure_contexts.jsonl  +{n_fig} 条
✓ industries/{industry_slug}/observations.jsonl    +{n_obs} 条
✓ industries/{industry_slug}/narratives/*.md       +{n_nar_ind} dim
{✓|⊘} arenas/{slug}/ (bootstrap)                    +{k_arenas} 新 arena / 全部拒绝
{✓|⊘} arenas/{slug}/narratives/*.md                +{n_nar_arena} dim across {k_arenas_total} arena
{✓|⊘} companies/{...} (autobuild)                   {k_auto_company} 家骨架 / 无
{✓|⊘} companies/{key}/narratives/*.md              +{n_nar_comp} dim
{✓|⊘} companies/{key}/claims.jsonl                 +{total_claims} 条 (source_id={source_id})
✓ industry qa_warnings: added={W} skipped_dup={Dd} reopened={Z}（scope=industry:{industry_slug}）
⊘ qa_gaps                                           行研不跑（无单一 company 绑定）
⊘ financials.db                                     行研不写
⊘ profile-*.md                                      行研不写

机构：{institution}
发布日期：{publish_date}
涉及公司 ticker（{len(detected_tickers)}）：{ticker_list_preview}
涉及 arena（{k_arenas_total}）：{arena_slug_list}
图表覆盖率：{fact_count_from_figures}/{n_fig} 图表产出 observation

下一步建议：
- 查看行业视图：`/industries/{industry_slug}`
- 查看新建 arena 的认知库：`arenas/{slug}/`
- 对照 detected_tickers 补 ingest 这些公司的年报 / 研报
- 行研 flags：
  - {flag 1}
  - {flag 2}
```

---

## 失败模式

| 场景 | 处理 |
|---|---|
| 预处理抽不到机构 / 日期 | Step 3a AskUserQuestion 补齐 |
| digest subagent 超时 / 返回非 JSON | Step 6 `load_json_tolerant` 尽力恢复；失败 → AskUserQuestion 重派 / 中止 |
| digest 返回 `industry` 桶为空 | Step 9 pause；AskUserQuestion 决定是重派 digest（补上 digest 已漏的 industry fact）还是接受（通常意味着报告不是典型行研——如"策略宏观"误入通道） |
| proposed_arenas 包含 `parent_industry_slug` 不在任何已存 industry 中 | Step 10.6 bootstrap 前 AskUserQuestion 让用户决定"改 parent / 先建 parent industry / 拒绝该 proposal" |
| industry slug 新建时用户给的 slug 已存在 | `ensure_industry_exists` 幂等；自然跳过新建，继续用该 slug（告知用户"slug 已存在，复用 scope 未更新"） |
| company autobuild 时 ticker 格式异常（如全角数字） | `ensure_company_exists` 不做清洗，直接调 `create_company`——后者会抛 ValueError；主 agent 在 Step 8 每家外面 try/except，记入 flags，跳过该家不阻塞 |
| QA warn 抛错（兼容 merged 结构不对） | Step 10.5 pause；把 error 报给用户，让用户选"跳过 QA 继续 / 中止"。QA 不影响已写入数据的完整性 |
| write_industry_narrative 抛 FileNotFoundError（某 dim 不在 INDUSTRY_DIMENSIONS 闭集） | digest 产出错了 dim key。把错误 dim 从 payload 里剥出来放 flags，继续 write 其它 dim；不整体中止 |

---

## 已知范围限制

- **单机构 / 多期合并**：同一机构发的同主题多期研报（季度 update），当前每次独立 ingest，不做 series 合并。未来可在 observations dedup 时做（已 Plan 2 范围内）。
- **跨 industry 研报**：digest 支持在 facts 里标不同 `target_refs.industry_slug`；但当前 workflow Step 3b 只处理一个主 industry（source 只落到主 industry 的 `sources/`）。跨行业需要 Plan 4 加"多 industry 绑定"扩展。
- **research 报告为 XLS/PPT**：preprocess 不支持；报告类型 force 到 "PDF/HTML/MD/TXT" 才进得来。
```

**验证：**
- 人工走读整份 `industry-research.md` Step 1→11，确认可串联
- 比对 annual/quarterly/sell-side 的 Step 11 报告模板结构，确保本 workflow 的版本风格一致（`✓ / ⊘ / {✓|⊘}` 前缀）
- QA checkpoint 的"兼容 merged 凑法"确实能喂给 `scripts.ingest_qa warn` 且不报错（依赖 Plan 2 现有的 QA scope 接受 `industry:...` 前缀——**此处有假设**，见风险章节）

**commit message：** `finish industry-research workflow with QA checkpoint, wrap-up, failure modes`

---

## Phase B：annual-report.md 升级到 digest dispatch

### Task 5: annual-report.md Step 7（section 派单 → 单 digest subagent）

**目标：** 把现有 Step 7（含 7b Arena checklist 路由）整段替换成 digest dispatch。保留 Step 4.5（arena 识别 + bootstrap）——这是单公司年报特有的，与行研的 `proposed_arenas` 路径不冲突。保留 arena checklist 的 bootstrap（4.5c），但**不再**在 Step 7b 做 item 路由——digest prompt 里把 checklist item 作为一个上下文段一起喂进去，让 digest subagent 在产 `competence_findings` 时直接对照（相当于把 7b 的路由合并进 digest prompt）。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/annual-report.md`（行 171-258，替换整个 Step 7 + 7b）

**关键 markdown 片段（新 Step 7）：**

```markdown
## Step 7：Digest dispatch（单 subagent，整份年报）

### 7a：准备 subagent context

主 agent 组装 annual-digest subagent 的完整 prompt。和行研不同的地方：
- 多了 `company_context`（ticker / market / name / industry_slugs / arenas）
- 多了 `subjects_whitelist`（claims subject_tag 白名单）
- 多了 `financial_line_rows`（preprocess 从三张表里粗抽的候选行）
- 多了 `checklist_items`（若 Step 4.5 有 `item_pool`）
- 少了 `known_arenas`（年报通常只绑 0-2 个 arena，直接用 `company_context.arenas` 覆盖）

```python
import json
from pathlib import Path
from app.io import arenas as arenas_io, industry as industry_io, claims as claims_io
from app import config as cfg

preprocess = json.loads(Path(f"/tmp/ingest-{sha8}.sections.json").read_text())

# 7a.1 整份报告文本（所有 extract sections）
full_text_chunks = []
for s in preprocess["sections"]:
    if s.get("action") == "extract":
        full_text_chunks.append(f"### {s['heading_raw']}\n\n{s['text']}")
full_text = "\n\n".join(full_text_chunks)

# 7a.2 company_context
meta_info = company_io.read_meta_with_body(ticker, market)
fm = meta_info["frontmatter"]
company_context = {
    "ticker": ticker,
    "market": market,
    "name": fm.get("name"),
    "industry_slugs": fm.get("industry_slugs") or [],
    "arenas": fm.get("arenas") or [],
}

# 7a.3 industry_context（若公司绑定了 industry，取第一个作 primary）
industry_context = None
if company_context["industry_slugs"]:
    primary_slug = company_context["industry_slugs"][0]
    try:
        im = industry_io.read_meta(primary_slug)
        industry_context = {"slug": primary_slug, "name": im.get("name")}
    except FileNotFoundError:
        pass   # 罕见；industry_slug 写在 meta 里但 industries/ 下没有

# 7a.4 known_arenas（公司已参与的）
known_arenas = []
for slug in company_context["arenas"]:
    try:
        a = arenas_io.read_definition(slug)
        known_arenas.append({
            "slug": slug,
            "battleground_focus": a.get("battleground_focus", ""),
            "participants": [p.get("name") or p.get("ticker") for p in a.get("participants", [])],
            "industry": a.get("industry"),
        })
    except FileNotFoundError:
        pass

# 7a.5 dimension_ref + industry_fields_hint
dimension_ref = {
    "industry": list(cfg.INDUSTRY_DIMENSIONS),
    "arena":    list(cfg.ARENA_DIMENSIONS),
    "company":  list(cfg.COMPANY_DIMENSIONS),
}
industry_fields_hint = cfg.INDUSTRY_FIELDS

# 7a.6 subjects_whitelist
subjects_whitelist = list(claims_io.load_subjects().keys())

# 7a.7 figure_contexts + detected_tickers（年报有 preprocess 产出）
figure_contexts = preprocess.get("figure_contexts", [])
detected_tickers = preprocess.get("detected_tickers", [])

# 7a.8 financial_line_rows（年报核心输入）
financial_line_rows = preprocess.get("financial_line_rows", [])

# 7a.9 checklist_items（若 Step 4.5 有 item_pool）
checklist_items_flat = [
    {"id": it["id"],
     "arena_slug": it["arena_slug"],
     "question": it["question"],
     "why_matters": it.get("why_matters", ""),
     "typical_evidence_section": it.get("typical_evidence_section", []),
     "tags": it.get("tags", [])}
    for it in item_pool.values()
]
```

### 7b：拼 prompt

```python
digest_common = Path(".claude/skills/ingest/prompts/digest/_common.md").read_text()
digest_annual = Path(".claude/skills/ingest/prompts/digest/annual-digest.md").read_text()

prompt = f"""
{digest_common}

---

{digest_annual}

---

## 本次输入

file_meta:
  source_id: {source_id}
  sha8: {sha8}
  fiscal_year: {meta['fiscal_year']}

company_context: {json.dumps(company_context, ensure_ascii=False)}

industry_context: {json.dumps(industry_context, ensure_ascii=False)}

known_arenas: {json.dumps(known_arenas, ensure_ascii=False, indent=2)}

dimension_ref: {json.dumps(dimension_ref, ensure_ascii=False)}

industry_fields_hint: {json.dumps(industry_fields_hint, ensure_ascii=False, indent=2)}

subjects_whitelist: {json.dumps(subjects_whitelist, ensure_ascii=False)}

figure_contexts: {json.dumps(figure_contexts, ensure_ascii=False, indent=2)}

detected_tickers: {json.dumps(detected_tickers, ensure_ascii=False, indent=2)}

financial_line_rows: {json.dumps(financial_line_rows, ensure_ascii=False, indent=2)}

checklist_items:
{json.dumps(checklist_items_flat, ensure_ascii=False, indent=2)}

full_text: |
{_indent(full_text, "  ")}

---

## 产出要求（除 _common.md 的 schema 外，年报专属）

1. **`financial_rows[]`** 必填（至少本期 + 上一期比较；用基础货币单位，A 股万元 → 元自行换算）
2. **`narratives.company.{ticker}`**（key 用 `{market}_{ticker}` 格式）必覆盖 ≥3 维
3. **`competence_findings.answered[]`**：对上面 checklist_items 里每条 item，尽量给出 level=concrete|vague|unanswered 的填答；附 evidence_quote
4. **`proposed_arenas`** 仅当年报明确谈及一个还不在 company_context.arenas 里的博弈焦点

现在请输出严格 JSON（顶层 keys 至少含：key_facts, narratives, proposed_arenas, financial_rows, meta_updates, competence_findings, flags）。
"""
```

### 7c：Dispatch

```
tool: Agent
subagent_type: Explore
prompt: <上面拼好的>
```

**并发**：年报只有一个 digest subagent。**不分批、不分段**。若返回超时 → AskUserQuestion（同行研）。

**Section-level merge 不再发生**：digest 直接读整份文本，无"同名 section 合并"问题。`dispatch-merge-rules.md` 在新架构下不再被引用（但保留文件做归档）。
```

**验证：**
- 新 Step 7 的 context 拼装覆盖了 annual-digest.md prompt 里列的所有必需 input（对照 `_common.md` 的"输入（主 agent 在你的 prompt 里会提供）"段落）
- `checklist_items_flat` 的 shape 与 `prompts/arena/bootstrap-checklist.md` 里定义的 item schema 对齐
- 没有遗漏 `industry_context`（年报公司可能挂 0 个 industry；此时留空）

**commit message：** `annual-report.md Step 7: replace section-per-subagent with single digest dispatch`

---

### Task 6: annual-report.md Step 8（section merge → route_key_facts）

**目标：** 替换 Step 8 聚合逻辑。不再 `agg.aggregate(outputs)`；改为 `agg.route_key_facts(digest["key_facts"])` + 三桶分拣。保留 `merged.json` 落盘（QA 依赖）。`dedup_claims` 仍跑（company 层 facts 经 `facts_to_claims` 之后有可能重复）。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/annual-report.md`（行 261-294，替换整个 Step 8）

**关键 markdown 片段：**

```markdown
## Step 8：主 agent 汇总（按 target_layer 分三桶 + 构造兼容 merged）

```python
from scripts import ingest_aggregate as agg
import json

# 8.1 容错解析 digest 产出
digest = agg.load_json_tolerant(subagent_raw_output)

# 8.2 健康检查
required = {"key_facts", "narratives", "financial_rows", "flags"}
missing = required - set(digest.keys())
if missing:
    # AskUserQuestion: 重派 / 继续但视缺失字段为空 / 中止
    ...

# 8.3 按 target_layer 分桶
buckets = agg.route_key_facts(digest["key_facts"])
company_facts_grouped = agg.group_company_facts(digest["key_facts"])

# 8.4 company facts → claims schema（走 claims 通道）
claims_all = []
for (t, m), facts in company_facts_grouped.items():
    # 年报只处理本公司的 claims；ticker / market 不匹配的 group 丢掉（理论上不会出现）
    if t != ticker or m != market:
        # digest 偶尔在 detected_tickers 驱动下产出"非本公司 ticker"的 company fact；
        # 放 flags 里，不写入本公司 claims.jsonl
        continue
    claims_all.extend(agg.facts_to_claims(facts))

# 8.5 dedup claims
claims_all = agg.dedup_claims(claims_all)

# 8.6 凑 QA 兼容 merged 结构
merged = {
    "claims": claims_all,
    "financial_rows": digest.get("financial_rows", []),
    "meta_updates": digest.get("meta_updates", {}),
    "competence_findings": digest.get("competence_findings", {
        "answered": [], "proposed_additions": []
    }),
    "flags_by_subagent": {"annual-digest": digest.get("flags", [])},
    "empty_subagents": [],
}

Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
Path(f"/tmp/ingest-{sha8}.digest.json").write_text(
    json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

**为什么仍保留 `merged` 结构**：Step 10.5 的 `scripts.ingest_qa warn --merged` 期望这个 shape；Plan 2 没改 `ingest_qa` 接口。digest 数据在 `digest.json`（供 Plan 4 新 QA 规则消费），claims QA 数据在 `merged.json`。

**丢弃的字段**：`profile_fragments` —— 不再存在（digest 不产 profile 段）。新架构下 `profile-*.md` 由 company narratives 替代（`narratives/*.md`）。
```

**验证：**
- `dedup_claims` 在 company facts 转换后的 claims 上能工作（claim_text 去重；不依赖 `section` 字段）——对照 `scripts/ingest_aggregate.py:207-223` 的 `dedup_claims` 实现
- `merged` 结构喂给 `ingest_qa warn` 不报错（QA 的 rule runner 期望 `claims[*]` / `flags_by_subagent` / `competence_findings`——现已都在）

**commit message：** `annual-report.md Step 8: route_key_facts + compat merged for QA`

---

### Task 7: annual-report.md Step 10（三层写入重构）

**目标：** 用 digest 通道重写 Step 10。删除 profile 草稿审阅 + 落盘（profile 废弃）；加 industry / arena / company narratives 三写；保留 financials + claims + meta + competence。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/annual-report.md`（行 322-407，替换整个 Step 10）

**关键 markdown 片段：**

```markdown
## Step 10：统一写入（前一步失败整体中止）

写入顺序：原文 → financials → industry observations → figure_contexts → narratives(industry → arena → company) → proposed_arenas bootstrap → meta → claims → competence。

```python
from datetime import datetime, timezone
extracted_by = "claude-opus-4-7"
extracted_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

source_meta = {
    "source_id": source_id,
    "source_file": Path(file_path).name,
    "sha8": sha8,
    "institution": "company-primary",   # 年报一手披露
    "date": meta.get("reporting_period", ""),
}
```

### 10.1 原文（Step 6 已做）

### 10.2 financials（年报主产物）

```python
n_fin = agg.write_financials(
    ticker, digest.get("financial_rows", []),
    source_file=Path(file_path).name,
)
```

### 10.3 industry observations（若 digest 产了 industry 桶）

年报里如果 digest 抽到"公司视角的行业事实"（TAM / market_share / 竞争格局），会在 `buckets["industry"]`：

```python
n_obs = agg.write_industry_observations(
    buckets["industry"],
    source_meta,
    extracted_by=extracted_by,
    extracted_at=extracted_at,
)
```

**autobuild industry（若 digest 引用了一个公司 meta 里没有的 industry_slug）**：

```python
for f in buckets["industry"]:
    slug = (f.get("target_refs") or {}).get("industry_slug")
    if slug and slug not in company_context["industry_slugs"]:
        # 检查 industries/{slug}/ 是否存在
        try:
            industry_io.read_meta(slug)
        except FileNotFoundError:
            # digest 给了一个不存在的 slug；通常是 hallucinate
            # 策略：flags + 跳过写入这条 observation
            # 主 agent 不做 ensure_industry_exists（需要用户确认 name / scope）
            ...
```

### 10.4 figure_contexts（若 digest 产了 industry 桶 + 至少一个 slug）

年报的 `figure_contexts` 通常较少（IR 图表），但仍要归档：

```python
# 按 industry_slug 分组（多 industry 的话）
slugs_touched = {(f.get("target_refs") or {}).get("industry_slug")
                 for f in buckets["industry"]}
for slug in slugs_touched:
    if not slug:
        continue
    n_fig = agg.write_figure_contexts(
        slug=slug,
        contexts=figure_contexts,
        source_meta=source_meta,
    )
```

### 10.5 narratives（industry + arena + company）

```python
# industry narratives（年报补充，confidence=medium）
ind_nar = digest["narratives"].get("industry", {})
# 若 shape 是 {dim: block}，wrap 到单 slug
first_keys = set(ind_nar.keys()) if ind_nar else set()
dim_set = set(cfg.INDUSTRY_DIMENSIONS)
if first_keys and first_keys.issubset(dim_set):
    ind_nar_payload = {company_context["industry_slugs"][0]: ind_nar} \
        if company_context["industry_slugs"] else {}
else:
    ind_nar_payload = ind_nar
n_nar_ind = agg.write_industry_narrative(ind_nar_payload, source_meta)

# arena narratives（仅写已存在的 arena；proposed_arenas 先 bootstrap 再写）
arena_nar = digest["narratives"].get("arena", {})
known_slugs = set(company_context["arenas"])
arena_nar_existing = {k: v for k, v in arena_nar.items() if k in known_slugs}
n_nar_arena = agg.write_arena_narrative(arena_nar_existing, source_meta)
```

### 10.6 proposed_arenas bootstrap + arena meta 联动

```python
proposals = agg.propose_arena_bootstrap(digest.get("proposed_arenas", []))
# AskUserQuestion 审阅，同行研 Step 10.6
approved_proposals = [...]
for p in approved_proposals:
    agg.bootstrap_arena(p)
    # 追加到公司 meta 的 arenas
    company_context["arenas"].append(p["slug"])

# 写 newly-bootstrapped arena 的 narrative（digest 里可能在 narratives.arena 有段）
new_slugs = {p["slug"] for p in approved_proposals}
arena_nar_new = {k: v for k, v in arena_nar.items() if k in new_slugs}
n_nar_arena += agg.write_arena_narrative(arena_nar_new, source_meta)
```

### 10.7 company narratives

```python
comp_nar = digest["narratives"].get("company", {})
n_nar_comp = agg.write_company_narrative(comp_nar, source_meta)
```

### 10.8 meta 更新（含 arenas 联动）

```python
meta_updates = digest.get("meta_updates", {})
info = company_io.read_meta_with_body(ticker, market)
fm = dict(info["frontmatter"])

# 合并 LLM 给的 meta_updates（需用户审）
if meta_updates:
    # AskUserQuestion 展示 before/after 对比
    if user_approved:
        fm.update(meta_updates)

# 无论用户是否批 meta_updates，arenas 字段都要同步（已 bootstrap 的 arena 必须写回）
existing_arenas = set(fm.get("arenas") or [])
new_arenas = set(company_context["arenas"])   # 含新 bootstrap 的
if new_arenas - existing_arenas:
    fm["arenas"] = sorted(existing_arenas | new_arenas)

company_io.write_meta(ticker, market, fm, info["body"])
```

**注意**：旧 Step 10 有"输出 profile 草稿给用户审 → `company_io.write_profile`"的子步——**删除**。profile-*.md 在新架构下由 `companies/{key}/narratives/*.md` 替代；`write_profile` 不再被调用（函数保留在 IO 里，未来 Plan 4 可能清理）。

### 10.9 claims

```python
n, errors = agg.write_claims(
    ticker, market, claims_all,   # 来自 Step 8.4+8.5
    source_id=source_id,
    source_file=Path(file_path).name,
    extracted_by=extracted_by,
    extracted_at=extracted_at,
)
if errors:
    # 报给用户；建议回 Step 7 重派（需说明是哪类 claim 失败——subject_tag 白名单错？company_dimension_hint 错？）
    ...
```

### 10.10 competence

同旧 annual Step 10 step 6：`consolidate_answers` + AskUserQuestion 审 + 按 arena 分组 `append_notes` + 新 item `write_checklist`。代码与旧 workflow 一致，**唯一差异**：`findings` 来自 `digest["competence_findings"]`，不是 `merged["competence_findings"]`（虽然 8.6 也把它塞进 `merged` 了，两处同源）。
```

**删除原 10.3**"输出 profile 草稿给用户审"整段。改动后旧"6. competence 写入"编号变成 10.10，内容不变。

**验证：**
- 走读 10.1→10.10 的依赖关系：proposed arena bootstrap（10.6） 必须在 arena narrative append（10.5 第二次）之前——确保顺序对
- `write_profile` 调用被完全移除；profile-*.md 仍可存在（旧历史），但本 workflow 不再创建新的
- meta.arenas 同步逻辑正确——bootstrap 完立刻更新 fm，write_meta 一次性写回

**commit message：** `annual-report.md Step 10: three-layer writes, drop profile drafting, keep financials+claims+meta+competence`

---

## Phase C：quarterly-report.md + sell-side-note.md 升级

### Task 8: quarterly-report.md 升级（Step 7/8/10）

**目标：** 和 annual 类似，替换 Step 7（section → digest）、Step 8（merge → route）、Step 10（三层写入）。季报的特殊性：`financial_rows` 是主产物；不写 profile / meta 已经是现状；industry / arena narrative **大多为空**（季报不讲行业）；`digest["narratives"].company.{key}` 通常只填 `financial_profile` + `catalysts` 两维。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/quarterly-report.md`（行 159-213 替换 Step 7；行 216-250 替换 Step 8；行 273-331 替换 Step 10）

**关键 markdown 片段（替换 Step 7）：**

```markdown
## Step 7：Digest dispatch（单 subagent，整份季报）

### 7a：Context 组装

和 `annual-report.md` Step 7a 的代码 99% 相同，**差异**：

1. `period_code`（如 `2025Q3`）作为额外字段注入 prompt（见下 7b）
2. `financial_line_rows` 重要性更高（季报主产物）
3. 不期待 digest 产出 `proposed_arenas`（季报素材不支持新开战场——但代码不强制禁止，如果 digest 真产出，Step 10.6 照常审阅）
4. `checklist_items` 通常稀疏（季报多数 item 答 unanswered）

```python
# 复用 annual Step 7a 的代码；补一行 period_code
period_code = <Step 4 推出的>   # 如 "2025Q3"
```

### 7b：拼 prompt（区别于 annual 的附加指令）

复用 annual Step 7b 的结构，但 digest prompt 换成 `quarterly-digest.md`，并在最终 prompt 末尾多一段：

```
## 季报专属指令（覆盖 annual-digest）

- 所有 financial_rows[*].period 必须是 `{period_code}`（如 "2025Q3"），period_type="quarterly"
- 所有 key_facts 的 timeframe 主要是 `{period_code}`（少量 long-term / 跨期对比允许）
- A 股"本报告期"vs"本年累计"：只抽"本报告期"列
- 10-Q "three months ended" vs "nine months ended"：只抽 three months ended
- narratives.company 仅填 financial_profile + catalysts 两维；其它 6 维度不列 key
- meta_updates 通常留空（季报罕见更新公司简介）
- proposed_arenas 预期为空；若有，简要写原因到 flags
```

### 7c：Dispatch（同 annual）
```

**关键 markdown 片段（替换 Step 8 "季报特有的后处理"段落）：**

```markdown
## Step 8：主 agent 汇总

```python
digest = agg.load_json_tolerant(subagent_raw_output)
buckets = agg.route_key_facts(digest["key_facts"])
company_facts_grouped = agg.group_company_facts(digest["key_facts"])

# 季报专属后处理：
# 1. 丢弃 proposed_arenas（季报通道不处理；若非空入 flags）
dropped_proposed = digest.pop("proposed_arenas", [])
if dropped_proposed:
    digest["flags"].append(
        f"季报 digest 产出了 {len(dropped_proposed)} 个 proposed_arena，已丢弃"
        f"（季报素材不适合新开战场）"
    )

# 2. 丢弃 meta_updates（季报原则不刷 meta）
dropped_meta = digest.pop("meta_updates", {})
if dropped_meta:
    digest["flags"].append(f"季报 digest 产出了 meta_updates，已丢弃")

# 3. company facts → claims
claims_all = []
for (t, m), facts in company_facts_grouped.items():
    if t != ticker or m != market:
        continue
    claims_all.extend(agg.facts_to_claims(facts))
claims_all = agg.dedup_claims(claims_all)

# 4. 凑兼容 merged
merged = {
    "claims": claims_all,
    "financial_rows": digest.get("financial_rows", []),
    "meta_updates": {},
    "competence_findings": digest.get("competence_findings", {
        "answered": [], "proposed_additions": []
    }),
    "flags_by_subagent": {"quarterly-digest": digest.get("flags", [])},
    "empty_subagents": [],
}
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
Path(f"/tmp/ingest-{sha8}.digest.json").write_text(
    json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8"
)
```
```

**关键 markdown 片段（替换 Step 10）：**

```markdown
## Step 10：统一写入

季报写入清单（前一步失败整体中止）：

```python
source_meta = {
    "source_id": source_id,
    "source_file": Path(file_path).name,
    "sha8": sha8,
    "institution": "company-primary",
    "date": period_code,
}
```

### 10.1 原文（Step 6 已做）

### 10.2 financials（主产物）

```python
n_fin = agg.write_financials(
    ticker, digest.get("financial_rows", []),
    source_file=Path(file_path).name,
)
```

### 10.3 figure_contexts + industry observations（季报通常为空）

```python
# 仅在 digest 真抽到（季报罕见）时写：
n_obs = agg.write_industry_observations(
    buckets["industry"], source_meta,
    extracted_by="claude-opus-4-7",
    extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
)
# figure_contexts 同 annual Step 10.4 的代码；通常 n_fig = 0
```

### 10.4 narratives

```python
# 季报的 narratives.company 通常只有 financial_profile + catalysts 两维
comp_nar = digest["narratives"].get("company", {})
n_nar_comp = agg.write_company_narrative(comp_nar, source_meta)

# industry / arena narrative 通常为空
ind_nar = digest["narratives"].get("industry", {})
if ind_nar:
    # 按 annual 10.5 的 wrap 逻辑处理
    ...
arena_nar = digest["narratives"].get("arena", {})
if arena_nar:
    n_nar_arena = agg.write_arena_narrative(arena_nar, source_meta)
```

### 10.5 claims

```python
n, errors = agg.write_claims(
    ticker, market, claims_all,
    source_id=source_id,
    source_file=Path(file_path).name,
    extracted_by="claude-opus-4-7",
    extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
)
```

### 10.6 profile / meta（都不写）

- `profile-*.md` 不写（季报不触发事实层快照）
- `meta.md` 不写（Step 8 已丢弃 `meta_updates`）

### 10.7 competence

同旧 quarterly Step 10 step 6：`consolidate_answers` + AskUserQuestion + `append_notes`。

**不再有 `proposed_arenas` 处理** —— Step 8 已丢弃。
```

**验证：**
- 确认季报 Step 10 的 financial_rows 仍是主产物，不遗漏
- 确认 Step 8 的"丢 meta_updates + proposed_arenas"符合"季报原则不刷 meta / 不开新 arena"的设计约束
- narratives 的 company 部分正确落到 `companies/{key}/narratives/financial-profile.md` + `catalysts.md`

**commit message：** `quarterly-report.md: upgrade Step 7/8/10 to digest dispatch, drop meta_updates + proposed_arenas`

---

### Task 9: sell-side-note.md 升级（Step 7/8/10）

**目标：** sell-side 的特点：无 financial_rows（研报预测是 forecast，走 claims 通道带 `time_type="forecast"`）；大量 company claims；少量 industry / arena narrative；**保留** Step 4.5 的 arena bootstrap（单公司研报是 arena 的主要 bootstrap 触发源，逻辑不变——但下游 Step 7/8/10 变）。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/workflows/sell-side-note.md`（行 205-285 替换 Step 7；行 287-319 替换 Step 8；行 338-409 替换 Step 10）

**关键 markdown 片段（替换 Step 7）：**

```markdown
## Step 7：Digest dispatch（单 subagent，整份研报）

### 7a：Context 组装

和 annual Step 7a 的代码 99% 相同，**差异**：
- 注入 `publish_date` + `institution`
- 注入 `forecasts_hint`（若 preprocess 抽到 forecasts 段的表格 row）
- digest prompt 换成 `sell-side-digest.md`

```python
# 复用 annual Step 7a 的代码
# 加：
file_meta = {
    "source_id": source_id,
    "sha8": sha8,
    "institution": institution,
    "publish_date": publish_date,
}
```

### 7b：拼 prompt（额外指令）

复用 annual Step 7b 的结构，digest prompt 换成 `sell-side-digest.md`，最终 prompt 末尾加：

```
## 卖方研报专属指令

1. polarity 以**研报作者立场**为准（分析师看多 → bull）
2. **不要**产出 financial_rows（预测走 claims 通道，subject_tag=eps_forecast / revenue_forecast / target_price / rating）
3. 预测 claim 的 `time_type="forecast"`；历史 claim（如 FY2024A "已披露收入"）的 time_type="actual"
4. meta_updates 通常留空（研报不是一手披露源）
5. claim_text 开头可选择加 `[{institution} {publish_date}]` 前缀便于下游区分
6. proposed_arenas 极少（研报少开新战场，除非主题就是"国产替代"等明确博弈）
7. narratives.company.{key}.valuation 必填（研报核心产出）
```

### 7c：Dispatch（同 annual）
```

**关键 markdown 片段（替换 Step 8 "研报特有后处理"）：**

```markdown
## Step 8：主 agent 汇总

```python
digest = agg.load_json_tolerant(subagent_raw_output)
buckets = agg.route_key_facts(digest["key_facts"])
company_facts_grouped = agg.group_company_facts(digest["key_facts"])

# 研报专属后处理：
# 1. 丢弃 financial_rows（研报不经此通道）
dropped_fin = digest.pop("financial_rows", [])
if dropped_fin:
    digest["flags"].append(
        f"sell-side digest 产出了 {len(dropped_fin)} 条 financial_rows，已丢弃"
        f"（预测数字应走 claims 通道 time_type=forecast）"
    )

# 2. 丢弃 meta_updates（研报不刷 meta）
dropped_meta = digest.pop("meta_updates", {})
if dropped_meta:
    digest["flags"].append(f"sell-side digest 产出了 meta_updates，已丢弃")

# 3. company facts → claims（研报是主产物）
claims_all = []
for (t, m), facts in company_facts_grouped.items():
    if t != ticker or m != market:
        # 研报偶尔引用可比公司；默认不写本公司以外的 claims
        # （多公司研报在 Step 4a 已拒绝，到这里 refs 应全是本公司）
        continue
    claims_all.extend(agg.facts_to_claims(facts))
claims_all = agg.dedup_claims(claims_all)

# 4. 凑兼容 merged
merged = {
    "claims": claims_all,
    "financial_rows": [],
    "meta_updates": {},
    "competence_findings": digest.get("competence_findings", {
        "answered": [], "proposed_additions": []
    }),
    "flags_by_subagent": {"sell-side-digest": digest.get("flags", [])},
    "empty_subagents": [],
}
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2)
)
Path(f"/tmp/ingest-{sha8}.digest.json").write_text(
    json.dumps(digest, ensure_ascii=False, indent=2)
)
```
```

**关键 markdown 片段（替换 Step 10）：**

```markdown
## Step 10：统一写入

研报写入清单（前一步失败整体中止）：

```python
source_meta = {
    "source_id": source_id,
    "source_file": Path(file_path).name,
    "sha8": sha8,
    "institution": institution,
    "date": publish_date,
}
```

### 10.1 原文（Step 6 已做）

### 10.2 图表上下文 + industry observations（研报偶有）

```python
# 若 buckets["industry"] 非空，写：
n_obs = agg.write_industry_observations(
    buckets["industry"], source_meta,
    extracted_by="claude-opus-4-7",
    extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
)
# figure_contexts 按 annual 10.4 的 multi-slug 模式写
```

### 10.3 narratives

```python
# industry narrative（研报"行业背景"段，confidence=medium）
ind_nar = digest["narratives"].get("industry", {})
# wrap 逻辑同 annual 10.5
...
n_nar_ind = agg.write_industry_narrative(ind_nar_payload, source_meta)

# arena narratives（已存在的）
arena_nar = digest["narratives"].get("arena", {})
known_slugs = set(company_arenas)
arena_nar_existing = {k: v for k, v in arena_nar.items() if k in known_slugs}
n_nar_arena = agg.write_arena_narrative(arena_nar_existing, source_meta)

# company narratives（研报主产物之一）
comp_nar = digest["narratives"].get("company", {})
n_nar_comp = agg.write_company_narrative(comp_nar, source_meta)
```

### 10.4 proposed_arenas bootstrap（研报偶有）

同 annual Step 10.6；然后写 newly-bootstrapped arena 的 narrative。

### 10.5 claims（研报主产物）

```python
n, errors = agg.write_claims(
    ticker, market, claims_all,
    source_id=source_id,
    source_file=Path(file_path).name,
    extracted_by="claude-opus-4-7",
    extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
)
```

### 10.6 financials / profile / meta 都不写

- `financials.db`：研报不写
- `profile-*.md`：研报不写（研报不是事实源）
- `meta.md`：原则不写；**例外** —— 若 Step 4.5 bootstrap 了新 arena，走 annual 10.8 的"arenas 字段同步"子步，把新 arena slug 追加到 `fm["arenas"]`

### 10.7 competence

同旧 sell-side Step 10 step 3：`consolidate_answers` + AskUserQuestion + 按 arena 分组 `append_notes` + 新 item `write_checklist`。
```

**验证：**
- sell-side 的"丢 financial_rows"保证预测走 claims 通道，不污染 financials.db
- `facts_to_claims` 对研报的 `time_type="forecast"` 正确传播到 claim（检查 `scripts/ingest_aggregate.py:579-603`——当前实现只保留 `confidence` / `timeframe` / `evidence` / `polarity`，**没有显式传 `time_type`**，所以需要在 sell-side workflow 里**提醒 digest subagent 把 forecast 信息写进 claim_text 前缀或 timeframe 格式**而不是依赖 `time_type` 字段）——**此处有潜在 gap**，见风险章节

**commit message：** `sell-side-note.md: upgrade Step 7/8/10 to digest dispatch, drop financial_rows + meta_updates`

---

## Phase D：SKILL.md 升级 + 旧 prompt 归档

### Task 10: SKILL.md 更新

**目标：** SKILL.md 的"流程总览"章节加 industry-research 类型路由；"关键资源索引"加三层 IO；"聚合/校验/写入库"章节换成 digest + route_key_facts 示例；删除 section-per-subagent 相关措辞。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/SKILL.md`（行 3、22-24、26-38、40-53、55-89、114-126 全部触动；整体重写比局部改动清晰）

**关键 markdown 片段（核心章节改写示例）：**

```markdown
---
name: ingest
description: 把一份财报（年报/季报/10-K/10-Q/20-F）、公司研报、或行业研报录入投资系统（三层知识：industry / arena / company）。触发词：ingest / 导入 / 录入 / 入库 / 10-K / 10-Q / 20-F / 年报 / 季报 / 半年报 / 研报 / 行业研报 / 行业深度 / Sector Report。适用于用户提供一个本地文件路径并说要把它"ingest / 导入 / 录入"到某家公司或某个行业。
allowed-tools: Bash Read Write Agent AskUserQuestion
argument-hint: "<file-path> [--key MARKET_TICKER | --industry INDUSTRY_SLUG]"
---

# ingest skill

把用户指定的一份财报 / 公司研报 / 行业研报按既定流程录入投资系统的**三层知识系统**：

- **industry/**（`industries/{slug}/`）：TAM / 竞争格局 / 生命周期等客观事实 + 11 维 narrative
- **arena/**（`arenas/{slug}/`）：博弈叙事（国产替代 / 挑战者 / 演进轨迹）+ 6 维 narrative + checklist
- **company/**（`companies/{market}_{ticker}/`）：业务 / 护城河 / 财务 等 8 维 narrative + claims.jsonl + financials.db

---

## 设计要点（Claude 执行前必读）

1. **直接调 `app/io/*`**，不走 HTTP 路由。
2. **LLM 抽取发生在对话内**（digest subagent 读整份报告）；Python 脚本只做预处理 / 校验 / 写入 / 查询。
3. **每份报告派 1 个 digest subagent**（`Explore` 类型，只读）——subagent 返回分层 JSON（`key_facts / narratives / proposed_arenas / flags / financial_rows / competence_findings / meta_updates`）；主 agent 用 `agg.route_key_facts` 分三桶分别写入。旧的 section-per-subagent 架构已退役。
4. **事实层写入前必须让用户审**——对应 `meta.md` 的合并、`proposed_arenas` 的 bootstrap、competence_findings 的 approve。
5. **autobuild 纪律**——industry / company 缺失 → `agg.ensure_industry_exists` / `agg.ensure_company_exists` 立刻建骨架，不中止。
6. **fix-forward 纪律**——preprocess / dispatch 失败改 template / 正则 / 白名单，workflow 里不写"主 agent 手工补"的一次性 workaround。

## 输入

- 必给：财报 / 研报文件的**绝对路径**。支持 `.pdf` / `.htm` / `.html` / `.md` / `.txt`。
- 可选：目标公司 key（`MARKET_TICKER`，单公司通道用）；或 `--industry SLUG`（行研通道用）。

## 流程总览

1. **识别源类型** → 财报年报 / 财报季报 / 公司研报 / **行业研报**（新增）
   - 文件名模式：`10-K`、`10-Q`、`20-F`、`年度报告`、`季度报告`、`半年度报告`、`citic`、`morgan`、**`行业深度`、`行业研究`、`Sector Report`、`Industry Report`**
   - 无法判定 → AskUserQuestion
2. **确认路由目标**：
   - 财报 / 公司研报 → 目标公司 key（不给则从文件名 / 封面推断后 AskUserQuestion 确认）
   - 行业研报 → 目标 industry_slug（若已存在则复用，否则 Step 3b-3c AskUserQuestion 让用户给 slug + name + scope）
3. **分派到对应 workflow**：
   - 年报 / 10-K / 20-F / 半年报 → `workflows/annual-report.md`
   - 季报 / 10-Q → `workflows/quarterly-report.md`
   - 公司研报 → `workflows/sell-side-note.md`
   - **行业研报 → `workflows/industry-research.md`**（新）
4. 单公司 workflow 的 Step 4.5 做 **Arena 识别 / 复用 / bootstrap**；行研 workflow 的 Step 10.6 从 digest 产出的 `proposed_arenas` bootstrap 新 arena（逻辑不同）。
5. **Step 10.5 QA checkpoint**：annual / quarterly / sell-side 跑 `ingest_qa warn + gap`；industry-research 仅跑 `warn`（不绑单一 company，`gap` 不适用）。
6. 按 workflow 执行完后，产出**写入清单 + 下一步建议**（`/industries/{slug}` / `/arenas/{slug}` / `/earnings-review/{key}` / `/qa/{key}`）

## 关键资源索引

- **受控词表**：`controlled-vocab/subjects.yaml`（`app.io.claims.load_subjects()` 可直接读）
- **模版剔除规则**：`.claude/skills/ingest/templates/{market-form}.yaml`（`a-share-annual / us-10k / ... / a-share-industry / us-industry`）
- **section 路由表**：`.claude/skills/ingest/section-routing.yaml`（主要用来标记 skip 样板章节；digest 不再看此表的 subagent 字段）
- **source_id 规则**：`.claude/skills/ingest/source-id-rules.yaml`（含 industry-research 格式）
- **交叉校验规则**：`.claude/skills/ingest/cross-checks.yaml`
- **digest prompts**：`prompts/digest/_common.md` + `industry-digest.md` / `annual-digest.md` / `quarterly-digest.md` / `sell-side-digest.md`
- **公司 market 白名单**：`app.config.VALID_MARKETS = ("US","SSE","SZSE","BSE","HK")`
- **三层维度集**：`app.config.INDUSTRY_DIMENSIONS` (11) / `ARENA_DIMENSIONS` (6) / `COMPANY_DIMENSIONS` (8)
- **Industry fields hint**：`app.config.INDUSTRY_FIELDS`（digest prompt 里用来建议 atomic field）
- **Arena IO**：`app.io.arenas`（`list_arenas` / `read_definition` / `write_definition` / `read_narrative` / `append_narrative_block` / `find_by_industry` / `find_by_company` / `read_checklist` / `write_checklist` / `append_notes` / `consolidate_answers`）
- **Industry IO**：`app.io.industry`（`create_industry` / `read_meta` / `write_meta` / `list_industries` / `read_observations` / `append_observations` / `dedup_observations` / `read_narrative` / `append_narrative_block` / `find_by_company` / `find_by_arena`）
- **Company IO**：`app.io.company`（`create_company` / `read_meta` / `read_meta_with_body` / `write_meta` / `list_sources` / `save_source_markdown` / `read_narrative` / `append_narrative_block`）
- **Figure contexts IO**：`app.io.figure_contexts`（`append_figure_contexts` / `read_figure_contexts` / `filter_by_source_id` / `filter_by_section`）
- **QA IO**：`app.io.qa`（`append_warnings` / `read_warnings` / `write_gap_markdown`）；CLI：`scripts.ingest_qa`
- **Aggregate helpers**：`scripts.ingest_aggregate`（下文详列）

## 预处理脚本

所有 workflow 第一步都调同一个：

```bash
.venv/bin/python -m scripts.preprocess_report <file> \
    --type {annual|quarterly|sell-side|industry} \
    --market {a-share|us} \
    --out <json_path>
```

输出 JSON 顶层新字段（Plan 2）：
- `meta.{source_file, sha8, detected_form, fiscal_year, reporting_period, institution, publish_date}`
- `sections[{name, heading_raw, order, char_count, action, reason, text}]`
- `figure_contexts[]` — 图表上下文（caption + surrounding_text + section_name）
- `detected_tickers[]` — 文本中检测到的所有 ticker
- `report_abstract` — 封面 / 首页摘要
- `financial_line_rows[]` — 财务三表候选行（annual/quarterly 用）

workflow 消费此 JSON 做后续 digest dispatch。

## 聚合/校验/写入库

Digest subagent 返回 JSON 后的汇总、分桶、校验、落盘全部走 `scripts.ingest_aggregate`：

```python
from scripts import ingest_aggregate as agg

digest = agg.load_json_tolerant(subagent_raw_output)     # 容错解析

# 按 target_layer 分三桶
buckets = agg.route_key_facts(digest["key_facts"])
company_facts_grouped = agg.group_company_facts(digest["key_facts"])

# 三层写入
agg.write_industry_observations(buckets["industry"], source_meta, extracted_by=..., extracted_at=...)
agg.write_figure_contexts(slug=industry_slug, contexts=figure_contexts, source_meta=source_meta)
agg.write_industry_narrative(ind_nar_payload, source_meta)
agg.write_arena_narrative(arena_nar_payload, source_meta)
agg.write_company_narrative(comp_nar_payload, source_meta)

# Company claims（company facts → claim schema）
claims = agg.facts_to_claims(company_facts)
claims = agg.dedup_claims(claims)
n, errors = agg.write_claims(ticker, market, claims, source_id=..., ...)

# Arena bootstrap（proposed_arenas → arenas/{slug}/）
proposals = agg.propose_arena_bootstrap(digest["proposed_arenas"])
for p in approved_by_user:
    agg.bootstrap_arena(p)

# Industry / Company autobuild
agg.ensure_industry_exists(slug=..., name=..., scope=...)
agg.ensure_company_exists(ticker=..., market=..., name=..., industry_slugs=..., currency=...)

# Cross-checks（annual/quarterly 跑；sell-side / industry-research 精简）
agg.check_revenue_consistency(merged, tol=0.02)
agg.check_period_consistency(merged, expected=fiscal_year_or_period_code)
agg.check_financials_required(merged)
```

`ingest_aggregate` 封装了：polarity 同义词归一化、`evidence_text → evidence[]` 包装、`FY2025 → 2025A` 期间转码、claims batch header 平铺、industry slug 缺失 autobuild 幂等等易错点。

## 直接调用的 IO 函数（绕过 HTTP）

（表格：同旧 SKILL.md，但补三层 IO 函数；移除 `company_io.write_profile`、`claims_io.validate_batch`——后者被 `agg.write_claims` 封装）

## 绝不做的事

- ❌ 从新闻 / 管理层展望 / 研报观点升级到事实层
- ❌ 不经用户审直接写 proposed_arena bootstrap
- ❌ 让 digest subagent 直接写任何文件（subagent 只返回 JSON）
- ❌ ~~多公司研报直接录入~~（改为"多公司研报走 industry-research 通道"）
- ❌ 调 HTTP 路由访问本地服务
- ❌ 跳过 `subjects.yaml` 白名单
- ❌ 回退到 section-per-subagent 模式（已归档；不再支持）

## 当前版本范围

**支持**：年报 / 10-K / 20-F / 半年报 / 季报 / 10-Q / 公司卖方研报 / **行业研报**（新）。

**不支持**（下一版）：公司公告（非财报）、电话会纪要、新闻、社媒。遇到这些类型直接告知用户并终止。
```

**验证：**
- 人工从 description / allowed-tools / 设计要点读到最底，确认整份 SKILL.md 语义与新 digest 架构一致
- description 字符数 ≤ 最大（防止被 frontmatter 截）
- 关键资源索引完整（不漏 `figure_contexts` / `bootstrap_arena` / `ensure_*`）

**commit message：** `SKILL.md: add industry-research type, describe three-layer + digest-dispatch architecture`

---

### Task 11: 旧 prompts 归档

**目标：** 把 `prompts/sections/` 和 `prompts/sell-side/` 整体移到 `prompts/_v1_archived/`（保留为参考，但 workflow 不再引用）。**推荐方案**：重命名（`git mv`），不直接 `rm`。理由：

1. **历史可回溯**：digest prompt 的设计借鉴了 section prompt 的部分经验（例如 `mdna.md` 的"不要把指引当事实"、`risk-factors.md` 的"逐条独立"），归档让后续 debug / prompt 迭代能回看原始出处。
2. **成本低**：整个文件夹只有 ~11 个 markdown，占用忽略不计。
3. **gitleaks / ls 白噪音可控**：`_v1_archived/` 前缀显式表明 deprecated，不会被误当成活文档。

**文件改动**（此 Task 不由 Claude 在 execute-plan 阶段做；属于人工 git 操作）：

```bash
# 不在本 Plan 的 read-only scope；在 execute-plan 时由执行者运行
cd /Users/yangqi/investing/.claude/skills/ingest/prompts
mkdir _v1_archived
git mv sections _v1_archived/sections
git mv sell-side _v1_archived/sell-side
# 在 _v1_archived/README.md 里写 1 段话说明这是 Plan 3 升级后归档的旧 section-per-subagent prompt
```

**归档时额外操作**：

- `.claude/skills/ingest/dispatch-merge-rules.md`（section-per-subagent 同名合并规则文档）：同样移到 `_v1_archived/`——digest 架构下"同名 section 合并"问题不存在。
- 若存在 `.claude/skills/ingest/prompts/sections/_common.md`，一并归档（digest 有自己的 `_common.md`）。

**验证：**
- 确认 `workflows/annual-report.md` / `quarterly-report.md` / `sell-side-note.md` / `industry-research.md` 对 `prompts/sections/` 和 `prompts/sell-side/` 的引用全部已删除（搜索 `sections/` 和 `sell-side/` 路径）
- `_v1_archived/README.md` 里写一句话："这些 prompt 来自 Plan 2 之前的 section-per-subagent 架构；Plan 3 升级到 digest dispatch 后不再被 workflow 引用，保留做历史参考。"

**commit message：** `archive v1 section-per-subagent prompts under _v1_archived/ (deprecated by Plan 3 digest dispatch)`

---

### Task 12: section-routing.yaml 简化

**目标：** section-routing.yaml 在新架构下的角色简化：只用来让 preprocess / workflow 判定哪些 section **应该 skip**（样板章节、披露、重复的附件清单）；digest 不再按 section 分派 subagent，所以 `subagent` 字段和 `targets` 字段都可以删。`industry-generic._fallback` 的 `subagent: industry-digest` 字段也只是个语义标记——实际 dispatch 硬编码在 workflow 里。

**文件改动：**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/section-routing.yaml`（整份精简；删除 `subagent` / `targets` 字段；只保留 `action: skip / extract` 和 `reason`）

**建议：最小改动策略 vs 大扫除策略**

| 策略 | 操作 | 风险 | 推荐 |
|---|---|---|---|
| 最小改动 | 保留 yaml 所有字段不动；workflow 只消费 `action` 字段，忽略 `subagent` / `targets` | yaml 和实际行为脱节；未来新加字段容易混淆 | ❌ |
| 大扫除 | 删掉所有 `subagent` / `targets` 字段；加顶部注释说明"字段 targets/subagent 在 v1 section-per-subagent 架构下使用；Plan 3 digest dispatch 已废弃" | 一次性改 100+ 行 | ✅ |

**推荐：大扫除**。示例改动（片段）：

```yaml
# Section action 路由表（Plan 3 后架构）
#
# Plan 3 digest dispatch 架构下，workflow 不再按 section 分派 subagent；
# 每份报告只派 1 个 digest subagent 读整份文本。本 yaml 的作用退化到：
#   1. 标记哪些 section `action: skip`（样板、免责、附件清单）—— preprocess 消费
#   2. 标记 `action: extract` 让整段 text 进入 digest 的 full_text 拼接
#
# 字段：
#   action: skip | extract
#   reason: (可选) skip 时的说明
#
# 历史字段 `subagent` / `targets` / `max_chars` / `oversize_action` / `oversize_reason`
# 已删除（v1 section-per-subagent 架构使用；Plan 3 废弃）。

a-share-annual:
  重要提示_目录_释义:     {action: skip, reason: 模版样板}
  公司简介_财务指标:      {action: extract}
  管理层讨论与分析:       {action: extract}
  公司治理:               {action: extract}
  环境与社会责任:         {action: skip, reason: ESG 与投资分析弱相关}
  重要事项:               {action: extract}
  股份变动_股东情况:      {action: extract}
  优先股情况:             {action: skip, reason: 多数公司无}
  债券情况:               {action: skip, reason: 多数公司无}
  财务报告:               {action: extract}

us-10k:
  Item_1_Business:                   {action: extract}
  Item_1A_Risk_Factors:              {action: extract}
  Item_1B_Unresolved_Staff_Comments: {action: skip, reason: 通常 None}
  # ... 同样精简 ...

# industry-generic 通道：所有已知维度都 extract，fallback 也 extract
industry-generic:
  _fallback: {action: extract}
  market_size:     {action: extract}
  competition:     {action: extract}
  value_chain:     {action: extract}
  technology:      {action: extract}
  regulation:      {action: extract}
  drivers:         {action: extract}
  lifecycle:       {action: extract}
  risks:           {action: extract}
  valuation:       {action: extract}

# 默认 fallback
_fallback: {action: extract}
```

**预处理侧依赖**：检查 `scripts/preprocess_report.py` 是否读 yaml 的 `subagent` / `targets` 字段——如果读了，等于 Plan 3 markdown 改动**真的需要联动改 preprocess 代码**，这就破坏了"Plan 3 是纯 markdown 改动"的约定。

走查 preprocess：

```
scripts/preprocess_report.py 里对 section-routing.yaml 的消费是否仅限 action？
→ 用 grep 的结果回答
```

（这是 Task 12 的前置调研。若 preprocess 读了 `subagent` / `targets`，把本 Task 降级为**仅删除 digest 架构相关字段**，保留 preprocess 仍在用的字段；并在 Plan 4 里加一条"清理 preprocess 对 section-routing 的多余消费"。）

**验证：**
- `grep "subagent\|targets\|max_chars\|oversize_" scripts/preprocess_report.py` 无命中 → 可以安全大扫除
- workflow 里的 `section-routing.yaml` 引用确实只使用 `action: skip` 做 preprocess-time 判断

**commit message：** `section-routing.yaml: drop subagent/targets (v1 dispatch fields), keep action-only`

---

## 依赖图（任务间顺序）

```
Task 1 (industry-research Step 0-4 骨架)
    ↓
Task 2 (industry-research Step 5-8 digest + route)
    ↓
Task 3 (industry-research Step 9-10 三层写入)
    ↓
Task 4 (industry-research Step 10.5-11 QA + 收尾)
    ↓
Task 5 (annual Step 7 digest dispatch)        ← Phase A 完结后启动；Task 2 的 context 组装模式是 Task 5 的模板
    ↓
Task 6 (annual Step 8 route + merged 凑)       ← Task 3 里的 route 模式复用
    ↓
Task 7 (annual Step 10 三层写入)               ← Task 3 里的写入模式复用
    ↓
Task 8 (quarterly Step 7/8/10)                ← 在 Task 7 之后，复用 annual 模板做 diff
    ↓
Task 9 (sell-side Step 7/8/10)                ← 并行于 Task 8 也行；但语义风险更多
    ↓
Task 10 (SKILL.md)                             ← 等 Task 1-9 全部完，统一在 SKILL.md 里把新架构讲清
    ↓
Task 11 (归档旧 prompts)                       ← Task 10 之后；工作量小
    ↓
Task 12 (section-routing.yaml 精简)            ← 最后；和 Task 11 可并行
```

**并行机会**：Task 5→6→7 和 Task 8、Task 9 虽逻辑独立，但共享模板（Task 7 的三层写入代码是 Task 8/9 的底座）——建议串行执行，减少模板差异带来的 diff bug。

---

## 验证策略（整体）

Plan 3 不涉及 Python 改动，所以**没有单元测试需要跑**。验证路径：

1. **文档一致性**：人工 diff 走读
   - 4 份 workflow 的 Step 7 / Step 8 / Step 10 必须有一致的 skeleton（只在专属后处理上分叉）
   - 4 份 workflow 对 `agg` 函数的调用参数形状一致
   - SKILL.md 的"关键资源索引"与 workflow 实际用到的 IO 函数一一对应

2. **流水线 dry-run**：选一份已 ingest 过的旧报告，从 Step 1 开始按新 workflow 走一遍
   - `preprocess_report.py` 产出的 JSON shape 与新 workflow Step 7a 消费的字段一致（特别是 `figure_contexts` / `detected_tickers` / `financial_line_rows`）
   - 新 workflow Step 10 的每一步 `agg.xxx(...)` 调用都能对上 Plan 2 落地的函数签名
   - 幂等：同一份报告重跑 2 次（autobuilt=False / observations dedup 生效）

3. **digest prompt 契约**：4 份 workflow 里的 prompt 拼接字段集 vs `prompts/digest/_common.md` 的"输入"段落字段集——两个集合必须相等
   - industry-research：`file_meta / industry_context / known_arenas / dimension_ref / industry_fields_hint / figure_contexts / detected_tickers / subjects_whitelist / full_text`
   - annual：多 `company_context / financial_line_rows / checklist_items`
   - quarterly：多 `period_code`
   - sell-side：加 `institution / publish_date / forecasts_hint`

4. **失败模式覆盖**：每份 workflow 底部的"失败模式"矩阵至少覆盖：
   - preprocess 层面（某关键字段抽不到）
   - digest 层面（subagent 超时 / 返回非 JSON / 缺必需顶层 key）
   - autobuild 层面（slug / ticker 异常）
   - cross-check 层面（empty layer / sanity 失败）
   - write 层面（某 dim 不在闭集 / 某文件不存在）

---

## 风险与已知遗留

### 风险 1：`scripts.ingest_qa warn` 接受 `--scope industry:{slug}` 的假设

行研 Step 10.5 假设 `ingest_qa warn --scope industry:{slug}` 会把告警写到 `industries/{slug}/qa_warnings.jsonl`（以 `industry:` 前缀区分 scope）。**此行为 Plan 2 未实现**。当前 `scripts.ingest_qa` 的 `--scope` 只接受 `{market}_{ticker}` 形态，写 `companies/{key}/qa_warnings.jsonl`。

**缓解**：
- 短期（Plan 3）：行研 Step 10.5 的 `--write` 改成"写到 `industries/{slug}/qa_warnings.jsonl`"；CLI 暂不支持则**先跳过 `--write`**，只跑 `warn` 产出 stdout 给用户看。workflow 文案加一行"注：行研 QA scope 当前为 read-only 预览，Plan 4 加 industries scope 支持"。
- 长期（Plan 4）：在 `app/io/qa.py` 加 `_scope_to_path(scope)` 处理 `industry:{slug}` 前缀。

### 风险 2：sell-side 的 `time_type=forecast` 传播

`facts_to_claims`（`scripts/ingest_aggregate.py:579-603`）当前不从 digest fact 的 `time_type` 字段传播到 claim。研报的预测 claim 会因此没有 `time_type`（或默认 `actual`，语义错）。

**缓解**：
- 短期（Plan 3）：在 sell-side-note.md Step 7b prompt 加一条"请在 claim_text 开头显式写 `[forecast]` 前缀标记"；`time_type` 字段留给下游 SQL 查询从 `claim_text` 正则识别。不完美但无需改 Python。
- 长期（Plan 4）：`facts_to_claims` 补一行 `"time_type": f.get("time_type", "actual")`；联动 `claims_io.validate_batch` 白名单接受 `time_type in ("actual", "forecast", "historical", "normalized")`。

### 风险 3：base convention 不统一

workflow 里一律不传 `base=`（走默认值）。但 Plan 2 遗留：`ensure_company_exists` 的 `base=` 是 `companies/` 目录；`create_industry` / `industry_io.*` 的 `base=` 是 `industries/` 目录本身；`arenas_io.*` 的 `base=` 是项目根。workflow 走默认值没事，但单元测试 / 人工 debug 时要警惕。

**缓解**：Plan 4 加一条"统一所有 IO base 为项目根"的重构 task。当前 Plan 3 不碰。

### 风险 4：digest subagent 上下文超出

上下文 =（整份 full_text）+（_common.md + annual-digest.md）+（figure_contexts / checklist_items / detected_tickers）≈ 经验值 30K-100K token。Opus 4.7 上下文 1M，安全边际大。但如果一份年报字数极大（如某些国资央企年报 >300 页），可能触发速率。

**缓解**：Step 5b / 7b 约定"不分段"，但若 `len(full_text) > 500_000 字`，AskUserQuestion 警告并让用户决定"继续（冒险）/ 预处理加 skip 规则减负 / 中止"。

### 风险 5：`find_by_industry`（arena）签名

`arenas_io.find_by_industry(industry_slug)` 返回 `list[str]`（slug 列表）。industry-research Step 5a.2 的代码 `for slug in arenas_io.find_by_industry(industry_slug)` 假设此返回值 —— 确认签名在 `app/io/arenas.py:708`。若未来签名变 `list[dict]`，workflow 要同步改。

**缓解**：约定签名在 Plan 3 的 "依赖函数清单" 里固化；Plan 4 若改 IO 需回来同步 workflow。

### 遗留 1：不再写 `profile-*.md`

旧架构的 `profile-{year}.md` 是"年报抽完后的事实层快照"。新架构改为 `companies/{key}/narratives/*.md`（按 8 维切分）。

**影响**：
- 已有 `profile-*.md` 文件不迁移（Plan 4 做专门的 migration script）
- `/profile/{key}/{year}` 等 web 路由继续读旧文件，但不再有新文件写入（stale 状态）；Plan 4 加 `/narratives/{key}` 新路由

### 遗留 2：competence checklist 的 digest 路径仍用 `consolidate_answers`

`arenas_io.consolidate_answers` 本是为"跨 subagent 同 q_id 合并"设计的（v1 架构）。digest 只有 1 个 subagent，`consolidate_answers` 退化成 no-op。但保留调用是为了保持代码一致性 + 未来如果行研也填 checklist（Plan 4 可能），跨 digest 合并用得到。

### 遗留 3：旧的 `prompts/arena/bootstrap-definition.md` / `bootstrap-checklist.md`

这两份 prompt 在 annual / sell-side 的 Step 4.5 仍在用（因为单公司 workflow 的 arena bootstrap 不由 digest 产出，而是由专门的 arena-bootstrap subagent 从 Item_1_Business / investment_thesis 片段里推导）。**保留不归档**；只归档 `prompts/sections/` 和 `prompts/sell-side/`。

### 遗留 4：dispatch-merge-rules.md

Plan 2 遗留的同名 section 合并规则文档。digest 架构下不再需要。归档到 `_v1_archived/`（Task 11 顺带）。

---

## 未来扩展（超出 Plan 3 范围）

- **半年报独立 digest prompt**：当前半年报按 annual 通道走。半年报内容较 annual 薄 30%-40%，数据范围 6 个月；加 `prompts/digest/semiannual-digest.md` 可让 LLM 更精准（明确时间范围 + 仅 5-6 维 narrative）。
- **多期合并 observations**：同机构同行业多份季度 update 研报的 observation 做 series 合并（`append_observations` 的 dedup 策略加强）。
- **arena narrative 跨 source diff view**：一个 arena 被多份报告覆盖后，narrative append 块会线性增长；未来加 `read_narrative_merged` 做按 source 去重 / 合并视图。
- **web 路由联动**：`/ingest` 页面暴露 workflow 进度（哪 step / 哪 digest subagent / autobuild 了哪些）；Plan 4 scope。
- **industry-research 的 QA 专属规则**：`figure_without_observation` / `arena_proposed_but_no_narrative` / `tam_unit_mismatch` / `dup_observation_across_institutions`；Plan 4 scope。
- **digest prompt 缓存**：4 份 digest prompt 都较长（4K-8K tokens），用 Anthropic prompt cache 做前缀缓存能显著降本。主 agent 在拼 prompt 时把 `_common.md` + `digest/*.md` 的静态段落放在前，动态 context（full_text / figure_contexts）放在后，命中率最高。

---

## 收尾清单

Plan 3 完成的判定：

- [x] `/Users/yangqi/investing/.claude/skills/ingest/workflows/industry-research.md` 存在且 Step 0→11 完整
- [x] `annual-report.md` / `quarterly-report.md` / `sell-side-note.md` 的 Step 7 / 8 / 10 已升级到 digest dispatch；无 `sections/` 或 `sell-side/` 子目录 prompt 引用
- [x] `SKILL.md` description / 关键资源索引 / 聚合章节描述三层 + digest
- [x] `prompts/_v1_archived/sections/` 和 `prompts/_v1_archived/sell-side/` 存在；`_v1_archived/README.md` 说明归档原因
- [x] `section-routing.yaml` 只保留 `action` 字段（或至少 `subagent` / `targets` 从 digest 入口无关的 entry 上被删）
- [x] 人工 dry-run 一份历史年报 / 研报 / 行研，走新 workflow 不报错、落盘路径符合预期

---

### Critical Files for Implementation

- `/Users/yangqi/investing/.claude/skills/ingest/SKILL.md`
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/industry-research.md`（新）
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/annual-report.md`
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/sell-side-note.md`
- `/Users/yangqi/investing/.claude/skills/ingest/workflows/quarterly-report.md`