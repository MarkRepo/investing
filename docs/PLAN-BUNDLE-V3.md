# Bundle Pipeline v3 改造计划

> **读者**：实施此计划的工程 agent（Sonnet）。文档自包含，无需参考其他上下文即可落地。
> **范围**：把 bundle schema 从 v2-phase1 重做为 v3，砍掉 ~70% 的复杂度，对齐"叙事逻辑 + 跨研报融合"的原始目标。
> **不做**：UI 改造、英文研报支持、新增 source_type、嵌入向量服务。

---

## 1. 战略锚

实测对比已证明：

- v2 schema + sonnet 抽取核聚变 → 9 ib + 6 claim，27 页公司深度压缩成 1 ib，narrative_arc 空，21k token 消耗在 28 条硬约束的字段填充。
- v3 schema（4 顶层 key）+ 同一 sonnet → 35 claim，4 公司各 3-5 条独立 claim，72 条 relations，0 isolated，0 broken。
- v3 schema + opus 4.7 → 50 claim，但 16 个 isolated，relations 仅 31。**Opus 不是更好。**

**结论**：v3 设计在 sonnet 单次调用下达到目标质量。本计划把 v3 设计落地到代码。

设计原则（不可妥协）：

1. bundle 是"可被 N 份研报融合的论点+证据图"，不是研报副本。
2. 叙事逻辑靠 `claims[].relations` 的有向图，不靠 priority/arc 这种位置约束。
3. **不设必提清单**。LLM 按报告自然展开。
4. 跨研报融合靠 `semantic_key + scope + direction` 三元组 + jaccard 匹配。
5. prompt 不写硬约束清单（28 条硬约束就是质量退化的元凶）。

---

## 2. Schema v3 正式定义

### 2.1 Bundle 顶层（仅 4 个 key + schema_version）

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

### 2.2 scope 格式（5 种）

```
industry/{industry_slug}        # 例: industry/cn-pet-industry
company/{MARKET_TICKER}         # 例: company/SSE_603011
arena/{arena_slug}              # 例: arena/cn-fusion-hts-magnet-supply
brand:{品牌名}                   # 例: brand:玛氏（保留中文，无 slug 化）
cross_cutting                   # 跨实体的方法论或宏观判断
```

### 2.3 砍掉的 v2 字段（实施时确认无引用后删除）

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

## 3. ClaimRegistry v3 记录格式

### 3.1 持久化 schema

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

### 3.2 claim_id 生成规则

`{scope_type}-c-{YYYY}-{NNNN}` —— 年份是 `as_of` 的年份，NNNN 是该年该 scope_type 下的递增序号（从 0001 开始，不复用）。

例：`industry-c-2025-0042` / `company-c-2026-0007`。

---

## 4. 新 Pipeline（6 步）

```
1. Convert    — scripts/mineru_ingest.py（不变）
2. Extract    — Sonnet subagent 按 v3 prompt 产 bundle.json
3. Validate   — scripts/ingest_qa.py（极简化，约 150 行）
4. Resolve    — scripts/ingest_apply.py 内调用 agg.ensure_industry/company；新增 ensure_brand
5. Merge      — scripts/ingest_match.py（重写为 jaccard 匹配）
6. Persist    — scripts/ingest_apply.py 写 ClaimRegistry + bundle 归档 + scripts/render_views.py
```

砍掉的步骤：narrative_propose / narrative_apply / narrative_flags / check_stage_gates / claim_decay_check 都从主链路移除。

---

## 5. 任务清单（按依赖顺序）

每个任务列出：goal / 文件路径 / 具体改动 / 验收。

**全部任务完成后**，再跑 §10 的回归测试。所有改动在 main 分支上分多个 commit 推进，每完成 1 个 task commit 一次。

### T1 — Schema v3 spec 文档

**文件**：`docs/architecture/bundle-schema-v3.md`（新建）

**内容**：把本计划 §2 完整复制为独立文档，不做删减。文档以 schema 定义、scope 格式、与 v2 的删除字段对照表为主。

**验收**：文档存在且包含本计划 §2 所有内容。

---

### T2 — 新 prompt 文档

**文件**：`docs/prompts/ingest-review-bundle-v3.md`（新建）

**内容**：使用以下完整 prompt（≤900 字主体）。`{schema}` 占位符替换为 §2.1 的 schema 块的 JSON 化版本。

```markdown
<!-- prompt_version: v3 -->

# Ingest Review Bundle v3 Prompt

你在读一份投资研报。任务：抽取一个可以辅助投资决策、且能在多份研报间融合
的论点+证据图。

输入：MinerU 产出的 `full-clean.md`（如有 keep_images 也可读）。
输出：一个 JSON bundle（schema 见末尾）。

## 抽取原则（按重要性）

1. **以叙事为先，按报告主线组织 claim。**
   作者想让读者得出什么投资判断？这是 bundle 的灵魂。
   按报告自身逻辑切分 claim，不要套框架。
   30 页通常 10-30 条；65 页通常 25-50 条；80 页通常 30-60 条。
   不刻意凑数，也不刻意压缩。

2. **每条 claim 必须有 1-5 条原文证据。**
   evidence.quote ≤120 字直引；图片信息末尾标 `(from image)`。
   evidence.why 一句话说明「该事实如何支持 claim」（≤30 字）。
   只能用"原文综合分析"支撑的 claim → 删除或并入。

3. **实体粒度：报告里点名的公司/品牌各自独立产 claim。**
   不要把"四家公司均受益"压成一条；分四条，挂到对应 scope。
   原因：跨研报融合时它们是独立实体。

4. **同类多实例必须独立成 claim。**
   "第一壁/偏滤器/磁体"是 3 条独立 claim，不是 1 条。
   "宠物食品/用品/医疗/服务"是 4 条。
   人口因素（银发/单身/丁克）也是多条。

5. **叙事关联用 relations 显形。**
   报告通常有一条主线："因为 A → 所以 B → 因此推荐 C"。
   relations 不是装饰：summary.threads 由 relations 反向推导。
   每条 claim 至少 1 条 relation（无论 in 还是 out），避免 isolated。

6. **summary.threads 是 claim 的分组视图。**
   通常 2-4 条主叙事线；每条串 3-8 条 claim。
   一条 claim 可同时属于多条 thread。

7. **semantic_key 是跨研报匹配的钩子（≤15 字）。**
   论点核心名词+动词组合。例：
     claim: "磁体在产业链中占金额敞口最高（24.9%）"
     semantic_key: "磁体 金额敞口 最高"
   不同研报对同一观点的 semantic_key 应自然趋同。

8. **confidence 默认 medium，仅在以下条件升降：**
   - high：原文有具体数字 + 多源印证或权威来源
   - low：仅图片描述、远期预测、强假设推断

9. **不能由本报告得出的结论 → cannot_conclude。**
   不要为"完整"编造。

10. **notes 显式标注：**
    - skipped_sections：哪些章节没读
    - weak_evidence：哪些 claim 质量低（可引 claim id）

## 不做什么

× 不要套必提类别清单。报告有就提，没有就不提。
× 不要给 claim 强制写 reasoning_chain / investment_implication / 
  block_type / dimension_hint —— 这些字段不存在。
× 不要把 atomic_facts 和 claim 拆开，证据直接挂在 claim 下。
× 不要为了形式齐全编造数字或公司名。

## Schema

严格 JSON，无 markdown 围栏，无解释。顶层结构：

{schema}
```

