# Plan: investment_lens 8/7/9 决策视图实现（三阶段）

## Context

`research-os-design.md §10.2-10.4` 定义了 investment_lens 三层投影视图——industry 8 维（`thesis/demand/supply_competition/profit_pool/unit_economics/stage_gates/catalysts_timeline/risks_disconfirming_evidence`）、arena 7 维（`battlefield_definition/players_positions/winning_variables/evidence_scoreboard/stage_gates/inflection_points/company_implications`）、company 9 维（`business_exposure/thesis_fit/moat_execution/financial_quality/growth_drivers/stage_gate_status/valuation_expectations/catalysts_risks/open_questions`）——但从未实现。

**与 archive 11/6/8 的定位区别**：archive 回答"关于这个实体我们知道什么"（分析面、归档），投影 Markdown 已由 Phase 3A/B/C 的 claim-proposal 管线写入。investment_lens 回答"我们的判断是什么、哪些证据会改变判断"（决策面），**尚未实现**。两层并列互补，不替代。

**数据源的权衡（关键讨论结论）**：  
- claim registry 保留跨报告去重 + lifecycle，但丢失 bundle 内 reasoning_chain 的叙事连贯
- bundle（`synthesis / stage_gates / insight_blocks / atomic_facts`）保留叙事连贯但无累积状态
- 结论：**lens 必须混合两种数据源**——decision-view 性字段（thesis / open_questions / stage_gates / ...）从 bundle synthesis 取；累积性字段（demand / profit_pool / financial_quality / ...）从 claim 聚合；archive narrative 段落作为已有写作上下文

**bundle 的多报告聚合**：`data/bundle_registry.jsonl` 每行带 `touched.{industries,arenas,companies}` 倒排索引，按 scope_ref 反查该实体被哪些 bundle 触及是廉价的 O(N_bundles) 扫描。

### 三阶段递进

每阶段独立可交付。Stage 1 的 mapping + fetcher 是 Stage 2/3 共用基础，代码无浪费。

| Stage | 交付 | 工作量 | 决策 |
|---|---|---|---|
| Stage 1 | `VIEW_DIMENSIONS` 配置 + `app/io/investment_lens.py` fetcher + 单测 | 2-3 天 | 必做 |
| Stage 2 | `/lens/{scope}/{slug}` 只读原料聚合页面，无写入层 | 1-2 天 | 基于 Stage 1 立即做 |
| Stage 3 | `app/io/lens_proposals.py` + Claude 对话综合 + `lens/{scope}/{slug}/{field}.md` 持久化 + lifecycle flag | 1-2 周 | **Stage 2 实际读过后再评估是否升级** |

---

## Stage 1 — Mapping + Fetcher（后端数据层）

### 1.1 配置：`app/config.py` 新增 VIEW_DIMENSIONS

现有 `INDUSTRY_DIMENSIONS / ARENA_DIMENSIONS / COMPANY_DIMENSIONS` 保持不变（archive 11/6/8）。新增：

```python
INDUSTRY_INVESTMENT_VIEW_DIMS = (
    "thesis", "demand", "supply_competition", "profit_pool",
    "unit_economics", "stage_gates", "catalysts_timeline",
    "risks_disconfirming_evidence",
)
ARENA_BATTLEFIELD_VIEW_DIMS = (
    "battlefield_definition", "players_positions", "winning_variables",
    "evidence_scoreboard", "stage_gates", "inflection_points",
    "company_implications",
)
COMPANY_MEMO_VIEW_DIMS = (
    "business_exposure", "thesis_fit", "moat_execution", "financial_quality",
    "growth_drivers", "stage_gate_status", "valuation_expectations",
    "catalysts_risks", "open_questions",
)

VIEW_DIMENSIONS = {
    "archive": {
        "industry": INDUSTRY_DIMENSIONS,
        "arena": ARENA_DIMENSIONS,
        "company": COMPANY_DIMENSIONS,
    },
    "investment_lens": {
        "industry": INDUSTRY_INVESTMENT_VIEW_DIMS,
        "arena": ARENA_BATTLEFIELD_VIEW_DIMS,
        "company": COMPANY_MEMO_VIEW_DIMS,
    },
}
```

### 1.2 字段 → 数据源 mapping 规则

每个 lens 字段的原料来自四类数据源的子集。mapping 表作为 `app/io/investment_lens.py` 顶部的常量（不放 config.py，因为涉及业务逻辑）：

