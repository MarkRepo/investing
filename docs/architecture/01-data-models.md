# 数据模型

## 1. ClaimRegistry

Claim 是系统的最小知识单元——一条可追溯的研究断言。所有 Claim 通过 `ClaimRegistry` 类管理，存储在项目根目录 `claims/` 下的 4 个 JSONL 文件中。

### 1.1 Claim 数据结构

```typescript
interface Claim {
  // === 身份标识 ===
  claim_id: string;          // "clm-arena-0001" | "clm-industry-0007" | "clm-company-0001" | "clm-cross_cutting-0001"
  scope_type: string;         // "industry" | "arena" | "company" | "cross_cutting"
  scope_ref: string;          // 对应 slug，如 "cn-pet-food" | "cn-pet-industry" | "SSE_603011"

  // === 内容 ===
  claim_text: string;         // 断言原文
  claim_type: string;         // "thesis" | "judgment" | "risk" | "scenario" | "gate_assessment"
  dimension_hint: string;     // 维度提示，如 "competition" | "drivers" | "technology"
  confidence: string;         // "high" | "medium_high" | "medium" | "medium_low" | "low"
  as_of: string;              // 断言的基准日期，如 "2025-06-01"

  // === 状态 ===
  status: string;             // "active" | "retired"
  review_by: string | null;   // 可选的审阅者
  user_override: any | null;  // 用户覆盖状态

  // === 证据链 ===
  supporting_evidence: EvidenceEntry[];

  // === 关系 ===
  related_claims: string[];   // 关联的 claim_id 列表

  // === 生命周期 ===
  state_log: StateLogEntry[]; // 状态变更审计
  created_at: string;         // ISO 时间
  last_updated: string;       // ISO 时间

  schema_version: string;     // "phase2-v1"
}

interface EvidenceEntry {
  source_id: string;      // 来源 ID，如 "行研-毕马威-2025-06-d385a3c7"
  block_ids: string[];    // Bundle 中的 insight_block ID
  fact_ids: string[];     // Bundle 中的 atomic_fact ID
  direction: string;      // "supports" | "refutes" | "neutral"
  weight: number;         // 证据权重，默认 1.0
  added_at: string;       // ISO 时间
  added_by: string;       // "ingest"
}

interface StateLogEntry {
  timestamp: string;
  from_status: string | null;
  to_status: string;
  trigger: string;        // "created" | "split" | ...
  trigger_ref: string;    // 引用源，如 "match-{source_id}.json#{candidate_id}"
}
```

### 1.2 存储文件

| 文件 | 存储内容 |
|---|---|
| `claims/industries.jsonl` | scope_type = "industry" 的 claims |
| `claims/arenas.jsonl` | scope_type = "arena" 的 claims |
| `claims/companies.jsonl` | scope_type = "company" 的 claims |
| `claims/cross_cutting.jsonl` | scope_type = "cross_cutting" 的 claims |
| `claims/.counters.json` | 各 scope_type 的 ID 计数器：`{"arena": 19, "industry": 14, ...}` |

### 1.3 ClaimRegistry 核心 API

```python
class ClaimRegistry:
    def __init__(self, base: Path)       # 加载所有 JSONL 到内存索引
    def find_by_id(claim_id) -> dict     # O(1) 查找
    def claims_for_scope(scope_type, scope_ref) -> list  # 某 scope 下的 claims
    def all_claims_for_scope_type(scope_type) -> list    # 某类型全部 claims
    def list_claims(scope_type?, scope_ref?) -> list     # 灵活查询

    def create_claim(...) -> dict         # 创建并持久化
    def append_evidence(claim_id, evidence, now) -> dict  # 追加证据
    def split_claim(claim_id, new_claim_specs, now) -> list  # 拆分为多个新 claim

    def append_audit_event(event: dict)   # 追加审计事件到 audit/claim-events.jsonl
    def check_integrity() -> list[str]    # 完整性检查（重复 ID、计数器一致性）
```

### 1.4 文件写入

`ClaimRegistry` 使用 **atomic write** 模式：先写入临时文件，再 `tmp.replace(path)` 原子替换。JSONL 文件按 `sort_keys=True` 序列化保证可重复性。

## 2. Bundle（数据捆绑）

Bundle 是 ingest 流水线的容器，承载一份源报告（PDF）的提取结果。

### 2.1 Bundle 数据结构