`{schema}` 替换为 §2.1 yaml 转 JSON 后的 schema 模板片段（注释保留）。

**验收**：文档存在；prompt 主体 ≤900 字（不含 schema 块）；无"必提"、"硬约束"、"block_type" 字样。

---

### T3 — 简化 ingest_qa.py

**文件**：`scripts/ingest_qa.py`（重写）

**目标**：从 ~1300 行减到 ~200 行。只保留 v3 校验。

**保留的子命令**：

- `review-bundle` — 校验 v3 bundle
- `evaluation init` — 仍生成 evaluation skeleton（不变）

**删除的子命令**：所有其他子命令（如有）。

**review-bundle 的检查清单**：

```python
def check_v3_bundle(bundle: dict, mineru_md_text: str | None) -> list[QAItem]:
    issues = []
    # C1: schema_version
    if bundle.get("schema_version") != "v3":
        issues.append(error("schema_version_mismatch", "expected 'v3'"))
        return issues  # 不继续，schema 不对其他校验无意义

    # C2: 必需顶层 key
    for k in ("meta", "claims", "summary", "notes"):
        if k not in bundle:
            issues.append(error(f"missing_top_key:{k}"))

    # C3: meta 字段完整性
    meta = bundle.get("meta", {})
    for k in ("source_id", "institution", "published_at", "source_type", "primary_scope", "touches"):
        if not meta.get(k):
            issues.append(error(f"meta_missing:{k}"))
    if meta.get("source_type") not in {"industry_report","company_report","annual","quarterly","sell_side","transcript"}:
        issues.append(error("invalid_source_type"))

    # C4: claims 数量与报告页数比例（提示 only，不阻塞）
    claims = bundle.get("claims", [])
    if not claims:
        issues.append(error("no_claims"))
    if mineru_md_text:
        pages = max(1, len(mineru_md_text) // 1500)  # 粗估每页 1500 字符
        ratio = len(claims) / pages
        if ratio < 0.25:
            issues.append(warn("under_extraction", f"{len(claims)} claims for ~{pages} pages"))
        if ratio > 2.0:
            issues.append(warn("over_extraction", f"{len(claims)} claims for ~{pages} pages"))

    # C5: 每条 claim 字段合法性
    all_ids = set()
    for c in claims:
        cid = c.get("id", "")
        if not cid or cid in all_ids:
            issues.append(error(f"claim_id_invalid_or_dup:{cid}"))
        all_ids.add(cid)
        # type
        if c.get("type") not in {"thesis","judgment","risk","catalyst"}:
            issues.append(error(f"{cid}.type_invalid"))
        # direction
        if c.get("direction") not in {-1, 0, 1}:
            issues.append(error(f"{cid}.direction_invalid"))
        # confidence
        if c.get("confidence") not in {"high","medium","low"}:
            issues.append(error(f"{cid}.confidence_invalid"))
        # scope 格式
        scope = c.get("scope", "")
        if not _valid_scope(scope):
            issues.append(error(f"{cid}.scope_invalid:{scope}"))
        # evidence 必须非空
        if not c.get("evidence"):
            issues.append(error(f"{cid}.no_evidence"))
        for i, e in enumerate(c.get("evidence", [])):
            if not e.get("quote"):
                issues.append(error(f"{cid}.evidence[{i}].no_quote"))
            if not e.get("why"):
                issues.append(error(f"{cid}.evidence[{i}].no_why"))
        # semantic_key
        if not c.get("semantic_key") or len(c["semantic_key"]) > 20:
            issues.append(error(f"{cid}.semantic_key_invalid"))
        # risk 默认 direction=-1
        if c.get("type") == "risk" and c.get("direction") == 1:
            issues.append(warn(f"{cid}.risk_with_positive_direction"))

    # C6: relations 引用合法
    for c in claims:
        for i, r in enumerate(c.get("relations", [])):
            if r.get("to") not in all_ids:
                issues.append(error(f"{c['id']}.relations[{i}].broken_ref:{r.get('to')}"))
            if r.get("kind") not in {"because_of","leads_to","tension_with","refines"}:
                issues.append(error(f"{c['id']}.relations[{i}].invalid_kind"))

    # C7: isolated 比例（提示 only）
    referenced = {r["to"] for c in claims for r in c.get("relations", []) if r.get("to") in all_ids}
    isolated = [c["id"] for c in claims if not c.get("relations") and c["id"] not in referenced]
    if len(isolated) / max(1, len(claims)) > 0.20:
        issues.append(warn("excessive_isolated_claims", f"{len(isolated)}/{len(claims)} isolated"))

    # C8: summary
    sm = bundle.get("summary", {})
    if not sm.get("one_liner"):
        issues.append(error("summary_missing_one_liner"))
    if not sm.get("threads"):
        issues.append(error("summary_missing_threads"))
    for t in sm.get("threads", []):
        for cid in t.get("claim_ids", []):
            if cid not in all_ids:
                issues.append(error(f"thread_unknown_claim:{cid}"))

    # C9: scope.ref 在 meta.touches 中可解析（提示 only）
    touches = meta.get("touches", {})
    touch_inds = set(touches.get("industries", []))
    touch_cos = set(touches.get("companies", []))
    touch_arenas = set(touches.get("arenas", []))
    for c in claims:
        s = c.get("scope", "")
        if s.startswith("industry/"):
            ref = s[len("industry/"):]
            if ref not in touch_inds:
                issues.append(warn(f"{c['id']}.scope_not_in_touches:{ref}"))
        elif s.startswith("company/"):
            ref = s[len("company/"):]
            if ref not in touch_cos:
                issues.append(warn(f"{c['id']}.scope_not_in_touches:{ref}"))
        elif s.startswith("arena/"):
            ref = s[len("arena/"):]
            if ref not in touch_arenas:
                issues.append(warn(f"{c['id']}.scope_not_in_touches:{ref}"))

    return issues


def _valid_scope(s: str) -> bool:
    if s == "cross_cutting":
        return True
    for prefix in ("industry/", "company/", "arena/"):
        if s.startswith(prefix) and len(s) > len(prefix):
            return True
    if s.startswith("brand:") and len(s) > len("brand:"):
        return True
    return False
```

**CLI**：

```
.venv/bin/python -m scripts.ingest_qa review-bundle \
    --bundle /tmp/ingest-{sha8}-bundle.json \
    [--mineru-md /path/to/full-clean.md]
```