```python
FIELD_SOURCES = {
    # ("scope_type", "field"): {
    #     "bundle_paths": [list of bundle JSON paths to scan, e.g. "synthesis.one_sentence", "stage_gates[]", "insight_blocks[dimension_hint=X]", "atomic_facts[linked_block_dim=Y]"],
    #     "claim_filter": {"dimension_hint": ["X", "Y"], "claim_type": ["thesis", ...]} | None,
    #     "archive_narrative_dim": "market_size" | None,  # 作为已有写作上下文
    # }
    ("industry", "thesis"): {
        "bundle_paths": ["synthesis.one_sentence"],
        "claim_filter": {"claim_type": ["thesis"]},
        "archive_narrative_dim": None,
    },
    ("industry", "demand"): {
        "bundle_paths": ["insight_blocks[dimension_hint=market_size|demand]", "atomic_facts[block_dim=market_size|demand]"],
        "claim_filter": {"dimension_hint": ["market_size", "demand"]},
        "archive_narrative_dim": "market_size",
    },
    ("industry", "supply_competition"): {
        "bundle_paths": ["insight_blocks[dimension_hint=competition|value_chain|lifecycle]"],
        "claim_filter": {"dimension_hint": ["competition", "value_chain", "lifecycle"]},
        "archive_narrative_dim": "competition",
    },
    # ... 完整 24 条 mapping（8 industry + 7 arena + 9 company），在实施时填入
    ("industry", "stage_gates"): {
        "bundle_paths": ["stage_gates[]"],
        "claim_filter": {"claim_type": ["gate_assessment"]},
        "archive_narrative_dim": None,
    },
    ("industry", "catalysts_timeline"): {
        "bundle_paths": ["insight_blocks[dimension_hint=drivers|catalysts]"],
        "claim_filter": {"dimension_hint": ["drivers", "catalysts"]},
        "archive_narrative_dim": "drivers",
    },
    ("industry", "risks_disconfirming_evidence"): {
        "bundle_paths": ["synthesis.cannot_conclude", "insight_blocks[dimension_hint=risks]"],
        "claim_filter": {"claim_type": ["risk"], "dimension_hint": ["risks"]},
        "archive_narrative_dim": "risks",
    },
    # company 9 维 / arena 7 维 类似...
    ("arena", "battlefield_definition"): {
        "bundle_paths": ["arena_candidates[slug=?].battleground_focus"],
        "claim_filter": None,
        "archive_narrative_dim": "definition",
    },
    ("company", "open_questions"): {
        "bundle_paths": ["synthesis.investment_questions"],
        "claim_filter": None,
        "archive_narrative_dim": None,
    },
    ("company", "thesis_fit"): {
        "bundle_paths": ["synthesis.one_sentence", "company_candidates[ticker=?].verification_questions"],
        "claim_filter": {"claim_type": ["thesis", "judgment"]},
        "archive_narrative_dim": "business_model",
    },
    # ... 其余字段参照规则
}
```

实施 Task 1 就是把这 24 条 mapping 全部精确填完，每条配 rationale 注释。

### 1.3 Fetcher 实现：`app/io/investment_lens.py`（新文件）

核心数据结构：

```python
@dataclass
class BundleExcerpt:
    source_id: str           # "行研-中银证券-2025-04-10-ad983472"
    publish_date: str        # "2025-04-10"
    source_type: str         # "industry_report"
    path_in_bundle: str      # "synthesis.one_sentence" 或 "insight_blocks[3]"
    text: str                # 原文摘录
    confidence: str | None   # bundle 来源的 confidence（如 insight_block.evidence_strength）
    bundle_sha8: str         # 跳回 /bundles/{sha8} 用

@dataclass
class ClaimCard:
    claim_id: str
    claim_text: str
    claim_type: str
    confidence: str
    status: str              # active / retired
    evidence_count: int      # 跨报告被引用次数
    as_of: str

@dataclass
class NarrativeExcerpt:
    scope_type: str
    scope_ref: str
    dimension: str           # archive dim
    path: str                # "industries/cn-nuclear-fusion/market-size.md"
    headline_count: int      # 文件里的 ### 段落数

@dataclass
class LensMaterial:
    scope_type: str
    scope_ref: str
    field: str               # lens field name
    bundle_excerpts: list[BundleExcerpt]
    claims: list[ClaimCard]
    narrative_excerpts: list[NarrativeExcerpt]
```

