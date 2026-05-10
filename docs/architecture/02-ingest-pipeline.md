# Ingest 流水线

Ingest 是将外部研究报告（PDF）导入系统的唯一路径。流水线全部通过 CLI 脚本完成，LLM 判断在 Claude 对话中执行，脚本只做后处理（校验、写入、查询）。

## 流水线概览

```
PDF 报告
  │
  ▼
① preprocess_report.py          # 提取章节结构、原子事实
  │
  ▼
② review-bundle                 # Claude 在对话中审阅，产出 bundle JSON
  │                               （LLM 判断，不在脚本中）
  │
  ▼
③ ingest_qa                     # 可选：质量检查
  │
  ▼
④ ingest_match.py               # 将 bundle 中的 claim_candidates 与现有 claims 匹配
  │
  ▼
⑤ ingest_apply.py               # 应用匹配决策：创建新 claim / 附加证据 / 拆分 claim
  │
  ▼
⑥ narrative_propose.py          # 基于新 claims 生成叙事提案
  │
  ▼
⑦ narrative_apply.py            # 将批准的叙事写入档案 .md 文件
  │
  ▼
⑧ narrative_flags.py            # 扫描叙事一致性标记
  │
  ▼
⑨ persist_bundle                # 注册 bundle 到 bundle_registry.jsonl
```

## 各阶段详解

### 阶段 1：preprocess_report

```bash
python -m scripts.preprocess_report \
  ~/Downloads/report.pdf \
  --out /tmp/ingest-<sha8>-sections.json
```

- 使用 PyMuPDF 解析 PDF
- 提取章节标题、正文文本、图表引用
- 输出 JSON 结构供 review-bundle 使用
- 同时复制源 PDF 到 `industries/{slug}/sources/` 或 `companies/{market}_{ticker}/sources/`

### 阶段 2：review-bundle（Claude 对话中执行）

这不是脚本，而是在 Claude 对话中完成的 LLM 判断。使用 `.claude/skills/ingest` skill 引导：

1. 读取预处理后的 JSON
2. 根据报告类型路由到对应 workflow（`workflows/industry-research.md` 等）
3. 提取 `claim_candidates`、`insight_blocks`、`atomic_facts`
4. 写入 bundle JSON：`{slug}/bundles/{sha8}.json`
5. 写入 bundle-evaluation：`{slug}/bundles/{sha8}-evaluation.json`

Bundle 必须同时产出 industry-scoped 和 arena-scoped 的 claim candidates（对多战场行业报告尤其重要）。

### 阶段 3：ingest_qa（可选）

```bash
python -m scripts.ingest_qa warn \
  --merged /tmp/ingest-<sha8>-merged.json \
  --preprocess /tmp/ingest-<sha8>-sections.json \
  --arena cn-pet-food
```

两类检查：
- **warn**：运行规则集 → 抽取异常告警（未提及、矛盾、极性不一致等）
- **gap**：扫描公司/竞技场现状 → 输出认知缺口

### 阶段 4：ingest_match

```bash
python -m scripts.ingest_match \
  --bundle /tmp/ingest-<sha8>-bundle.json \
  --registry-base . \
  --industry-match /tmp/ingest-<sha8>-match-industry.json \
  --arena-match /tmp/ingest-<sha8>-match-arena.json
```

对 bundle 中的每个 `claim_candidate`：
1. 根据 `scope_type` + `scope_ref` 在 ClaimRegistry 中查找已有 claims
2. 使用 `claim_matching.py` 的匹配引擎计算相似度（文本重叠 + 维度匹配）
3. 输出匹配文件（JSON），包含 `decisions_required` 列表，每条候选的 `decision` 字段为 null 待填写

匹配结果输出到多个文件（按 scope_type 分组）。

### 阶段 5：ingest_apply

```bash
python -m scripts.ingest_apply \
  --bundle /tmp/ingest-<sha8>-bundle.json \
  --registry-base . \
  --decisions /tmp/ingest-<sha8>-match-industry.json \
  --decisions /tmp/ingest-<sha8>-match-arena.json \
  --applied-out /tmp/ingest-<sha8>-applied.jsonl
```

合法决策类型：