退出码：errors > 0 → 1；只有 warnings → 0。

**删除**：原 `ingest_qa.py` 中所有针对 v2 的检查函数（约 40 个），全部删除。

**验收**：
- `wc -l scripts/ingest_qa.py` < 250
- 用 `/tmp/ingest-9314b977-bundle-v3.json` 跑 review-bundle 必须 pass（0 errors）
- 用现有 v2 bundle 跑 review-bundle 必须 fail（schema_version 不匹配）

---

### T4 — 重写 ingest_match.py（jaccard 匹配）

**文件**：`scripts/ingest_match.py`（重写）

**目标**：用 semantic_key + scope + direction 三元组做 jaccard 匹配，砍掉 anchor_hash 逻辑。

**核心算法**：

```python
import re

def tokenize_zh(s: str) -> set[str]:
    """中文按字 + 英数按词。filter 长度=1 的非中文字符。"""
    s = s.lower().strip()
    tokens = set()
    # 中文字逐字
    for ch in s:
        if '一' <= ch <= '鿿':
            tokens.add(ch)
    # 英数按 \w+
    for w in re.findall(r"[a-z0-9]+", s):
        if len(w) >= 2:
            tokens.add(w)
    return tokens

def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def match_against_registry(claim: dict, registry: ClaimRegistry) -> list[dict]:
    """对一条 v3 claim，返回 top 5 候选 ClaimRegistry record + jaccard score。"""
    scope_type, scope_ref = _split_scope(claim["scope"])
    if scope_type == "cross_cutting":
        existing = registry.all_claims_for_scope_type("cross_cutting")
    else:
        existing = registry.claims_for_scope(scope_type, scope_ref)
    new_tokens = tokenize_zh(claim["semantic_key"])
    scored = []
    for ec in existing:
        # 必须同 scope_type + scope_ref（cross_cutting 已 pre-filter）
        sc = jaccard(new_tokens, tokenize_zh(ec["semantic_key"]))
        scored.append({
            "claim_id": ec["claim_id"],
            "text": ec["text"],
            "semantic_key": ec["semantic_key"],
            "direction": ec["direction"],
            "score": sc,
            "same_direction": ec["direction"] == claim["direction"],
        })
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:5]


def decide_route(claim: dict, top_matches: list[dict]) -> tuple[str, str]:
    """返回 (route, reason)。route ∈ {auto_apply, pending_review}。"""
    # risk 类强制 pending（保留原 P0.3 规则）
    if claim["type"] == "risk":
        return "pending_review", "risk_class_forced_review"
    # direction=-1 且非 risk（即反驳类）也强制 pending
    if claim["direction"] == -1 and claim["type"] != "risk":
        return "pending_review", "negative_direction_forced_review"
    # 高 jaccard + 同方向 + high confidence → auto_apply attach
    if top_matches and top_matches[0]["score"] >= 0.6 and top_matches[0]["same_direction"]:
        if claim["confidence"] == "high":
            return "auto_apply", f"high_jaccard_attach_to_{top_matches[0]['claim_id']}"
        else:
            return "pending_review", f"medium_jaccard_attach_candidate_{top_matches[0]['claim_id']}"
    # 无匹配 + high confidence → auto_apply new
    if not top_matches or top_matches[0]["score"] < 0.3:
        if claim["confidence"] == "high":
            return "auto_apply", "new_high_confidence"
        return "pending_review", "new_low_confidence"
    # 中等 jaccard 总是 pending
    return "pending_review", "ambiguous_match"


def _split_scope(scope: str) -> tuple[str, str]:
    """'industry/cn-pet-industry' → ('industry', 'cn-pet-industry')
       'brand:玛氏' → ('brand', '玛氏')
       'cross_cutting' → ('cross_cutting', '')"""
    if scope == "cross_cutting":
        return "cross_cutting", ""
    if scope.startswith("brand:"):
        return "brand", scope[len("brand:"):]
    if "/" in scope:
        kind, ref = scope.split("/", 1)
        return kind, ref
    raise ValueError(f"invalid scope: {scope}")
```

**输出文件**：

- `auto_apply.json`：route=auto_apply 的 claim 列表，每条含 `bundle_local_id`、`decision`（"new" 或 "attach"）、`target_claim_id`（attach 时填）、`reason`。
- `pending_review.json`：route=pending_review 的 claim 列表，每条含 `top_matches` 供用户决策。

**CLI**：

```
.venv/bin/python -m scripts.ingest_match \
    --bundle /tmp/ingest-{sha8}-bundle.json \
    --registry-base . \
    --auto-out /tmp/ingest-{sha8}-auto_apply.json \
    --pending-out /tmp/ingest-{sha8}-pending_review.json
```

**删除**：原 `_compute_anchor_hash`、`_find_anchor_match` 函数。原 `derive_arena_candidates` 也删除（v3 没有 arena_candidates）。

**验收**：用 `/tmp/ingest-9314b977-bundle-v3.json` 在空 registry 上跑：
- 全部 35 claim 进入 auto_apply 或 pending_review，无报错
- risk 类 (3 条) 全部进 pending_review

---

### T5 — 重写 ingest_apply.py

**文件**：`scripts/ingest_apply.py`（重写）

**目标**：把 auto_apply.json 和 pending_review.json 的 decision 落地到 ClaimRegistry，并维护 relations 跨 bundle 累积。

**核心流程**：

```python
def apply_decisions(bundle: dict, decisions: list[dict], registry: ClaimRegistry, now: str) -> list[dict]:
    """decisions 是 auto_apply.json 和 pending_review.json 合并后的所有有 decision 字段的行。
    返回 applied.jsonl 行列表（每条 {bundle_local_id, claim_id, action}）。"""
    bundle_to_persistent = {}  # 本地 c1 → persistent claim_id
    applied = []

    # Pass 1: 处理 new + attach（不含 relations）
    for row in decisions:
        if row.get("decision") == "skip":
            continue
        bid = row["bundle_local_id"]
        claim_v3 = _find_claim_in_bundle(bundle, bid)
        if row["decision"] == "new":
            persistent_id = registry.create_claim_v3(claim_v3, bundle["meta"], now)
            bundle_to_persistent[bid] = persistent_id
            applied.append({"bundle_local_id": bid, "claim_id": persistent_id, "action": "new"})
        elif row["decision"] == "attach":
            target_id = row["target_claim_id"]
            registry.attach_evidence_v3(target_id, claim_v3, bundle["meta"], now)
            bundle_to_persistent[bid] = target_id
            applied.append({"bundle_local_id": bid, "claim_id": target_id, "action": "attach"})
        # split 暂不支持（用户用 skip + 手动新建替代）

    # Pass 2: 处理 relations（必须等所有 claim 落地后才能解析）
    for row in decisions:
        if row.get("decision") == "skip":
            continue
        bid = row["bundle_local_id"]
        claim_v3 = _find_claim_in_bundle(bundle, bid)
        my_persistent = bundle_to_persistent.get(bid)
        if not my_persistent:
            continue
        for rel in claim_v3.get("relations", []):
            target_persistent = bundle_to_persistent.get(rel["to"])
            if not target_persistent:
                continue  # 目标 claim 被 skip 了
            registry.append_relation_v3(my_persistent, target_persistent, rel["kind"], bundle["meta"]["source_id"])

    return applied
```