关键函数：

```python
def bundles_for_scope(scope_type: str, scope_ref: str, base: Path) -> list[dict]:
    """扫 data/bundle_registry.jsonl，按 touched[scope_type] 过滤返回 entry 列表，按 publish_date 倒序"""

def load_bundle(entry: dict, base: Path) -> dict:
    """读 entry['bundle_path'] 指向的 JSON"""

def fetch_lens_material(
    scope_type: str,
    scope_ref: str,
    field: str,
    *,
    registry: ClaimRegistry,
    base: Path,
) -> LensMaterial:
    """核心 fetcher：按 FIELD_SOURCES[(scope_type, field)] 从 bundle/claim/narrative 抓原料"""
```

内部细节：
- `bundle_paths` 用小型 dispatcher：`synthesis.X` 直接取；`stage_gates[]` 返回所有；`insight_blocks[dimension_hint=X|Y]` 过滤；`atomic_facts[block_dim=X]` 要 join insight_blocks
- `claim_filter` 调用 `registry.claims_for_scope(scope_type, scope_ref)` 后按 `dimension_hint`/`claim_type` 过滤
- `archive_narrative_dim` 用现有 `app.io.industries/arenas/companies` 的 `read_narrative` 读摘要

### 1.4 测试：`tests/test_investment_lens_fetcher.py`

- 构造 `tmp_path` 下的 mini fixture（1 bundle + 3 claims + 2 narrative 段落），覆盖 cn-nuclear-fusion industry 8 维每个都能抓到至少 1 个 source
- 覆盖边界：`bundles_for_scope` 返回空列表、`claim_filter` 不命中、archive narrative 不存在
- 验证 `LensMaterial` 结构序列化到 JSON 没有遗漏字段（为 Stage 3 的 proposal 准备）

### 1.5 CLI 调试入口（可选，复用于 Stage 2/3 联调）

`scripts/lens_inspect.py`:
```bash
.venv/bin/python -m scripts.lens_inspect \
    --scope industry --ref cn-nuclear-fusion
# 打印 8 个字段每个的 LensMaterial 摘要（counts + 首条样本）
```

---

## Stage 2 — A3 只读聚合页面

### 2.1 路由：`app/routes/investment_lens.py`（新文件）

```python
router = APIRouter(prefix="/lens", tags=["investment_lens"])

@router.get("/industry/{slug}")
def industry_lens(request: Request, slug: str):
    registry = ClaimRegistry(base=cfg.BASE_PATH / "data")
    fields = cfg.VIEW_DIMENSIONS["investment_lens"]["industry"]
    materials = {f: fetch_lens_material("industry", slug, f, registry=registry, base=cfg.BASE_PATH) for f in fields}
    return templates.TemplateResponse(
        request, "investment_lens/industry.html",
        {"slug": slug, "materials": materials, "fields": fields, "meta": industry_io.read_meta(slug)},
    )

# 类似 arena_lens / company_lens
```

### 2.2 模板（3 份）

- `app/templates/investment_lens/industry.html`（8 section）
- `app/templates/investment_lens/arena.html`（7 section）
- `app/templates/investment_lens/company.html`（9 section）

共用布局 pattern：

```html
<h1>投资决策视图 · {{ meta.name }}</h1>
<p><a href="/industries/{{ slug }}">← 返回 archive 视图</a></p>

{% for field in fields %}
<section class="lens-field">
  <h2>{{ FIELD_LABELS[field] }} <span class="hint">{{ field }}</span></h2>

  <h3>📘 研报综述 ({{ materials[field].bundle_excerpts|length }})</h3>
  <ul class="bundle-excerpts">
    {% for ex in materials[field].bundle_excerpts %}
    <li>
      <span class="badge">{{ ex.publish_date }}</span>
      <a href="/bundles/{{ ex.source_id }}">{{ ex.source_id }}</a>
      <blockquote>{{ ex.text }}</blockquote>
      <span class="hint">{{ ex.path_in_bundle }}</span>
    </li>
    {% endfor %}
  </ul>

  <h3>🗂 累积 claim ({{ materials[field].claims|length }})</h3>
  <table class="claims">
    {% for c in materials[field].claims %}
    <tr>
      <td><code>{{ c.claim_id }}</code></td>
      <td>{{ c.claim_text }}</td>
      <td><span class="badge badge-conf">{{ c.confidence }}</span></td>
      <td>{{ c.status }}</td>
    </tr>
    {% endfor %}
  </table>

  {% if materials[field].narrative_excerpts %}
  <h3>📝 已有 archive narrative</h3>
  {% for ne in materials[field].narrative_excerpts %}
  <a href="/industries/{{ slug }}#{{ ne.dimension }}">{{ ne.dimension }}（{{ ne.headline_count }} 段）</a>
  {% endfor %}
  {% endif %}
</section>
{% endfor %}
```