| 决策 | 含义 |
|---|---|
| `new` | 创建新 claim |
| `attach` | 附加到已有 claim（追加 evidence） |
| `split` | 拆分已有 claim 为多个新 claim |
| `skip` | 跳过该候选 |

执行顺序：先验证所有匹配文件的合法性，再批量写入，确保原子性。

副作用：
- 创建/修改 `claims/{scope_type}.jsonl`
- 更新 `claims/.counters.json`
- 追加 `audit/claim-events.jsonl`
- 写入 `pending/arenas-{source_id}.jsonl`（竞技场候选记录）

### 阶段 6：narrative_propose

```bash
python -m scripts.narrative_propose \
  --registry-base . \
  --base . \
  --source-id "行研-毕马威-2025-06-d385a3c7" \
  --scope industry --ref cn-pet-industry \
  --out /tmp/ingest-<sha8>-proposals-industry.json
```

工作原理：
1. 从 ClaimRegistry 过滤出 `scope_type + scope_ref + source_id` 匹配的活跃 claims
2. 通过 `dimension_hint` → 叙事维度映射表，将 claims 分组到叙事维度
3. 对每个有 claims 的维度，生成一条 proposal
4. 同时读取已有叙事文件的最后 1200 字符作为 `existing_narrative_excerpt`
5. 输出提案 JSON 文件

维度映射表（`narrative_proposals.py`）：

```
# Industry 映射示例
"market_size" → "market_size"
"drivers"     → "drivers"
"thesis"      → "drivers"
"competition" → "competition"

# Arena 映射示例
"technology"     → "decisive_factors"
"catalysts"      → "trajectory"
"thesis"         → "narratives"
"valuation"      → "investment_view"
```

对每个受影响的 scope（industry + 每个 arena）都需要独立运行一次。

### 阶段 7：narrative_apply

```bash
python -m scripts.narrative_apply \
  --registry-base . \
  --base . \
  --proposal /tmp/ingest-<sha8>-proposals-industry.json \
  --today 2026-05-02
```

验证通过后，对每条 proposal：
- `approve`：将 body 追加到对应维度 .md 文件
- `edit`：将 edited_body 追加到对应维度 .md 文件
- `reject`：不写入，记录审计事件
- `defer`：不写入，记录审计事件

写入格式（`_render_markdown_block`）：

```markdown
### {标题}

status: active
last_written: {today}
supported_by_claims: [clm-xxx, clm-yyy]
source_ids: [source-1]
proposal_id: np-001

{body}
```

副作用：
- 追加到 `{scope}/{slug}/{dimension}.md`
- 追加到 `data/audit/narrative-events.jsonl`
- 归档提案文件到 `data/pending/archive/`

### 阶段 8：narrative_flags

```bash
python -m scripts.narrative_flags \
  --registry-base . \
  --base . \
  --scope industry --ref cn-pet-industry
```

扫描已写入的叙事文件，解析 `supported_by_claims` 中的 claim_id，检查：
- claim 是否存在
- claim 是否为 active 状态
- claim 是否有 refuting evidence

发现问题则写入 `{scope}/{slug}/narrative-flags.jsonl`。

### 阶段 9：注册 Bundle

将 bundle 信息追加到 `data/bundle_registry.jsonl`：

```json
{
  "source_id": "行研-毕马威-2025-06-d385a3c7",
  "sha8": "d385a3c7",
  "source_type": "industry_report",
  "institution": "毕马威",
  "publish_date": "2025-06-01",
  "bundle_path": "industries/cn-pet-industry/bundles/d385a3c7.json",
  "source_file_path": "industries/cn-pet-industry/sources/2025-china-pet-industry-market-report.pdf",
  "ingested_at": "2026-05-02T01:00:00+00:00",
  "touched": {
    "industries": ["cn-pet-industry"],
    "arenas": ["cn-pet-food", "cn-pet-medical", "cn-pet-ecommerce", "cn-smart-pet-supplies"],
    "companies": []
  }
}
```

## 新增行业 / 公司时的自动构建

如果 ingest 过程中发现目标 industry 或 company 不存在于注册表中，`ingest_aggregate.py` 会调用 `agg.ensure_industry_exists()` / `agg.ensure_company_exists()` 自动创建 meta 文件，不会中止流程。