**ClaimRegistry 新方法**（在 `app/io/claim_registry.py` 里加）：

```python
def create_claim_v3(self, claim_v3: dict, meta: dict, now: str) -> str:
    """从 v3 claim + bundle meta 创建一条 ClaimRegistry record，返回 claim_id。"""
    scope_type, scope_ref = _split_scope_v3(claim_v3["scope"])
    year = meta["published_at"][:4]
    new_id = self._next_id_v3(scope_type, year)
    record = {
        "claim_id": new_id,
        "schema_version": "v3",
        "scope_type": scope_type,
        "scope_ref": scope_ref,
        "text": claim_v3["text"],
        "type": claim_v3["type"],
        "direction": claim_v3["direction"],
        "confidence": claim_v3["confidence"],
        "semantic_key": claim_v3["semantic_key"],
        "evidence": [
            _evidence_with_provenance(e, meta, claim_v3["direction"])
            for e in claim_v3["evidence"]
        ],
        "sources": [{
            "source_id": meta["source_id"],
            "institution": meta["institution"],
            "as_of": meta["published_at"],
            "direction_in_source": claim_v3["direction"],
            "confidence_in_source": claim_v3["confidence"],
            "bundle_local_id": claim_v3["id"],
        }],
        "relations": [],
        "first_seen_at": now,
        "last_updated_at": now,
    }
    self._rows_by_scope_type.setdefault(scope_type, []).append(record)
    self._persist_scope(scope_type)
    return new_id

def attach_evidence_v3(self, claim_id: str, claim_v3: dict, meta: dict, now: str) -> None:
    """把 v3 claim 的 evidence 累加到现有 record。text/direction/confidence 走 last-writer-wins。"""
    record = self.find_by_id(claim_id)
    if not record:
        raise ValueError(f"claim not found: {claim_id}")
    # 累积 evidence
    for e in claim_v3["evidence"]:
        record["evidence"].append(_evidence_with_provenance(e, meta, claim_v3["direction"]))
    # 追加 source
    record["sources"].append({
        "source_id": meta["source_id"],
        "institution": meta["institution"],
        "as_of": meta["published_at"],
        "direction_in_source": claim_v3["direction"],
        "confidence_in_source": claim_v3["confidence"],
        "bundle_local_id": claim_v3["id"],
    })
    # last writer wins
    record["text"] = claim_v3["text"]
    record["direction"] = claim_v3["direction"]
    record["confidence"] = claim_v3["confidence"]
    record["last_updated_at"] = now
    self._persist_scope(record["scope_type"])

def append_relation_v3(self, from_id: str, to_id: str, kind: str, source_id: str) -> None:
    """累积 relation。键 'kind|to' 去重。"""
    record = self.find_by_id(from_id)
    key = f"{kind}|{to_id}"
    existing = {f"{r['kind']}|{r['to']}" for r in record.get("relations", [])}
    if key not in existing:
        record.setdefault("relations", []).append({
            "to": to_id,
            "kind": kind,
            "from_source": source_id,
        })
    record["last_updated_at"] = now_iso()
    self._persist_scope(record["scope_type"])

def _next_id_v3(self, scope_type: str, year: str) -> str:
    """生成 {scope_type}-c-{year}-{NNNN}。NNNN 是该 (scope_type, year) 下递增。"""
    rows = self._rows_by_scope_type.get(scope_type, [])
    existing_nums = []
    prefix = f"{scope_type}-c-{year}-"
    for r in rows:
        cid = r.get("claim_id", "")
        if cid.startswith(prefix):
            try:
                existing_nums.append(int(cid[len(prefix):]))
            except ValueError:
                pass
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    return f"{prefix}{next_num:04d}"
```

**`_split_scope_v3`** 在 `app/io/claim_registry.py` 顶层新增（与 ingest_match.py 内的同名工具保持一致；建议提取到 `app/io/scope_utils.py` 共享）。

**SCOPE_FILES 映射扩展**：

```python
SCOPE_FILES = {
    "industry": "industries.jsonl",
    "arena": "arenas.jsonl",
    "company": "companies.jsonl",
    "brand": "brands.jsonl",            # 新增
    "cross_cutting": "cross_cutting.jsonl",
}
```

**CLI**：

```
.venv/bin/python -m scripts.ingest_apply \
    --bundle /tmp/ingest-{sha8}-bundle.json \
    --registry-base . \
    --decisions /tmp/ingest-{sha8}-auto_apply.json \
    --decisions /tmp/ingest-{sha8}-pending_review.json \
    --applied-out /tmp/ingest-{sha8}-applied.jsonl
```

**删除**：原 `derive_arena_candidates`、`_apply_split` 暂时禁用（split 路径 v3 不实现，遇到 decision="split" 报错）。

**验收**：
- 把核聚变 v3 bundle 全 decision="new" apply 到空 registry，应产生 35 条 ClaimRegistry record，分布在 industries/companies/cross_cutting 三个 jsonl
- relations 总数 = bundle 里 relations 数（72 条全部映射到 persistent id）
- 重跑同一份 bundle（全 attach），evidence 翻倍，relations 不重复（按 kind|to 去重）

---

### T6 — Scope 工具模块

**文件**：`app/io/scope_utils.py`（新建）

**目的**：消除 ingest_match.py 与 claim_registry.py 之间的 `_split_scope` 重复。

**内容**：

```python
"""Bundle v3 scope helpers."""

VALID_SCOPE_TYPES = {"industry", "arena", "company", "brand", "cross_cutting"}


def split_scope(scope: str) -> tuple[str, str]:
    """
    'industry/cn-pet-industry' -> ('industry', 'cn-pet-industry')
    'company/SSE_603011'        -> ('company', 'SSE_603011')
    'arena/cn-fusion-magnet'    -> ('arena', 'cn-fusion-magnet')
    'brand:玛氏'                  -> ('brand', '玛氏')
    'cross_cutting'              -> ('cross_cutting', '')
    """
    if scope == "cross_cutting":
        return "cross_cutting", ""
    if scope.startswith("brand:"):
        ref = scope[len("brand:"):]
        if not ref:
            raise ValueError(f"empty brand ref: {scope!r}")
        return "brand", ref
    for prefix in ("industry/", "arena/", "company/"):
        if scope.startswith(prefix):
            ref = scope[len(prefix):]
            if not ref:
                raise ValueError(f"empty ref: {scope!r}")
            return prefix.rstrip("/"), ref
    raise ValueError(f"invalid scope: {scope!r}")


def join_scope(scope_type: str, scope_ref: str) -> str:
    if scope_type == "cross_cutting":
        return "cross_cutting"
    if scope_type == "brand":
        return f"brand:{scope_ref}"
    if scope_type in {"industry", "arena", "company"}:
        return f"{scope_type}/{scope_ref}"
    raise ValueError(f"invalid scope_type: {scope_type!r}")


def is_valid_scope(scope: str) -> bool:
    try:
        split_scope(scope)
        return True
    except ValueError:
        return False
```