`FIELD_LABELS` 字典在模板顶部或 context 中传入，中文 label（如 `thesis` → "核心论点"、`demand` → "需求"）。

### 2.3 跨页链接

在三份 archive detail 模板顶部加按钮：
- `app/templates/industries/detail.html` line 4 附近（现有 nav 之后）：`<a href="/lens/industry/{{ slug }}" class="btn">投资决策视图 →</a>`
- `app/templates/arenas/detail.html` 同位置
- `app/templates/companies/detail.html` 同位置

lens 页面反向链回 archive（已在模板示例里）。

### 2.4 `app/main.py` 注册

在现有 router include 列表末尾加：
```python
from app.routes.investment_lens import router as investment_lens_router
app.include_router(investment_lens_router)
```

### 2.5 测试：`tests/test_investment_lens_routes.py`

- 对 cn-nuclear-fusion 三层各发一次 GET，断言 200 + context 里 materials 字段完整
- 断言 archive detail 页面包含 `/lens/.../` 链接
- 断言 bundle excerpts 链接指向正确的 `/bundles/{source_id}`

### 2.6 Stage 2 交付验证标准

人工打开 `/lens/industry/cn-nuclear-fusion`，检查：
- 8 个 section 每个都有原料（至少 bundle excerpt 或 claim 有一个）
- 点 bundle source_id 能跳到 `/bundles/{sha8}` 详情页
- 点 archive narrative 链接能跳回 archive detail
- FIELD_LABELS 中文标签语义对投资决策阅读顺畅

**如果某个 lens 字段映射原料总是空**，回 Stage 1 调 `FIELD_SOURCES` mapping。

---

## Stage 3 — B 综合写入层（Stage 2 验证后执行）

### 3.1 存储格式

`lens/{scope_type}/{slug}/{field}.md`，与 archive narrative 一致的嵌入式 frontmatter：

```markdown
# {field_label} · {scope_name}
*{slug} · lens 字段: {field}*

### {综合 body 的 headline}
source_bundles: [行研-中银证券-2025-04-10-ad983472]
supported_by_claims: [clm-industry-0001, clm-industry-0005]
status: active
last_written: 2026-05-02
proposal_id: lp-001

{200-400 字中文综合 body}
```

关键差异 vs archive：
- 路径根：`lens/` 而不是 `industries/` / `arenas/` / `companies/`
- 前置行叫 `lens 字段:` 而不是 `维度:`
- 多了 `source_bundles` 字段（lens 综合可能引用多份 bundle）

### 3.2 I/O 层：`app/io/lens_proposals.py`（新文件）

复刻 `app/io/narrative_proposals.py` 的 scope-aware 结构但独立文件（不扩展 `SCOPE_CONFIGS`，避免 narrative_proposals 被污染）：

```python
@dataclass(frozen=True)
class LensConfig:
    scope_type: str          # "industry" / "arena" / "company"
    lens_fields: tuple[str, ...]  # 8/7/9 字段
    top_dir: str             # 统一 "lens"

LENS_CONFIGS = {
    "industry": LensConfig("industry", cfg.INDUSTRY_INVESTMENT_VIEW_DIMS, "lens"),
    "arena": LensConfig("arena", cfg.ARENA_BATTLEFIELD_VIEW_DIMS, "lens"),
    "company": LensConfig("company", cfg.COMPANY_MEMO_VIEW_DIMS, "lens"),
}

def build_lens_proposal_file(
    scope_type: str, scope_ref: str,
    registry: ClaimRegistry, base: Path,
) -> dict:
    """对每个 lens 字段，fetch_lens_material → 生成 proposal skeleton（body=null）
       proposal 结构：{ proposal_id, scope_type, scope_ref, field, title,
                       material: LensMaterial 序列化, existing_body_excerpt,
                       body: null, decision: null, decision_reason: null, ... }
       写 data/pending/lens-proposals-{scope}-{slug}.json
    """

def validate_lens_proposal_decisions(data: dict) -> list[str]:
    """验证：decision ∈ {approve, edit, reject, defer}、approve/edit 要有 body 非空、
       supported_by_claims 都存在且 status='active'、source_bundles 都在 registry"""

def apply_lens_proposal_file(path: Path, *, base: Path) -> dict:
    """对 approve/edit proposal，append 到 lens/{scope}/{slug}/{field}.md，
       格式见 §3.1。审计事件写 data/audit/lens-events.jsonl。
       文件移到 data/pending/archive/"""

def scan_lens_flags(scope_type: str, scope_ref: str, *, registry: ClaimRegistry, base: Path) -> list[dict]:
    """扫 lens/{scope}/{slug}/*.md 的 supported_by_claims，对每个 claim 检查
       status / retired / refuting evidence，写 lens/{scope}/{slug}/lens-flags.jsonl"""
```

