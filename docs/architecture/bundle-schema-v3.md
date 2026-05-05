# Bundle Schema v3

> 本文档是 v3 schema 的权威规范。历史 v2 定义见 `bundle-schema-v2-phase2.md`。

---

## 1. Bundle 顶层（仅 4 个 key + schema_version）

```yaml
schema_version: "v3"

meta:
  source_id: string                      # 短 id，如 "kpmg-cn-pet-2025-{sha8}"
  source_title: string
  institution: string                    # "中银国际证券" / "毕马威" / 公司名（年报时）
  published_at: "YYYY-MM-DD"
  source_type: industry_report | company_report | annual | quarterly | sell_side | transcript
  primary_scope:
    kind: industry | company
    ref: string                          # industry slug 或 MARKET_TICKER
  touches:
    industries: [slug, ...]
    companies: [MARKET_TICKER, ...]
    arenas:    [slug, ...]               # 可空
    brands:    [string, ...]             # 可空，外资品牌或未上市品牌

claims:
  - id: "c1"                             # bundle 内稳定，c1/c2/.../cN
    text: string                         # 单句论点，≤80 字
    type: thesis | judgment | risk | catalyst
    scope: string                        # 见下方 scope 格式
    direction: -1 | 0 | 1                # 多空方向，risk 类默认 -1
    confidence: high | medium | low
    evidence:                            # 1-5 条原文支撑（必须非空）
      - quote: string                    # ≤120 字直引或近似连续片段；图片信息标 "(from image)"
        page: integer | null             # 原文页码；找不到设 null
        why: string                      # ≤30 字，"该事实如何支持 claim"
    relations:                           # 与其他 claim 的逻辑关系，可空数组
      - to: "c3"                         # 必须指向本 bundle 内 claim id
        kind: because_of | leads_to | tension_with | refines
    semantic_key: string                 # ≤15 字，论点核心名词+动词，跨研报匹配用
    as_of: "YYYY-MM-DD"                  # 等于 meta.published_at

summary:
  one_liner: string                      # ≤40 字，全报告核心判断
  threads:                               # 主叙事线（2-5 条）
    - title: string                      # ≤20 字
      claim_ids: ["c1", "c2", ...]       # 串起的 claim
  cannot_conclude: [string, ...]         # 每条 ≤30 字，本报告不能得出的结论

notes:
  skipped_sections: [string, ...]        # 哪些章节被跳过（免责声明/卷首语/联系人等）
  weak_evidence: [string, ...]           # 哪些 claim 质量低（≤40 字一条，可引 claim id）
```

---

## 2. scope 格式（5 种）

```
industry/{industry_slug}        # 例: industry/cn-pet-industry
company/{MARKET_TICKER}         # 例: company/SSE_603011
arena/{arena_slug}              # 例: arena/cn-fusion-hts-magnet-supply
brand:{品牌名}                   # 例: brand:玛氏（保留中文，无 slug 化）
cross_cutting                   # 跨实体的方法论或宏观判断
```

---

## 3. 砍掉的 v2 字段

| v2 字段 | v3 替代 |
|---|---|
| `bundle_version`, `write_status` | `schema_version: "v3"` |
| `insight_blocks[]` | 整体删除，无中间层 |
| `atomic_facts[]` | 合入 `claims[].evidence[]` |
| `stage_gates[]` | 用 `type=risk` 的 claim + `cannot_conclude` 表达 |
| `company_candidates[]`, `arena_candidates[]` | `meta.touches.{companies,arenas,brands}` + `claim.scope` |
| `synthesis` | `summary` |
| `schema_fit_review` | 删除 |
| `narrative_arc` | `summary.threads` |
| `block_type / dimension_hint / claim_type / exposure_type / gate_type` 五套枚举 | 仅 `claim.type` 4 值 |
| `narrative_priority / transition_hint` | `claim.relations` 表达 |
| `investment_implication` | `claim.text` 本身 |
| `reasoning_chain` | `claim.evidence[*].why` + `relations` |
| `evidence_basis / evidence_sparse / sparse_reason` | `confidence` 三档 + evidence 数量 |
| `anchor_hash / semantic_nucleus` | 合并为 `semantic_key`（plain text，不哈希） |
| `coverage_review` | `notes.skipped_sections` |
| `industry_archetype / source_quality / verification_questions` | 删除 |

---

## 4. ClaimRegistry v3 记录格式

5 个文件：`data/claims/{industries,arenas,companies,brands,cross_cutting}.jsonl`。

每行一条 record：

```yaml
claim_id: "industry-c-2025-0042"           # 持久化 id，scope_type 前缀 + 序号
schema_version: "v3"
scope_type: industry | arena | company | brand | cross_cutting
scope_ref: string                          # 与 bundle scope 后半段一致
text: string                               # latest（最新写入者覆盖）
type: thesis | judgment | risk | catalyst
direction: -1 | 0 | 1                      # latest
confidence: high | medium | low            # latest
semantic_key: string

evidence:                                  # 跨 source 累积
  - quote: string
    page: integer | null
    why: string
    source_id: string                      # 哪份 bundle 贡献
    institution: string
    as_of: "YYYY-MM-DD"
    direction_in_source: -1 | 0 | 1

sources:                                   # institution 维度索引
  - source_id: string
    institution: string
    as_of: "YYYY-MM-DD"
    direction_in_source: -1 | 0 | 1
    confidence_in_source: high | medium | low
    bundle_local_id: "c1"                  # 该 bundle 内的本地 id，调试用

relations:                                 # 跨 bundle 累积，键 "kind|to" 去重
  - to: "industry-c-2025-0043"             # 持久化 id
    kind: because_of | leads_to | tension_with | refines
    from_source: string                    # 提出该关系的 bundle source_id

first_seen_at: ISO timestamp
last_updated_at: ISO timestamp
```

### claim_id 生成规则

`{scope_type}-c-{YYYY}-{NNNN}` —— 年份是 `as_of` 的年份，NNNN 是该年该 scope_type 下的递增序号（从 0001 开始，不复用）。

例：`industry-c-2025-0042` / `company-c-2026-0007`。