**改造点**：`ingest_match.py`、`claim_registry.py`、`ingest_qa.py` 全部 import 这个模块的 `split_scope` / `is_valid_scope`，不重复实现。

**验收**：单元测试覆盖 5 种 scope 格式 + 3 种异常情况。测试文件：`tests/test_scope_utils.py`。

---

### T7 — render_views.py（替代 narrative 三件套）

**文件**：`scripts/render_views.py`（新建）

**目标**：从 ClaimRegistry 渲染下游所有 view 文件（.md），是机械模板渲染，不调 LLM。

**渲染目标（按优先级）**：

1. **每个 industry 的 narrative.md** — `industries/{slug}/narrative.md`
2. **每个 arena 的 narrative.md** — `arenas/{slug}/narrative.md`
3. **每个 company 的 dashboard.md** — `companies/{TICKER}/dashboard.md`
4. **每个 brand 的 brief.md** — `brands/{name}/brief.md`（新目录）
5. **每个 bundle 的 INSIGHTS.md** — `industries/{slug}/insights/{bundle_sha8}.md`（或对应 company 路径）

**统一 narrative.md 模板**（industry/arena/brand 共用）：

```markdown
---
scope_type: {scope_type}
scope_ref: {scope_ref}
last_rendered: {ISO}
claim_count: {N}
source_count: {M}
---

# {scope display name}

## 一句话主线
{从最新 bundle 的 summary.one_liner 拿；多 bundle 时取 published_at 最新}

## 主要论点（按 type 分组）

### Thesis（{n} 条）
- **{claim.text}** [{semantic_key}]  
  方向: {direction emoji}  · 置信: {conf}  · 来源: {institution list}  
  最新证据: "{evidence[-1].quote[:100]}" — {institution}, {as_of}

### Judgment（{n} 条）
... 同上格式 ...

### Catalyst（{n} 条）
...

### Risk（{n} 条）
...

## 共识与分歧
{groupby semantic_key, 同 key 多条 record 时}
- "国产替代": 中银/中信均看多，毕马威保留意见 → consensus_strength=2/3
- "原料风险": 中银/西部超导年报方向相反 → divergence

## 关系链路（简略）
{选 top 5 relations, 例: "c12 → leads_to → c19 → because_of → c33"}

## 边界（cannot_conclude 跨 source 累积）
- {一条/source}
```

**dashboard.md 模板**（company 专用，沿用现有结构但改为 v3 数据源）：

```markdown
---
ticker: {MARKET_TICKER}
last_rebuilt: {ISO}
source_count: {N}
---

# {company name} ({TICKER}) — 多源观点面板

## 观点矩阵
| source | as_of | type | claim | direction | confidence |
|---|---|---|---|---|---|
| {institution-as_of} | ... | thesis | ... | +1 | high |

## 时间线
{以 as_of 排序的 source list}

## 共识与分歧
{同 narrative.md}

## 风险一览
{所有 type=risk 的 claim}
```

**INSIGHTS.md 模板**（每 bundle 一份）：

```markdown
---
source_id: {source_id}
bundle_path: {path}
synthesized_at: {ISO}
---

# {meta.source_title}

## 一句话核心
> {summary.one_liner}

## 主要叙事线
{for thread in summary.threads:}
### {thread.title}
{for claim_id in thread.claim_ids: 渲染 claim text + evidence[0].quote}

## 关键数字
{所有 confidence=high 且 evidence 有 page 的 evidence quote, 最多 8 条}

## 不能由本报告得出的结论
{summary.cannot_conclude}

## 注意事项
{notes.weak_evidence}
```

**CLI**：

```
.venv/bin/python -m scripts.render_views \
    --registry-base . \
    [--scope industry|arena|company|brand|all] \
    [--ref <slug_or_ticker>] \
    [--bundle <bundle_path>]   # 仅渲染单个 bundle 的 INSIGHTS.md

# 全量重建:
.venv/bin/python -m scripts.render_views --scope all
```

**实现要点**：
- 不调 LLM
- 渲染前清空目标文件（避免增量产生 stale 内容）
- 使用 `app.io.claim_registry.ClaimRegistry` 读 registry
- 关系链路提取算法：在 registry 内按 scope 子集做 BFS 找最长连通链，输出最长 5 条

**验收**：
- 把核聚变 + 宠物两份 v3 bundle apply 到 registry 后，运行 `render_views.py --scope all`
- 产出文件：`industries/cn-nuclear-fusion/narrative.md`、`industries/cn-pet-industry/narrative.md`、4 个公司的 `dashboard.md`、各 bundle 的 INSIGHTS.md
- 文件内容包含 frontmatter + 论点表格 + 共识分歧段

---

### T8 — 删除 narrative_propose / narrative_apply / narrative_flags

**删除文件**：
- `scripts/narrative_propose.py`
- `scripts/narrative_apply.py`
- `scripts/narrative_flags.py`

**保留**：`app/io/narrative_proposals.py` —— 这是 web routes 的依赖。**先不删**，T11 处理。

**测试文件清理**：
- `tests/test_narrative_apply_cli.py` —— 删除
- `tests/test_narrative_flags.py` —— 删除
- `tests/test_industry_narrative_flags.py` —— 删除（或重写为 v3 版本）
- `tests/test_company_narrative_flags.py` —— 删除
- `tests/test_phase3c_narrative_end_to_end.py` —— 删除
- `tests/test_workflow_integration.py` —— 改写：把 narrative_propose/apply 步骤替换为 ingest_apply + render_views

**验收**：
- `git ls-files scripts/narrative_*.py` 空输出
- `pytest tests/` 在删除上述测试后全部 pass（或者只剩可复现的失败由 T11 处理）

---

### T9 — 历史 bundle 迁移脚本

**文件**：`scripts/migrate_bundle_v2_to_v3.py`（新建）

**目标**：把 `industries/*/bundles/*.json` 里所有 v2 bundle 转换为 v3 格式（写到同名 `*-v3.json`），并选择性重建 ClaimRegistry。

**转换规则**：

