# 叙事系统

叙事系统是知识库的「合成层」——将原子化的 Claim 组织成结构化的可读档案。

## 架构

```
Claims (原子断言)
  │
  │ dimension_hint 映射
  ▼
Narrative Proposals (待审批的叙事草稿)
  │
  │ human decision: approve / edit / reject / defer
  ▼
Narrative Archive Files (Markdown 维度文件)
  │
  │ flag scanning
  ▼
Narrative Flags (一致性标记)
```

## 维度映射

每条 Claim 有一个 `dimension_hint` 字段，通过映射表转换为对应层级的叙事维度。映射是多对一的——多个不同的 dimension_hint 可以映射到同一个叙事维度。

### Industry 映射 (`CLAIM_DIMENSION_TO_INDUSTRY_NARRATIVE`)

```
market_size, tam          → market_size
lifecycle, stage_gate      → lifecycle
value_chain, supply_chain  → value_chain
competition, competitive_position, participants → competition
drivers, catalysts         → drivers
thesis, judgment           → drivers（注意：thesis/judgment 映射到 drivers 而非 narratives）
technology                 → technology
regulation                 → regulation
benchmark, winning_variables, moat → benchmark
risk, risks, scenario      → risks
valuation, investment_view, financial_profile → valuation
```

### Arena 映射 (`CLAIM_DIMENSION_TO_ARENA_NARRATIVE`)

```
participants, competition, competitive_position → participants
moat, technology, supply_chain, value_chain, benchmark, winning_variables → decisive_factors
catalysts, stage_gate, regulation, market_size, lifecycle, drivers → trajectory
thesis, judgment, risk, risks, scenario → narratives
valuation, investment_view, financial_profile → investment_view
```

### Company 映射 (`CLAIM_DIMENSION_TO_COMPANY_NARRATIVE`)

```
business_model, thesis        → business_model
moat, competition, competitive_position, technology, supply_chain, value_chain, winning_variables → moat
growth_engine, market_size, lifecycle, drivers → growth_engine
management                    → management
financial_profile, benchmark  → financial_profile
catalysts, stage_gate         → catalysts
regulation, risk, risks, scenario → risks
valuation, investment_view, judgment → valuation
```

## 核心模块

### `app/io/narrative_proposals.py`

该模块同时负责 **提案生成**、**提案验证**、**提案应用**、**标记扫描** 四个功能。

#### 提案生成 `build_proposal_file()`

```python
def build_proposal_file(
    *,
    registry: ClaimRegistry,         # 已加载的 Claim 注册表
    source_id: str,                  # 本次 ingest 的来源 ID
    generated_at: str,               # 生成时间
    existing_excerpt_loader: Callable,  # 读取已有叙事的回调
    scope_type: str = "arena",       # 层级类型
    scope_ref: str | None = None,    # 层级引用（slug）
) -> dict[str, Any]
```

流程：
1. 从 registry 过滤出 `scope_type + scope_ref + source_id` 的活跃 claims
2. 对每条 claim，通过 `scope.mapping.get(claim.dimension_hint)` 查找叙事维度
3. 按维度分组
4. 为每个维度生成一条 proposal
5. 调用 `existing_excerpt_loader` 读取已有叙事的尾部 1200 字符作为参考
6. 返回包含 proposals + unmapped_claims + summary_stats 的字典

#### 提案验证 `validate_proposal_decisions()`

验证规则：
- `decision` 必须是 "approve" | "edit" | "reject" | "defer" 之一
- 必须有 `decision_reason`
- 维度必须是该 scope 的合法叙事维度
- Arena 的 `definition` 维度不能通过提案写入（需手动编辑）
- approve/edit 决策必须有非空的 `supported_by_claims`
- 所有引用的 claim 必须存在且为 active 状态
- approve 的 `body` / edit 的 `edited_body` 不能是占位文本（"待 Claude"、"待填写" 等）

#### 提案应用 `apply_proposal_file()`

```python
def apply_proposal_file(
    *,
    data: dict[str, Any],            # 提案 JSON（含已填写的 decision）
    registry: ClaimRegistry,
    base: Path,
    pending_path: Path,
    today: str | None = None,
) -> dict[str, int]                  # {"applied": N, "rejected": N, "deferred": N}
```

对每条 proposal 按 decision 执行操作，并追加审计事件。

#### 标记扫描 `scan_narrative_flags()`

扫描已写入的叙事文件，解析每个 `###` 段落的 `supported_by_claims`，检查每条引用的 claim：
- claim 不存在 → `critical: supporting claim missing`
- claim 已 retired → `critical: supporting claim retired`
- claim 非 active → `critical: supporting claim not active`
- claim 有 refuting evidence → `significant: supporting claim has refuting evidence`

标记写入 `{scope}/{slug}/narrative-flags.jsonl`，Web UI 在叙事页面中展示。

## 文件路径解析

`dimension_path(base, scope_type, scope_ref, dimension)` 计算叙事文件的绝对路径：

```python
# Industry → industries/{slug}/{dimension}.md
# Arena    → arenas/{slug}/{dimension}.md
# Company  → companies/{slug}/narratives/{dimension}.md
```

维度名使用 kebab-case（`decisive_factors` → `decisive-factors.md`）。

## Web 渲染

叙事页面通过以下方式判断一个维度是否有实际内容：

```python
# industries.py 的 _is_skeleton_only()
def _is_skeleton_only(md: str) -> bool:
    stripped = md.strip()
    if not stripped.startswith("#"):
        return False
    # 有真实内容当且仅当包含旧 digest 格式或新 narrative_apply 格式标记
    return "### 来源" not in stripped and "supported_by_claims:" not in stripped
```

- 旧格式（digest）：包含 `### 来源 {institution} {date}`
- 新格式（narrative_apply）：包含 `supported_by_claims:` 元数据
- 如果只有 H1 标题行（骨架文件），视为无内容

同样的逻辑用于 arenas.py：

```python
has_content = md.strip() and ("### 来源" in md or "supported_by_claims:" in md)
```

## 叙事与 Lens 的区别

Archive 叙事回答「我们知道了什么」，Investment Lens 回答「我们的判断是什么」。

| | Archive | Lens |
|---|---|---|
| 来源 | 维度 .md 文件 | bundles + claims + archive |
| 视角 | 客观综合 | 主观判断 |
| 维度 | 行业 11 / 竞技场 6 / 公司 8 | 各有独立的维度定义 |
| 更新 | 通过 narrative_apply | 通过 lens 专用写入 |

Lens 维度定义在 `config.py` 的 `INDUSTRY_INVESTMENT_VIEW_DIMS`、`ARENA_BATTLEFIELD_VIEW_DIMS`、`COMPANY_MEMO_VIEW_DIMS` 中。
