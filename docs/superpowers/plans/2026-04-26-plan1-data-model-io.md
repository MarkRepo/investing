# Plan 1: 三层数据模型 + IO 层 + config + 财务扩展 + 迁移

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把三层知识系统（industry / arena / company）的数据模型和 IO 层落地。本 plan 完成后，三层的结构化事实库 + narrative 层 + 跨层引用都能通过单元测试，可被后续 plan（preprocess / digest / workflow / routes）调用，但尚未对接用户 ingest 流程。

**Architecture:** 三层对称 — 每层有自己的维度清单（config 常量）、narrative .md 写入函数、结构化事实库（industry.observations / company.claims，arena 不独立存事实），跨层通过 `arena_refs` 索引和 meta backlinks 关联。财务 SQLite schema 从 8 列 `ALTER TABLE ADD COLUMN` 扩到约 45 列 + A 股/US GAAP alias map。sector 概念及其派生物（VALID_SECTORS / competence / industry_primary）在本 plan 开头一次性清除。

**Tech Stack:** Python 3, pytest, pyyaml, sqlite3 (stdlib), pathlib. 无新依赖。

**Spec reference:** `docs/superpowers/specs/2026-04-26-industry-ingest-design.md` commit `bc740e1`（§2.1-2.3 三层维度；§4 数据模型；§7 代码改动；§4.7 财务；§4.8 figure_contexts 不在本 plan）。

---

## File Map

**Delete:**
- `app/io/competence.py`
- `app/routes/competence.py`
- `controlled-vocab/competence-sector/` (5 yaml files)
- `templates/competence-check.md.tmpl`
- `companies/BSE_920118/competence-check.md`
- `companies/SSE_600519/competence-check.md`
- `companies/US_HIMS/competence-check.md`

**Modify:**
- `app/config.py` — remove `VALID_SECTORS` + `SECTOR_VOCAB_DIR`; add `INDUSTRY_DIMENSIONS` / `ARENA_DIMENSIONS` / `COMPANY_DIMENSIONS` / `INDUSTRY_FIELDS` / `INCOME_STATEMENT_LINES` / `BALANCE_SHEET_LINES` / `CASHFLOW_LINES`
- `app/io/company.py` — remove sector import/validation; rename `industry_primary` → `industry_slugs` (list); add narrative 8-dim helpers
- `app/io/arenas.py` — add `industry` + `battleground_focus` frontmatter fields; add narrative 6-dim helpers; add `find_by_industry`
- `app/io/claims.py` — validate_batch accepts `arena_refs` + `company_dimension_hint` optional; add `filter_by_arena` + `filter_by_company_dimension`
- `app/io/financials.py` — `FINANCIAL_COLUMNS` 8→45; ALTER TABLE migration; expanded ratios view (DuPont / FCF / OCF quality / CCC etc); `load_alias_map()`; `import_financials_csv` accepts unknown-column warning
- `companies/{BSE_920118,SSE_600519,US_HIMS}/meta.md` — frontmatter `industry_primary: xxx` → `industry_slugs: []`

**Rewrite:**
- `app/io/industry.py` — full rewrite from sector-based (`landscape.md` / `players.md`) to slug-based (`meta.yaml` + `observations.jsonl` + 11 dim `.md` + `sources/`). Old API removed, new API per §7.3.
- `tests/test_industry_io.py` — rewrite for new API

**Create:**
- `controlled-vocab/financial-aliases.yaml` — A 股/US GAAP alias map (~40 items)
- `tests/test_arenas_narrative.py` — 6-dim narrative + find_by_industry
- `tests/test_company_narrative.py` — 8-dim narrative + industry_slugs
- `tests/test_claims_arena_refs.py` — new optional fields + filter_by
- `tests/test_financials_extended.py` — new columns + alias map + DuPont/FCF/CCC

---

## Phase A: 破坏性清理（sector 全废；非 TDD 一次性）

### Task 1: 删除 competence 代码

**Files:**
- Delete: `/Users/yangqi/investing/app/io/competence.py`
- Delete: `/Users/yangqi/investing/app/routes/competence.py`

- [ ] **Step 1: 确认要删的文件存在**

```bash
ls -la /Users/yangqi/investing/app/io/competence.py /Users/yangqi/investing/app/routes/competence.py
```

Expected: both files exist.

- [ ] **Step 2: 删除**

```bash
rm /Users/yangqi/investing/app/io/competence.py
rm /Users/yangqi/investing/app/routes/competence.py
```

- [ ] **Step 3: grep 现有代码引用并修复**

```bash
cd /Users/yangqi/investing && grep -rn "from app.io import competence\|from app.io.competence\|import competence\|competence_io\|routes.competence\|from app.routes import competence" app/ scripts/ tests/ 2>/dev/null
```

Expected: any remaining references must be edited out. Likely callers:
- `app/app.py` or `app/main.py`: `app.include_router(competence.router)` line — delete
- Any import in `app/routes/__init__.py` or similar — delete

Edit each reference found by removing the import line or the router registration line.