```typescript
interface Bundle {
  source_digest: {
    source_id: string;      // 唯一来源标识："行研-机构-YYYY-MM-sha8"
    source_type: string;    // "industry_report" | "annual_report" | "quarterly_report" | "sell_side_note"
    institution: string;
    source_date: string;
  };

  claim_candidates: ClaimCandidate[];   // 待审核的 claim 候选
  industry_candidates: ClaimCandidate[]; // 行业层候选
  arena_candidates: ClaimCandidate[];    // 竞技场层候选
  company_candidates: ClaimCandidate[];  // 公司层候选
  insight_blocks: InsightBlock[];        // 主题信息块
  atomic_facts: AtomicFact[];            // 原子事实
}

interface ClaimCandidate {
  candidate_id: string;        // "cc-001"（自动生成）
  claim_text: string;          // 候选断言
  scope_type: string;          // 目标 scope
  scope_ref: string;           // 目标 slug
  claim_type: string;
  dimension_hint: string;
  confidence: string;
  as_of: string;
  direction_on_source: string; // "strengthens" | "weakens" | "neutral"
  supporting_block_ids: string[];
}

interface InsightBlock {
  id: string;               // "ib-001"
  title: string;
  summary: string;
  contained_facts: string[];
  archive_routing_hints: {
    scope_type_hint: string;
    dimension_hint: string;
  };
}

interface AtomicFact {
  fact_id: string;          // "fact-001"
  text: string;
  page_ref: string;
  linked_block_id: string;
}
```

### 2.2 Bundle 注册表

`data/bundle_registry.jsonl` 每条记录：

```typescript
interface BundleRegistryEntry {
  source_id: string;
  sha8: string;                      // 源文件 SHA-256 前 8 位
  source_type: string;
  institution: string;
  publish_date: string;
  bundle_path: string;               // bundle JSON 文件路径
  source_file_path: string;          // 原始 PDF 路径
  ingested_at: string;               // ISO 时间
  touched: {
    industries: string[];            // 影响的行业
    arenas: string[];                // 影响的竞技场
    companies: string[];             // 影响的公司
  };
}
```

## 3. Narrative（叙事档案）

叙事是组织在行业 / 竞技场 / 公司维度下的 Markdown 档案文件。

### 3.1 维度体系

| 层级       | 维度数量 | 维度列表                                                                                                                       |
| -------- | ---- | -------------------------------------------------------------------------------------------------------------------------- |
| Industry | 11   | definition, market_size, lifecycle, value_chain, competition, drivers, technology, regulation, benchmark, risks, valuation |
| Arena    | 6    | definition, participants, decisive_factors, trajectory, narratives, investment_view                                        |
| Company  | 8    | business_model, moat, growth_engine, management, financial_profile, catalysts, risks, valuation                            |

### 3.2 文件路径规则

```
# Industry: industries/{slug}/{dimension-kebab-case}.md
industries/cn-pet-industry/drivers.md

# Arena: arenas/{slug}/{dimension-kebab-case}.md
arenas/cn-pet-food/decisive-factors.md

# Company: companies/{MARKET}_{TICKER}/narratives/{dimension-kebab-case}.md
companies/SSE_603011/narratives/moat.md
```

### 3.3 Narrative 文件格式

```markdown
# 增长驱动与催化 · 宠物行业

*slug: cn-pet-industry · 维度: drivers*
### 双端驱动：老龄化与年轻主力共撑宠物消费长坡

status: active
last_written: 2026-05-02
supported_by_claims: [clm-industry-0008, clm-industry-0012]
source_ids: [行研-毕马威-2025-06-d385a3c7]
proposal_id: np-001

段落正文，支持 Markdown 表格、列表等。
```

- 文件顶部是 H1 标题（维度中文名 + 层级名）
- 第二行是斜体 slug + 维度标识
- `###` 开头的三级标题是叙事段落的标题
- 紧随其后的 YAML-like 元数据块：status, last_written, supported_by_claims, source_ids, proposal_id
- 之后是自由格式的正文

一个维度文件可以包含多个 `###` 段落，每个段落有自己独立的元数据。

## 4. Industry / Arena / Company 元数据

### 4.1 Industry meta.yaml

```yaml
slug: cn-pet-industry
name: 宠物行业
scope: 中国宠物消费市场全景
linked_arenas:
  - cn-pet-food
  - cn-pet-medical
linked_tickers:
  - { ticker: "301016", market: "SZSE", name: "乖宝宠物" }
```

### 4.2 Arena definition.md