```python
def convert_v2_to_v3(v2: dict) -> dict:
    sd = v2["source_digest"]
    v3 = {
        "schema_version": "v3",
        "meta": {
            "source_id": sd.get("source_id", ""),
            "source_title": sd.get("source_title", ""),
            "institution": _extract_institution(sd.get("source_id", "")),
            "published_at": sd.get("source_date", "1970-01-01"),
            "source_type": _map_source_type(sd.get("source_type")),
            "primary_scope": _infer_primary_scope(v2),
            "touches": _build_touches(v2),
        },
        "claims": [],
        "summary": {},
        "notes": {},
    }
    # claims: 从 claim_candidates 转
    ib_to_facts = _index_facts_by_block(v2)
    for cc in v2.get("claim_candidates", []):
        new_claim = {
            "id": cc["candidate_id"].replace("cc-", "c"),
            "text": cc["claim_text"],
            "type": _map_claim_type(cc.get("claim_type")),
            "scope": _build_scope(cc),
            "direction": _direction_from_v2(cc),
            "confidence": _map_confidence(cc.get("confidence")),
            "evidence": _build_evidence(cc, ib_to_facts),
            "relations": [],   # v2 没有 claim 间 relations，留空
            "semantic_key": cc.get("semantic_nucleus", "")[:20],
            "as_of": cc.get("as_of", sd.get("source_date", "1970-01-01")),
        }
        v3["claims"].append(new_claim)
    # summary: 从 synthesis 转
    syn = v2.get("synthesis", {})
    v3["summary"] = {
        "one_liner": syn.get("one_sentence", ""),
        "threads": _threads_from_narrative_arc(v2.get("narrative_arc", []), v3["claims"]),
        "cannot_conclude": syn.get("cannot_conclude", []),
    }
    # notes: 从 limitations 转
    v3["notes"] = {
        "skipped_sections": (sd.get("coverage_review", {}).get("coverage_notes", []) or [])[:3],
        "weak_evidence": sd.get("limitations", []),
    }
    return v3


def _map_claim_type(v2_type: str) -> str:
    """v2 5 值 → v3 4 值"""
    return {
        "thesis": "thesis",
        "judgment": "judgment",
        "risk": "risk",
        "scenario": "judgment",          # 合并
        "gate_assessment": "judgment",   # 合并
    }.get(v2_type, "judgment")


def _direction_from_v2(cc: dict) -> int:
    if cc.get("claim_type") == "risk":
        return -1
    return {"supports": 1, "neutral": 0, "refutes": -1}.get(cc.get("direction_on_source"), 0)


def _build_scope(cc: dict) -> str:
    st = cc.get("scope_type")
    sr = cc.get("scope_ref", "")
    if st == "cross_cutting":
        return "cross_cutting"
    if st == "company":
        return f"company/{sr}"
    return f"{st}/{sr}"


def _build_evidence(cc: dict, ib_to_facts: dict) -> list[dict]:
    """从 supporting_block_ids → atomic_facts → evidence。每条最多 5 个。"""
    evidence = []
    for ib_id in cc.get("supporting_block_ids", []):
        for f in ib_to_facts.get(ib_id, []):
            evidence.append({
                "quote": f.get("evidence_quote", ""),
                "page": f.get("source_page"),
                "why": f.get("fact_text", "")[:30],
            })
            if len(evidence) >= 5:
                return evidence
    return evidence
```

**CLI**：

```
.venv/bin/python -m scripts.migrate_bundle_v2_to_v3 \
    --bundles "industries/*/bundles/*.json" \
    --output-suffix "-v3" \
    [--rebuild-registry]   # 可选：迁移后清空 registry 并重新 apply 全部 v3 bundle
```

**输出报告**（stdout）：每个 bundle 的转换前后 claim 数 + 跳过原因（如有）。

**验收**：
- 现有 4 个 v2 bundle（核聚变 3 + 宠物 1）全部转换为 v3，无报错
- 转换后的 v3 bundle 用 `ingest_qa review-bundle` 校验，errors=0（warnings 允许，因为缺 relations）
- 可选：用 `--rebuild-registry` 重建 ClaimRegistry，count match 转换后所有 v3 bundle 的 claim 总和

---

### T10 — Skill / workflow 文档更新

**文件**：
- `.claude/skills/ingest/SKILL.md`（修改）
- `.claude/skills/ingest/workflows/_ingest-common.md`（重写为 6 步版本）
- `.claude/skills/ingest/workflows/{annual-report,quarterly-report,sell-side-note,industry-research}.md`（精简，移除 v2 特有步骤）

**`_ingest-common.md` 6 步骨架**：

```markdown
# Endgame Ingest Common Workflow (v3)

## Step 1 — Convert Source

PDF 推荐 MinerU：
```bash
.venv/bin/python -m scripts.mineru_ingest <mineru_dir> --out /tmp/ingest-{sha8}-mineru.json
```

## Step 2 — Extract Bundle

Dispatch general-purpose subagent (sonnet model) with `docs/prompts/ingest-review-bundle-v3.md` 作为 prompt body. 输出 v3 bundle JSON 到 `/tmp/ingest-{sha8}-bundle.json`.

## Step 3 — Validate

```bash
.venv/bin/python -m scripts.ingest_qa review-bundle \
    --bundle /tmp/ingest-{sha8}-bundle.json \
    --mineru-md <mineru_dir>/full-clean.md
```

errors > 0 必须修复 bundle 后重跑。warnings 可视情况修。

## Step 4 — Resolve Entities

For each industry/company/arena/brand in `meta.touches`:
```python
agg.ensure_industry_exists(slug=...)
agg.ensure_company_exists(ticker=..., market=..., name=..., industry_slugs=[...])
agg.ensure_arena_exists(slug=..., name=..., parent_industry_slug=...)   # T11.5 新增
agg.ensure_brand_exists(name=...)                                       # T11.5 新增
```

## Step 5 — Match & Decide

```bash
.venv/bin/python -m scripts.ingest_match \
    --bundle /tmp/ingest-{sha8}-bundle.json \
    --registry-base . \
    --auto-out /tmp/ingest-{sha8}-auto_apply.json \
    --pending-out /tmp/ingest-{sha8}-pending_review.json
```

Review pending_review.json via AskUserQuestion. 设置 decision = new | attach | skip.

## Step 6 — Apply & Render

```bash
.venv/bin/python -m scripts.ingest_apply \
    --bundle /tmp/ingest-{sha8}-bundle.json \
    --registry-base . \
    --decisions /tmp/ingest-{sha8}-auto_apply.json \
    --decisions /tmp/ingest-{sha8}-pending_review.json \
    --applied-out /tmp/ingest-{sha8}-applied.jsonl

# 持久化 bundle
python -c "from app.io.bundle_registry import persist_bundle; ..."

# 渲染下游 view
.venv/bin/python -m scripts.render_views --scope all
```
```

**`SKILL.md` 修改**：在「## Pipeline Overview」段把 15 步改为本 6 步，删除 narrative_propose 等所有引用，删除 stage_gate / claim_decay 引用。