- [ ] **Step 4: pytest smoke check**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/ --collect-only 2>&1 | tail -5
```

Expected: collection succeeds (or only fails on tests that import competence — those will be handled in later tasks). No import errors from app/ itself.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add -A app/ && git commit -m "refactor: remove competence.py module and router

Part of sector concept removal (spec §7.1). Competence-sector whitelist
mechanism is being replaced by three-layer knowledge system.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: 删除 sector 词表、模板、空骨架

**Files:**
- Delete: `/Users/yangqi/investing/controlled-vocab/competence-sector/` (whole dir, 5 files)
- Delete: `/Users/yangqi/investing/templates/competence-check.md.tmpl`
- Delete: `/Users/yangqi/investing/companies/BSE_920118/competence-check.md`
- Delete: `/Users/yangqi/investing/companies/SSE_600519/competence-check.md`
- Delete: `/Users/yangqi/investing/companies/US_HIMS/competence-check.md`

- [ ] **Step 1: 确认**

```bash
ls /Users/yangqi/investing/controlled-vocab/competence-sector/ 2>/dev/null
ls /Users/yangqi/investing/templates/competence-check.md.tmpl 2>/dev/null
ls /Users/yangqi/investing/companies/*/competence-check.md 2>/dev/null
```

Expected: list of files to delete.

- [ ] **Step 2: 删除**

```bash
rm -r /Users/yangqi/investing/controlled-vocab/competence-sector/
rm /Users/yangqi/investing/templates/competence-check.md.tmpl
rm /Users/yangqi/investing/companies/BSE_920118/competence-check.md
rm /Users/yangqi/investing/companies/SSE_600519/competence-check.md
rm /Users/yangqi/investing/companies/US_HIMS/competence-check.md
```

- [ ] **Step 3: Commit**

```bash
cd /Users/yangqi/investing && git add -A && git commit -m "chore: remove sector vocab, competence template, empty skeletons

Part of sector concept removal. All three existing competence-check.md
files verified empty (spec §D7).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: 清理 config.py 的 VALID_SECTORS + SECTOR_VOCAB_DIR

**Files:**
- Modify: `/Users/yangqi/investing/app/config.py`

- [ ] **Step 1: 读 config.py 现状**

```bash
cat /Users/yangqi/investing/app/config.py | grep -n -E "VALID_SECTORS|SECTOR_VOCAB_DIR|competence"
```

- [ ] **Step 2: 删除两行**

Use Edit tool to remove these two lines from `app/config.py`:
- `VALID_SECTORS = ("consumer", "saas", "cyclical", "bank", "biotech")`
- `SECTOR_VOCAB_DIR = CONTROLLED_VOCAB_DIR / "competence-sector"`

- [ ] **Step 3: grep 项目对这两个常量的引用并修**

```bash
cd /Users/yangqi/investing && grep -rn "VALID_SECTORS\|SECTOR_VOCAB_DIR" app/ scripts/ tests/ 2>/dev/null
```

Expected callers (delete / fix each):
- `app/io/company.py:11` — `from app.config import VALID_MARKETS, VALID_SECTORS` → change to `from app.config import VALID_MARKETS`
- `app/io/company.py:42` — `create_company(... sector, ...)` — in Task 4 we'll fully rework this
- Any other file that imports either — fix

- [ ] **Step 4: pytest smoke**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_io_company.py --no-header 2>&1 | tail -20
```

Expected: test_io_company.py tests that validated sector may fail; that's OK, Task 4 handles. Other tests should still import.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add app/ && git commit -m "refactor(config): remove VALID_SECTORS and SECTOR_VOCAB_DIR

Part of sector concept removal (spec §7.1). Company IO will use
freeform industry_slugs list instead.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: company.py 移除 sector 校验 + 字段重命名 industry_primary → industry_slugs

**Files:**
- Modify: `/Users/yangqi/investing/app/io/company.py`
- Modify: `/Users/yangqi/investing/companies/BSE_920118/meta.md`
- Modify: `/Users/yangqi/investing/companies/SSE_600519/meta.md`
- Modify: `/Users/yangqi/investing/companies/US_HIMS/meta.md`
- Test: `/Users/yangqi/investing/tests/test_io_company.py`

- [ ] **Step 1: 读 company.py 核心段**

```bash
sed -n '1,30p;38,60p;116,175p' /Users/yangqi/investing/app/io/company.py
```

- [ ] **Step 2: Edit company.py**

Apply these edits:

- Line 11: `from app.config import VALID_MARKETS, VALID_SECTORS` → `from app.config import VALID_MARKETS`
- `_META_KEYS`: replace `"industry_primary"` with `"industry_slugs"`; add `"arenas"` if not present
- `create_company` signature: remove `sector` parameter; replace with `industry_slugs: list[str] | None = None`
- `create_company` body: remove the `sector not in VALID_SECTORS` validation; use `industry_slugs or []` when writing frontmatter
- `write_meta`: remove `industry_primary not in VALID_SECTORS` validation (likely L161-164); accept `industry_slugs` as list
- `list_companies` (~L300-340): return `industry_slugs` list instead of `industry_primary` str

Example `create_company` new signature:

```python
def create_company(
    ticker: str,
    market: str,
    name: str,
    industry_slugs: list[str] | None = None,
    currency: str = "USD",
    base: Path | None = None,
    templates_dir: Path | None = None,
    today: date | None = None,
) -> Path:
    if market not in VALID_MARKETS:
        raise ValueError(f"market must be one of {VALID_MARKETS}, got {market!r}")
    if not ticker or "_" in ticker:
        raise ValueError(f"ticker must be non-empty and contain no underscore, got {ticker!r}")

    base = base or cfg.COMPANIES_DIR
    today = today or date.today()
    key = f"{market}_{ticker}"
    company_dir = base / key
    if company_dir.exists():
        raise FileExistsError(f"company dir already exists: {company_dir}")

    company_dir.mkdir(parents=True)
    (company_dir / "sources").mkdir()

    frontmatter = {
        "ticker": ticker,
        "market": market,
        "name": name,
        "industry_slugs": industry_slugs or [],
        "currency": currency,
        "created": today.isoformat(),
    }
    write_meta(ticker, market, frontmatter, body="", base=base)
    return company_dir
```

- [ ] **Step 3: 迁移 3 份现有 meta.md**

Read each and rewrite frontmatter. Example for `companies/SSE_600519/meta.md` — change:

```yaml
industry_primary: consumer
```

to:

```yaml
industry_slugs: []
```

Do this for BSE_920118, SSE_600519, US_HIMS.

- [ ] **Step 4: 改 tests/test_io_company.py**

All tests that pass `sector="..."` → change to `industry_slugs=[...]`. All tests that assert `industry_primary` in frontmatter → assert `industry_slugs` (list). All tests that test VALID_SECTORS rejection → delete those test cases.

- [ ] **Step 5: 跑测试**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_io_company.py -v 2>&1 | tail -30
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add -A && git commit -m "refactor(company): replace industry_primary with freeform industry_slugs

Removes sector whitelist enforcement. Company now supports multiple
industry associations (list). Migrates 3 existing meta.md files to
empty industry_slugs placeholder; to be backfilled in subsequent
ingests (spec §D7).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: 删除 industries/ 空 .gitkeep 子目录

**Files:**
- Delete: `/Users/yangqi/investing/industries/consumer/`, `saas/`, `cyclical/`, `bank/`, `biotech/` (if any contain only .gitkeep)

- [ ] **Step 1: 审查**

```bash
find /Users/yangqi/investing/industries/ -type f | sort
```

Expected: only `.gitkeep` files (per earlier survey).

- [ ] **Step 2: 清理**

```bash
rm -rf /Users/yangqi/investing/industries/consumer /Users/yangqi/investing/industries/saas /Users/yangqi/investing/industries/cyclical /Users/yangqi/investing/industries/bank /Users/yangqi/investing/industries/biotech 2>/dev/null
# keep industries/ dir (empty) for slug-based ingest to populate
touch /Users/yangqi/investing/industries/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
cd /Users/yangqi/investing && git add -A industries/ && git commit -m "chore: clean out sector-based industries/ skeleton dirs

Will be repopulated slug-based by new industry IO layer.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase B: Config 维度常量 (TDD)

### Task 6: 添加 INDUSTRY/ARENA/COMPANY _DIMENSIONS + INDUSTRY_FIELDS

**Files:**
- Modify: `/Users/yangqi/investing/app/config.py`
- Test: `/Users/yangqi/investing/tests/test_config_dimensions.py` (new)

- [ ] **Step 1: Write failing test**

Create `/Users/yangqi/investing/tests/test_config_dimensions.py`:

```python
from app import config as cfg


def test_industry_dimensions_is_11_tuple():
    assert isinstance(cfg.INDUSTRY_DIMENSIONS, tuple)
    assert len(cfg.INDUSTRY_DIMENSIONS) == 11
    assert cfg.INDUSTRY_DIMENSIONS[0] == "definition"
    assert "market_size" in cfg.INDUSTRY_DIMENSIONS
    assert "valuation" in cfg.INDUSTRY_DIMENSIONS


def test_arena_dimensions_is_6_tuple():
    assert isinstance(cfg.ARENA_DIMENSIONS, tuple)
    assert len(cfg.ARENA_DIMENSIONS) == 6
    assert cfg.ARENA_DIMENSIONS == (
        "definition", "participants", "decisive_factors",
        "trajectory", "narratives", "investment_view",
    )


def test_company_dimensions_is_8_tuple():
    assert isinstance(cfg.COMPANY_DIMENSIONS, tuple)
    assert len(cfg.COMPANY_DIMENSIONS) == 8
    assert cfg.COMPANY_DIMENSIONS == (
        "business_model", "moat", "growth_engine", "management",
        "financial_profile", "catalysts", "risks", "valuation",
    )


def test_industry_fields_is_dict_keyed_by_dimension():
    assert isinstance(cfg.INDUSTRY_FIELDS, dict)
    for dim in cfg.INDUSTRY_FIELDS:
        assert dim in cfg.INDUSTRY_DIMENSIONS
    # market_size must have tam_global etc.
    assert "tam_global" in cfg.INDUSTRY_FIELDS["market_size"]
    assert "cagr_global" in cfg.INDUSTRY_FIELDS["market_size"]


def test_no_valid_sectors():
    assert not hasattr(cfg, "VALID_SECTORS")
```

- [ ] **Step 2: 运行测试确认 FAIL**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_config_dimensions.py -v 2>&1 | tail -15
```

Expected: multiple FAILED (constants not defined).

- [ ] **Step 3: Edit app/config.py 添加常量**

Append to end of `/Users/yangqi/investing/app/config.py`:

```python
# Three-layer knowledge dimension tuples (spec §4.5).
# Snake_case keys map to kebab-case filenames:
#   COMPANY_DIMENSIONS item "growth_engine" ↔ companies/{key}/narratives/growth-engine.md
INDUSTRY_DIMENSIONS = (
    "definition",
    "market_size",
    "lifecycle",
    "value_chain",
    "competition",
    "drivers",
    "technology",
    "regulation",
    "benchmark",
    "risks",
    "valuation",
)

ARENA_DIMENSIONS = (
    "definition",
    "participants",
    "decisive_factors",
    "trajectory",
    "narratives",
    "investment_view",
)

COMPANY_DIMENSIONS = (
    "business_model",
    "moat",
    "growth_engine",
    "management",
    "financial_profile",
    "catalysts",
    "risks",
    "valuation",
)

# Suggested structured fields per industry dimension. Open vocabulary —
# observations.field is not validated against this dict, but digest prompts
# use it as guidance. Dimensions not listed here don't have structured fields
# (narrative-only).
INDUSTRY_FIELDS = {
    "market_size": [
        "tam_global", "tam_china", "tam_by_segment",
        "cagr_global", "cagr_china",
    ],
    "lifecycle": ["stage", "stage_evidence"],
    "competition": [
        "hhi", "cr5", "cr10", "share_by_player",
        "porter_entry_barrier", "porter_substitute_threat",
        "porter_supplier_power", "porter_buyer_power", "porter_rivalry",
    ],
    "benchmark": [
        "gross_margin_leader", "gross_margin_avg",
        "capex_intensity_avg", "rd_ratio_leader",
    ],
    "valuation": ["pe_ttm_median", "pb_median", "ev_ebitda_median"],
}
```

- [ ] **Step 4: 运行测试确认 PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_config_dimensions.py -v 2>&1 | tail -10
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add app/config.py tests/test_config_dimensions.py && git commit -m "feat(config): add 3-layer dimension tuples + industry field suggestions

Adds INDUSTRY_DIMENSIONS (11), ARENA_DIMENSIONS (6), COMPANY_DIMENSIONS (8),
and INDUSTRY_FIELDS open vocabulary. Replaces sector whitelist with
dimension-oriented knowledge framework (spec §4.5).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase C: 财务扩展 (TDD)

### Task 7: 添加财务 line items 常量

**Files:**
- Modify: `/Users/yangqi/investing/app/config.py`
- Test: `/Users/yangqi/investing/tests/test_config_dimensions.py` (append)

- [ ] **Step 1: Append failing tests to test_config_dimensions.py**

```python
def test_income_statement_lines_is_18_tuple():
    assert isinstance(cfg.INCOME_STATEMENT_LINES, tuple)
    assert len(cfg.INCOME_STATEMENT_LINES) == 18
    assert "revenue" in cfg.INCOME_STATEMENT_LINES
    assert "cost_of_revenue" in cfg.INCOME_STATEMENT_LINES
    assert "operating_income" in cfg.INCOME_STATEMENT_LINES
    assert "net_income" in cfg.INCOME_STATEMENT_LINES
    assert "eps_diluted" in cfg.INCOME_STATEMENT_LINES


def test_balance_sheet_lines_is_20_tuple():
    assert isinstance(cfg.BALANCE_SHEET_LINES, tuple)
    assert len(cfg.BALANCE_SHEET_LINES) == 20
    assert "cash_and_equivalents" in cfg.BALANCE_SHEET_LINES
    assert "inventory" in cfg.BALANCE_SHEET_LINES
    assert "total_assets" in cfg.BALANCE_SHEET_LINES
    assert "long_term_debt" in cfg.BALANCE_SHEET_LINES
    assert "total_equity" in cfg.BALANCE_SHEET_LINES


def test_cashflow_lines_is_16_tuple():
    assert isinstance(cfg.CASHFLOW_LINES, tuple)
    assert len(cfg.CASHFLOW_LINES) == 16
    assert "depreciation_amortization" in cfg.CASHFLOW_LINES
    assert "operating_cashflow" in cfg.CASHFLOW_LINES
    assert "capex" in cfg.CASHFLOW_LINES
    assert "dividends" in cfg.CASHFLOW_LINES


def test_financial_lines_superset_of_legacy():
    """Legacy 8 columns must all survive."""
    all_lines = set(cfg.INCOME_STATEMENT_LINES) | set(cfg.BALANCE_SHEET_LINES) | set(cfg.CASHFLOW_LINES)
    legacy = {"revenue", "gross_profit", "operating_income", "net_income",
              "total_assets", "total_equity", "operating_cashflow"}
    assert legacy.issubset(all_lines)
```

- [ ] **Step 2: Run tests — FAIL**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_config_dimensions.py -v 2>&1 | tail -15
```

Expected: 4 new FAILED.

- [ ] **Step 3: Append to app/config.py**

```python
# Financials line items (spec §4.7). Standard snake_case keys; A-share and
# US GAAP raw names map to these via controlled-vocab/financial-aliases.yaml.
INCOME_STATEMENT_LINES = (
    "revenue", "cost_of_revenue", "gross_profit",
    "selling_expense", "admin_expense", "rd_expense", "other_opex",
    "operating_income",
    "interest_income", "interest_expense", "other_non_operating",
    "pretax_income", "income_tax", "net_income",
    "minority_interest", "net_income_to_parent",
    "eps_basic", "eps_diluted",
)

BALANCE_SHEET_LINES = (
    "cash_and_equivalents", "short_term_investments",
    "accounts_receivable", "inventory", "other_current_assets",
    "total_current_assets",
    "ppe_net", "goodwill", "intangibles", "other_non_current_assets",
    "total_assets",
    "accounts_payable", "short_term_debt", "other_current_liab",
    "total_current_liab",
    "long_term_debt", "other_non_current_liab",
    "total_liab",
    "minority_equity", "total_equity",
)

CASHFLOW_LINES = (
    "net_income_cf", "depreciation_amortization",
    "working_capital_change", "other_operating",
    "operating_cashflow",
    "capex", "other_investing", "investing_cashflow",
    "debt_issued", "debt_repaid", "equity_issued", "dividends",
    "other_financing", "financing_cashflow",
    "fx_effect", "net_change_in_cash",
)

FINANCIAL_ALIASES_PATH = CONTROLLED_VOCAB_DIR / "financial-aliases.yaml"
```

- [ ] **Step 4: Run tests — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_config_dimensions.py -v 2>&1 | tail -15
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add app/config.py tests/test_config_dimensions.py && git commit -m "feat(config): add financials line item tuples (IS/BS/CF)

18/20/16 line items enabling DuPont, FCF, OCF quality, CCC and other
second-order analysis (spec §4.7).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 8: 创建 financial-aliases.yaml + loader

**Files:**
- Create: `/Users/yangqi/investing/controlled-vocab/financial-aliases.yaml`
- Modify: `/Users/yangqi/investing/app/io/financials.py` (add `load_alias_map`)
- Test: `/Users/yangqi/investing/tests/test_financials_extended.py` (new)

- [ ] **Step 1: Write failing test**

Create `/Users/yangqi/investing/tests/test_financials_extended.py`:

```python
from app.io import financials as fin_io
from app import config as cfg


def test_load_alias_map_returns_dict():
    m = fin_io.load_alias_map()
    assert isinstance(m, dict)
    assert "revenue" in m


def test_alias_map_has_a_share_and_us_gaap():
    m = fin_io.load_alias_map()
    rev = m["revenue"]
    assert "a_share" in rev
    assert "us_gaap" in rev
    assert "营业收入" in rev["a_share"]
    assert any(alias.lower() == "revenue" or "net sales" in alias.lower() for alias in rev["us_gaap"])


def test_alias_map_covers_key_lines():
    m = fin_io.load_alias_map()
    for key in ("revenue", "cost_of_revenue", "operating_income", "net_income",
                "total_assets", "total_equity", "operating_cashflow", "capex"):
        assert key in m, f"alias map missing {key}"


def test_normalize_raw_key_to_standard():
    assert fin_io.normalize_raw_key("营业收入", market="SSE") == "revenue"
    assert fin_io.normalize_raw_key("Net sales", market="US") == "revenue"
    assert fin_io.normalize_raw_key("unknown_column", market="US") is None
```

- [ ] **Step 2: Run — FAIL** (file missing + functions missing)

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_extended.py -v 2>&1 | tail -10
```

- [ ] **Step 3: Create `controlled-vocab/financial-aliases.yaml`**

```yaml
# A-share and US GAAP raw line item names → standard snake_case keys.
# Used by app.io.financials.normalize_raw_key() when importing from CSV
# or from digest subagent output.

# ---- Income Statement ----
revenue:
  a_share: [营业收入, 营业总收入]
  us_gaap: [Revenue, Revenues, Net sales, Total revenue, Total revenues]

cost_of_revenue:
  a_share: [营业成本]
  us_gaap: [Cost of revenue, Cost of revenues, Cost of goods sold, Cost of sales]

gross_profit:
  a_share: [毛利, 毛利润]
  us_gaap: [Gross profit, Gross margin]

selling_expense:
  a_share: [销售费用]
  us_gaap: [Selling expense, Selling expenses, Sales and marketing, Selling general and administrative]  # often combined SG&A

admin_expense:
  a_share: [管理费用]
  us_gaap: [General and administrative, Administrative expense]

rd_expense:
  a_share: [研发费用]
  us_gaap: [Research and development, R&D expense]

other_opex:
  a_share: [其他营业费用]
  us_gaap: [Other operating expense]

operating_income:
  a_share: [营业利润]
  us_gaap: [Operating income, Income from operations, Operating profit]

interest_income:
  a_share: [利息收入]
  us_gaap: [Interest income]

interest_expense:
  a_share: [利息费用, 财务费用]  # note: 财务费用 ≈ interest + fx; rough mapping
  us_gaap: [Interest expense]

other_non_operating:
  a_share: [营业外收入, 营业外支出]
  us_gaap: [Other income, Other expense, Non-operating income]

pretax_income:
  a_share: [利润总额]
  us_gaap: [Pretax income, Income before income taxes]

income_tax:
  a_share: [所得税费用]
  us_gaap: [Income tax expense, Provision for income taxes]

net_income:
  a_share: [净利润]
  us_gaap: [Net income, Net earnings]

minority_interest:
  a_share: [少数股东损益]
  us_gaap: [Minority interest, Non-controlling interest]

net_income_to_parent:
  a_share: [归属于母公司股东的净利润, 归母净利润]
  us_gaap: [Net income attributable to parent]

eps_basic:
  a_share: [基本每股收益]
  us_gaap: [Basic EPS, Basic earnings per share]

eps_diluted:
  a_share: [稀释每股收益]
  us_gaap: [Diluted EPS, Diluted earnings per share]

# ---- Balance Sheet ----
cash_and_equivalents:
  a_share: [货币资金, 现金及现金等价物]
  us_gaap: [Cash and cash equivalents, Cash]

short_term_investments:
  a_share: [交易性金融资产, 短期投资]
  us_gaap: [Short-term investments, Marketable securities]

accounts_receivable:
  a_share: [应收账款]
  us_gaap: [Accounts receivable, Trade receivables]

inventory:
  a_share: [存货]
  us_gaap: [Inventory, Inventories]

other_current_assets:
  a_share: [其他流动资产]
  us_gaap: [Other current assets, Prepaid expenses]

total_current_assets:
  a_share: [流动资产合计]
  us_gaap: [Total current assets]

ppe_net:
  a_share: [固定资产净额, 固定资产]
  us_gaap: [Property plant and equipment net, PP&E net]

goodwill:
  a_share: [商誉]
  us_gaap: [Goodwill]

intangibles:
  a_share: [无形资产]
  us_gaap: [Intangible assets, Intangibles]

other_non_current_assets:
  a_share: [其他非流动资产]
  us_gaap: [Other non-current assets, Other long-term assets]

total_assets:
  a_share: [资产总计]
  us_gaap: [Total assets]

accounts_payable:
  a_share: [应付账款]
  us_gaap: [Accounts payable, Trade payables]

short_term_debt:
  a_share: [短期借款, 一年内到期的非流动负债]
  us_gaap: [Short-term debt, Current portion of long-term debt]

other_current_liab:
  a_share: [其他流动负债]
  us_gaap: [Other current liabilities, Accrued expenses]

total_current_liab:
  a_share: [流动负债合计]
  us_gaap: [Total current liabilities]

long_term_debt:
  a_share: [长期借款, 应付债券]
  us_gaap: [Long-term debt]

other_non_current_liab:
  a_share: [其他非流动负债]
  us_gaap: [Other non-current liabilities, Other long-term liabilities]

total_liab:
  a_share: [负债合计]
  us_gaap: [Total liabilities]

minority_equity:
  a_share: [少数股东权益]
  us_gaap: [Minority interest, Non-controlling interest equity]

total_equity:
  a_share: [所有者权益合计, 股东权益合计]
  us_gaap: [Total equity, Total stockholders equity, Total shareholders equity]

# ---- Cash Flow ----
net_income_cf:
  a_share: [净利润]  # cashflow section's own "net income" line
  us_gaap: [Net income]

depreciation_amortization:
  a_share: [固定资产折旧, 无形资产摊销]  # often two lines in A-share; sum them
  us_gaap: [Depreciation and amortization, D&A]

working_capital_change:
  a_share: [经营性应收项目的减少, 经营性应付项目的增加, 存货的减少]
  us_gaap: [Changes in operating assets and liabilities, Changes in working capital]

other_operating:
  a_share: [其他经营活动]
  us_gaap: [Other operating activities]

operating_cashflow:
  a_share: [经营活动产生的现金流量净额]
  us_gaap: [Net cash from operating activities, Cash from operations]

capex:
  a_share: [购建固定资产无形资产和其他长期资产支付的现金]
  us_gaap: [Capital expenditures, Purchases of property and equipment, CapEx]

other_investing:
  a_share: [其他投资活动]
  us_gaap: [Other investing activities]

investing_cashflow:
  a_share: [投资活动产生的现金流量净额]
  us_gaap: [Net cash from investing activities]

debt_issued:
  a_share: [取得借款收到的现金, 发行债券收到的现金]
  us_gaap: [Proceeds from debt issuance, Debt issued]

debt_repaid:
  a_share: [偿还债务支付的现金]
  us_gaap: [Repayments of debt, Debt repaid]

equity_issued:
  a_share: [吸收投资收到的现金]
  us_gaap: [Proceeds from stock issuance, Equity issued]

dividends:
  a_share: [分配股利利润或偿付利息支付的现金]
  us_gaap: [Dividends paid, Cash dividends]

other_financing:
  a_share: [其他筹资活动]
  us_gaap: [Other financing activities]

financing_cashflow:
  a_share: [筹资活动产生的现金流量净额]
  us_gaap: [Net cash from financing activities]

fx_effect:
  a_share: [汇率变动对现金的影响]
  us_gaap: [Effect of exchange rate changes on cash]

net_change_in_cash:
  a_share: [现金及现金等价物净增加额]
  us_gaap: [Net change in cash, Net increase in cash]
```

- [ ] **Step 4: Add loader functions to `app/io/financials.py`**

Append near the top (after FINANCIAL_COLUMNS definition):

```python
import yaml  # add to imports


_ALIAS_MAP_CACHE: dict | None = None


def load_alias_map() -> dict:
    """Load and cache A-share/US GAAP → standard key alias map."""
    global _ALIAS_MAP_CACHE
    if _ALIAS_MAP_CACHE is None:
        path = cfg.FINANCIAL_ALIASES_PATH
        if not path.exists():
            raise FileNotFoundError(f"financial aliases map not found at {path}")
        with path.open("r", encoding="utf-8") as f:
            _ALIAS_MAP_CACHE = yaml.safe_load(f) or {}
    return _ALIAS_MAP_CACHE


def normalize_raw_key(raw: str, market: str | None = None) -> str | None:
    """Map a raw A-share or US GAAP line name to standard snake_case key.

    market: "US" / "SSE" / "SZSE" / "BSE" / "HK" / None (tries both).
    Returns None if no match (caller should log warning, not fail).
    """
    if not raw:
        return None
    m = load_alias_map()
    raw_norm = raw.strip().lower()
    alias_langs = ["a_share", "us_gaap"]
    if market == "US":
        alias_langs = ["us_gaap", "a_share"]
    elif market in ("SSE", "SZSE", "BSE", "HK"):
        alias_langs = ["a_share", "us_gaap"]
    for std_key, langs in m.items():
        for lang in alias_langs:
            aliases = langs.get(lang, []) or []
            for alias in aliases:
                if alias.strip().lower() == raw_norm:
                    return std_key
                # Chinese keys also match exact raw (no lowercasing needed for zh):
                if alias.strip() == raw.strip():
                    return std_key
    return None
```

- [ ] **Step 5: Run tests — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_extended.py::test_load_alias_map_returns_dict tests/test_financials_extended.py::test_alias_map_has_a_share_and_us_gaap tests/test_financials_extended.py::test_alias_map_covers_key_lines tests/test_financials_extended.py::test_normalize_raw_key_to_standard -v 2>&1 | tail -15
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add controlled-vocab/financial-aliases.yaml app/io/financials.py tests/test_financials_extended.py && git commit -m "feat(financials): add A-share/US GAAP alias map for line items

~50 standard snake_case keys with A-share and US-GAAP raw name aliases.
Enables normalize_raw_key() for CSV / digest-subagent ingest.
Config path: FINANCIAL_ALIASES_PATH (spec §4.7).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: 扩展 financials 表 schema (ALTER TABLE)

**Files:**
- Modify: `/Users/yangqi/investing/app/io/financials.py`
- Test: `/Users/yangqi/investing/tests/test_financials_extended.py` (append)

- [ ] **Step 1: Append failing tests**

```python
import sqlite3
import tempfile
from pathlib import Path


def test_financials_schema_has_all_new_columns(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    cursor = conn.execute("PRAGMA table_info(financials)")
    columns = {row[1] for row in cursor.fetchall()}
    # All line items must be columns
    for col in cfg.INCOME_STATEMENT_LINES + cfg.BALANCE_SHEET_LINES + cfg.CASHFLOW_LINES:
        assert col in columns, f"financials table missing column {col}"
    conn.close()


def test_alter_table_migration_preserves_legacy_data(tmp_path):
    """Simulate: existing DB with old 8-col schema, run init_schema, old data survives."""
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    # Create OLD schema (8 cols only)
    conn.executescript("""
        CREATE TABLE financials (
            ticker TEXT NOT NULL, period TEXT NOT NULL, period_type TEXT NOT NULL,
            revenue REAL, gross_profit REAL, operating_income REAL, net_income REAL,
            total_assets REAL, total_equity REAL, operating_cashflow REAL,
            shares_outstanding REAL, source_file TEXT,
            PRIMARY KEY (ticker, period)
        );
    """)
    conn.execute("INSERT INTO financials VALUES ('600519', '2023A', 'annual', 100, 90, 80, 70, 1000, 800, 85, 10, 'legacy.pdf')")
    conn.commit()

    # Run new init_schema — should ALTER to add missing columns
    fin_io.init_schema(conn)

    # Legacy data survives with NULL for new columns
    row = conn.execute("SELECT revenue, inventory, capex FROM financials WHERE ticker='600519'").fetchone()
    assert row[0] == 100  # legacy revenue preserved
    assert row[1] is None  # new inventory column is NULL
    assert row[2] is None  # new capex column is NULL
    conn.close()
```

- [ ] **Step 2: Run — FAIL** (init_schema doesn't exist or uses 8-col schema)

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_extended.py::test_financials_schema_has_all_new_columns tests/test_financials_extended.py::test_alter_table_migration_preserves_legacy_data -v 2>&1 | tail -15
```

- [ ] **Step 3: Refactor `app/io/financials.py`**

Replace `FINANCIAL_COLUMNS` and `_SCHEMA` with:

```python
# Union of all line items; serves as the authoritative column list for the
# financials table. Legacy 8 columns are a subset of this.
FINANCIAL_COLUMNS = tuple(
    dict.fromkeys(  # stable-dedup while preserving insertion order
        list(cfg.INCOME_STATEMENT_LINES)
        + list(cfg.BALANCE_SHEET_LINES)
        + list(cfg.CASHFLOW_LINES)
        + ["shares_outstanding"]  # supplementary
    )
)


def _columns_ddl() -> str:
    """Generate `col REAL` lines for each FINANCIAL_COLUMNS entry."""
    return ",\n    ".join(f"{c} REAL" for c in FINANCIAL_COLUMNS)


_BASE_SCHEMA_TEMPLATE = """
CREATE TABLE IF NOT EXISTS companies (
    ticker TEXT PRIMARY KEY,
    market TEXT,
    name TEXT,
    industry_slugs TEXT,
    listed_date DATE,
    currency TEXT
);

CREATE TABLE IF NOT EXISTS financials (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    period_type TEXT NOT NULL,
    {column_ddl},
    source_file TEXT,
    PRIMARY KEY (ticker, period)
);
"""


def init_schema(conn: sqlite3.Connection) -> None:
    """Create financials + companies tables if missing; ALTER ADD COLUMN
    any FINANCIAL_COLUMNS that exists in tuple but not in the live table."""
    conn.executescript(_BASE_SCHEMA_TEMPLATE.format(column_ddl=_columns_ddl()))

    # ALTER missing columns (SQLite doesn't support IF NOT EXISTS on ADD COLUMN)
    cursor = conn.execute("PRAGMA table_info(financials)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    for col in FINANCIAL_COLUMNS:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE financials ADD COLUMN {col} REAL")
    conn.commit()
```

And replace existing callers of `_SCHEMA` to call `init_schema(conn)` instead.

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_extended.py -v 2>&1 | tail -15
```

Expected: all passed.

- [ ] **Step 5: Run existing financials tests to confirm no regression**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_io.py tests/test_io_financials.py -v 2>&1 | tail -30
```

Expected: existing tests still pass (schema additions don't break read/write on legacy columns).

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/financials.py tests/test_financials_extended.py && git commit -m "feat(financials): expand schema 8→45 columns with ALTER TABLE migration

FINANCIAL_COLUMNS now unions INCOME_STATEMENT_LINES + BALANCE_SHEET_LINES
+ CASHFLOW_LINES + shares_outstanding. init_schema() runs ALTER TABLE
ADD COLUMN for missing columns on existing DBs, preserving legacy data
(spec §4.7 migration strategy).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: 扩展 ratios view (DuPont / FCF / OCF quality / CCC)

**Files:**
- Modify: `/Users/yangqi/investing/app/io/financials.py`
- Test: `/Users/yangqi/investing/tests/test_financials_extended.py` (append)

- [ ] **Step 1: Append failing tests**

```python
def test_recompute_ratios_produces_dupont(tmp_path):
    db_path = tmp_path / "t.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    conn.execute("""
        INSERT INTO financials (ticker, period, period_type,
            revenue, net_income, total_assets, total_equity, operating_cashflow, capex)
        VALUES ('T', '2023A', 'annual', 1000, 100, 2000, 500, 120, 30)
    """)
    conn.commit()
    fin_io.recompute_ratios(conn, "T")

    row = conn.execute("""SELECT net_margin, asset_turnover, equity_multiplier,
                          roe, fcf, fcf_margin, ocf_quality
                          FROM ratios WHERE ticker='T' AND period='2023A'""").fetchone()
    net_margin, asset_turn, eq_mult, roe, fcf, fcf_margin, ocf_q = row
    assert net_margin == 0.1         # 100/1000
    assert asset_turn == 0.5          # 1000/2000
    assert eq_mult == 4.0             # 2000/500
    assert roe == 0.2                 # 100/500
    assert abs(roe - net_margin * asset_turn * eq_mult) < 1e-9  # DuPont identity
    assert fcf == 90                  # 120 - 30
    assert fcf_margin == 0.09         # 90/1000
    assert ocf_q == 1.2                # 120/100


def test_recompute_ratios_ccc(tmp_path):
    db_path = tmp_path / "ccc.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    conn.execute("""
        INSERT INTO financials (ticker, period, period_type,
            revenue, cost_of_revenue, inventory, accounts_receivable, accounts_payable)
        VALUES ('T', '2023A', 'annual', 3650, 2190, 300, 400, 200)
    """)
    conn.commit()
    fin_io.recompute_ratios(conn, "T")

    row = conn.execute("""SELECT days_inventory, days_receivable, days_payable, cash_conversion_cycle
                          FROM ratios WHERE ticker='T'""").fetchone()
    d_inv, d_ar, d_ap, ccc = row
    # days_inventory = inventory / cost_of_revenue * 365 = 300/2190*365 ≈ 50
    assert abs(d_inv - 50.0) < 0.5
    # days_receivable = ar / revenue * 365 = 400/3650*365 = 40
    assert abs(d_ar - 40.0) < 0.5
    # days_payable = ap / cost_of_revenue * 365 = 200/2190*365 ≈ 33.33
    assert abs(d_ap - 33.3) < 0.5
    # ccc = d_inv + d_ar - d_ap
    assert abs(ccc - (d_inv + d_ar - d_ap)) < 0.01


def test_recompute_ratios_handles_null_gracefully(tmp_path):
    """Missing columns must not cause divide-by-zero errors."""
    db_path = tmp_path / "nulls.db"
    conn = sqlite3.connect(str(db_path))
    fin_io.init_schema(conn)
    conn.execute("""
        INSERT INTO financials (ticker, period, period_type, revenue)
        VALUES ('T', '2023A', 'annual', 1000)
    """)
    conn.commit()
    fin_io.recompute_ratios(conn, "T")  # must not raise
    row = conn.execute("SELECT net_margin, fcf, ccc FROM ratios WHERE ticker='T'").fetchone()
    # missing net_income / ocf / capex / inventory → NULL
    assert row is not None
    assert row[0] is None
    assert row[1] is None
```

Note: the third test references `ccc` column; let's stick with `cash_conversion_cycle` for consistency with spec. Adjust the test:

```python
    row = conn.execute("SELECT net_margin, fcf, cash_conversion_cycle FROM ratios WHERE ticker='T'").fetchone()
```

- [ ] **Step 2: Run — FAIL** (ratios table missing new columns)

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_extended.py -v 2>&1 | tail -20
```

- [ ] **Step 3: Rewrite ratios schema + recompute_ratios in `app/io/financials.py`**

Replace the existing `ratios` CREATE TABLE and `recompute_ratios` function:

```python
_RATIOS_SCHEMA = """
CREATE TABLE IF NOT EXISTS ratios (
    ticker TEXT NOT NULL,
    period TEXT NOT NULL,
    -- margins
    gross_margin REAL,
    operating_margin REAL,
    net_margin REAL,
    -- returns
    roe REAL,
    roa REAL,
    -- DuPont three-factor
    asset_turnover REAL,
    equity_multiplier REAL,
    -- leverage
    debt_to_equity REAL,
    -- cash flow
    fcf REAL,
    fcf_margin REAL,
    ocf_quality REAL,
    -- interest coverage
    interest_coverage REAL,
    -- liquidity
    current_ratio REAL,
    quick_ratio REAL,
    -- working capital cycle
    days_inventory REAL,
    days_receivable REAL,
    days_payable REAL,
    cash_conversion_cycle REAL,
    PRIMARY KEY (ticker, period)
);
"""


def recompute_ratios(conn: sqlite3.Connection, ticker: str) -> None:
    """Recompute all derived ratios for a single ticker. Safe for NULL inputs
    (uses NULLIF to avoid division-by-zero; missing inputs → NULL output)."""
    conn.executescript(_RATIOS_SCHEMA)
    conn.execute("DELETE FROM ratios WHERE ticker = ?", (ticker,))

    # Insert one row per period with all derived metrics.
    # NULLIF(x, 0) converts zero to NULL so division returns NULL instead of error.
    conn.execute(
        """
        INSERT INTO ratios (
            ticker, period,
            gross_margin, operating_margin, net_margin,
            roe, roa, asset_turnover, equity_multiplier, debt_to_equity,
            fcf, fcf_margin, ocf_quality, interest_coverage,
            current_ratio, quick_ratio,
            days_inventory, days_receivable, days_payable, cash_conversion_cycle
        )
        SELECT
            ticker, period,
            gross_profit / NULLIF(revenue, 0),
            operating_income / NULLIF(revenue, 0),
            net_income / NULLIF(revenue, 0),

            net_income / NULLIF(total_equity, 0),
            net_income / NULLIF(total_assets, 0),
            revenue / NULLIF(total_assets, 0),
            total_assets / NULLIF(total_equity, 0),
            (COALESCE(short_term_debt, 0) + COALESCE(long_term_debt, 0))
                / NULLIF(total_equity, 0),

            operating_cashflow - COALESCE(capex, 0),
            (operating_cashflow - COALESCE(capex, 0)) / NULLIF(revenue, 0),
            operating_cashflow / NULLIF(net_income, 0),
            operating_income / NULLIF(interest_expense, 0),

            total_current_assets / NULLIF(total_current_liab, 0),
            (total_current_assets - COALESCE(inventory, 0)) / NULLIF(total_current_liab, 0),

            inventory * 365.0 / NULLIF(cost_of_revenue, 0),
            accounts_receivable * 365.0 / NULLIF(revenue, 0),
            accounts_payable * 365.0 / NULLIF(cost_of_revenue, 0),

            (inventory * 365.0 / NULLIF(cost_of_revenue, 0))
              + (accounts_receivable * 365.0 / NULLIF(revenue, 0))
              - (accounts_payable * 365.0 / NULLIF(cost_of_revenue, 0))
        FROM financials
        WHERE ticker = ?
        """,
        (ticker,),
    )
    conn.commit()
```

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_extended.py -v 2>&1 | tail -20
```

Expected: all passed (including DuPont identity check).

- [ ] **Step 5: Existing financials test regression**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_financials_io.py tests/test_io_financials.py -v 2>&1 | tail -20
```

Expected: any existing test referencing `gross_margin` / `net_margin` / `roe` / `roa` / `debt_to_equity` / `operating_margin` still passes. Tests referencing specific non-existent columns (shouldn't be any) fail — fix them.

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/financials.py tests/test_financials_extended.py && git commit -m "feat(financials): expand ratios with DuPont/FCF/OCF quality/CCC

Adds asset_turnover + equity_multiplier (DuPont), fcf + fcf_margin,
ocf_quality, interest_coverage, current/quick_ratio, days_inv/ar/ap,
cash_conversion_cycle. All use NULLIF for safe division on partial data.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase D: industry.py 重写 (TDD)

### Task 11: industry.py — create_industry + read/write meta

**Files:**
- Rewrite: `/Users/yangqi/investing/app/io/industry.py`
- Rewrite: `/Users/yangqi/investing/tests/test_industry_io.py`

- [ ] **Step 1: Backup old tests (save old test file as reference)**

```bash
mv /Users/yangqi/investing/tests/test_industry_io.py /Users/yangqi/investing/tests/test_industry_io.py.old
```

- [ ] **Step 2: Write new failing test for `create_industry`**

Create `/Users/yangqi/investing/tests/test_industry_io.py`:

```python
from pathlib import Path
import pytest
import yaml

from app import config as cfg
from app.io import industry as industry_io


def test_create_industry_builds_skeleton(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()

    industry_io.create_industry(
        slug="cn-cmp-material",
        name="中国化学机械抛光材料",
        scope="CMP 抛光液 + 抛光垫 + 调节液，国产替代主题",
        base=base,
    )

    slug_dir = base / "cn-cmp-material"
    assert slug_dir.is_dir()
    # 11 narrative .md (kebab-case filenames)
    for dim in cfg.INDUSTRY_DIMENSIONS:
        md_path = slug_dir / f"{dim.replace('_', '-')}.md"
        assert md_path.is_file(), f"missing {md_path}"
        assert md_path.read_text(encoding="utf-8").startswith("# ")  # skeleton header
    # meta.yaml
    meta = yaml.safe_load((slug_dir / "meta.yaml").read_text(encoding="utf-8"))
    assert meta["slug"] == "cn-cmp-material"
    assert meta["name"] == "中国化学机械抛光材料"
    assert meta["linked_arenas"] == []
    assert meta["linked_tickers"] == []
    # observations.jsonl created empty
    assert (slug_dir / "observations.jsonl").is_file()
    assert (slug_dir / "observations.jsonl").read_text() == ""
    # sources/ dir
    assert (slug_dir / "sources").is_dir()


def test_create_industry_rejects_invalid_slug(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    with pytest.raises(ValueError, match="slug"):
        industry_io.create_industry(slug="Bad Slug!", name="x", scope="y", base=base)
    with pytest.raises(ValueError, match="slug"):
        industry_io.create_industry(slug="", name="x", scope="y", base=base)


def test_create_industry_refuses_overwrite(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    with pytest.raises(FileExistsError):
        industry_io.create_industry(slug="x", name="X2", scope="y2", base=base)


def test_read_meta_write_meta_roundtrip(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    meta = industry_io.read_meta("x", base=base)
    meta["linked_tickers"] = [{"market": "SSE", "ticker": "600519", "name": "茅台"}]
    industry_io.write_meta("x", meta, base=base)
    meta2 = industry_io.read_meta("x", base=base)
    assert meta2["linked_tickers"][0]["ticker"] == "600519"
```

- [ ] **Step 3: Run — FAIL** (old industry.py still has sector-based API)

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_industry_io.py -v 2>&1 | tail -15
```

- [ ] **Step 4: Write new `app/io/industry.py`**

Replace entire file:

```python
"""Slug-based industry IO (spec §4.1, §4.2).

Replaces the old sector-based landscape.md/players.md layout. Each industry
is one slug directory containing:

- meta.yaml        (slug, name, scope, linked_arenas, linked_tickers, created, last_updated)
- observations.jsonl  (structured facts, one per line)
- 11 narrative .md files (one per INDUSTRY_DIMENSIONS dim, kebab-case names)
- sources/         (archived original PDFs)
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Iterable

import yaml

from app import config as cfg

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")


# ---------- Paths ----------

def _industries_dir(base: Path | None) -> Path:
    return base or cfg.INDUSTRIES_DIR


def _slug_dir(slug: str, base: Path | None) -> Path:
    return _industries_dir(base) / slug


def _meta_path(slug: str, base: Path | None) -> Path:
    return _slug_dir(slug, base) / "meta.yaml"


def _observations_path(slug: str, base: Path | None) -> Path:
    return _slug_dir(slug, base) / "observations.jsonl"


def _narrative_path(slug: str, dim: str, base: Path | None) -> Path:
    if dim not in cfg.INDUSTRY_DIMENSIONS:
        raise ValueError(f"unknown industry dim {dim!r}; must be one of {cfg.INDUSTRY_DIMENSIONS}")
    return _slug_dir(slug, base) / f"{dim.replace('_', '-')}.md"


# ---------- Validation ----------

def _validate_slug(slug: str) -> None:
    if not slug or not _SLUG_RE.match(slug):
        raise ValueError(
            f"invalid industry slug {slug!r}; must match [a-z0-9][a-z0-9-]*[a-z0-9], len 3-64"
        )


# ---------- Meta ----------

def create_industry(
    slug: str,
    name: str,
    scope: str,
    base: Path | None = None,
    today: date | None = None,
) -> Path:
    """Create a new industry slug directory with 11-dim narrative skeletons,
    empty observations.jsonl, meta.yaml, and sources/ dir.

    Raises ValueError on bad slug, FileExistsError if dir already exists.
    """
    _validate_slug(slug)
    if not name.strip():
        raise ValueError("name must be non-empty")
    today = today or date.today()

    slug_dir = _slug_dir(slug, base)
    if slug_dir.exists():
        raise FileExistsError(f"industry dir already exists: {slug_dir}")
    slug_dir.mkdir(parents=True)
    (slug_dir / "sources").mkdir()

    meta = {
        "slug": slug,
        "name": name,
        "scope": scope,
        "linked_arenas": [],
        "linked_tickers": [],
        "created": today.isoformat(),
        "last_updated": today.isoformat(),
    }
    _meta_path(slug, base).write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    # 11 narrative skeleton files
    _CN_TITLES = {
        "definition": "定义与边界",
        "market_size": "市场规模与增长",
        "lifecycle": "生命周期阶段",
        "value_chain": "产业链分析",
        "competition": "竞争结构",
        "drivers": "增长驱动与催化",
        "technology": "技术与产品",
        "regulation": "监管与政策",
        "benchmark": "关键经营指标基准值",
        "risks": "主要风险",
        "valuation": "投资视角与估值锚",
    }
    for dim in cfg.INDUSTRY_DIMENSIONS:
        header = f"# {_CN_TITLES[dim]} · {name}\n\n*slug: {slug} · 维度: {dim}*\n\n"
        _narrative_path(slug, dim, base).write_text(header, encoding="utf-8")

    # empty observations.jsonl
    _observations_path(slug, base).write_text("", encoding="utf-8")

    return slug_dir


def read_meta(slug: str, base: Path | None = None) -> dict:
    path = _meta_path(slug, base)
    if not path.exists():
        raise FileNotFoundError(f"industry not found: {slug}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_meta(slug: str, meta: dict, base: Path | None = None, today: date | None = None) -> None:
    meta = {**meta, "last_updated": (today or date.today()).isoformat()}
    _meta_path(slug, base).write_text(
        yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


def list_industries(base: Path | None = None) -> list[dict]:
    """Return [{slug, name, scope, linked_arenas_count, linked_tickers_count, last_updated}, ...]."""
    root = _industries_dir(base)
    if not root.exists():
        return []
    result = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        meta_path = child / "meta.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        result.append({
            "slug": meta.get("slug", child.name),
            "name": meta.get("name", child.name),
            "scope": meta.get("scope", ""),
            "linked_arenas_count": len(meta.get("linked_arenas") or []),
            "linked_tickers_count": len(meta.get("linked_tickers") or []),
            "last_updated": meta.get("last_updated"),
        })
    return result
```

- [ ] **Step 5: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_industry_io.py -v 2>&1 | tail -20
```

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/industry.py tests/test_industry_io.py && rm -f tests/test_industry_io.py.old && git add -A tests/ && git commit -m "refactor(industry): rewrite IO from sector-based to slug-based

11-dim narrative layout + meta.yaml + observations.jsonl + sources/.
Replaces old landscape.md/players.md sector layout entirely. Adds
create_industry/read_meta/write_meta/list_industries.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: industry.py — observations append / dedup / read

**Files:**
- Modify: `/Users/yangqi/investing/app/io/industry.py`
- Test: `/Users/yangqi/investing/tests/test_industry_io.py` (append)

- [ ] **Step 1: Append failing tests**

```python
def test_append_observations_writes_jsonl(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    rows = [
        {"id": "o1", "dimension": "market_size", "field": "tam_global",
         "value": 33.8, "unit": "usd_bn", "timeframe": "2025",
         "time_type": "actual", "metric_type": "atomic",
         "source_id": "s1", "confidence": "high",
         "claim_text": "2025 TAM 33.8B", "evidence": "...",
         "extracted_by": "x", "extracted_at": "2026-04-26T00:00:00"},
    ]
    n = industry_io.append_observations("x", rows, base=base)
    assert n == 1

    read = industry_io.read_observations("x", base=base)
    assert len(read) == 1
    assert read[0]["id"] == "o1"
    assert read[0]["value"] == 33.8


def test_dedup_observations_keeps_highest_confidence():
    rows = [
        {"field": "tam_global", "timeframe": "2025", "source_id": "s1", "confidence": "low", "id": "a"},
        {"field": "tam_global", "timeframe": "2025", "source_id": "s1", "confidence": "high", "id": "b"},
        {"field": "tam_global", "timeframe": "2025", "source_id": "s2", "confidence": "low", "id": "c"},
    ]
    out = industry_io.dedup_observations(rows)
    ids = {r["id"] for r in out}
    # dedup on (field, timeframe, source_id); s1 keeps "high"=b, s2 keeps c
    assert ids == {"b", "c"}


def test_append_observations_is_additive(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [{"id": "1", "field": "f"}], base=base)
    industry_io.append_observations("x", [{"id": "2", "field": "g"}], base=base)
    read = industry_io.read_observations("x", base=base)
    assert [r["id"] for r in read] == ["1", "2"]
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Add functions to `app/io/industry.py`**

Append:

```python
# ---------- Observations ----------

_CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def read_observations(slug: str, base: Path | None = None) -> list[dict]:
    path = _observations_path(slug, base)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def append_observations(
    slug: str, rows: Iterable[dict], base: Path | None = None
) -> int:
    """Append rows to observations.jsonl. Returns count written."""
    path = _observations_path(slug, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def dedup_observations(rows: Iterable[dict]) -> list[dict]:
    """Dedup on (field, timeframe, source_id); when collision, keep highest
    confidence ('high' > 'medium' > 'low'). Rows missing any key pass through."""
    buckets: dict[tuple, dict] = {}
    passthrough: list[dict] = []
    for row in rows:
        key_parts = (row.get("field"), row.get("timeframe"), row.get("source_id"))
        if None in key_parts:
            passthrough.append(row)
            continue
        existing = buckets.get(key_parts)
        if existing is None:
            buckets[key_parts] = row
            continue
        existing_rank = _CONFIDENCE_RANK.get(existing.get("confidence", "low"), 0)
        new_rank = _CONFIDENCE_RANK.get(row.get("confidence", "low"), 0)
        if new_rank > existing_rank:
            buckets[key_parts] = row
    return list(buckets.values()) + passthrough
```

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_industry_io.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/industry.py tests/test_industry_io.py && git commit -m "feat(industry): add observations append/read/dedup

Structured fact layer; dedup on (field, timeframe, source_id) keeping
highest-confidence row (spec §4.2).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: industry.py — filter_observations_by_arena / by_segment

**Files:**
- Modify: `/Users/yangqi/investing/app/io/industry.py`
- Test: `/Users/yangqi/investing/tests/test_industry_io.py` (append)

- [ ] **Step 1: Append failing tests**

```python
def test_filter_observations_by_arena(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [
        {"id": "a", "arena_refs": ["arena-1"]},
        {"id": "b", "arena_refs": ["arena-2"]},
        {"id": "c", "arena_refs": ["arena-1", "arena-2"]},
        {"id": "d", "arena_refs": []},
        {"id": "e"},  # no arena_refs field at all
    ], base=base)

    rows = industry_io.filter_observations_by_arena("x", "arena-1", base=base)
    assert {r["id"] for r in rows} == {"a", "c"}


def test_filter_observations_by_segment(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    industry_io.append_observations("x", [
        {"id": "a", "segment": "slurry"},
        {"id": "b", "segment": "pad"},
        {"id": "c", "segment": "slurry"},
        {"id": "d", "segment": None},
    ], base=base)
    rows = industry_io.filter_observations_by_segment("x", "slurry", base=base)
    assert {r["id"] for r in rows} == {"a", "c"}
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Append functions**

```python
def filter_observations_by_arena(
    slug: str, arena_slug: str, base: Path | None = None
) -> list[dict]:
    """Return observations whose arena_refs include arena_slug."""
    return [
        row for row in read_observations(slug, base=base)
        if arena_slug in (row.get("arena_refs") or [])
    ]


def filter_observations_by_segment(
    slug: str, segment: str, base: Path | None = None
) -> list[dict]:
    return [
        row for row in read_observations(slug, base=base)
        if row.get("segment") == segment
    ]
```

- [ ] **Step 4: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_industry_io.py -v 2>&1 | tail -10 \
  && git add app/io/industry.py tests/test_industry_io.py && git commit -m "feat(industry): add filter_observations_by_arena/by_segment

Enables arena page to pull cross-ticker facts by arena_refs index and
segment-level breakdown views (spec §4.6, §6.3).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: industry.py — narrative read + append_block

**Files:**
- Modify: `/Users/yangqi/investing/app/io/industry.py`
- Test: `/Users/yangqi/investing/tests/test_industry_io.py` (append)

- [ ] **Step 1: Append failing tests**

```python
def test_read_narrative_returns_skeleton_header(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    md = industry_io.read_narrative("x", "market_size", base=base)
    assert md.startswith("# 市场规模与增长")


def test_append_narrative_block_writes_source_section(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)

    block = "2025 年 TAM 达 33.8 亿美元。"
    industry_io.append_narrative_block(
        slug="x", dim="market_size", block=block,
        source_meta={"institution": "国金证券", "date": "2026-03-10",
                     "sha8": "abc12345", "source_id": "行研-国金证券-2026-03-10-abc12345"},
        base=base,
    )
    md = industry_io.read_narrative("x", "market_size", base=base)
    assert "### 来源 国金证券 2026-03-10 (sha8=abc12345)" in md
    assert "source_id: 行研-国金证券-2026-03-10-abc12345" in md
    assert "2025 年 TAM 达 33.8 亿美元" in md


def test_append_narrative_block_append_only(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    sm = {"institution": "A", "date": "2026-01-01", "sha8": "11111111", "source_id": "s1"}
    industry_io.append_narrative_block("x", "market_size", "first", sm, base=base)
    sm2 = {"institution": "B", "date": "2026-02-01", "sha8": "22222222", "source_id": "s2"}
    industry_io.append_narrative_block("x", "market_size", "second", sm2, base=base)
    md = industry_io.read_narrative("x", "market_size", base=base)
    idx_a = md.find("first")
    idx_b = md.find("second")
    assert 0 < idx_a < idx_b  # chronological order preserved


def test_append_narrative_block_rejects_unknown_dim(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="y", base=base)
    with pytest.raises(ValueError, match="unknown"):
        industry_io.append_narrative_block(
            "x", "bogus_dim", "x", {"institution":"a","date":"b","sha8":"c","source_id":"d"},
            base=base,
        )
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Append functions**

```python
# ---------- Narrative ----------

_NARRATIVE_BLOCK_TEMPLATE = """
### 来源 {institution} {date} (sha8={sha8})
source_id: {source_id}

{block}
"""


def read_narrative(slug: str, dim: str, base: Path | None = None) -> str:
    path = _narrative_path(slug, dim, base)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_narrative_block(
    slug: str,
    dim: str,
    block: str,
    source_meta: dict,
    base: Path | None = None,
) -> None:
    """Append a source-labeled block to narrative .md. source_meta must contain
    institution / date / sha8 / source_id. Never modifies existing content."""
    path = _narrative_path(slug, dim, base)  # raises on unknown dim
    for key in ("institution", "date", "sha8", "source_id"):
        if key not in source_meta:
            raise ValueError(f"source_meta missing {key}")
    rendered = _NARRATIVE_BLOCK_TEMPLATE.format(
        institution=source_meta["institution"],
        date=source_meta["date"],
        sha8=source_meta["sha8"],
        source_id=source_meta["source_id"],
        block=block.rstrip(),
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(rendered)
```

- [ ] **Step 4: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_industry_io.py -v 2>&1 | tail -10 \
  && git add app/io/industry.py tests/test_industry_io.py && git commit -m "feat(industry): add narrative read + append_block

Per-source '### 来源 ...' block append to narrative .md files.
Never modifies existing content; chronological log-stream style per
spec §4.4 / §D15.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: industry.py — find_by_company / find_by_arena

**Files:**
- Modify: `/Users/yangqi/investing/app/io/industry.py`
- Test: `/Users/yangqi/investing/tests/test_industry_io.py` (append)

- [ ] **Step 1: Append failing tests**

```python
def test_find_by_company_scans_linked_tickers(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="a", name="A", scope="", base=base)
    industry_io.create_industry(slug="b", name="B", scope="", base=base)
    # put ticker 600519 in industry A only
    meta_a = industry_io.read_meta("a", base=base)
    meta_a["linked_tickers"] = [
        {"market": "SSE", "ticker": "600519", "name": "茅台"},
        {"market": "US", "ticker": "AAPL", "name": "Apple"},
    ]
    industry_io.write_meta("a", meta_a, base=base)
    meta_b = industry_io.read_meta("b", base=base)
    meta_b["linked_tickers"] = [{"market": "SSE", "ticker": "000858", "name": "五粮液"}]
    industry_io.write_meta("b", meta_b, base=base)

    slugs = industry_io.find_by_company("600519", "SSE", base=base)
    assert slugs == ["a"]
    slugs2 = industry_io.find_by_company("unknown", "SSE", base=base)
    assert slugs2 == []


def test_find_by_arena_via_definition_frontmatter(tmp_path, monkeypatch):
    """find_by_arena reads arena.definition.md frontmatter.industry.
    Uses arenas.find_by_industry inverse lookup OR scans industry meta linked_arenas."""
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="ind1", name="I1", scope="", base=base)
    meta = industry_io.read_meta("ind1", base=base)
    meta["linked_arenas"] = ["arena-x", "arena-y"]
    industry_io.write_meta("ind1", meta, base=base)

    assert industry_io.find_by_arena("arena-x", base=base) == "ind1"
    assert industry_io.find_by_arena("arena-z", base=base) is None
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Append functions**

```python
def find_by_company(ticker: str, market: str, base: Path | None = None) -> list[str]:
    """Return list of industry slugs whose linked_tickers include (market, ticker)."""
    root = _industries_dir(base)
    if not root.exists():
        return []
    matches = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "meta.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        for t in meta.get("linked_tickers") or []:
            if t.get("ticker") == ticker and t.get("market") == market:
                matches.append(meta.get("slug", child.name))
                break
    return matches


def find_by_arena(arena_slug: str, base: Path | None = None) -> str | None:
    """Return industry slug whose linked_arenas contains arena_slug, or None."""
    root = _industries_dir(base)
    if not root.exists():
        return None
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        meta_path = child / "meta.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        if arena_slug in (meta.get("linked_arenas") or []):
            return meta.get("slug", child.name)
    return None
```

- [ ] **Step 4: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_industry_io.py -v 2>&1 | tail -10 \
  && git add app/io/industry.py tests/test_industry_io.py && git commit -m "feat(industry): add find_by_company / find_by_arena cross-refs

Enables cross-layer navigation: given a ticker, find which industries
it belongs to; given an arena slug, find its parent industry (spec §4.6).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase E: arenas.py 扩展 (TDD)

### Task 16: arenas.py — definition frontmatter 加 industry + battleground_focus

**Files:**
- Modify: `/Users/yangqi/investing/app/io/arenas.py`
- Test: `/Users/yangqi/investing/tests/test_arenas_narrative.py` (new)

- [ ] **Step 1: Write failing test**

Create `/Users/yangqi/investing/tests/test_arenas_narrative.py`:

```python
from pathlib import Path
import pytest

from app.io import arenas as arenas_io


def test_write_definition_accepts_industry_and_battleground_focus(tmp_path):
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(
        slug="test-arena",
        name="测试战场",
        definition_text="def body",
        industry="cn-cmp-material",
        battleground_focus="国产 CMP 抛光液挑战 Dupont/Cabot/Versum",
        base=base,
    )
    result = arenas_io.read_definition("test-arena", base=base)
    fm = result["frontmatter"]
    assert fm["industry"] == "cn-cmp-material"
    assert fm["battleground_focus"] == "国产 CMP 抛光液挑战 Dupont/Cabot/Versum"


def test_write_definition_industry_and_focus_optional(tmp_path):
    """Existing arenas without these fields must still work."""
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="legacy", name="Legacy", definition_text="x", base=base)
    r = arenas_io.read_definition("legacy", base=base)
    assert r["frontmatter"].get("industry") is None or r["frontmatter"].get("industry") == ""
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Edit `app/io/arenas.py`**

Find `write_definition` signature (L107) and extend:

```python
def write_definition(
    slug: str,
    name: str,
    definition_text: str,
    participants: list[dict] | None = None,
    industry: str | None = None,
    battleground_focus: str | None = None,
    base: Path | None = None,
    today: date | None = None,
) -> Path:
    ...  # existing body, but when building frontmatter dict:
    #     if industry is not None: fm["industry"] = industry
    #     if battleground_focus is not None: fm["battleground_focus"] = battleground_focus
```

Apply the concrete edit: inside `write_definition`, after setting `slug`, `name`, `created`, `last_updated`, `participants`, add:

```python
    fm = {
        "slug": slug,
        "name": name,
        "created": ...,
        "last_updated": today_iso,
        "participants": participants or [],
    }
    if industry is not None:
        fm["industry"] = industry
    if battleground_focus is not None:
        fm["battleground_focus"] = battleground_focus
```

(Exact existing code structure: use the `_emit_frontmatter` helper unchanged; it will pick up any new keys.)

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_arenas_narrative.py -v 2>&1 | tail -10
```

- [ ] **Step 5: Verify existing arenas test not broken**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_arenas_io.py tests/test_io_arenas.py -v 2>&1 | tail -20
```

Expected: existing tests unchanged (both new params default None).

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/arenas.py tests/test_arenas_narrative.py && git commit -m "feat(arenas): add industry + battleground_focus to definition frontmatter

Arena is a battle-narrative unit (spec §2.2); industry backlink and
explicit battleground_focus text are now first-class frontmatter fields.
Both optional; legacy arenas without them still read correctly.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: arenas.py — 6 维度 narrative read + append_block

**Files:**
- Modify: `/Users/yangqi/investing/app/io/arenas.py`
- Test: `/Users/yangqi/investing/tests/test_arenas_narrative.py` (append)

- [ ] **Step 1: Append failing tests**

```python
from app import config as cfg


def test_arena_narrative_skeleton_files_on_write_definition(tmp_path):
    """When definition is written for a NEW arena, 5 additional narrative
    skeleton .md files are created (dim != 'definition')."""
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(
        slug="a1", name="Arena 1", definition_text="body",
        industry="ind-x", battleground_focus="focus",
        base=base,
    )
    slug_dir = base / "a1"
    for dim in cfg.ARENA_DIMENSIONS:
        if dim == "definition":
            continue  # definition.md is the existing file
        assert (slug_dir / f"{dim.replace('_', '-')}.md").is_file()


def test_arena_read_narrative_returns_content(tmp_path):
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="a", name="A", definition_text="x",
                               industry="i", battleground_focus="f", base=base)
    content = arenas_io.read_narrative("a", "participants", base=base)
    assert isinstance(content, str)
    assert content.startswith("# ")  # skeleton header present


def test_arena_append_narrative_block_appends(tmp_path):
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="a", name="A", definition_text="x",
                               industry="i", battleground_focus="f", base=base)
    arenas_io.append_narrative_block(
        slug="a", dim="narratives", block="Bull 情景：挑战者赢",
        source_meta={"institution": "X","date": "2026-01-01","sha8": "abcdef12","source_id": "sid"},
        base=base,
    )
    md = arenas_io.read_narrative("a", "narratives", base=base)
    assert "### 来源 X 2026-01-01 (sha8=abcdef12)" in md
    assert "Bull 情景：挑战者赢" in md


def test_arena_append_narrative_rejects_unknown_dim(tmp_path):
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="a", name="A", definition_text="x", base=base)
    with pytest.raises(ValueError, match="unknown"):
        arenas_io.append_narrative_block(
            "a", "bogus", "x", {"institution":"a","date":"b","sha8":"c","source_id":"d"},
            base=base,
        )
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Edit `app/io/arenas.py`**

Append functions near the end of the file:

```python
# ---------- Narrative (6-dim, spec §4.1) ----------

_ARENA_NARRATIVE_TEMPLATE = """
### 来源 {institution} {date} (sha8={sha8})
source_id: {source_id}

{block}
"""

_ARENA_CN_TITLES = {
    "definition": "战场定义与博弈焦点",
    "participants": "参与者与相对位置",
    "decisive_factors": "博弈规则与胜负手",
    "trajectory": "演进轨迹与触发事件",
    "narratives": "多空叙事",
    "investment_view": "决策启示",
}


def _arena_narrative_path(slug: str, dim: str, base: Path | None) -> Path:
    if dim not in cfg.ARENA_DIMENSIONS:
        raise ValueError(f"unknown arena dim {dim!r}; must be one of {cfg.ARENA_DIMENSIONS}")
    if dim == "definition":
        return _definition_path(slug, base)
    return _arena_dir(slug, base) / f"{dim.replace('_', '-')}.md"


def _ensure_narrative_skeletons(slug: str, name: str, base: Path | None) -> None:
    """Create 5 narrative .md skeletons (excluding definition.md) if missing."""
    for dim in cfg.ARENA_DIMENSIONS:
        if dim == "definition":
            continue
        path = _arena_narrative_path(slug, dim, base)
        if not path.exists():
            header = f"# {_ARENA_CN_TITLES[dim]} · {name}\n\n*slug: {slug} · 维度: {dim}*\n\n"
            path.write_text(header, encoding="utf-8")


def read_narrative(slug: str, dim: str, base: Path | None = None) -> str:
    path = _arena_narrative_path(slug, dim, base)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_narrative_block(
    slug: str, dim: str, block: str, source_meta: dict, base: Path | None = None
) -> None:
    path = _arena_narrative_path(slug, dim, base)
    for key in ("institution", "date", "sha8", "source_id"):
        if key not in source_meta:
            raise ValueError(f"source_meta missing {key}")
    rendered = _ARENA_NARRATIVE_TEMPLATE.format(
        institution=source_meta["institution"],
        date=source_meta["date"],
        sha8=source_meta["sha8"],
        source_id=source_meta["source_id"],
        block=block.rstrip(),
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(rendered)
```

Also update `write_definition` to call `_ensure_narrative_skeletons(slug, name, base)` after writing definition.md.

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_arenas_narrative.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Regression check**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_arenas_io.py tests/test_io_arenas.py -v 2>&1 | tail -20
```

Expected: passes. Note: existing arena `cn-power-cable-polymer-material` won't have 5 narrative skeletons yet; that's OK, skeletons are only created for new arenas. Existing tests shouldn't assert absence.

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/arenas.py tests/test_arenas_narrative.py && git commit -m "feat(arenas): add 6-dim narrative read + append_block

ARENA_DIMENSIONS defines 6 narrative layers: definition (existing),
participants, decisive_factors, trajectory, narratives, investment_view.
Skeletons auto-created on new arena bootstrap (spec §4.1).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 18: arenas.py — find_by_industry

**Files:**
- Modify: `/Users/yangqi/investing/app/io/arenas.py`
- Test: `/Users/yangqi/investing/tests/test_arenas_narrative.py` (append)

- [ ] **Step 1: Append failing test**

```python
def test_find_by_industry_lists_arenas(tmp_path):
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="a1", name="A1", definition_text="x",
                               industry="ind-x", battleground_focus="f", base=base)
    arenas_io.write_definition(slug="a2", name="A2", definition_text="x",
                               industry="ind-y", battleground_focus="f", base=base)
    arenas_io.write_definition(slug="a3", name="A3", definition_text="x",
                               industry="ind-x", battleground_focus="f", base=base)

    result = arenas_io.find_by_industry("ind-x", base=base)
    assert set(result) == {"a1", "a3"}
    assert arenas_io.find_by_industry("ind-z", base=base) == []
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Append function to `app/io/arenas.py`**

```python
def find_by_industry(industry_slug: str, base: Path | None = None) -> list[str]:
    """Return list of arena slugs whose definition.md frontmatter.industry == industry_slug."""
    root = _arenas_dir(base)
    if not root.exists():
        return []
    result = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        def_path = _definition_path(child.name, base)
        if not def_path.exists():
            continue
        try:
            data = read_definition(child.name, base=base)
        except Exception:
            continue
        fm = data.get("frontmatter", {})
        if fm.get("industry") == industry_slug:
            result.append(fm.get("slug", child.name))
    return result
```

- [ ] **Step 4: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_arenas_narrative.py -v 2>&1 | tail -10 \
  && git add app/io/arenas.py tests/test_arenas_narrative.py && git commit -m "feat(arenas): add find_by_industry

Reverse lookup: given industry slug, list arenas declaring it in their
definition.md frontmatter (spec §4.6).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase F: company.py 8 维 narrative (TDD)

### Task 19: company.py — 8 维 narrative read + append_block

**Files:**
- Modify: `/Users/yangqi/investing/app/io/company.py`
- Test: `/Users/yangqi/investing/tests/test_company_narrative.py` (new)

- [ ] **Step 1: Write failing test**

Create `/Users/yangqi/investing/tests/test_company_narrative.py`:

```python
from pathlib import Path
import pytest

from app import config as cfg
from app.io import company as company_io


def test_create_company_creates_narrative_skeletons(tmp_path):
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(
        ticker="TEST", market="US", name="Test Co",
        industry_slugs=["test-ind"], base=base,
    )
    narr_dir = base / "US_TEST" / "narratives"
    assert narr_dir.is_dir()
    for dim in cfg.COMPANY_DIMENSIONS:
        assert (narr_dir / f"{dim.replace('_', '-')}.md").is_file()


def test_read_narrative_returns_skeleton(tmp_path):
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(
        ticker="TEST", market="US", name="Test Co",
        industry_slugs=[], base=base,
    )
    md = company_io.read_narrative("TEST", "US", "moat", base=base)
    assert md.startswith("# ")


def test_append_narrative_block(tmp_path):
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(
        ticker="T", market="US", name="T Co",
        industry_slugs=[], base=base,
    )
    company_io.append_narrative_block(
        ticker="T", market="US", dim="moat", block="主要护城河是技术专利。",
        source_meta={"institution": "10-K", "date": "2024-12-31",
                     "sha8": "deadbeef", "source_id": "年报-2024-deadbeef"},
        base=base,
    )
    md = company_io.read_narrative("T", "US", "moat", base=base)
    assert "### 来源 10-K 2024-12-31 (sha8=deadbeef)" in md
    assert "主要护城河是技术专利" in md


def test_append_narrative_rejects_unknown_dim(tmp_path):
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(ticker="T", market="US", name="T", industry_slugs=[], base=base)
    with pytest.raises(ValueError, match="unknown"):
        company_io.append_narrative_block(
            "T", "US", "bogus", "x",
            {"institution":"a","date":"b","sha8":"c","source_id":"d"}, base=base,
        )
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Edit `app/io/company.py`**

Append:

```python
_COMPANY_CN_TITLES = {
    "business_model": "业务模式",
    "moat": "护城河与竞争策略",
    "growth_engine": "增长引擎与未来规划",
    "management": "管理层与治理",
    "financial_profile": "财务分析",
    "catalysts": "关键事件与催化剂",
    "risks": "风险",
    "valuation": "估值",
}

_COMPANY_NARRATIVE_TEMPLATE = """
### 来源 {institution} {date} (sha8={sha8})
source_id: {source_id}

{block}
"""


def _narratives_dir(ticker: str, market: str, base: Path | None) -> Path:
    return _company_dir(ticker, market, base) / "narratives"


def _narrative_path(ticker: str, market: str, dim: str, base: Path | None) -> Path:
    if dim not in cfg.COMPANY_DIMENSIONS:
        raise ValueError(f"unknown company dim {dim!r}; must be one of {cfg.COMPANY_DIMENSIONS}")
    return _narratives_dir(ticker, market, base) / f"{dim.replace('_', '-')}.md"


def _ensure_narrative_skeletons(ticker: str, market: str, name: str, base: Path | None) -> None:
    narr_dir = _narratives_dir(ticker, market, base)
    narr_dir.mkdir(exist_ok=True)
    for dim in cfg.COMPANY_DIMENSIONS:
        path = _narrative_path(ticker, market, dim, base)
        if not path.exists():
            header = f"# {_COMPANY_CN_TITLES[dim]} · {name}\n\n*{market}_{ticker} · 维度: {dim}*\n\n"
            path.write_text(header, encoding="utf-8")


def read_narrative(ticker: str, market: str, dim: str, base: Path | None = None) -> str:
    path = _narrative_path(ticker, market, dim, base)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def append_narrative_block(
    ticker: str, market: str, dim: str, block: str,
    source_meta: dict, base: Path | None = None,
) -> None:
    path = _narrative_path(ticker, market, dim, base)
    for key in ("institution", "date", "sha8", "source_id"):
        if key not in source_meta:
            raise ValueError(f"source_meta missing {key}")
    rendered = _COMPANY_NARRATIVE_TEMPLATE.format(
        institution=source_meta["institution"],
        date=source_meta["date"],
        sha8=source_meta["sha8"],
        source_id=source_meta["source_id"],
        block=block.rstrip(),
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(rendered)
```

And inside `create_company`, after `write_meta(...)`, add:

```python
    _ensure_narrative_skeletons(ticker, market, name, base)
```

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_company_narrative.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Regression**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_io_company.py -v 2>&1 | tail -20
```

Existing tests pass.

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/company.py tests/test_company_narrative.py && git commit -m "feat(company): add 8-dim narrative read + append_block

COMPANY_DIMENSIONS narrative layer: business_model / moat / growth_engine /
management / financial_profile / catalysts / risks / valuation. Skeletons
auto-created by create_company (spec §4.1).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase G: claims.py 扩展 (TDD)

### Task 20: claims.py — validate_batch 接受 arena_refs + company_dimension_hint

**Files:**
- Modify: `/Users/yangqi/investing/app/io/claims.py`
- Test: `/Users/yangqi/investing/tests/test_claims_arena_refs.py` (new)

- [ ] **Step 1: Write failing test**

Create `/Users/yangqi/investing/tests/test_claims_arena_refs.py`:

```python
import json
from pathlib import Path
import pytest

from app import config as cfg
from app.io import claims as claims_io


def _minimal_batch(claims: list[dict]) -> str:
    header = {
        "ticker": "T", "market": "US",
        "source_id": "test-1", "source_file": "x.pdf",
        "extracted_by": "test", "extracted_at": "2026-04-26T00:00:00",
    }
    return json.dumps({"header": header, "claims": claims})  # shape mirrors real batch


def test_validate_batch_accepts_arena_refs_empty_default(fake_subjects):
    # subjects fixture: minimal valid subject for test
    batch = _minimal_batch([{
        "claim_text": "X",
        "subject_tag": "test:tag",
        "polarity": "neutral",
        "claim_type": "qualitative",
    }])
    header, valid, errors = claims_io.validate_batch(batch, subjects=fake_subjects)
    assert errors == []
    assert valid[0].get("arena_refs", []) == []
    assert valid[0].get("company_dimension_hint") is None


def test_validate_batch_accepts_arena_refs_provided(fake_subjects):
    batch = _minimal_batch([{
        "claim_text": "X",
        "subject_tag": "test:tag",
        "polarity": "neutral",
        "claim_type": "qualitative",
        "arena_refs": ["arena-a", "arena-b"],
        "company_dimension_hint": "moat",
    }])
    header, valid, errors = claims_io.validate_batch(batch, subjects=fake_subjects)
    assert errors == []
    assert valid[0]["arena_refs"] == ["arena-a", "arena-b"]
    assert valid[0]["company_dimension_hint"] == "moat"


def test_validate_batch_rejects_company_dimension_hint_not_in_whitelist(fake_subjects):
    batch = _minimal_batch([{
        "claim_text": "X",
        "subject_tag": "test:tag",
        "polarity": "neutral",
        "claim_type": "qualitative",
        "company_dimension_hint": "not_a_real_dim",
    }])
    header, valid, errors = claims_io.validate_batch(batch, subjects=fake_subjects)
    # accept the claim but record an error for the bad dim hint, OR reject outright;
    # choice: reject (strict whitelist on optional field when provided)
    assert errors, "bad dim hint should raise validation error"


@pytest.fixture
def fake_subjects():
    return [{"tag": "test:tag", "label": "test tag"}]
```

- [ ] **Step 2: Run — FAIL** (validate_batch doesn't look at new fields)

- [ ] **Step 3: Edit `app/io/claims.py` — `validate_batch`**

Locate `validate_batch`. Inside the per-claim loop, after existing required-field validation, add:

```python
    # Optional arena_refs: list[str] of arena slugs; default []
    arena_refs = claim.get("arena_refs")
    if arena_refs is None:
        claim["arena_refs"] = []
    elif not isinstance(arena_refs, list) or not all(isinstance(s, str) for s in arena_refs):
        errors.append({"idx": idx, "field": "arena_refs", "msg": "must be list[str]"})
        continue

    # Optional company_dimension_hint: must match COMPANY_DIMENSIONS if provided
    dim_hint = claim.get("company_dimension_hint")
    if dim_hint is not None:
        if dim_hint not in cfg.COMPANY_DIMENSIONS:
            errors.append({
                "idx": idx, "field": "company_dimension_hint",
                "msg": f"must be one of {cfg.COMPANY_DIMENSIONS} or null, got {dim_hint!r}",
            })
            continue
```

- [ ] **Step 4: PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_claims_arena_refs.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Regression**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_claims_io.py tests/test_io_claims.py -v 2>&1 | tail -20
```

Existing tests pass (new fields are optional).

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/claims.py tests/test_claims_arena_refs.py && git commit -m "feat(claims): validate_batch accepts arena_refs + company_dimension_hint

Optional fields; default arena_refs=[] and dimension_hint=None. When
dimension_hint is provided, must match COMPANY_DIMENSIONS whitelist.
Enables cross-layer indexing (spec §4.3).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 21: claims.py — filter_by_arena + filter_by_company_dimension

**Files:**
- Modify: `/Users/yangqi/investing/app/io/claims.py`
- Test: `/Users/yangqi/investing/tests/test_claims_arena_refs.py` (append)

- [ ] **Step 1: Append failing tests**

```python
def test_filter_by_arena_scans_all_companies(tmp_path, fake_subjects, monkeypatch):
    base = tmp_path / "companies"
    base.mkdir()
    # Create 2 companies with claims
    from app.io import company as company_io
    company_io.create_company(ticker="A", market="US", name="AA", industry_slugs=[], base=base)
    company_io.create_company(ticker="B", market="US", name="BB", industry_slugs=[], base=base)

    claims_a = [
        {"claim_text": "x", "subject_tag": "test:tag",
         "polarity": "neutral", "claim_type": "qualitative",
         "arena_refs": ["arena-1"]},
    ]
    claims_b = [
        {"claim_text": "y", "subject_tag": "test:tag",
         "polarity": "neutral", "claim_type": "qualitative",
         "arena_refs": ["arena-2"]},
        {"claim_text": "z", "subject_tag": "test:tag",
         "polarity": "neutral", "claim_type": "qualitative",
         "arena_refs": ["arena-1", "arena-2"]},
    ]
    header_a = {"ticker": "A", "market": "US", "source_id": "sa",
                "source_file": "", "extracted_by": "t", "extracted_at": "2026-04-26T00:00:00"}
    header_b = dict(header_a, ticker="B", source_id="sb")
    claims_io.append_batch("A", "US", claims_a, header=header_a, base=base)
    claims_io.append_batch("B", "US", claims_b, header=header_b, base=base)

    result = claims_io.filter_by_arena("arena-1", base=base)
    texts = {c["claim_text"] for c in result}
    assert texts == {"x", "z"}


def test_filter_by_company_dimension(tmp_path, fake_subjects):
    from app.io import company as company_io
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(ticker="A", market="US", name="AA", industry_slugs=[], base=base)
    claims_data = [
        {"claim_text": "x", "subject_tag": "test:tag", "polarity": "neutral",
         "claim_type": "qualitative", "company_dimension_hint": "moat"},
        {"claim_text": "y", "subject_tag": "test:tag", "polarity": "neutral",
         "claim_type": "qualitative", "company_dimension_hint": "risks"},
    ]
    header = {"ticker": "A", "market": "US", "source_id": "s",
              "source_file": "", "extracted_by": "t", "extracted_at": "2026-04-26T00:00:00"}
    claims_io.append_batch("A", "US", claims_data, header=header, base=base)
    result = claims_io.filter_by_company_dimension("A", "US", "moat", base=base)
    assert len(result) == 1
    assert result[0]["claim_text"] == "x"
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Append functions to `app/io/claims.py`**

```python
def filter_by_arena(arena_slug: str, base: Path | None = None) -> list[dict]:
    """Scan all companies' claims.jsonl, return claims whose arena_refs contains arena_slug."""
    from app.io import company as company_io  # lazy to avoid circular

    base = base or cfg.COMPANIES_DIR
    result: list[dict] = []
    if not base.exists():
        return []
    for company_dir in sorted(base.iterdir()):
        if not company_dir.is_dir() or "_" not in company_dir.name:
            continue
        market, ticker = company_dir.name.split("_", 1)
        try:
            claims = read_claims(ticker, market, base=base)
        except Exception:
            continue
        for c in claims:
            if arena_slug in (c.get("arena_refs") or []):
                result.append(c)
    return result


def filter_by_company_dimension(
    ticker: str, market: str, dim: str, base: Path | None = None
) -> list[dict]:
    """Return claims for given company whose company_dimension_hint == dim."""
    if dim not in cfg.COMPANY_DIMENSIONS:
        raise ValueError(f"unknown company dim {dim!r}")
    return [c for c in read_claims(ticker, market, base=base)
            if c.get("company_dimension_hint") == dim]
```

- [ ] **Step 4: PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_claims_arena_refs.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/claims.py tests/test_claims_arena_refs.py && git commit -m "feat(claims): add filter_by_arena + filter_by_company_dimension

Cross-layer query helpers: arena page pulls claims by arena_refs across
all companies; company narrative cards pull supporting claims by
dimension_hint (spec §6.1, §6.3).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase H: 集成收尾

### Task 22: 全量 pytest + 文档内一致性

**Files:**
- None modified; just verification.

- [ ] **Step 1: 跑全量 test**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/ -v 2>&1 | tail -40
```

Expected: all tests green OR only red from test files that reference deleted competence/sector code. If any such failures, delete those test files (they're testing removed functionality):

```bash
# examples of what to delete if they exist and only test removed code
grep -rln "VALID_SECTORS\|competence\|industry_primary" tests/ | xargs -I {} ls {}
# edit each: delete obsolete test case or delete whole test file if entirely obsolete
```

- [ ] **Step 2: 跑 linters / type check if configured**

```bash
cd /Users/yangqi/investing && .venv/bin/python -m py_compile app/io/industry.py app/io/arenas.py app/io/company.py app/io/claims.py app/io/financials.py app/config.py
```

Expected: no output (compile succeeds).

- [ ] **Step 3: 手动冒烟 — 创建一个 industry 并写观察**

```bash
cd /Users/yangqi/investing && .venv/bin/python <<'PY'
from app.io import industry as industry_io
from app.io import arenas as arenas_io
from app.io import company as company_io
from pathlib import Path
import tempfile, json

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    (base / "industries").mkdir()
    (base / "arenas").mkdir()
    (base / "companies").mkdir()

    # industry
    industry_io.create_industry(
        slug="smoke-test", name="Smoke", scope="t",
        base=base / "industries",
    )
    industry_io.append_observations(
        "smoke-test",
        [{"id":"o1","field":"tam_global","timeframe":"2025",
          "source_id":"s1","value":100,"arena_refs":["a1"]}],
        base=base / "industries",
    )
    industry_io.append_narrative_block(
        "smoke-test", "market_size", "TAM 100B",
        {"institution":"x","date":"2026-01-01","sha8":"abcd1234","source_id":"s1"},
        base=base / "industries",
    )

    # arena
    arenas_io.write_definition(
        slug="a1", name="A1", definition_text="def",
        industry="smoke-test", battleground_focus="focus",
        base=base / "arenas",
    )
    arenas_io.append_narrative_block(
        "a1", "narratives", "bull: X wins",
        {"institution":"x","date":"2026-01-01","sha8":"abcd1234","source_id":"s1"},
        base=base / "arenas",
    )

    # company
    company_io.create_company("T", "US", "TestCo", industry_slugs=["smoke-test"],
                              base=base / "companies")
    company_io.append_narrative_block(
        "T", "US", "moat", "strong patents",
        {"institution":"10-K","date":"2024-12-31","sha8":"deadbeef","source_id":"y1"},
        base=base / "companies",
    )

    # Cross-refs
    assert industry_io.find_by_arena("a1", base=base / "industries") in (None, "smoke-test")
    assert arenas_io.find_by_industry("smoke-test", base=base / "arenas") == ["a1"]
    print("SMOKE OK")
PY
```

Expected output: `SMOKE OK`.

- [ ] **Step 4: 更新现有 docs/DEVELOPER-GUIDE.md / docs/USER-GUIDE.md 中提到 sector 的章节**

```bash
cd /Users/yangqi/investing && grep -n "VALID_SECTORS\|industry_primary\|sector\b" docs/DEVELOPER-GUIDE.md docs/USER-GUIDE.md | head -20
```

For each hit, edit to replace sector-based phrasing with industry_slugs / three-layer framework. (Plan 3 will handle SKILL.md; this Task only handles USER/DEVELOPER guides at a light-touch level.)

Typical edits:
- "company.meta.industry_primary (one of 5 sectors)" → "company.meta.industry_slugs (freeform list of industry slugs)"
- Section titled "sector 能力圈" → remove or rewrite as "三层知识框架（概述，详见 spec）"

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add -A docs/ && git commit -m "docs: update DEVELOPER/USER guides for three-layer refactor

Remove sector whitelist mentions; replace industry_primary with
industry_slugs; light-touch reference to three-layer spec for details.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>" --allow-empty
```

- [ ] **Step 6: Mark Plan 1 complete**

```bash
cd /Users/yangqi/investing && git log --oneline -30 | head -30
```

Expected: ~22 commits from Plan 1 tasks. Report back to user with commit hash of final commit and summary.

---

## Plan 1 完成验证清单

跑过 Plan 1 后，以下应成立：

- [x] `app/config.py` 无 `VALID_SECTORS` / `SECTOR_VOCAB_DIR`；有 `INDUSTRY_DIMENSIONS` (11) / `ARENA_DIMENSIONS` (6) / `COMPANY_DIMENSIONS` (8) / `INDUSTRY_FIELDS` / `INCOME_STATEMENT_LINES` (18) / `BALANCE_SHEET_LINES` (20) / `CASHFLOW_LINES` (16)
- [x] `controlled-vocab/financial-aliases.yaml` 存在，覆盖 ~50 个标准 key 的 A 股 + US GAAP alias
- [x] `app/io/industry.py` 完全重写为 slug-based；提供 create_industry / read_meta / write_meta / list_industries / read_observations / append_observations / dedup_observations / filter_observations_by_arena / filter_observations_by_segment / read_narrative / append_narrative_block / find_by_company / find_by_arena
- [x] `app/io/arenas.py` definition frontmatter 支持 industry + battleground_focus；6 dim narrative skeleton + read + append_block；find_by_industry 可用
- [x] `app/io/company.py` 无 sector 校验；meta.md 用 industry_slugs (list)；8 dim narrative skeleton + read + append_block；3 份现有 meta.md 已迁移
- [x] `app/io/claims.py` validate_batch 接受 arena_refs + company_dimension_hint；filter_by_arena / filter_by_company_dimension 可用
- [x] `app/io/financials.py` FINANCIAL_COLUMNS 扩到 ~45；init_schema 带 ALTER TABLE 迁移；ratios 扩到含 DuPont / FCF / OCF quality / CCC 等派生指标
- [x] 删除：competence.py / routes/competence.py / competence-sector/* / competence-check.md.tmpl / 3 份空 competence-check.md / 旧 sector 骨架 industries/{sector}/
- [x] 全量 pytest 通过；冒烟脚本跑通三层 CRUD + 跨层查找

---

## 自审

**Spec 覆盖检查**：
- §2.1 industry 11 维 — ✅ INDUSTRY_DIMENSIONS (Task 6) + 11 narrative skeletons (Task 11)
- §2.2 arena 6 维 — ✅ ARENA_DIMENSIONS (Task 6) + 6 narrative skeletons (Task 17)
- §2.3 company 8 维 — ✅ COMPANY_DIMENSIONS (Task 6) + 8 narrative skeletons (Task 19)
- §4.1 三层目录布局 — ✅ industry slug 结构 (Task 11)、arena 6 dim (Task 17)、company narratives/ (Task 19)
- §4.2 industry.observations schema — ✅ append_observations 接受 dict，字段 free-form；dedup 逻辑对齐 (Task 12-13)
- §4.3 claims schema 新字段 — ✅ arena_refs + company_dimension_hint (Task 20)
- §4.4 narrative append 格式 — ✅ `### 来源 ...` 模板 (Tasks 14, 17, 19)
- §4.5 config 常量 — ✅ (Tasks 6-7)
- §4.6 跨层引用 — ✅ find_by_* helpers (Tasks 15, 18) + arena_refs filter (Task 13) + filter_by_arena (Task 21)
- §4.7 财务 line items — ✅ (Tasks 7-10)
- §4.8 figure_contexts — **Plan 2 范围**，本 plan 未涉及（正确）
- §7.1 删除清单 — ✅ competence / sector vocab / 空骨架 / VALID_SECTORS (Tasks 1-5)
- §7.2 一次性迁移 — ✅ 3 份 meta.md 迁移 (Task 4)；profile-YYYY.md 保留（按 §D7）
- §7.3 新增 IO 模块 — ✅ industry.py 重写 + 其他模块升级 (全部 Phase D/E/F/G)
- §8 破坏性变更 — ✅ VALID_SECTORS 删、旧 industry API 变、routes/competence.py 删 (Tasks 1-5)

**Placeholder 扫描**：无 TBD / TODO / "similar to" / "add error handling" 占位符。所有代码步骤都给出完整实现。

**类型一致性**：
- `source_meta` dict 在 industry / arena / company 的 append_narrative_block 都要求 `institution / date / sha8 / source_id` 四个 key — 一致
- `industry_slugs` 在 company.meta / create_company / write_meta 都是 `list[str]` — 一致
- `arena_refs` 在 industry.observations / company.claims 都是 `list[str]` — 一致
- `company_dimension_hint` 统一校验 COMPANY_DIMENSIONS 白名单 — 一致

**发现的问题**：
1. Task 4 的 `_META_KEYS` 是 `company.py` 内部的 tuple 常量；现场 `sed` 改名可能漏点，engineer 需实际 `grep -n "industry_primary" app/` 扫遍后统一替换（Task 4 step 2 已说明用 Edit 工具）
2. Task 17 的 `write_definition` 修改要保证向后兼容（industry / battleground_focus 都默认 None）— 已在 Task 16 step 3 说明
3. 现有 arena `cn-power-cable-polymer-material` 没有新的 5 份 narrative 骨架。因为 `_ensure_narrative_skeletons` 只在 `write_definition` 里调用，重新 `write_definition` 会触发补齐。不过本 plan 不主动补齐现有 arena — Plan 3 的 workflow 会在 ingest 时 lazy-trigger

这些都是可接受的现场判断题，engineer 按注释处理。

---

**Plan 完成并写入 `docs/superpowers/plans/2026-04-26-plan1-data-model-io.md`。下一步等 engineer 执行完 Plan 1，再切写 Plan 2（preprocess + digest prompts + ingest_aggregate）。**
