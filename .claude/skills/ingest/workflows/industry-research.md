# workflow: industry-research

处理行业研报（非单公司聚焦）。主 agent（你）按步骤执行；digest subagent 只读整份报告，返回分层事实 + 叙事 + 候选 arena，由你统一校验、分拣、落盘。

**与其它 workflow 的核心差异：**

1. **主产物在 industry 层**：observations.jsonl（atomic 数值 / structured field / enum）+ narratives/*.md（11 维浓缩）+ figure_contexts.jsonl（图表上下文）。company / arena 层是附带产物。
2. **不写 financials**：行业研报谈公司通常 1-2 句，不是结构化财报。
3. **不写 profile**：profile 是单公司事实层快照，与行业无关。
4. **arena 是"主要来源"**：行研里的"国产替代 / 技术路线之争 / 龙头挑战"等章节是 arena 的最大催化源。`proposed_arenas` 由 digest 直接产出，主 agent 审用户后 `bootstrap_arena` 落盘，无需复用单公司 Step 4.5 的流程。
5. **company layer 是 opportunistic**：研报里每个被提到 ≥3 句话的 ticker 产 ≥1 条 company key_fact，公司缺失则 `ensure_company_exists` 自动建骨架。
6. **QA 只跑 warn（read-only 预览），不跑 gap**：行研不绑单一 company，`ingest_qa gap --company` 无意义；`--write` 依赖 `industry:` scope 前缀（Plan 4 实现），当前只做 stdout 预览。

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

---