**workflow 文件**：保留 source_type 路由信息和 figure_contexts 写入位置（这部分不变），删除所有 narrative_priority / block_type 必提清单引用。

**验收**：
- `grep -rn "narrative_propose\|narrative_apply\|narrative_flags\|insight_block\|atomic_fact\|stage_gate" .claude/skills/ingest/` 为空
- 6 步 workflow 可独立执行（不引用任何已删除脚本）

---

### T11 — Web routes 兼容性

**问题**：`app/routes/{industries,arenas,companies}.py` + `app/io/narrative_proposals.py` 当前依赖 narrative .md 文件按 dimension 拆分（valuation.md / competitive_moat.md 等）。v3 改为按 scope 单一 narrative.md。

**最小改造方案**（保持 web 可访问，不重写路由）：

1. **保留 `app/io/narrative_proposals.py`**，但删除写入相关的函数（`save_proposal`, `apply_proposal` 等），保留读取函数。
2. **路由文件**：`industries.py` / `arenas.py` / `companies.py` 在读取 narrative 时：
   - 优先读 `industries/{slug}/narrative.md`（v3 单文件）
   - 找不到时降级读旧的 dimension .md 文件（兼容期保留）
3. **新增** `app/io/narrative_v3.py`：

```python
"""Read v3 narrative.md files."""

def load_industry_narrative(slug: str, base: Path | None = None) -> str | None:
    p = (base or Path(".")) / "industries" / slug / "narrative.md"
    return p.read_text(encoding="utf-8") if p.exists() else None

def load_arena_narrative(slug: str, base: Path | None = None) -> str | None:
    p = (base or Path(".")) / "arenas" / slug / "narrative.md"
    return p.read_text(encoding="utf-8") if p.exists() else None

def load_brand_brief(name: str, base: Path | None = None) -> str | None:
    p = (base or Path(".")) / "brands" / name / "brief.md"
    return p.read_text(encoding="utf-8") if p.exists() else None
```

4. **路由调整**：在每个 view function 起始处，先尝试 `load_*_narrative()`，命中即渲染 markdown 整页；未命中走旧逻辑。

**验收**：
- 跑 `app/main.py` 启动 server
- 访问 `/industries/cn-nuclear-fusion` 应渲染新 narrative.md（运行 render_views 后）
- 访问没 v3 narrative 的实体仍能访问（降级到旧逻辑）

---

### T12 — agg.ensure_brand / ensure_arena helper

**文件**：`scripts/ingest_aggregate.py`（修改）

加两个函数：

```python
def ensure_brand_exists(name: str, base: Path = Path(".")) -> Path:
    """如果 brands/{name}/ 不存在则建。返回目录路径。"""
    brand_dir = base / "brands" / name
    brand_dir.mkdir(parents=True, exist_ok=True)
    meta_file = brand_dir / "meta.yaml"
    if not meta_file.exists():
        meta_file.write_text(f"name: {name}\ncreated_at: {now_iso()}\n", encoding="utf-8")
    return brand_dir


def ensure_arena_exists(slug: str, name: str, parent_industry_slug: str, base: Path = Path(".")) -> Path:
    """如果 arenas/{slug}/ 不存在则建。"""
    arena_dir = base / "arenas" / slug
    arena_dir.mkdir(parents=True, exist_ok=True)
    meta_file = arena_dir / "meta.yaml"
    if not meta_file.exists():
        meta_file.write_text(
            f"slug: {slug}\nname: {name}\nparent_industry_slug: {parent_industry_slug}\n"
            f"created_at: {now_iso()}\n",
            encoding="utf-8",
        )
    return arena_dir
```

**验收**：单元测试调用两个函数，验证目录 + meta.yaml 创建成功。

---

## 6. 删除清单

完成所有 T 后，下列文件应彻底从 repo 移除：

```
scripts/narrative_propose.py
scripts/narrative_apply.py
scripts/narrative_flags.py
scripts/check_stage_gates.py        # P3.3 设计但价值低
scripts/claim_decay_check.py        # P3.2 设计但本期不做
scripts/synthesize_insights.py      # 由 render_views.py 替代
scripts/build_company_dashboard.py  # 由 render_views.py 替代

tests/test_narrative_apply_cli.py
tests/test_narrative_flags.py
tests/test_industry_narrative_flags.py
tests/test_company_narrative_flags.py
tests/test_phase3c_narrative_end_to_end.py
tests/test_synthesize_insights.py   # 如存在

docs/prompts/ingest-review-bundle.md   # 旧 v2 prompt 归档到 docs/superpowers/archive/
docs/prompts/synthesize-insights.md    # 同上归档
```

`app/io/narrative_proposals.py` 暂留（保留读取函数），后续 PR 完全清理。

---

## 7. 阶段依赖

```
T1 (schema doc)         ─┐
T2 (prompt doc)         ─┼── 可并行
T6 (scope_utils)        ─┘
                          ↓
T3 (qa)                 ─┐
T4 (match)              ─┤── 依赖 T6
T5 (apply + registry)   ─┤── 依赖 T6
T12 (ensure_brand/arena) ┘
                          ↓
T7 (render_views)       ─── 依赖 T5
                          ↓
T8 (delete narrative)   ─── 依赖 T7（确保 view 替代后再删）
                          ↓
T11 (route compat)      ─── 依赖 T7
T9 (migration)          ─── 依赖 T3-T5
                          ↓
T10 (skill/workflow)    ─── 最后写文档
```

推荐 commit 顺序：
1. Commit 1：T1 + T2（纯文档）
2. Commit 2：T6（scope_utils + 测试）
3. Commit 3：T5（claim_registry v3 方法 + apply 重写）+ T12（ensure helper）
4. Commit 4：T4（match 重写）
5. Commit 5：T3（qa 简化）
6. Commit 6：T7（render_views）
7. Commit 7：T8（删除 narrative 三件套）+ T11（路由兼容）
8. Commit 8：T9（migration script + 跑迁移）
9. Commit 9：T10（skill / workflow 文档）

每个 commit 跑一次 `pytest tests/` 确保不退化。

---

## 8. 整体验收

### 8.1 功能验收

- [ ] 用核聚变 + 宠物 + 一份现有年报（任选）跑端到端 v3 ingest，无错误
- [ ] 三种 source_type 都能产出符合 §2.1 的 v3 bundle
- [ ] `ingest_qa review-bundle` 对 3 份新 bundle 全部 0 errors
- [ ] `ingest_match` 在第二次 ingest 同一份研报时识别相似 claim 走 attach
- [ ] `ingest_apply` 写入 ClaimRegistry，relations 跨 bundle 正确累积
- [ ] `render_views --scope all` 产出所有 view 文件，markdown 渲染正常

### 8.2 代码质量验收