内部可以复用 `narrative_proposals.py` 的工具函数（`_render_markdown_block`、`append_audit_event`）——把它们提到 `app/io/_narrative_common.py`，`narrative_proposals.py` 和 `lens_proposals.py` 共同 import（小型 refactor）。

### 3.3 CLI wrappers（与 Phase 3 对称）

- `scripts/lens_propose.py`：`--scope {industry|arena|company} --ref <slug> [--base .] [--registry-base data]` → 写 pending proposal JSON
- `scripts/lens_apply.py`：`--proposals <path> [--base .]` → apply
- `scripts/lens_flags.py`：`--scope ... --ref ...` → scan flags

### 3.4 Claude 对话综合（工作流指令）

每份 pending proposal 交给 Claude（主 agent 或 sonnet 子 agent），prompt 给：
- 该 field 的 `LensMaterial`（bundle 原句 + claim 卡片 + narrative 段落）
- `existing_body_excerpt`（如果已有 lens .md）
- 指令："为本字段起草一段 300-500 字中文综合 body，要求：基于提供的原料，不引入外部知识；明确区分'已知'与'判断'；列明支撑的 claim_id/source_bundle"

Claude 输出填到 `proposal.body`。用户审批 / edit / reject / defer。

### 3.5 页面升级：lens 模板加 body 区

Stage 2 的模板新增顶部 body section：

```html
{% if materials[field].body_md %}
<section class="lens-body">
  <h3>💡 综合判断</h3>
  <div class="markdown">{{ materials[field].body_md | safe }}</div>
  <div class="hint">
    supported_by_claims: {{ materials[field].body_claims | join(", ") }} ·
    source_bundles: {{ materials[field].body_bundles | join(", ") }}
    {% if materials[field].flags %}<span class="badge badge-flag">needs review ({{ materials[field].flags|length }})</span>{% endif %}
  </div>
</section>
{% endif %}
```

`body_md` / `body_claims` / `body_bundles` / `flags` 由 fetcher 读 `lens/{scope}/{slug}/{field}.md` + `lens-flags.jsonl` 填入 `LensMaterial`（Stage 3 扩展 LensMaterial）。

### 3.6 工作流集成

在 `.claude/skills/ingest/workflows/_ingest-common.md` 的 Step 14 后加一步（可选）：

```
### Step 14.5 — lens_propose（可选，用户请求时触发）
对每个 touched (scope, ref)，如果 scope ∈ {industry, arena, company}：
  .venv/bin/python -m scripts.lens_propose --scope ... --ref ...
  → 生成 /tmp/lens-proposals-<scope>-<ref>.json
主 agent 或 sonnet 子 agent 按 §3.4 起草 body → 用户审批 → lens_apply
```

默认不跑，避免 ingest 每次都产生等审批的 lens proposal 堆积。

### 3.7 测试

- `tests/test_lens_proposals.py`：proposal 生成、validate、apply
- `tests/test_lens_flags.py`：lifecycle flag 扫描
- `tests/test_lens_apply_cli.py`：CLI 端到端
- 更新 Stage 2 的 route test，覆盖 `body_md` 展示路径

---

## 关键文件

