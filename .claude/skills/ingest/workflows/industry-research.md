# workflow: industry-research

处理行业研报（非单公司聚焦）。主 agent（你）按步骤执行；digest subagent 只读整份报告，返回分层事实 + 叙事 + 候选 arena，由你统一校验、分拣、落盘。

**与其它 workflow 的核心差异：**

1. **主产物在 industry 层**：observations.jsonl（atomic 数值 / structured field / enum）+ narratives/*.md（11 维浓缩）+ figure_contexts.jsonl（图表上下文）。company / arena 层是附带产物。
2. **不写 financials**：行业研报谈公司通常 1-2 句，不是结构化财报。
3. **不写 profile**：profile 是单公司事实层快照，与行业无关。
4. **arena 是"主要来源"**：行研里的"国产替代 / 技术路线之争 / 龙头挑战"等章节是 arena 的最大催化源。`proposed_arenas` 由 digest 直接产出，主 agent 审用户后 `bootstrap_arena` 落盘，无需复用单公司 Step 4.5 的流程。
5. **company layer 是 opportunistic**：研报里每个被提到 ≥3 句话的 ticker 产 ≥1 条 company key_fact，公司缺失则 `ensure_company_exists` 自动建骨架。
6. **QA 只跑 warn，不跑 gap**：行研不绑单一 company，`ingest_qa gap --company` 无意义。Plan 4 T3 起 `--write --scope industry:{slug}` 落盘到 `industries/{slug}/qa_warnings.jsonl`。

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
  - 抽不到机构名 → 后续 Step 3a AskUserQuestion 补齐（复用 sell-side 的机构补齐流程）

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
- `sections[*]`：action = skip（封面 / 免责 / 分析师 bio / 目录行等）或 keep（实际内容）
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

---

## Step 5：Digest dispatch（单 subagent，整份报告）

### 5a：准备 subagent context

主 agent 组装 digest subagent 的完整 prompt：

```python
import json
from pathlib import Path
from app.io import arenas as arenas_io, industry as industry_io, claims as claims_io

# 5a.1 拼接整份报告文本（所有 action=extract 的 section 按 order 串起）
preprocess = json.loads(Path(f"/tmp/ingest-{sha8}.sections.json").read_text())
full_text_chunks = []
for s in preprocess["sections"]:
    if s.get("action") == "keep":    # preprocess 产出 "keep" 或 "skip"
        full_text_chunks.append(f"### {s['heading_raw']}\n\n{s['text']}")
full_text = "\n\n".join(full_text_chunks)

# 5a.2 已知 arenas（同 industry 的）
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

# 5a.4 figure_contexts / detected_tickers（preprocess 直接出）
figure_contexts = preprocess.get("figure_contexts", [])
detected_tickers = preprocess.get("detected_tickers", [])

# 5a.5 subjects_whitelist（给 company key_fact 的 subject_tag_hint 用）
subjects_whitelist = [s["id"] for s in claims_io.load_subjects()]

# 5a.6 industry_context
industry_meta = industry_io.read_meta(industry_slug)
industry_context = {"slug": industry_slug, "name": industry_meta.get("name")}
```

### 5b：Dispatch

读 `.claude/skills/ingest/prompts/digest/_common.md` + `prompts/digest/industry-digest.md`，拼成最终 prompt：

```python
digest_common = Path(".claude/skills/ingest/prompts/digest/_common.md").read_text()
digest_industry = Path(".claude/skills/ingest/prompts/digest/industry-digest.md").read_text()

def _indent(text: str, prefix: str = "  ") -> str:
    return "\n".join(prefix + ln for ln in text.splitlines())

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

**并发**：行研只有一个 digest subagent，无并发问题。若 subagent 返回超时（>10min），AskUserQuestion 问是继续等 / 重派 / 中止。

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

**注意**：`ensure_company_exists` 不问用户 sector（行研没有好的 sector 判据）；meta.md 的 sector 字段留默认空，等后续 ingest 年报 / 研报时再由那时的 workflow 用 AskUserQuestion 补。

若用户不希望静默建公司骨架，可在 autobuild 前 AskUserQuestion 列出候选公司 + 让用户批量选择 / 排除。默认行为是静默建（减少用户打扰）。

---

## Step 9：交叉校验（行研精简版）

行研的 cross-check 与 annual 不同：

- 不跑 `revenue_consistency`（行研没 total revenue 锚）
- 不跑 `period_consistency`（行研事实跨多 FY / 多 timeframe；众数概念无意义）
- **跑** empty-layer check（检查 digest 是否忘了某层）
- **新增** `industry_observation_sanity`（主 agent 在对话里写简单校验，见下）

```python
issues = []

# 9.1 empty layer check（digest 模式专用；不调 agg.check_empty_sections——
# 后者是针对 section-per-subagent 的）
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

**触发处理**：`issues` 非空 → AskUserQuestion 展示前 10 条，让用户选"接受差异（继续写入但标 flag） / 重派 digest（回到 Step 5b） / 中止"。

---

## Step 10：统一写入

**写入顺序**（前一步失败则中止；不回滚已写）：

### 10.1 原文（Step 4c 已做）

### 10.2 figure_contexts（行研主产物）

```python
from datetime import datetime, timezone

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
```

### 10.3 industry observations（atomic 数值）

```python
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

`digest["narratives"]["industry"]` 的 shape 可能是：
- `{dim: md_block}`（单 slug 上下文；11 维扁平）
- `{slug: {dim: md_block}, slug2: {dim: md_block}}`（多 slug）

IO 函数 `write_industry_narrative` 期望 `{slug: {dim: md_block}}`——主 agent 检测后统一 wrap：

```python
raw = digest["narratives"].get("industry", {})
first_keys = set(raw.keys())
dim_set = set(cfg.INDUSTRY_DIMENSIONS)

if first_keys and first_keys.issubset(dim_set):
    # 扁平：单 slug
    industry_nar_payload = {industry_slug: raw}
else:
    # 已按 slug 分组
    industry_nar_payload = raw

n_nar_ind = agg.write_industry_narrative(industry_nar_payload, source_meta)
```

### 10.5 proposed_arenas 审阅 + bootstrap（写 arena narrative 前）

```python
proposals = agg.propose_arena_bootstrap(digest["proposed_arenas"])
# returns [{slug, name, industry, battleground_focus, participants}, ...]
```

**AskUserQuestion** 展示每个 proposal（slug / focus / participants），让用户批量选：
- approve 全部
- approve 部分（逐条勾选）
- approve 全部但逐条改 slug / focus（用户编辑）
- 拒绝所有

**对每个 approved proposal**：

```python
for p in approved_proposals:
    agg.bootstrap_arena(p)
    # 此时 arenas/{slug}/ 下已有 definition.md + 5 份 narrative 骨架
```

**注意**：bootstrap 必须在 10.6（arena narrative append）之前完成——`write_arena_narrative` 在 arena 不存在时抛 FileNotFoundError。

### 10.6 arena narratives（若有）

```python
arena_nar_raw = digest["narratives"].get("arena", {})
# shape: {arena_slug: {dim: md_block}}

# 过滤掉被用户 reject 的 proposed arena slug
rejected_slugs = {p["slug"] for p in proposals if p not in approved_proposals}
arena_nar = {s: dims for s, dims in arena_nar_raw.items() if s not in rejected_slugs}

n_nar_arena = agg.write_arena_narrative(arena_nar, source_meta)
```

### 10.7 company narratives

```python
comp_nar = digest["narratives"].get("company", {})
# shape: {"MARKET_TICKER": {dim: md_block}, ...}
n_nar_comp = agg.write_company_narrative(comp_nar, source_meta)
```

Step 8 已经做完 `ensure_company_exists` —— 所有 key 对应的目录都已存在。

### 10.8 company claims

行研的 company facts 数量通常很少（每个 ticker 1-3 条），但仍要写到 `companies/{key}/claims.jsonl`——`facts_to_claims` 把它们转成 claim schema：

```python
total_claims = 0
for (ticker, market), facts in company_facts.items():
    claims_payload = agg.facts_to_claims(facts)
    if not claims_payload:
        continue
    n, errors = agg.write_claims(
        ticker, market, claims_payload,
        source_id=source_id,
        source_file=Path(file_path).name,
        extracted_by=extracted_by,
        extracted_at=extracted_at,
    )
    total_claims += n
    if errors:
        # 报给用户；不阻塞后续公司（行研 company layer 是 opportunistic）
        ...
```

**注意**：`facts_to_claims` 默认 `claim_type="qualitative"`（除非 value_numeric 存在）。行研里大部分 company fact 是 qualitative（护城河 / 业务结构描述）。

### 10.9 industry meta 联动

若 bootstrap 了新 arena，`industries/{slug}/meta.yaml` 的 `linked_arenas` 字段追加；若 autobuilt 了 company，`linked_tickers` 追加：

```python
industry_meta = industry_io.read_meta(industry_slug)
changed = False

# 追加 linked_arenas
existing_arenas = set(industry_meta.get("linked_arenas") or [])
new_arenas = {p["slug"] for p in approved_proposals}
if new_arenas - existing_arenas:
    industry_meta["linked_arenas"] = sorted(existing_arenas | new_arenas)
    changed = True

# 追加 linked_tickers
existing_tickers = {(t["market"], t["ticker"])
                    for t in industry_meta.get("linked_tickers") or []}
new_tickers_list = industry_meta.setdefault("linked_tickers", [])
for (ticker, market) in company_facts.keys():
    if (market, ticker) not in existing_tickers:
        new_tickers_list.append({"market": market, "ticker": ticker, "role": "mentioned"})
        changed = True

if changed:
    industry_io.write_meta(industry_slug, industry_meta)
```

---

## Step 10.5：QA checkpoint（行研精简版：落盘到 industry scope）

行研不绑单一 company，`ingest_qa gap --company` 无意义。Plan 4 T3 起
`app/io/qa.py` 支持 `scope='industry:{slug}'`，本 step 落盘到
`industries/{industry_slug}/qa_warnings.jsonl`。

**凑一份兼容 merged.json**（现有 `scripts.ingest_qa warn` 的 `--merged` 参数期望 v1 aggregate 结构；digest 模式下没有现成的 merge 产物，主 agent 手凑）：

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
    json.dumps(compat_merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

```bash
.venv/bin/python -m scripts.ingest_qa warn \
    --merged /tmp/ingest-{sha8}.merged.json \
    --preprocess /tmp/ingest-{sha8}.sections.json \
    --write --scope industry:{industry_slug}
# stdout 预览 + 落盘到 industries/{industry_slug}/qa_warnings.jsonl
```

**不跑 `gap`**，也**不用 `--arena`**（行研常触多 arena，挑一个没意义）。

**未来扩展**：
- 行研专属规则：`figure_without_observation` / `arena_proposed_but_no_narrative` / `tam_unit_mismatch` / `dup_observation_across_institutions`

---

## Step 11：收尾报告

```
已 ingest 行业研报：industries/{industry_slug}/sources/{filename}
✓ industries/{industry_slug}/figure_contexts.jsonl  +{n_fig} 条
✓ industries/{industry_slug}/observations.jsonl    +{n_obs} 条
✓ industries/{industry_slug}/*.md (11 dim narratives 在根目录)  +{n_nar_ind} dim
{✓|⊘} arenas/{slug}/ (bootstrap)                    +{k_arenas} 新 arena / 全部拒绝
{✓|⊘} arenas/{slug}/*.md (5 dim narratives 在根目录)  +{n_nar_arena} dim across {k_arenas_total} arena
{✓|⊘} companies/{...} (autobuild)                   {k_auto_company} 家骨架 / 无
{✓|⊘} companies/{key}/narratives/*.md              +{n_nar_comp} dim
{✓|⊘} companies/{key}/claims.jsonl                 +{total_claims} 条 (source_id={source_id})
✓ industries/{industry_slug}/qa_warnings.jsonl     +{n_qa} 条（rule 分布见 stdout 预览）
⊘ qa_gaps                                          行研不跑（无单一 company 绑定）
⊘ financials.db                                     行研不写
⊘ profile-*.md                                     行研不写

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
| digest 返回 `industry` 桶为空 | Step 9 pause；AskUserQuestion 决定是重派 digest（补漏）还是接受（通常意味着报告不是典型行研——如"策略宏观"误入通道） |
| proposed_arenas 的 `parent_industry_slug` 不在任何已存 industry 中 | Step 10.5 bootstrap 前 AskUserQuestion 让用户决定"改 parent / 先建 parent industry / 拒绝该 proposal" |
| industry slug 新建时用户给的 slug 已存在 | `ensure_industry_exists` 幂等；自然跳过新建，继续用该 slug（告知用户"slug 已存在，复用；scope 未更新"） |
| company autobuild 时 ticker 格式异常（如全角数字） | `ensure_company_exists` 不做清洗，直接调 `create_company`；后者抛 ValueError；主 agent 在 Step 8 每家外面 try/except，记入 flags，跳过该家不阻塞 |
| write_industry_narrative 抛 FileNotFoundError（某 dim 不在 INDUSTRY_DIMENSIONS 闭集） | digest 产出错了 dim key；把错误 dim 从 payload 里剥出来放 flags，继续 write 其它 dim；不整体中止 |
| write_arena_narrative 抛 FileNotFoundError（slug 未 bootstrap） | Step 10.5 的 rejected 过滤漏了该 slug，或 digest 吐了 known_arenas 之外的 slug；过滤掉 → 记 flag → 继续 |
| QA warn 抛错（兼容 merged 结构不对） | Step 10.5 pause；把 error 报给用户，让用户选"跳过 QA 继续 / 中止"。QA 不影响已写入数据的完整性 |

---

## 已知范围限制

- **单机构 / 多期合并**：同一机构发的同主题多期研报（季度 update），当前每次独立 ingest，不做 series 合并。未来可在 observations dedup 时做。
- **跨 industry 研报**：digest 支持在 facts 里标不同 `target_refs.industry_slug`；但当前 workflow Step 3b 只处理一个主 industry（source 只落到主 industry 的 `sources/`）。跨行业需要 Plan 4 加"多 industry 绑定"扩展。
- **研报为 XLS/PPT**：preprocess 不支持；只支持 PDF/HTML/MD/TXT。