```markdown
---
slug: cn-pet-food
name: 中国宠物食品市场
industry: cn-pet-industry
participants:
  - { market: SZSE, ticker: "301016", name: 乖宝宠物 }
  - { market: SSE, ticker: "603011", name: 中宠股份 }
---

Arena 定义正文...
```

Arena 使用 frontmatter + body 格式，通过 `---` 分隔。

### 4.3 Company meta.md

```yaml
---
ticker: 603011
market: SSE
name: 中宠股份
industry_slugs: [cn-pet-industry]
currency: CNY
listed_date: 2017-01-01
website: https://...
---
```

## 5. Portfolio / Watchlist / Journal

### 5.1 持仓表 `portfolio/positions.md`

GitHub Flavored Markdown 表格：

```markdown
| date_added | ticker | market | shares | avg_cost | ... |
|---|---|---|---|---|---|
| 2025-04-15 | 301016 | SZSE | 1000 | 25.50 | ... |
```

### 5.2 规则文件 `portfolio/rules.md`

```yaml
---
max_single_pct: 0.15       # 单票最大仓位
max_sector_pct: 0.40       # 单行业最大仓位
min_cash_pct: 0.10         # 最小现金仓位
max_theme_pct: 0.30        # 单主题最大仓位
---

规则正文（markdown 自由格式）...
```

### 5.3 价格触发器 `portfolio/triggers.md`

```markdown
| date_set | ticker | market | trigger_type | trigger_price | action |
|---|---|---|---|---|---|
| 2025-04-15 | 301016 | SZSE | stop_loss | 22.00 | sell |
```

### 5.4 观察池 `watchlist/researching.md` 等

```markdown
# 观察池 · 预筛段

> 阶段规则描述...

| date_added | ticker | source_type | source | notes |
|---|---|---|---|---|
| 2025-04-15 | 603011 | quant_screen | Momentum screen | ... |
```

### 5.5 决策日志 `journal/decisions/{YYYY}-Q{n}/`

每个决策是一个独立的 Markdown 文件，命名格式 `{date}-{TICKER}-{action}.md`：

```yaml
---
id: 2025-04-15-AAPL-buy
date: 2025-04-15
ticker: AAPL
market: US
action: buy
price: 175.50
position_change: 1.5
v0_snapshot_path: companies/US_AAPL/v0.md
v0_snapshot_hash: abc123
process_quality: 5
process_rigor: 4
process_rule_adherence: 5
process_emotional_control: 4
---

## 1. 决策内容
...
```

## 6. SQLite 数据库 `data/financials.db`

### 6.1 quotes_daily

日线行情数据，PK = (ticker, date)：

| 字段组 | 字段 |
|---|---|
| 标识 | ticker, date, market |
| 价格 | open, high, low, close |
| 成交量 | volume, amount, turnover_rate |
| 估值 | pe_ttm, pe_static, pe_forward, pb, ps, peg, dividend_yield |
| 市值 | market_cap, float_market_cap, shares_outstanding |
| 其他 | high_52w, low_52w, source, fetched_at |

### 6.2 financials_cn / financials_us

财务报表数据，PK = (ticker, period, period_type)：

| 字段组 | 示例字段 |
|---|---|
| 利润表 | total_revenue, net_income, eps_basic, eps_diluted |
| 资产负债表 | total_assets, total_liabilities, cash_and_equivalents, net_ppe |
| 现金流量表 | operating_cashflow, capex, investing_cashflow |

## 7. 审计日志

### 7.1 Claim 事件 `audit/claim-events.jsonl`

```typescript
interface ClaimEvent {
  candidate_id: string;
  claim_id: string;
  event_type: "claim_created" | "evidence_attached" | "candidate_skipped" | "claim_split";
  source_id: string;
  // split 事件额外字段:
  retired_claim_id?: string;
  new_claim_ids?: string[];
}
```

### 7.2 Narrative 事件 `data/audit/narrative-events.jsonl`

```typescript
interface NarrativeEvent {
  event_type: "narrative_applied" | "narrative_rejected" | "narrative_deferred";
  source_id: string;
  proposal_id: string;
  scope_type: string;
  scope_ref: string;
  dimension: string;
  decision_reason: string;
  created_at: string;
}
```

## 8. 受控词汇

`controlled-vocab/` 目录定义系统级别的词汇约束，当前包含：

- `subjects.yaml`：claim_type 的合法取值及描述
- 其他白名单文件

Claim 创建时 `claim_type` 必须在此白名单内。