| Stage | 文件 | 动作 |
|---|---|---|
| 1 | `app/config.py` | 加 `VIEW_DIMENSIONS` + 3 个 DIM 元组 |
| 1 | `app/io/investment_lens.py` | 新建，FIELD_SOURCES + fetcher |
| 1 | `tests/test_investment_lens_fetcher.py` | 新建 |
| 1 | `scripts/lens_inspect.py` | 新建（可选调试 CLI）|
| 2 | `app/routes/investment_lens.py` | 新建，3 个 GET |
| 2 | `app/templates/investment_lens/industry.html` | 新建 |
| 2 | `app/templates/investment_lens/arena.html` | 新建 |
| 2 | `app/templates/investment_lens/company.html` | 新建 |
| 2 | `app/templates/{industries,arenas,companies}/detail.html` | 加"决策视图"链接 |
| 2 | `app/main.py` | 注册 router |
| 2 | `tests/test_investment_lens_routes.py` | 新建 |
| 3 | `app/io/_narrative_common.py` | 新建，抽公用 markdown 工具 |
| 3 | `app/io/narrative_proposals.py` | 小改：import 公用工具 |
| 3 | `app/io/lens_proposals.py` | 新建 |
| 3 | `scripts/lens_propose.py` / `lens_apply.py` / `lens_flags.py` | 新建 |
| 3 | `app/templates/investment_lens/*.html` | 扩展：body section |
| 3 | `app/routes/investment_lens.py` | 扩展：读 lens .md + flags 塞 context |
| 3 | `.claude/skills/ingest/workflows/_ingest-common.md` | 加 Step 14.5 |
| 3 | `tests/test_lens_*.py` | 新建（3-4 份）|

---

## 验证

### Stage 1
```bash
.venv/bin/python -m pytest tests/test_investment_lens_fetcher.py -v
.venv/bin/python -m scripts.lens_inspect --scope industry --ref cn-nuclear-fusion
# 期望：8 字段每个都能打印出非空 material（至少一个源）
```

### Stage 2
```bash
.venv/bin/python -m uvicorn app.main:app --reload
# 访问 http://localhost:8000/lens/industry/cn-nuclear-fusion
# 检查：8 section / bundle excerpt 可跳 /bundles / claim 列表可读 / archive narrative 反向链接
.venv/bin/python -m pytest tests/test_investment_lens_routes.py -v
```

### Stage 3
```bash
# 完整流程
.venv/bin/python -m scripts.lens_propose --scope industry --ref cn-nuclear-fusion \
    --out /tmp/lens-industry-cn-nuclear-fusion.json
# → Claude 在对话里为 8 字段起草 body，用户审批
.venv/bin/python -m scripts.lens_apply --proposals /tmp/lens-industry-cn-nuclear-fusion.json
# → lens/industry/cn-nuclear-fusion/*.md 生成
.venv/bin/python -m scripts.lens_flags --scope industry --ref cn-nuclear-fusion
# 访问 /lens/industry/cn-nuclear-fusion 看综合 body 顶部显示，原料区保留在下方
```

---

## 非目标

- **不做 investment_lens → archive 反向同步**：lens body 是 archive 之外的独立投影，不回写 archive narrative
- **不做自动 LLM 生成（脚本调 LLM API）**：body 写作全部在 Claude 对话里完成（遵守 memory 规则）
- **不合并 archive 和 investment_lens 维度**：两层并列
- **不做 lens 字段的全局 `/lens` 列表页**：单个入口从 archive detail 页跳；列表页价值不高，可以后续补
- **不重构 Phase 3 narrative_proposals.py**：Stage 3 只抽小型公用工具，narrative_proposals 主逻辑不动
- **Stage 3 的范围问题**：默认三层（industry / arena / company）一起做；如果实施时发现 fetcher / proposal 差异大，可拆成 3A（industry）→ 3B（arena）→ 3C（company），对齐 Phase 3 节奏

---

## Open questions（实施时确认）

1. Stage 1 FIELD_SOURCES 24 条 mapping 的精确 dimension_hint 关键字映射——需要在写代码前逐字段过一次，可能要和用户对一遍语义边界（如 `lifecycle` 算 `demand` 还是 `supply_competition`）
2. Stage 2 的 FIELD_LABELS 中文翻译——给 lens 字段中文标题（"核心论点" / "需求" / ...）需要统一术语表
3. Stage 3 proposal body 长度上限——Phase 3 是 150-300 字，lens 综合信息更多可能要 300-500 字，最终数字需在跑一次对话综合后确认
4. Stage 3 是否按 Phase 3A/B/C 节奏拆成 3 子阶段——默认一把梭，但如果 fetcher 跑起来 scope 差异大可以再拆