- [ ] `scripts/ingest_qa.py` ≤ 250 行
- [ ] `docs/prompts/ingest-review-bundle-v3.md` 主体 ≤ 900 字
- [ ] 5 套枚举（v2 时代）只剩 1 套（claim.type 4 值）
- [ ] 无任何代码 import `narrative_propose / narrative_apply / narrative_flags`
- [ ] `pytest tests/` 全部 pass

### 8.3 通用性回归

| 行业大类 | 样本 | 必须验证点 |
|---|---|---|
| technology_driven | 核聚变 | claim ≥ 25，4 公司各 ≥ 3 条独立 claim，relations isolated 比例 < 10% |
| consumer_driven | 宠物 | claim ≥ 30，子赛道 ≥ 4 条独立，人口因素 ≥ 3 条独立 |
| sell_side / annual | 任一历史样本 | 字段映射正确，无 v2 残留字段 |

### 8.4 性能锚

- 单次 sonnet ingest token 消耗稳定在 100k-180k（v2 时代约 70k，v3 因 prompt 简化、字段填充少，但内容更密，预期略增）
- 单次 sonnet ingest 耗时 ≤ 15 分钟
- `pytest tests/` 整体耗时不增加 > 10%

---

## 9. 不做（明确排除）

1. 不引入嵌入向量服务（jaccard 已够用）
2. 不重写 `app/routes/*.py` UI 渲染逻辑（T11 只做 fallback hook）
3. 不删除历史 v2 narrative .md 文件（保留兼容期，3 个月后另一 PR 清理）
4. 不实现 `decision="split"` 路径（v3 暂不支持，遇到时报错）
5. 不实现 stage_gate 自动追踪 / claim decay（用 cannot_conclude + risk type 替代足够）
6. 不做英文研报支持（保持中文 A 股 / KPMG 等场景）
7. 不实现跨研报 LLM 合成 narrative（INSIGHTS.md / dashboard 全部机械模板）

---

## 10. 参考实测数据（决策依据）

### 核聚变研报 v2 vs v3

| 指标 | v2 (sonnet) | v3 (sonnet) |
|---|---|---|
| 中间结构 | 9 ib + 6 claim | 35 claim 直接 |
| 公司维度 | 4 公司压成 1 ib | 4 公司各 3-5 条 |
| relations | 0 有效 | 72 有效，0 isolated |
| 耗时 | 16.5 min | 7 min |
| token | 71k | 162k |

### 宠物研报 v3 sonnet vs opus

| 指标 | sonnet | opus 4.7 |
|---|---|---|
| claim 数 | 43 | 50 |
| relations | 67 | 31 |
| isolated | 0 | 16 |
| token | 137k | 131k |
| 耗时 | 10.4 min | 3.9 min |

**结论**：sonnet 在 v3 schema 下产出质量优于 opus（关系图谱更完整），且成本更低。本计划主链路定 sonnet。

---

## 11. 实施前必读

1. **不要把 v3 prompt 加任何"必提"条款**。本计划核心信念是 prompt 里出现"必提 X 类"会触发 LLM 计数锚定，反而压缩内容。
2. **不要恢复 anchor_hash 机制**。jaccard 在实测中通过率足够，且更人类可读。
3. **不要扩展 claim.type 超过 4 值**。每加一个值都会增加 LLM 决策负担。
4. **不要把 evidence 拆出 claim**。把 atomic_facts 单独成数组是 v2 的反例。

5. **不要在 prompt 里加 source 特化的例子或品类**。这是 v2 时代积重难返的根因之一——每发现一种"漏掉的内容类型"就在 prompt 里加一句"必提 XX"或"举例 XX"，最终 prompt 膨胀到 28 条硬约束 + N 个细分例子。

   反例（实施时不要做）：
   - ❌ "人口结构因素（银发/单身/丁克）必须独立成 claim" —— 这是 consumer_driven 特化
   - ❌ "产业链环节（第一壁/偏滤器/磁体）必须独立成 claim" —— 这是 technology_driven 特化
   - ❌ "财务分部（按业务/按地域）必须独立成 claim" —— 这是 annual_report 特化

   正例（已在 v3 prompt 里）：
   - ✅ 原则 4 抽象表述："同类多实例必须独立成 claim"。具体例子在原则下作 illustration（"第一壁/偏滤器/磁体"作为示例，不作为强制类别），不展开为枚举清单。

   判断标准：**如果某条规则只对一种 source_type 或一种行业大类有效，就不要写进 prompt**。LLM 看到示例会顺势照做，不需要枚举。

6. **不要在 prompt 里重复已有规则**。
   - confidence 校准已在原则 8（"不要默认全 high"），不要在原则 3/4 里重复
   - 实体独立性已在原则 3+4，不要在原则 7 里再加一句"实体要独立"

   每加一句 prompt 文字都在抢 LLM 的注意力预算。重复规则反而稀释每条规则的权重。

7. **下游路由 > prompt 调整**。如果发现 LLM 输出某种系统性偏差（如"全 high"），优先在 `decide_route()` / `ingest_match.py` 解决，不在 prompt 里加文字。
   - sonnet 把 confidence 全标 high → 不要在 prompt 加"请校准 confidence"；改 `decide_route()` 要求 high confidence + high jaccard 才走 auto_apply
   - sonnet 漏掉某 scope 的 claim → 不要在 prompt 加"必须包含 X scope"；改 `ingest_qa.py` 在 meta.touches 与 claim.scope 不一致时 warn

8. **改 default 锚点 > 加内容**。当 prompt 已有规则但 LLM adherence 不足时，**重写规则的默认值锚点**，不要追加新文字。

   反例（"加"）：
   - ❌ 当前规则: "confidence 校准要细"
   - 错误修法: 在后面加 "请仔细评估每条 claim 的 evidence 质量，确保不要过度自信，特别注意远期预测应降为 medium 或 low"
   - 后果: prompt 变长，LLM 注意力被稀释，且新文字可能与现有 high/medium/low 定义重复

   正例（"重写默认锚"）：
   - 当前规则: "不要默认全 high。high：xxx；medium：xxx；low：xxx"
   - 正确修法: "默认 medium。high：xxx + xxx（更严）；low：xxx"
   - 字数不变或减少，但 LLM 的预设从 "high 是 default，需要降" 翻转为 "medium 是 default，需要升"，自然抑制偏差

   适用场景：
   - LLM 在某个枚举字段上偏向某一极值（confidence 全 high、direction 全 +1、type 全 thesis 等）
   - 不适合枚举值数量 ≤ 2 或语义无锚点优劣的字段（如 type 4 值无主次）

   实施前先验证：跑一次新 default 锚点版本，对比修改前后该字段的分布。如果分布显著向中间靠拢即采纳；如分布不变，说明是模型硬性 bias，转 §11.7 路由层处理。

按 §7 commit 顺序推进，每完成 1 个 commit 跑一次 `pytest`，确保不退化。

迁移完成后，用本计划 §8.3 的 3 份样本回归一次，全部 pass 才能声明 v3 上线。
