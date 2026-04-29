# Plan 2: Ingest pipeline — preprocess + digest prompts + aggregate + figure_contexts + autobuild

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 ingest 流水线的三段——preprocess（PDF→结构化 sections + figure_contexts + financial line 抽取）/ digest 4 套 prompt 契约（LLM 调用走主 agent 对话，不走 Python）/ aggregate（把 digest JSON 分拣落到 Plan 1 的三层 IO 写入点）——落地到可跑、可单测、可对接 Plan 3 skill 的状态。新增 `figure_contexts`（§4.8，Plan 1 未实现的 §4 最后一块）的 IO + schema。实现 autobuild-meta / autobuild-industry-slug 两条 fallback 语义。所有 Python 脚本 **只做校验+写入+查询，不调 LLM API**。

**Architecture:**
- `scripts/preprocess_report.py` 扩 `--type industry`，新增 `detected_tickers` / `report_abstract` / `figure_contexts[]` / `financial_line_rows[]`（按 alias map 从 section 文本粗抽财务行）四个字段；其余既有逻辑保留
- `app/io/figure_contexts.py`（新）提供 figure_context 的 schema 常量 + append/read IO，把 §4.8 实现为和 `observations.jsonl` 对称的 per-industry jsonl；preprocess 直接写 `industries/{slug}/figure_contexts.jsonl`
- `.claude/skills/ingest/prompts/digest/{industry|annual|quarterly|sell-side}-digest.md`（4 份）——**prompt 文件本身**定义 digest subagent 的 input/output 契约；Python 不调用这些 prompt，主 agent 在 Plan 3 的 workflow 里 dispatch Explore subagent 时读这些 prompt
- `scripts/ingest_aggregate.py` 新增 triple-layer 分拣函数（`route_key_facts` / `write_industry_observations` / `write_industry_narrative` / `write_arena_narrative` / `write_company_narrative` / `ensure_industry_exists` / `ensure_company_exists` / `propose_arena_bootstrap`）。旧的 `aggregate` / `write_claims` / `write_financials` / cross-checks 保留（annual/quarterly/sell-side workflow 仍用）
- autobuild 语义落在 `ingest_aggregate` 的 `ensure_*` helper 里——被 digest 路由到一个不存在的公司/行业时，调 `company_io.create_company` / `industry_io.create_industry` 自动补齐，**不抛错**（用户审阅步骤在 Plan 3 的 workflow 里，本 plan 写一个"主 agent 应该在 Plan 3 里做"的显式注释）
- fix-forward 语义体现为：所有 preprocess 错误应映射到 template YAML / regex 行 / section_normalize 表的具体行；每个 preprocess 单测失败场景都指向"该改 template 的哪里"

**Tech Stack:** Python 3, pytest, pyyaml, pymupdf（已有依赖）。**不引入** openai / anthropic / litellm 等 LLM SDK。

**Spec reference:** `docs/superpowers/specs/2026-04-26-industry-ingest-design.md`（§4.8 figure_contexts、§5.1 统一 digest + 主 agent 分拣架构、§5.2–5.5 四类 workflow 的 preprocess/digest 角色）。

**Plan 1 依赖（已合并到 main）：**
- `app.config.INDUSTRY_DIMENSIONS` (11) / `ARENA_DIMENSIONS` (6) / `COMPANY_DIMENSIONS` (8) / `INDUSTRY_FIELDS` / `INCOME_STATEMENT_LINES` / `BALANCE_SHEET_LINES` / `CASHFLOW_LINES` / `FINANCIAL_ALIASES_PATH`
- `app.io.industry`：create_industry / read_meta / write_meta / read_observations / append_observations / dedup_observations / filter_observations_by_arena / filter_observations_by_segment / read_narrative / append_narrative_block / find_by_company / find_by_arena
- `app.io.arenas`：write_definition（含 industry / battleground_focus）/ read_narrative / append_narrative_block / find_by_industry
- `app.io.company`：create_company(industry_slugs=[...]) / read_meta_with_body / write_meta / read_narrative / append_narrative_block / list_sources / save_source_markdown
- `app.io.claims`：validate_batch（接受 arena_refs + company_dimension_hint）/ append_batch / filter_by_arena / filter_by_company_dimension
- `app.io.financials`：init_schema (45 列 ALTER) / load_alias_map / normalize_raw_key / recompute_ratios (DuPont/FCF/OCF/CCC)
- `controlled-vocab/financial-aliases.yaml`

Plan 2 **不改** Plan 1 的 IO 接口；只 **调用**。

---

## File Map

**Create (code):**
- `app/io/figure_contexts.py` — §4.8 IO：append/read per-industry jsonl
- `scripts/dispatch_digest.py`（可选辅助，见 Task 11）— 聚合 preprocess + digest prompts + 已知 arenas 列表为 **一份给主 agent 的 context bundle**；**不** 调 LLM
- `tests/test_figure_contexts_io.py`
- `tests/test_preprocess_figure_contexts.py`
- `tests/test_preprocess_industry_type.py`
- `tests/test_preprocess_financial_lines.py`
- `tests/test_ingest_aggregate_triple.py`
- `tests/test_ingest_aggregate_autobuild.py`
- `tests/test_digest_prompt_contracts.py` — 轻量 contract test：加载 4 份 prompt，校验 fences + 必含字段名

**Create (prompts):**
- `.claude/skills/ingest/prompts/digest/industry-digest.md`
- `.claude/skills/ingest/prompts/digest/annual-digest.md`
- `.claude/skills/ingest/prompts/digest/quarterly-digest.md`
- `.claude/skills/ingest/prompts/digest/sell-side-digest.md`
- `.claude/skills/ingest/prompts/digest/_common.md` — 三层维度清单 + key_facts schema 注入模板（4 份 digest 都 `!include`-style 引用，人工 copy 也 OK）

**Create (templates):**
- `.claude/skills/ingest/templates/a-share-industry.yaml` — 行业研报剔除规则 + section_detection
- `.claude/skills/ingest/templates/us-industry.yaml` — 对应美股

**Modify:**
- `scripts/preprocess_report.py` — 加 `industry` 型 template map、`detect_tickers()`、`extract_report_abstract()`、`extract_figure_contexts()`、`extract_financial_line_rows()`；output JSON 顶层扩 `detected_tickers` / `report_abstract` / `figure_contexts` / `financial_line_rows`；CLI 加 `--type industry`
- `scripts/ingest_aggregate.py` — 新增 triple-layer 分拣 + autobuild helpers；旧 `aggregate` / `write_claims` / `write_financials` 保留
- `.claude/skills/ingest/section-routing.yaml` — 加 `industry-generic` 通道（但实际 digest 不再按 section 分派；保留给 fallback）
- `.claude/skills/ingest/source-id-rules.yaml` — 加 `industry-research: "行研-{institution}-{date}-{sha8}"`

**Do not modify in this plan（Plan 3 scope）:**
- `.claude/skills/ingest/SKILL.md`
- `.claude/skills/ingest/workflows/*.md`
- 任何 `app/routes/*`（Plan 4）

---

## Phase A: figure_contexts IO + schema (TDD)

### Task 1: 添加 figure_contexts 路径常量 + schema 校验

**Files:**
- Modify: `/Users/yangqi/investing/app/config.py`
- Create: `/Users/yangqi/investing/app/io/figure_contexts.py`
- Create: `/Users/yangqi/investing/tests/test_figure_contexts_io.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_figure_contexts_io.py`:

```python
import json
from pathlib import Path
import pytest

from app.io import figure_contexts as fc_io
from app.io import industry as industry_io


def test_figure_context_schema_required_keys():
    assert set(fc_io.REQUIRED_KEYS) == {"id", "page", "caption", "surrounding_text", "section_name", "source_id"}


def test_append_write_read_roundtrip(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="s", base=base)
    rows = [
        {"id": "fig-001", "page": 3,
         "caption": "图表1: 2020-2030 全球 CMP 市场规模",
         "surrounding_text": "如图表1所示，2025 市场规模 33.8 亿美元，CAGR 9.0%",
         "section_name": "market_size",
         "source_id": "行研-国金证券-2026-03-10-abc12345"},
    ]
    n = fc_io.append_figure_contexts("x", rows, base=base)
    assert n == 1
    read = fc_io.read_figure_contexts("x", base=base)
    assert len(read) == 1
    assert read[0]["caption"].startswith("图表1")


def test_append_rejects_missing_required_key(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="", base=base)
    bad = [{"id": "f1", "page": 1}]  # missing caption etc.
    with pytest.raises(ValueError, match="missing"):
        fc_io.append_figure_contexts("x", bad, base=base)


def test_filter_by_source_id(tmp_path):
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="", base=base)
    fc_io.append_figure_contexts("x", [
        {"id": "a", "page": 1, "caption": "c1", "surrounding_text": "t",
         "section_name": "market_size", "source_id": "s1"},
        {"id": "b", "page": 2, "caption": "c2", "surrounding_text": "t",
         "section_name": "market_size", "source_id": "s2"},
    ], base=base)
    rows = fc_io.filter_by_source_id("x", "s1", base=base)
    assert {r["id"] for r in rows} == {"a"}
```

- [ ] **Step 2: Run — FAIL** (module missing)

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_figure_contexts_io.py -v 2>&1 | tail -15
```

- [ ] **Step 3: Create `app/io/figure_contexts.py`**

```python
"""figure_contexts IO (spec §4.8).

Per-industry JSONL of research-report figure captions + surrounding text.
Written by scripts.preprocess_report at ingest time; consumed by digest
prompts (main agent reads these and prioritizes extraction from captions).

Schema (one row per figure):
    {id, page, caption, surrounding_text, section_name, source_id}
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app import config as cfg

REQUIRED_KEYS = ("id", "page", "caption", "surrounding_text", "section_name", "source_id")


def _path(slug: str, base: Path | None) -> Path:
    root = base or cfg.INDUSTRIES_DIR
    return root / slug / "figure_contexts.jsonl"


def read_figure_contexts(slug: str, base: Path | None = None) -> list[dict]:
    path = _path(slug, base)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _validate(row: dict) -> None:
    for k in REQUIRED_KEYS:
        if k not in row:
            raise ValueError(f"figure_context row missing required key: {k}")


def append_figure_contexts(
    slug: str, rows: Iterable[dict], base: Path | None = None
) -> int:
    path = _path(slug, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    for r in rows:
        _validate(r)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def filter_by_source_id(slug: str, source_id: str, base: Path | None = None) -> list[dict]:
    return [r for r in read_figure_contexts(slug, base=base) if r.get("source_id") == source_id]


def filter_by_section(slug: str, section_name: str, base: Path | None = None) -> list[dict]:
    return [r for r in read_figure_contexts(slug, base=base) if r.get("section_name") == section_name]
```

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_figure_contexts_io.py -v 2>&1 | tail -15
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add app/io/figure_contexts.py tests/test_figure_contexts_io.py && git commit -m "feat(figure_contexts): add per-industry figure_contexts.jsonl IO

Spec §4.8. Stores caption + surrounding text excerpts extracted from
research-report figures; consumed by digest prompts to prioritize
quantitative data hiding inside figure captions (which pure-text PDF
extraction loses).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase B: preprocess 扩展 (TDD)

### Task 2: 新增 industry template (a-share + us)

**Files:**
- Create: `/Users/yangqi/investing/.claude/skills/ingest/templates/a-share-industry.yaml`
- Create: `/Users/yangqi/investing/.claude/skills/ingest/templates/us-industry.yaml`

- [ ] **Step 1: 参考已有 template 结构**

```bash
cd /Users/yangqi/investing && cat .claude/skills/ingest/templates/sell-side-generic.yaml
```

观察字段：`form` / `form_detection` / `section_detection.patterns` / `section_normalize` / `skip_rules` / `institution_extraction` / `publish_date_extraction` / `_section_fallback`。

- [ ] **Step 2: Write `a-share-industry.yaml`**

```yaml
form: industry-research-a-share

# 行业研报特点：封面含"行业深度报告"/"行业研究"/"行业点评"等关键词；
# 不含"Form 10-K"等公司年报术语。
form_detection:
  positive:
    - 行业深度
    - 行业研究
    - 行业点评
    - 行业专题
    - 产业链深度
    - Sector\s+Report
    - Industry\s+Report
  negative:
    - Form\s+10-K
    - 年度报告全文
    - 10-Q

# 章节检测：行业研报章节极自由（"市场空间"/"竞争格局"/"技术演进"等），
# 没有 A 股年报那种"第一节/第二节"固定骨架。用中文冒号/括号/加粗前缀作弱匹配。
section_detection:
  patterns:
    - '^[一二三四五六七八九十][、.．]\s*(.+)$'          # 一、市场空间
    - '^\d+[、.．]\s*(.+)$'                              # 1、市场空间
    - '^\d+\.\d+\s+(.+)$'                                # 1.1 市场空间
    - '^##\s+(.+)$'                                      # markdown H2

# 未在此表里的标题归 UNKNOWN_N（preprocess 保留原文，留给 digest subagent 作上下文）
section_normalize:
  市场空间: market_size
  市场规模: market_size
  行业空间: market_size
  TAM: market_size
  行业格局: competition
  竞争格局: competition
  产业链: value_chain
  产业链分析: value_chain
  技术演进: technology
  技术趋势: technology
  政策环境: regulation
  政策梳理: regulation
  风险提示: risks
  投资建议: valuation
  估值: valuation
  生命周期: lifecycle
  驱动因素: drivers
  增长驱动: drivers

# 行业研报无"正文标题自由"问题 —— UNKNOWN 章节不降级到某通道，保持 UNKNOWN
_section_fallback: null

skip_rules:
  sections:
    - HEADER          # 封面
    - disclaimer      # 免责声明
    - analyst_bio     # 分析师介绍
    - rating_definition

institution_extraction:
  patterns:
    - '(国金证券|中信证券|中信建投|中金公司|华泰证券|国泰君安|招商证券|广发证券|海通证券|光大证券|东吴证券|申万宏源|东方证券|国信证券|兴业证券|天风证券|平安证券|中泰证券|浙商证券)'

publish_date_extraction:
  patterns:
    - '(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'
    - '(\d{4})-(\d{1,2})-(\d{1,2})'
    - '(\d{4})/(\d{1,2})/(\d{1,2})'
```

- [ ] **Step 3: Write `us-industry.yaml`**

```yaml
form: industry-research-us

form_detection:
  positive:
    - Industry\s+(Report|Outlook|Primer|Deep\s+Dive)
    - Sector\s+(Report|Outlook|Primer)
    - Market\s+Outlook
    - Thematic\s+Report
  negative:
    - Form\s+10-K
    - Form\s+10-Q

section_detection:
  patterns:
    - '^\d+[\.)]\s+(.+)$'
    - '^##\s+(.+)$'

section_normalize:
  Market\ Size: market_size
  TAM: market_size
  Competitive\ Landscape: competition
  Value\ Chain: value_chain
  Technology: technology
  Regulation: regulation
  Risk\ Factors: risks
  Valuation: valuation
  Lifecycle: lifecycle
  Growth\ Drivers: drivers

_section_fallback: null

skip_rules:
  sections:
    - HEADER
    - disclaimer
    - analyst_bio
    - rating_definition

institution_extraction:
  patterns:
    - '(Goldman\s+Sachs|Morgan\s+Stanley|JPMorgan|J\.P\.\s+Morgan|Credit\s+Suisse|UBS|Barclays|Citi|Citigroup|Deutsche\s+Bank|HSBC|BofA|Bank\s+of\s+America|Jefferies|Evercore|Wells\s+Fargo|Baird|Cowen|Piper\s+Sandler)'

publish_date_extraction:
  patterns:
    - '(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})'
    - '(\d{4})-(\d{1,2})-(\d{1,2})'
```

- [ ] **Step 4: 冒烟**

```bash
cd /Users/yangqi/investing && .venv/bin/python -c "import yaml; \
  print(yaml.safe_load(open('.claude/skills/ingest/templates/a-share-industry.yaml')).get('form')); \
  print(yaml.safe_load(open('.claude/skills/ingest/templates/us-industry.yaml')).get('form'))"
```

Expected: `industry-research-a-share` / `industry-research-us`.

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add .claude/skills/ingest/templates/ && git commit -m "feat(ingest): add industry-research templates (a-share + us)

Section detection + section_normalize + institution/date extraction
rules for 行业研报 / sector reports (spec §5.2).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: preprocess `--type industry` 分支

**Files:**
- Modify: `/Users/yangqi/investing/scripts/preprocess_report.py`
- Create: `/Users/yangqi/investing/tests/test_preprocess_industry_type.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_preprocess_industry_type.py`:

```python
from pathlib import Path
import json
import pytest

from scripts import preprocess_report as pre


def test_template_map_includes_industry():
    assert ("a-share", "industry") in pre.TEMPLATE_MAP
    assert ("us", "industry") in pre.TEMPLATE_MAP


def test_load_template_industry(tmp_path):
    t = pre.load_template("a-share", "industry")
    assert t["form"] == "industry-research-a-share"


def test_cli_accepts_industry_type(tmp_path, monkeypatch, capsys):
    # Prepare a minimal md report file so the CLI path runs end-to-end.
    report = tmp_path / "sample.md"
    report.write_text(
        "国金证券\n2026 年 3 月 10 日\n\n# 中国 CMP 抛光材料行业深度\n\n"
        "一、市场空间\n\n2025 年市场规模约 33.8 亿美元。\n\n"
        "二、竞争格局\n\n龙头 Dupont 市占 75%。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    rc = pre.main([str(report), "--type", "industry", "--market", "a-share", "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["meta"]["cli_type"] == "industry"
    # market_size and competition sections should be normalized
    names = [s["name"] for s in data["sections"]]
    assert "market_size" in names
    assert "competition" in names
```

- [ ] **Step 2: Run — FAIL** (TEMPLATE_MAP has no industry key)

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_industry_type.py -v 2>&1 | tail -20
```

- [ ] **Step 3: Edit `scripts/preprocess_report.py`**

- 扩 `TEMPLATE_MAP`：

```python
TEMPLATE_MAP = {
    ("a-share", "annual"):    "a-share-annual.yaml",
    ("a-share", "quarterly"): "a-share-quarterly.yaml",
    ("a-share", "sell-side"): "sell-side-generic.yaml",
    ("a-share", "industry"):  "a-share-industry.yaml",   # NEW
    ("us", "annual"):         "us-10k.yaml",
    ("us", "quarterly"):      "us-10q.yaml",
    ("us", "sell-side"):      "sell-side-generic.yaml",
    ("us", "industry"):       "us-industry.yaml",        # NEW
}
```

- argparse `--type` choices：加 `"industry"`：

```python
ap.add_argument("--type", required=True, choices=["annual", "quarterly", "sell-side", "industry"])
```

- [ ] **Step 4: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_industry_type.py -v 2>&1 | tail -15
```

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add scripts/preprocess_report.py tests/test_preprocess_industry_type.py && git commit -m "feat(preprocess): add --type industry branch

Routes to a-share-industry.yaml / us-industry.yaml templates. section_normalize
maps 一、市场空间 → market_size etc. so downstream aggregator can address
industry dimensions by name. Fourth report class per spec §5.2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `extract_figure_contexts` — 抽 caption + 前后 2 段 (TDD)

**Files:**
- Modify: `/Users/yangqi/investing/scripts/preprocess_report.py`
- Create: `/Users/yangqi/investing/tests/test_preprocess_figure_contexts.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_preprocess_figure_contexts.py`:

```python
from pathlib import Path
import pytest

from scripts import preprocess_report as pre


SAMPLE = """
一、市场空间

CMP 抛光材料是半导体制造关键耗材。

图表1: 2020-2030 全球 CMP 抛光材料市场规模（亿美元）
数据来源：华经产业研究院

如图表1所示，2025 年市场规模 33.8 亿美元，CAGR 9.0%。

二、竞争格局

Figure 2. Global CMP slurry market share, 2024
Source: Market Growth Reports

Dupont holds 75% of the pad market. The top 6 vendors account for 85%.

表 3：CMP 抛光液成本结构
磨料占 54.6%，化学添加剂占 20.1%。
"""


def test_extract_figure_contexts_matches_chinese_and_english():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE.split("二、竞争格局")[0], "order": 1},
        {"name": "competition", "text": "二、竞争格局" + SAMPLE.split("二、竞争格局")[1], "order": 2},
    ])
    captions = [c["caption"] for c in contexts]
    assert any("图表1" in c for c in captions)
    assert any(c.startswith("Figure 2") for c in captions)
    assert any("表 3" in c for c in captions)


def test_figure_context_has_required_fields():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE, "order": 1}
    ])
    for c in contexts:
        for key in ("id", "page", "caption", "surrounding_text", "section_name"):
            assert key in c


def test_surrounding_text_includes_context_around_caption():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE, "order": 1}
    ])
    fig1 = [c for c in contexts if "图表1" in c["caption"]][0]
    # surrounding_text should pull in the "CAGR 9.0%" line downstream
    assert "33.8" in fig1["surrounding_text"] or "CAGR" in fig1["surrounding_text"]


def test_section_name_attribution():
    contexts = pre.extract_figure_contexts(SAMPLE, sections=[
        {"name": "market_size", "text": SAMPLE.split("二、竞争格局")[0], "order": 1},
        {"name": "competition", "text": "二、竞争格局" + SAMPLE.split("二、竞争格局")[1], "order": 2},
    ])
    fig_cn_1 = [c for c in contexts if "图表1" in c["caption"]][0]
    assert fig_cn_1["section_name"] == "market_size"
    fig_en_2 = [c for c in contexts if c["caption"].startswith("Figure 2")][0]
    assert fig_en_2["section_name"] == "competition"
```

- [ ] **Step 2: Run — FAIL** (`extract_figure_contexts` missing)

- [ ] **Step 3: Implement `extract_figure_contexts()` in `scripts/preprocess_report.py`**

```python
# --- figure_contexts (spec §4.8) ---------------------------------------------

_FIGURE_CAPTION_PATTERNS = [
    re.compile(r"^(图表?\s*\d+[:：].{0,120})$", re.MULTILINE),
    re.compile(r"^(表\s*\d+[:：].{0,120})$", re.MULTILINE),
    re.compile(r"^((?:Exhibit|Figure|Chart|Table)\s+\d+[:\.]\s.{0,200})$",
               re.MULTILINE | re.IGNORECASE),
]


def _paragraphs(text: str) -> list[str]:
    # Split on blank lines; strip; drop empties.
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def extract_figure_contexts(
    full_text: str,
    sections: list[dict],
) -> list[dict]:
    """Scan each section body for figure/table captions; for each caption emit
    a context row with the 2 paragraphs before + 2 paragraphs after as
    surrounding_text. No LLM — pure regex + paragraph slicing.
    """
    out: list[dict] = []
    fig_counter = 0
    for sec in sections:
        sec_text = sec.get("text", "")
        if not sec_text:
            continue
        paras = _paragraphs(sec_text)
        for p_idx, para in enumerate(paras):
            for pat in _FIGURE_CAPTION_PATTERNS:
                m = pat.match(para) or pat.search(para)
                if not m:
                    continue
                caption = m.group(1).strip()
                # Surrounding: up to 2 paragraphs before and 2 after (skipping
                # the caption paragraph itself).
                before = paras[max(0, p_idx - 2): p_idx]
                after = paras[p_idx + 1: p_idx + 3]
                surrounding = "\n\n".join(before + after).strip()
                fig_counter += 1
                out.append({
                    "id": f"fig-{fig_counter:03d}",
                    "page": None,  # page tracking not yet wired; TODO in v2
                    "caption": caption,
                    "surrounding_text": surrounding,
                    "section_name": sec.get("name", "UNKNOWN"),
                })
                break  # next paragraph
    return out
```

- [ ] **Step 4: Plumb into `build_result`**

In `build_result(...)`, before return, add:

```python
    fig_contexts = extract_figure_contexts(text_full, sections)
    result = {
        "meta": {...},
        "sections": out_sections,
        "figure_contexts": fig_contexts,
    }
    return result
```

- [ ] **Step 5: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_figure_contexts.py -v 2>&1 | tail -15
```

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add scripts/preprocess_report.py tests/test_preprocess_figure_contexts.py && git commit -m "feat(preprocess): extract figure captions + surrounding text (§4.8)

Scans 图表N: / 表N: / Figure/Chart/Exhibit/Table N: patterns per section.
For each match, emits {id, caption, surrounding_text, section_name} with
2 paragraphs before + 2 after. Zero-cost prep so digest prompts can
prioritize data hiding inside figures (PDF text extraction loses the
figures themselves).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: `detect_tickers` + `extract_report_abstract` (TDD)

**Files:**
- Modify: `/Users/yangqi/investing/scripts/preprocess_report.py`
- Create: `/Users/yangqi/investing/tests/test_preprocess_industry_extras.py`

- [ ] **Step 1: Write failing test**

```python
from scripts import preprocess_report as pre


_SAMPLE_TEXT = """
中国 CMP 抛光材料行业深度
国金证券 2026-03-10

摘要：CMP 抛光材料是半导体制造环节不可或缺的消耗品。全球 2025 年市场规模
33.8 亿美元，CAGR 9%。国产替代是主线，安集(SSE 688019)、鼎龙(SZ 300054)
为代表性玩家。

...

安集科技 (SSE:688019) 专注 CMP 抛光液，当前市占 ... 鼎龙股份 (SZ:300054)
CMP pad 后起之秀 ... 上海新阳 603659 也有布局。

茅台 600519 作为对照（非 CMP）。
"""


def test_detect_tickers_a_share():
    tickers = pre.detect_tickers(_SAMPLE_TEXT)
    got = {(t["market"], t["ticker"]) for t in tickers}
    assert ("SSE", "688019") in got
    assert ("SZSE", "300054") in got  # 300XXX → SZSE
    assert ("SSE", "603659") in got
    # we don't require it to include 茅台 since it appears without explicit market prefix


def test_detect_tickers_us_pattern():
    text = "We like Apple (NASDAQ:AAPL) and Microsoft (NYSE: MSFT) in this cycle."
    tickers = pre.detect_tickers(text)
    got = {(t["market"], t["ticker"]) for t in tickers}
    assert ("US", "AAPL") in got
    assert ("US", "MSFT") in got


def test_detect_tickers_unique():
    text = "安集 688019 出现多次 ... 688019 又一次 ... 688019"
    tickers = pre.detect_tickers(text)
    ids = [t["ticker"] for t in tickers]
    assert ids.count("688019") == 1


def test_extract_report_abstract_takes_leading_paragraph():
    abstract = pre.extract_report_abstract(_SAMPLE_TEXT, max_chars=200)
    assert "摘要" in abstract or "CMP" in abstract
    assert len(abstract) <= 200
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement in `scripts/preprocess_report.py`**

```python
# --- detect_tickers ----------------------------------------------------------

# A-share 6-digit code mapping to exchange (prefix rules):
#   6*     -> SSE   (上海主板/科创板)
#   000*/001*/002*/003* -> SZSE (深交所主板/中小板/创业板 3XX)
#   300*/301* -> SZSE (创业板)
#   8* (6-digit)/9*  -> BSE
# We keep it simple: first-char rules.
_A_SHARE_CODE_RE = re.compile(r"(?<!\d)([036][0-9]{5}|8[0-9]{5}|9[0-9]{5})(?!\d)")
_US_TICKER_RE = re.compile(
    r"\b(?:NYSE|NASDAQ|NASDAQ:NYSE)\s*:?\s*([A-Z]{1,5})\b"
)


def _classify_a_share(code: str) -> str:
    if code.startswith("6"):
        return "SSE"
    if code.startswith(("0", "3")):
        return "SZSE"
    if code.startswith(("8", "9")):
        return "BSE"
    return "SSE"


def detect_tickers(text: str) -> list[dict]:
    """Scan for plausible A-share 6-digit codes + US NYSE/NASDAQ: tickers.
    Returns a de-duplicated list of {market, ticker} rows, in first-seen order.
    """
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []
    for m in _A_SHARE_CODE_RE.finditer(text):
        code = m.group(1)
        market = _classify_a_share(code)
        key = (market, code)
        if key not in seen:
            seen.add(key)
            out.append({"market": market, "ticker": code})
    for m in _US_TICKER_RE.finditer(text):
        sym = m.group(1).upper()
        key = ("US", sym)
        if key not in seen:
            seen.add(key)
            out.append({"market": "US", "ticker": sym})
    return out


# --- extract_report_abstract -------------------------------------------------

def extract_report_abstract(text: str, max_chars: int = 500) -> str | None:
    """Pull the leading 200-500 chars as an abstract. Skip obvious header
    boilerplate (institution name, date line). Stop on first section heading.
    """
    # Trim to first section start (one of our common heading patterns).
    head = text[:3000]
    # Find first "一、" or "1、" or "##" or "PART I" style heading:
    stop_re = re.compile(r"(?m)^(?:[一二三四五六七八九十]、|\d+[、.．]|##\s+|PART\s+I)")
    m = stop_re.search(head)
    body = head[: m.start()] if m else head
    # Collapse blank lines.
    body = re.sub(r"\n{2,}", "\n", body).strip()
    if not body:
        return None
    return body[:max_chars]
```

- [ ] **Step 4: Plumb into `build_result`**

```python
    result = {
        "meta": {...},
        "sections": out_sections,
        "figure_contexts": fig_contexts,
        "detected_tickers": detect_tickers(text_full),
        "report_abstract": extract_report_abstract(text_full),
    }
```

- [ ] **Step 5: Run — PASS + existing preprocess tests regression**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_industry_extras.py tests/test_preprocess_industry_type.py tests/test_preprocess_figure_contexts.py -v 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add scripts/preprocess_report.py tests/test_preprocess_industry_extras.py && git commit -m "feat(preprocess): detect_tickers + extract_report_abstract

detect_tickers: A-share 6-digit code → SSE/SZSE/BSE by prefix; US 'NYSE:'
/ 'NASDAQ:' tagged symbols. extract_report_abstract pulls leading text
until the first section heading (Chinese 一、 / 1、, ASCII PART I, MD ##).
Preprocess JSON now exposes both so §5.2 industry workflow can confirm
industry_slug + preview proposed arenas before dispatching digest.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `extract_financial_line_rows` — 用 alias map 从 annual/quarterly section 粗抽 (TDD)

**Files:**
- Modify: `/Users/yangqi/investing/scripts/preprocess_report.py`
- Create: `/Users/yangqi/investing/tests/test_preprocess_financial_lines.py`

**设计：** 不是做严格三表解析（那属于 LLM 判断 → 主 agent 做），而是**粗抽候选行**。对每一行文本，若首列命中 financial-aliases.yaml 的某个 a_share/us_gaap alias，且行内含至少一个数字，就吐一个 `{raw_label, standard_key, numeric_candidates: [...], line}` candidate。主 agent 读这个 candidate 列表 + 原文上下文决定填哪一列。

- [ ] **Step 1: Write failing test**

```python
from scripts import preprocess_report as pre


def test_extract_financial_line_rows_a_share():
    text = """
    项目                     2025/12/31       2024/12/31
    营业收入               168,838,102.55   147,693,382.69
    营业成本                 59,831,212.11    52,004,113.45
    研发费用                  1,243,567.89     1,134,812.00
    归属于母公司股东的净利润  85,219,487.33    74,734,102.54
    """
    rows = pre.extract_financial_line_rows(text, market="SSE")
    keys = {r["standard_key"] for r in rows}
    assert "revenue" in keys
    assert "cost_of_revenue" in keys
    assert "rd_expense" in keys
    assert "net_income_to_parent" in keys


def test_extract_financial_line_rows_us():
    text = """
    Consolidated Statements of Operations
    (in thousands)                                    2024            2023
    Revenue                                        1,477,056         872,053
    Cost of revenue                                   268,291         169,400
    Research and development                           38,504          27,432
    Net income                                        126,221           5,558
    """
    rows = pre.extract_financial_line_rows(text, market="US")
    keys = {r["standard_key"] for r in rows}
    assert "revenue" in keys
    assert "cost_of_revenue" in keys
    assert "rd_expense" in keys
    assert "net_income" in keys


def test_extract_financial_line_rows_numeric_candidates():
    text = "营业收入  168,838,102.55   147,693,382.69"
    rows = pre.extract_financial_line_rows(text, market="SSE")
    assert len(rows) == 1
    # Candidates should hold BOTH year columns (caller picks fiscal_year)
    assert len(rows[0]["numeric_candidates"]) == 2
    assert 168838102.55 in rows[0]["numeric_candidates"]


def test_extract_financial_line_rows_unknown_label_skipped():
    text = "不存在的科目名  100   200"
    rows = pre.extract_financial_line_rows(text, market="SSE")
    assert rows == []
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement in `scripts/preprocess_report.py`**

```python
# --- extract_financial_line_rows ---------------------------------------------

_NUMERIC_RE = re.compile(r"-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?")


def extract_financial_line_rows(text: str, market: str) -> list[dict]:
    """Scan financial statement text line by line. If the first token(s) match
    an alias in FINANCIAL_ALIASES, emit a candidate row.

    Output row shape:
      {raw_label, standard_key, numeric_candidates: [float,...], line}

    The caller (main agent / digest) decides which candidate (which column,
    e.g. current-year vs prior-year) actually populates the financials row
    — we don't guess here.
    """
    # Lazy import to avoid pulling app.io.financials at module load time
    # (preprocess is meant to run stand-alone without heavy deps).
    from app.io import financials as fin_io

    alias_map = fin_io.load_alias_map()
    lang_key = "us_gaap" if market == "US" else "a_share"

    # Flatten alias list -> standard_key, sorted longest-first so "营业总收入"
    # wins over "营业收入" when it appears literally in a line.
    flat: list[tuple[str, str]] = []
    for std_key, langs in alias_map.items():
        for alias in (langs or {}).get(lang_key, []) or []:
            flat.append((alias.strip(), std_key))
    flat.sort(key=lambda p: len(p[0]), reverse=True)

    rows: list[dict] = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or len(stripped) > 300:
            continue
        # Must contain at least one number to be a candidate.
        nums = _NUMERIC_RE.findall(stripped)
        if not nums:
            continue
        for alias, std_key in flat:
            # Anchored: alias must appear at the START of the line (allowing
            # optional leading item numbering like "1.", "一、").
            prefix_re = re.compile(
                r"^\s*(?:[一二三四五六七八九十]、|\d+[、.．]|\d+\))?\s*" + re.escape(alias)
            )
            if not prefix_re.match(stripped):
                continue
            numeric_candidates = [float(n.replace(",", "")) for n in nums]
            rows.append({
                "raw_label": alias,
                "standard_key": std_key,
                "numeric_candidates": numeric_candidates,
                "line": stripped,
            })
            break
    return rows
```

- [ ] **Step 4: Plumb into `build_result`（only for annual/quarterly type）**

Inside `build_result`:

```python
    fin_rows: list[dict] = []
    if form_cli in ("annual", "quarterly"):
        market_norm = "US" if market == "us" else ("SSE" if market == "a-share" else market)
        for s in sections:
            if s.get("name") in (
                "财务报告", "主要财务数据", "季度财务报表",
                "Item_8_Financial_Statements",
                "Part_I_Item_1_Financial_Statements",
            ):
                fin_rows.extend(extract_financial_line_rows(s["text"], market=market_norm))

    result = {
        "meta": {...},
        "sections": out_sections,
        "figure_contexts": fig_contexts,
        "detected_tickers": detect_tickers(text_full),
        "report_abstract": extract_report_abstract(text_full),
        "financial_line_rows": fin_rows,
    }
```

- [ ] **Step 5: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_preprocess_financial_lines.py -v 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```bash
cd /Users/yangqi/investing && git add scripts/preprocess_report.py tests/test_preprocess_financial_lines.py && git commit -m "feat(preprocess): extract financial line candidates via alias map

For annual/quarterly PDFs, scan each financial-statement section line-by-line.
If the line prefix matches an a_share or us_gaap alias from
controlled-vocab/financial-aliases.yaml, emit a candidate row with the
standard_key + all numbers in the line. Main agent later picks which
candidate populates which fiscal period — preprocess never guesses.

This gives the digest prompt a structured jumping-off point instead of
raw text for financial tables, while keeping LLM judgment in-conversation.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: preprocess integration test — full output JSON shape

**Files:**
- Append: `/Users/yangqi/investing/tests/test_preprocess_industry_type.py`

- [ ] **Step 1: Append test**

```python
def test_preprocess_industry_full_output_shape(tmp_path):
    report = tmp_path / "r.md"
    report.write_text(
        "国金证券\n2026 年 3 月 10 日\n\n"
        "摘要：中国 CMP 抛光材料行业深度。2025 年全球市场 33.8 亿美元。"
        "代表公司 安集(SSE 688019) / 鼎龙(SZ 300054)。\n\n"
        "一、市场空间\n\n"
        "图表1: 全球市场规模\n如图表1所示，2025 年市场规模 33.8 亿美元。\n\n"
        "二、竞争格局\n\nDupont 市占 75%。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    rc = pre.main([str(report), "--type", "industry", "--market", "a-share", "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))

    # Required top-level keys
    for key in ("meta", "sections", "figure_contexts", "detected_tickers", "report_abstract"):
        assert key in data, f"missing top-level key: {key}"
    # industry type should NOT populate financial_line_rows
    assert data.get("financial_line_rows", []) == []

    # detected tickers
    markets = {t["market"] for t in data["detected_tickers"]}
    assert "SSE" in markets

    # figure_contexts present with at least 1 figure
    assert len(data["figure_contexts"]) >= 1
    fig = data["figure_contexts"][0]
    assert "caption" in fig
    assert "surrounding_text" in fig
    assert "section_name" in fig

    # report_abstract non-empty
    assert data["report_abstract"]
```

- [ ] **Step 2: Run — PASS**

- [ ] **Step 3: Commit**

```bash
cd /Users/yangqi/investing && git add tests/test_preprocess_industry_type.py && git commit -m "test(preprocess): integration test for industry-type full JSON shape

Asserts top-level keys (meta / sections / figure_contexts /
detected_tickers / report_abstract), industry type does NOT populate
financial_line_rows, and ticker/figure extraction round-trips through
the CLI entrypoint.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase C: Digest prompt 契约 (非 TDD — prompt 是文本契约，测试为 contract 校验)

### Task 8: `_common.md` digest 共享上下文段

**Files:**
- Create: `/Users/yangqi/investing/.claude/skills/ingest/prompts/digest/_common.md`

- [ ] **Step 1: Write prompt**

```markdown
# Digest subagent 通用指令（4 份 digest prompt 的共享前置段）

你是"三层知识系统"的 **digest-extract** subagent。你在一次对话里**读完整份报告**（而不是单个 section），产出一份**结构化 JSON 摘要**供主 agent 分拣到 industry / arena / company 三层。

## 角色分工（硬边界）

1. **你** 只做**机械抽取**：读文本、识别事实、给出路由提示（target_layer / dimension_hint / arena_refs）。
2. **你不做** 语义归属的最终决策（归谁、写不写、冲突哪条赢）——这是**主 agent** 的工作。
3. **你不写文件**、**不做跨报告聚合**、**不调工具**；只读 prompt 里给你的文本，吐 JSON。

## 输入（主 agent 在你的 prompt 里会提供）

```
file_meta:
  source_id: <如 行研-国金证券-2026-03-10-abc12345>
  institution: <如 国金证券>
  publish_date: <YYYY-MM-DD>
  sha8: <8-char hex>

full_text: |
  <整份报告的正文；preprocess 已去封面/目录/免责>

figure_contexts:
  - id: fig-001
    caption: "图表1: ..."
    surrounding_text: "..."
    section_name: market_size
  - ...

detected_tickers:
  - {market: SSE, ticker: 688019}
  - ...

known_arenas:                       # 主 agent 预加载，仅相关 industry 的
  - slug: cn-cmp-slurry-domestic-substitution
    battleground_focus: 国产 CMP 抛光液挑战海外龙头
    participants: [安集, Dupont, Cabot]
    industry: cn-cmp-material
  - ...

industry_context:                    # 若报告能锚定到某一 industry slug
  slug: cn-cmp-material
  name: 中国化学机械抛光材料

company_context:                     # annual/quarterly/sell-side 才有
  ticker: 688019
  market: SSE
  name: 安集科技
  industry_slugs: [cn-cmp-material]
  arenas: [cn-cmp-slurry-domestic-substitution]

dimension_ref:
  industry: [definition, market_size, lifecycle, value_chain, competition,
             drivers, technology, regulation, benchmark, risks, valuation]
  arena:    [definition, participants, decisive_factors, trajectory,
             narratives, investment_view]
  company:  [business_model, moat, growth_engine, management,
             financial_profile, catalysts, risks, valuation]

industry_fields_hint:                # 建议用的 structured fields
  market_size:  [tam_global, tam_china, tam_by_segment, cagr_global, cagr_china]
  lifecycle:    [stage, stage_evidence]
  competition:  [hhi, cr5, cr10, share_by_player, porter_*]
  benchmark:    [gross_margin_leader, gross_margin_avg, capex_intensity_avg, rd_ratio_leader]
  valuation:    [pe_ttm_median, pb_median, ev_ebitda_median]

subjects_whitelist: [list]           # annual/quarterly/sell-side 才注入
```

## 产出 JSON schema（严格；top-level keys 必须齐全）

```json
{
  "key_facts": [
    {
      "idx": 1,
      "fact_text": "≤80 字；含具体数字和单位",
      "evidence_quote": "原文直引 ≤200 字",
      "target_layer": "industry|arena|company|cross",
      "target_refs": {
        "industry_slug": "cn-cmp-material",
        "arena_slug": null,
        "ticker": null,
        "market": null
      },
      "dimension_hint": "market_size",
      "field_hint": "tam_global",
      "value_numeric": 33.8,
      "unit": "usd_bn",
      "timeframe": "2025",
      "time_type": "actual",
      "metric_type": "atomic",
      "segment": null,
      "arena_refs": [],
      "subject_tag_hint": null,
      "company_dimension_hint": null,
      "confidence": "high"
    }
  ],
  "narratives": {
    "industry": {"market_size": "≤300 字浓缩；必要时 quote 原文"},
    "arena":    {"cn-cmp-slurry-domestic-substitution": {"participants": "..."}},
    "company":  {"SSE_688019": {"moat": "..."}}
  },
  "proposed_arenas": [
    {
      "tentative_slug": "cn-cmp-slurry-domestic-substitution",
      "battleground_focus": "国产 CMP 抛光液厂商挑战 Dupont/Cabot 等海外龙头",
      "tentative_participants": [
        {"name": "安集", "role": "challenger"},
        {"name": "Dupont", "role": "incumbent"}
      ],
      "parent_industry_slug": "cn-cmp-material",
      "evidence_quote": "..."
    }
  ],
  "flags": [
    "数字 X 和上下文 Y 对不上，疑似单位错",
    "图表3 的 caption 提了 '市占 35%'，但正文未见"
  ]
}
```

## 铁律

1. **只返回严格 JSON**。第一个字符 `{`，最后一个字符 `}`。不加 ` ```json ` 代码块。
2. **所有事实必须含 `evidence_quote`**。无原文直引即非事实，抛弃。
3. **`target_layer` 4 个值**：
   - `industry` — 行业客观事实（TAM、技术、政策、生命周期、产业链）
   - `arena` — 博弈叙事（多空观点、参与者相对位置、演进轨迹、投资启示）
   - `company` — 单公司属性（业务、护城河、管理层、单公司财务、单公司事件）
   - `cross` — 跨层事实（某公司的市占率既是 company 事实也是 industry competition.share_by_player 事实）
4. **`dimension_hint` 必须在 `dimension_ref[target_layer]` 闭集内**，写错整条被丢弃。
5. **`arena_refs`**：若事实与某场博弈直接相关（参与者/规则/演进）→ 填 [slug, ...]；否则空。
6. **`field_hint`**：仅当 `target_layer=industry` 且 fact 是 atomic 数值时填；用 `industry_fields_hint[dimension_hint]` 里的建议 key。无合适时省略。
7. **figure_contexts 优先级**：caption + surrounding_text 中出现的 TAM / share / CAGR 必须抽成 atomic observation（研报核心数据常在图表里）。
8. **proposed_arenas**：仅当报告明确讨论了**一个**或**多个 known_arenas 之外的博弈焦点**时才填。没发现新博弈 → 空 list；不要硬凑。
9. **narratives**：按维度写浓缩段（≤300 字），不是抄原文。每个 dim 一段，缺失维度不列 key（空段**不要**填进来）。
10. **subject_tag_hint / company_dimension_hint 仅当 target_layer=company**；值必须在 subjects_whitelist / COMPANY_DIMENSIONS 内。

## 输出前自查

- [ ] JSON 能 `json.loads` 解析（工具会校验；不能解析整批被主 agent 拒）
- [ ] 每条 key_fact 有 evidence_quote（≥5 字）
- [ ] 每条 key_fact 的 target_layer/dimension_hint 在闭集内
- [ ] arena_refs 里的 slug 只来自 known_arenas 或 proposed_arenas[].tentative_slug
- [ ] narratives 的 industry/arena/company 三段字典结构正确（缺失维度不列 key，不写空串）
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yangqi/investing && git add .claude/skills/ingest/prompts/digest/_common.md && git commit -m "feat(ingest): add digest subagent common prompt (contract)

Defines the shared input schema (file_meta / full_text / figure_contexts /
detected_tickers / known_arenas / dimension_ref) and output JSON schema
(key_facts / narratives / proposed_arenas / flags) used by all 4
digest prompts. Rules enforce target_layer/dimension_hint closed sets,
evidence_quote mandatory, figure_contexts priority, and proposed_arenas
only-when-actually-new semantics. No LLM call — prompt is a contract
for Plan 3's workflow to dispatch.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: `industry-digest.md` — 行业研报 digest prompt

**Files:**
- Create: `/Users/yangqi/investing/.claude/skills/ingest/prompts/digest/industry-digest.md`

- [ ] **Step 1: Write prompt**

```markdown
# industry-digest prompt（行业研报专用 digest subagent）

读 `_common.md` 的通用规则先；本文档只写 **与行业研报（`--type industry`）相关的专属指令**。

## 你面对的输入

行业研报（国金/中信/Goldman/MS 等出的 20-100 页行业深度）。核心期望产出：

- 大量 **industry.observations**（atomic 数值、structured field、enum stage 等）
- 11 份 **industry.narratives**（按维度浓缩）
- 若讨论到具体博弈 → **arena narrative** + **proposed_arenas**
- 若提到 ≥2 句话的具体 ticker → **per-ticker company narratives**（只在 moat / business_model / growth_engine 三维）+ 少量 **company.claims**（不走 claims 通道，放在 key_facts 里 target_layer=company）

**行业研报 ≠ 公司年报**：不要产 financial_rows（研报谈一家公司通常只 1-2 句，不是结构化财务）；不要产 meta_updates（不知道公司全名）。

## 产出分层侧重

| target_layer | 应占 key_facts 比例 | 典型 dimension_hint |
|---|---|---|
| industry | 50-70% | market_size / competition / value_chain / technology / regulation / drivers |
| arena    | 15-25% | participants / decisive_factors / trajectory / narratives |
| company  | 10-25% | moat / business_model / growth_engine（研报多半在"推荐公司"章节给几条） |
| cross    | 少见 | share_by_player（某 ticker 的行业市占是 cross） |

## Industry observations 细则

- **market_size.tam_* / cagr_***：figure_contexts 里 100% 必须扫一遍；研报图表几乎必带 TAM 时间序列
- **competition.share_by_player**：每家头部公司 1 条（metric_type=segment, segment=ticker）
- **competition.hhi / cr5 / cr10**：单数字就 atomic
- **lifecycle.stage**：enum（Embryonic/Growth/Shakeout/Mature/Decline），必带 stage_evidence 配对的 narrative 段
- **benchmark.gross_margin_leader / capex_intensity_avg**：research 常见；找到就抽
- **valuation.pe_ttm_median**：很多研报给"历史 PE 中枢"——抽

## Arena 识别与 proposed_arenas

**建 arena 的充分条件**（任一满足）：
- 报告有独立章节讨论"国产替代 / 技术路线之争 / 某 incumbent 被挑战"等博弈主题
- 出现 ≥3 家 ticker 围绕一个焦点博弈
- 研报用了"格局"、"竞争态势"、"国产化率"等措辞配合 ≥2 家公司

**不建 arena**：
- 报告只做"产业链分析"/"行业介绍"，无博弈叙事
- 只提到 1 家公司的竞争位置

**已知 arena 判重**：
- prompt 里的 `known_arenas` 给了已存在 arena 的 slug + focus + participants
- 若你发现的博弈与已知 arena 的 battleground_focus 重合 → 只填 `arena_refs: [existing_slug]`，不走 proposed_arenas
- 重合判断宽松：focus 语义相近 + 至少 1 个 participant 重合 → 视为已存在

**proposed_arena slug 命名规则**：
- 英文 kebab-case
- 前缀地域：`cn-`（中国）/ `us-`（美国）/ `global-`
- 中段主题：产品/技术/子市场
- 后缀博弈性质：`-domestic-substitution` / `-incumbent-challenge` / `-platform-migration` 等
- 例：`cn-cmp-slurry-domestic-substitution` / `us-weight-loss-glp1-platform` / `cn-power-cable-polymer-material`

## Company 事实的处理

- 报告里每个 ticker 若被提及 ≥3 句话 → 产 ≥1 条 company key_fact（target_layer=company）
- 若只出现在 "涉及公司" 列表或图表角标 → 不产 company key_fact，但 `target_refs.ticker` 可挂在 industry 事实的 segment 上
- `subject_tag_hint` 留空或给可能的白名单值；主 agent 做最终归属
- **不要**产 `financial_rows` —— 研报里的公司财务片段由 sell-side-digest 走，不是 industry-digest

## 对 figure_contexts 的硬要求

你会收到 `figure_contexts[]`。逐个过，判断 caption + surrounding_text 是否含**定量事实**：

- 有具体数字 → 必须抽成 atomic observation（target_layer=industry，field_hint + value_numeric + unit + timeframe）
- 只有 X 轴名没有具体值 → 不抽 observation，但 figure 本身的主题可以并入 narrative
- caption 叫"行业格局"但 surrounding_text 无数字 → narrative 提一下就行

## narratives 段的写法

每个 industry 维度一段，≤300 字：

- 开头 1 句话定论（"2025 年全球 CMP 市场 ~34 亿美元，CAGR 近 10%"）
- 中间 2-4 句证据（可含 1-2 条 quote `> ...`）
- 结尾 1 句话行业层面的判断（"国产替代空间大，但认证门槛是主要摩擦"）

**不要**：
- 复述报告章节原文（那是 source 已存 PDF 的事）
- 把自己变成 outline（`- 市场规模: 34 亿`）— 要 narrative 散文
- 写"有待观察"、"值得关注"等空话

## 输出自查（补充通用自查之外）

- [ ] key_facts 中 target_layer=industry 的条数占多数（研报的正活）
- [ ] 若有 figure_contexts，≥80% 的图表 caption 被扫过（要么产 observation，要么至少影响 narrative）
- [ ] proposed_arenas 的每个 tentative_slug 都有 battleground_focus + ≥2 participants + parent_industry_slug
- [ ] `narratives.industry` 覆盖至少 3 个维度（除非报告真的只讲一维）
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yangqi/investing && git add .claude/skills/ingest/prompts/digest/industry-digest.md && git commit -m "feat(ingest): add industry-digest prompt

Industry research reports: ≥50% key_facts go to industry layer;
heavy use of figure_contexts (captions often carry the only TAM
numbers). arena detection rules (≥3 tickers + battle theme →
propose arena); company events de-prioritized. Slug naming
convention for proposed arenas.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: `annual-digest.md` + `quarterly-digest.md` + `sell-side-digest.md`

**Files:**
- Create: `/Users/yangqi/investing/.claude/skills/ingest/prompts/digest/annual-digest.md`
- Create: `/Users/yangqi/investing/.claude/skills/ingest/prompts/digest/quarterly-digest.md`
- Create: `/Users/yangqi/investing/.claude/skills/ingest/prompts/digest/sell-side-digest.md`

- [ ] **Step 1: Write `annual-digest.md`**

```markdown
# annual-digest prompt（年报 / 10-K / 半年报 专用 digest subagent）

读 `_common.md` 的通用规则先；本文档只写年报专属指令。

## 你面对的输入

A 股年报（100+页）/ 10-K / 半年报。核心期望产出：

- 大量 **company.claims 候选**（key_facts[].target_layer=company，带 subject_tag_hint / company_dimension_hint）
- 8 份 **company.narratives**（按 COMPANY_DIMENSIONS 维度浓缩）
- **financial_rows**（从预处理 `financial_line_rows[]` 里主 agent 已做了初筛；你读这些 rows + 原文 context 做最终填表）
- **meta_updates**（website / listed_date / 行业补充 / 实控人变更）
- 若有"行业 / 市场"章节 → 少量 **industry 补充 narrative**（confidence=medium，作为"公司视角的行业段"）
- 若公司属于某 arena（prompt 里 company_context.arenas 非空）→ arena narrative 补充段

## 产出分层侧重

| target_layer | 典型占比 | 说明 |
|---|---|---|
| company | 70-85% | 主力 |
| industry | 10-20% | "行业竞争格局"/"市场概况"章节的客观事实（confidence 偏 medium） |
| arena    | 5-15% | 仅当公司参与的 arena 在 narratives 里有自然段落 |

## Financial rows 细则

- prompt 里有 `financial_line_rows: [{raw_label, standard_key, numeric_candidates, line}, ...]`（preprocess 抽的）
- 你的任务：对每个 fiscal period（通常是 2 期：本期 + 比较期），选出哪个 numeric_candidate 填哪个 `standard_key`
- 典型 A 股"单位: 万元" 陷阱：**硬转到基础单位（元）**；看到"万元"表头 → 所有数字 × 10000
- 输出到 JSON 里走 **单独字段** `financial_rows`（不是 key_facts）：

```json
{
  "financial_rows": [
    {
      "period": "2025A",
      "period_type": "annual",
      "revenue": 168838102500,
      "cost_of_revenue": 59831212100,
      "net_income_to_parent": 85219487300,
      ...
    }
  ]
}
```

- `period` 用 `{YYYY}A` (年报) / `{YYYY}Q{1-4}` (季报) / `HY{YYYY}H1` (半年报)
- 缺行就省略 key（不要填 null）；主 agent 会走 NULL 保护

## Company narratives 8 维度

逐维度写浓缩段：

| dim | 典型素材 |
|---|---|
| business_model | 业务线/收入结构/单位经济 → `§业务概要`/`MD&A` |
| moat | 差异化/成本/聚焦来源 → `§核心竞争力` |
| growth_engine | 量/价/新品/地理/M&A → `§主要业务` 和 `§未来展望` |
| management | 实控人/CEO/激励 → `§公司治理`/`§股东情况`/`§董监高` |
| financial_profile | 核心指标演进 / 利润结构 / 现金流质量 → `§财务报告` |
| catalysts | 短期触发点 / 在手订单 / 产能爬坡里程碑 → `§重要事项`/`§未来展望` |
| risks | 公司层面风险（业务/财务/治理/特殊）→ `§风险` |
| valuation | 年报鲜少给，管理层"可比公司 PE"偶尔有 → 通常留空 |

**空维度**：年报不覆盖某维度（如 valuation）→ `narratives.company.{key}` 里不要列该 dim key。

## Subject tag hint + company_dimension_hint

- `subject_tag_hint`：必须在 `subjects_whitelist` 里（主 agent 注入了）；违反整条被主 agent 降级
- `company_dimension_hint`：必须在 COMPANY_DIMENSIONS 闭集；violating 整条被 validate_batch 拒

一条典型 company key_fact：

```json
{
  "fact_text": "FY2025 营业收入 1,688 亿元，同比 +14.3%",
  "evidence_quote": "报告期内，公司实现营业收入 168,883,810.25 万元 ...",
  "target_layer": "company",
  "target_refs": {"ticker": "600519", "market": "SSE"},
  "dimension_hint": "financial_profile",
  "value_numeric": 1688.38,
  "unit": "cny_bn",
  "timeframe": "FY2025",
  "subject_tag_hint": "revenue_growth",
  "company_dimension_hint": "financial_profile",
  "confidence": "high"
}
```

## Industry / Arena 补充

- 公司的"行业地位"章节里谈到行业格局（"全球 CMP pad 市场 Dupont 市占 75%"）→ target_layer=industry，confidence=medium
- 公司在某 arena 里 → 该 arena 的 narrative 某维度可以自然 append（"我司在低端国产替代战场处于挑战者位置"）

## 输出自查（补充通用自查之外）

- [ ] 每个 financial_row 至少有 revenue + net_income 两列
- [ ] company narratives 覆盖至少 3 维（通常 5-7 维）
- [ ] 没有抽 company_dimension_hint=catalysts 的空泛项（"公司将继续发展"不是 catalyst）
- [ ] A 股"万元"换算已硬乘 10000（回头自查：营收在 100-10,000 亿量级才合理）
```

- [ ] **Step 2: Write `quarterly-digest.md`**

```markdown
# quarterly-digest prompt（季报 / 10-Q 专用 digest subagent）

读 `_common.md` + `annual-digest.md` 的通用规则先；本文档只写季报专属差异。

## 与年报的差异

季报比年报薄很多（10-30 页），核心期望产出：

- **financial_rows**（最主产物；季报主业）
- 少量 **company.claims** 候选（催化剂进展、重大合同、业绩前瞻）
- 极少 **narrative 更新**（一般只在 financial_profile / catalysts 两维追一段）

**不产出**：
- 完整 8 维 company narrative（季报素材不支持）
- meta_updates（季报罕见有 website/listed_date 变化）
- industry / arena narrative（季报不讲行业）

## financial_rows 特别

- `period_type: "quarterly"` / `period: "{YYYY}Q{N}"`
- A 股季报常有"本报告期"和"本年初至报告期末"两套数据；取 **本报告期** 那一列（即单 Q）
- 10-Q 有"three months ended"和"nine months ended"两套；取 three months ended 作为 Q2/Q3 单季

## narratives 段只写两维度

- `financial_profile`：本 Q 核心指标 vs QoQ / YoY；毛利率变动原因
- `catalysts`：本 Q 有无新催化（如新品发布、重大合同、产能落地）

其它 6 维度 narrative dict 不列 key（空）。

## 输出自查

- [ ] financial_rows 非空且至少 1 期
- [ ] narrative 仅限 financial_profile / catalysts 两维
- [ ] company.claims 候选集中在 subject_tag=revenue_growth / margin_trend / catalyst / guidance
```

- [ ] **Step 3: Write `sell-side-digest.md`**

```markdown
# sell-side-digest prompt（卖方公司研报 专用 digest subagent）

读 `_common.md` 的通用规则先；本文档只写卖方研报专属指令。

## 你面对的输入

卖方研报（10-30 页 / 单公司为主，偶尔含 1-2 家可比公司）。核心期望产出：

- **company.claims 候选**（大量：评级/目标价/财务预测/赛道判断）
- **company narratives**（5-8 维度浓缩，尤其 valuation / growth_engine / moat / catalysts）
- **少量 industry narrative**（研报前几页"行业简介"章节的事实，confidence=medium）
- **少量 arena narrative**（竞争格局/行业地位章节，confidence=medium，仅当 arena 已存在）
- **proposed_arenas 极少**（研报少主动开战场；除非研报主题就是"国产替代"等明确博弈 → 可提 1 个）

## 产出分层侧重

| target_layer | 典型占比 |
|---|---|
| company | 70-80% |
| industry | 10-20% |
| arena    | 5-15% |
| cross    | 0-5% |

## 不产 financial_rows

研报给的"预测"是前瞻（forecast），不是已发生财务；走 **company.claims** 通道，带 `time_type: "forecast"` 而非填 `financial_rows`。财务口径的真值来自年报/季报。

## valuation narrative 必填

研报核心产出：目标价、估值锚、WACC 假设、相对估值（PE / PB / EV/EBITDA 区间）。**必填 `narratives.company.{key}.valuation`**。

## subject_tag 集中

典型 subject_tag_hint：
- `target_price` / `rating` / `revenue_forecast` / `eps_forecast`
- `moat` / `catalyst` / `risk_highlight`
- `industry_outlook`（target_layer=industry 才用）

## 输出自查

- [ ] narratives.company.{key}.valuation 非空
- [ ] 若研报给了目标价 / 评级 → 必有至少 1 条 subject_tag_hint=target_price 的 company claim
- [ ] 研报里的行业数据标 confidence=medium（非一手）
- [ ] proposed_arenas ≤1（研报少开新战场）
```

- [ ] **Step 4: Commit**

```bash
cd /Users/yangqi/investing && git add .claude/skills/ingest/prompts/digest/annual-digest.md .claude/skills/ingest/prompts/digest/quarterly-digest.md .claude/skills/ingest/prompts/digest/sell-side-digest.md && git commit -m "feat(ingest): add annual/quarterly/sell-side digest prompts

Three prompts share _common.md contract, add per-type rules:
  * annual: 70-85% company, 8-dim narratives, financial_rows primary
  * quarterly: financial_rows is primary, narratives only 2 dims
  * sell-side: no financial_rows (use forecast claim), valuation narrative mandatory

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Digest prompt contract test（校验 prompt 字段齐全）

**Files:**
- Create: `/Users/yangqi/investing/tests/test_digest_prompt_contracts.py`

- [ ] **Step 1: Write test**

```python
from pathlib import Path
import pytest

PROMPT_DIR = Path(__file__).resolve().parent.parent / ".claude/skills/ingest/prompts/digest"


def _read(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", [
    "_common.md",
    "industry-digest.md",
    "annual-digest.md",
    "quarterly-digest.md",
    "sell-side-digest.md",
])
def test_prompt_file_exists_and_nonempty(name):
    assert (PROMPT_DIR / name).is_file(), f"missing {name}"
    assert len(_read(name).strip()) > 500, f"{name} too short"


def test_common_declares_schema_keys():
    md = _read("_common.md")
    # key schema tokens that MUST appear
    for tok in ("key_facts", "narratives", "proposed_arenas", "flags",
                "target_layer", "dimension_hint", "arena_refs",
                "evidence_quote", "figure_contexts", "known_arenas"):
        assert tok in md, f"_common.md missing schema token {tok!r}"


def test_common_declares_dimension_ref():
    md = _read("_common.md")
    assert "INDUSTRY_DIMENSIONS" in md or "dimension_ref" in md
    # all 11 industry dim keys should be textually present somewhere
    for dim in ("market_size", "lifecycle", "value_chain", "competition",
                "drivers", "technology", "regulation", "benchmark",
                "risks", "valuation"):
        assert dim in md, f"_common.md missing industry dim {dim}"


def test_industry_digest_declares_figure_context_priority():
    md = _read("industry-digest.md")
    assert "figure_contexts" in md
    assert "atomic observation" in md or "atomic" in md


def test_annual_digest_declares_financial_rows():
    md = _read("annual-digest.md")
    assert "financial_rows" in md
    assert "万元" in md  # unit-conversion warning
    assert "10000" in md or "× 10000" in md


def test_quarterly_digest_limits_narrative_dims():
    md = _read("quarterly-digest.md")
    assert "financial_profile" in md
    assert "catalysts" in md
    # Must state that other dims are not produced
    assert "不产出" in md or "不列 key" in md or "两维" in md


def test_sell_side_digest_declares_valuation_mandatory():
    md = _read("sell-side-digest.md")
    assert "valuation" in md
    assert "目标价" in md or "target_price" in md
```

- [ ] **Step 2: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_digest_prompt_contracts.py -v 2>&1 | tail -15
```

- [ ] **Step 3: Commit**

```bash
cd /Users/yangqi/investing && git add tests/test_digest_prompt_contracts.py && git commit -m "test(digest): contract tests assert prompt schema/field presence

Lightweight regression: if someone drops 'figure_contexts' from the
industry digest, or 'financial_rows' from annual, or the '万元' unit
warning, CI fails. Prompts are plain markdown so this is string match;
it's the cheapest way to prevent prompt drift.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase D: Aggregate 三层分拣 + autobuild (TDD)

### Task 12: `route_key_facts` — 把 digest key_facts 按 target_layer 分桶

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Create: `/Users/yangqi/investing/tests/test_ingest_aggregate_triple.py`

- [ ] **Step 1: Write failing test**

```python
from scripts import ingest_aggregate as agg


def test_route_key_facts_splits_by_target_layer():
    key_facts = [
        {"idx": 1, "target_layer": "industry", "dimension_hint": "market_size",
         "target_refs": {"industry_slug": "cn-cmp-material"}},
        {"idx": 2, "target_layer": "industry", "dimension_hint": "competition",
         "target_refs": {"industry_slug": "cn-cmp-material"}},
        {"idx": 3, "target_layer": "arena", "dimension_hint": "participants",
         "target_refs": {"arena_slug": "cn-cmp-slurry-domestic-substitution"}},
        {"idx": 4, "target_layer": "company", "dimension_hint": "moat",
         "target_refs": {"ticker": "688019", "market": "SSE"}},
        {"idx": 5, "target_layer": "cross", "dimension_hint": "competition",
         "field_hint": "share_by_player",
         "target_refs": {"industry_slug": "cn-cmp-material", "ticker": "688019"}},
    ]
    buckets = agg.route_key_facts(key_facts)
    assert [f["idx"] for f in buckets["industry"]] == [1, 2, 5]  # cross goes to industry by default
    assert [f["idx"] for f in buckets["arena"]] == [3]
    assert [f["idx"] for f in buckets["company"]] == [4]


def test_route_key_facts_drops_malformed():
    key_facts = [
        {"idx": 1, "target_layer": "industry"},  # no target_refs
        {"idx": 2, "target_layer": "bogus", "target_refs": {"industry_slug": "x"}},
    ]
    buckets = agg.route_key_facts(key_facts)
    assert sum(len(v) for v in buckets.values()) == 0


def test_route_key_facts_cross_layer_also_tagged_as_company():
    """Cross-layer facts (target_layer=cross) with a ticker should ALSO appear
    in the company bucket (so company page shows the share_by_player claim)."""
    key_facts = [
        {"idx": 5, "target_layer": "cross", "dimension_hint": "competition",
         "field_hint": "share_by_player",
         "target_refs": {"industry_slug": "i", "ticker": "688019", "market": "SSE"}},
    ]
    buckets = agg.route_key_facts(key_facts)
    assert any(f["idx"] == 5 for f in buckets["industry"])
    assert any(f["idx"] == 5 for f in buckets["company"])
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement `route_key_facts` in `scripts/ingest_aggregate.py`**

```python
def route_key_facts(key_facts: list[dict]) -> dict[str, list[dict]]:
    """Split digest key_facts into per-layer buckets based on target_layer.

    cross-layer facts (e.g. share_by_player that reports a ticker's industry
    market share) go into BOTH industry and company buckets so the arena
    page / company page both see the fact. Malformed facts (no target_refs,
    unknown target_layer) are silently dropped.
    """
    out: dict[str, list[dict]] = {"industry": [], "arena": [], "company": []}
    for f in key_facts:
        layer = f.get("target_layer")
        refs = f.get("target_refs") or {}
        if not refs:
            continue
        if layer == "industry":
            if refs.get("industry_slug"):
                out["industry"].append(f)
        elif layer == "arena":
            if refs.get("arena_slug"):
                out["arena"].append(f)
        elif layer == "company":
            if refs.get("ticker") and refs.get("market"):
                out["company"].append(f)
        elif layer == "cross":
            # Cross-layer: append to industry (primary) and also company if
            # ticker present.
            if refs.get("industry_slug"):
                out["industry"].append(f)
            if refs.get("ticker") and refs.get("market"):
                out["company"].append(f)
        # else: unknown target_layer → drop
    return out
```

- [ ] **Step 4: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_triple.py::test_route_key_facts_splits_by_target_layer tests/test_ingest_aggregate_triple.py::test_route_key_facts_drops_malformed tests/test_ingest_aggregate_triple.py::test_route_key_facts_cross_layer_also_tagged_as_company -v 2>&1 | tail -15 \
  && git add scripts/ingest_aggregate.py tests/test_ingest_aggregate_triple.py && git commit -m "feat(aggregate): route_key_facts splits digest output by target_layer

Malformed rows (missing target_refs, unknown target_layer) are dropped.
cross-layer facts land in both industry and company buckets so both
pages render them.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: `fact_to_observation` + write_industry_observations

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Append: `/Users/yangqi/investing/tests/test_ingest_aggregate_triple.py`

- [ ] **Step 1: Append failing tests**

```python
from pathlib import Path


def test_fact_to_observation_maps_standard_fields():
    fact = {
        "idx": 1, "fact_text": "2025 TAM 33.8B USD",
        "evidence_quote": "...原文 ...",
        "target_layer": "industry",
        "target_refs": {"industry_slug": "cn-cmp-material"},
        "dimension_hint": "market_size",
        "field_hint": "tam_global",
        "value_numeric": 33.8,
        "unit": "usd_bn",
        "timeframe": "2025",
        "time_type": "actual",
        "metric_type": "atomic",
        "arena_refs": [],
        "confidence": "high",
    }
    source_meta = {
        "source_id": "行研-国金证券-2026-03-10-abc12345",
        "institution": "国金证券",
        "date": "2026-03-10",
        "sha8": "abc12345",
        "source_file": "cmp.pdf",
        "source_note": "引用 Market Growth Reports",
    }
    row = agg.fact_to_observation(fact, source_meta, extracted_by="claude-opus-4-7",
                                  extracted_at="2026-04-26T00:00:00Z")
    assert row["dimension"] == "market_size"
    assert row["field"] == "tam_global"
    assert row["value"] == 33.8
    assert row["unit"] == "usd_bn"
    assert row["timeframe"] == "2025"
    assert row["source_id"] == "行研-国金证券-2026-03-10-abc12345"
    assert row["confidence"] == "high"
    assert row["evidence"].startswith("...原文")
    assert row["id"].startswith("cmp-")  # ID convention: {industry-prefix}-{nnnn}


def test_write_industry_observations_roundtrip(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="cn-cmp-material", name="CMP", scope="", base=base)

    facts = [{
        "idx": 1, "fact_text": "TAM 33.8B",
        "evidence_quote": "原文",
        "target_layer": "industry",
        "target_refs": {"industry_slug": "cn-cmp-material"},
        "dimension_hint": "market_size",
        "field_hint": "tam_global",
        "value_numeric": 33.8, "unit": "usd_bn",
        "timeframe": "2025", "time_type": "actual",
        "metric_type": "atomic",
        "confidence": "high",
    }]
    source_meta = {"source_id": "s1", "institution": "X", "date": "2026-01-01",
                   "sha8": "abcd1234", "source_file": "x.pdf"}
    n = agg.write_industry_observations(
        facts, source_meta,
        extracted_by="t", extracted_at="2026-04-26T00:00:00Z",
        base=base,
    )
    assert n == 1
    rows = industry_io.read_observations("cn-cmp-material", base=base)
    assert len(rows) == 1
    assert rows[0]["field"] == "tam_global"
    assert rows[0]["value"] == 33.8
```

- [ ] **Step 2: Implement**

```python
def fact_to_observation(
    fact: dict,
    source_meta: dict,
    *,
    extracted_by: str,
    extracted_at: str,
) -> dict:
    """Map a digest key_fact (target_layer=industry) to an observations.jsonl row
    matching spec §4.2 schema.
    """
    slug = (fact.get("target_refs") or {}).get("industry_slug", "")
    # ID: first 3 chars of slug after any "cn-"/"us-" prefix + hash-like suffix
    prefix = re.sub(r"[^a-z]", "", slug.split("-")[-1] or slug)[:3] or "obs"
    # Use fact idx + source sha8 for deterministic local id.
    obs_id = f"{prefix}-{source_meta.get('sha8', '')}-{fact.get('idx', 0):04d}"
    return {
        "id": obs_id,
        "dimension": fact.get("dimension_hint"),
        "field": fact.get("field_hint"),
        "value": fact.get("value_numeric"),
        "unit": fact.get("unit"),
        "timeframe": fact.get("timeframe"),
        "time_type": fact.get("time_type", "actual"),
        "metric_type": fact.get("metric_type", "atomic"),
        "segment": fact.get("segment"),
        "arena_refs": fact.get("arena_refs") or [],
        "source_id": source_meta["source_id"],
        "source_file": source_meta.get("source_file"),
        "source_note": source_meta.get("source_note"),
        "confidence": fact.get("confidence", "medium"),
        "claim_text": fact.get("fact_text"),
        "evidence": fact.get("evidence_quote"),
        "extracted_by": extracted_by,
        "extracted_at": extracted_at,
    }


def write_industry_observations(
    facts: list[dict],
    source_meta: dict,
    *,
    extracted_by: str,
    extracted_at: str,
    base: Path | None = None,
) -> int:
    """Convert digest facts → observation rows, dedup, append per-slug.
    Returns total rows written across all slugs.
    """
    from app.io import industry as industry_io  # lazy: avoid circular

    by_slug: dict[str, list[dict]] = {}
    for f in facts:
        refs = f.get("target_refs") or {}
        slug = refs.get("industry_slug")
        if not slug:
            continue
        by_slug.setdefault(slug, []).append(fact_to_observation(
            f, source_meta, extracted_by=extracted_by, extracted_at=extracted_at,
        ))

    total = 0
    for slug, rows in by_slug.items():
        rows = industry_io.dedup_observations(rows)
        total += industry_io.append_observations(slug, rows, base=base)
    return total
```

- [ ] **Step 3: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_triple.py -v 2>&1 | tail -15 \
  && git add scripts/ingest_aggregate.py tests/test_ingest_aggregate_triple.py && git commit -m "feat(aggregate): fact_to_observation + write_industry_observations

Maps digest key_facts (target_layer=industry, atomic/segment metric_type)
to spec §4.2 observation rows; groups by industry_slug; applies dedup
via industry_io.dedup_observations; writes per-slug.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 14: `write_industry_narrative` / `write_arena_narrative` / `write_company_narrative`

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Append: `/Users/yangqi/investing/tests/test_ingest_aggregate_triple.py`

- [ ] **Step 1: Append failing tests**

```python
def test_write_industry_narrative_appends_block(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="", base=base)

    narratives = {"x": {"market_size": "TAM 34B, CAGR 9%", "technology": "铜抛光液演进"}}
    source_meta = {"source_id": "s1", "institution": "国金", "date": "2026-03-10",
                   "sha8": "abcd1234"}
    agg.write_industry_narrative(narratives, source_meta, base=base)

    md = industry_io.read_narrative("x", "market_size", base=base)
    assert "TAM 34B" in md
    assert "来源 国金 2026-03-10" in md

    md_t = industry_io.read_narrative("x", "technology", base=base)
    assert "铜抛光液" in md_t


def test_write_arena_narrative_appends_block(tmp_path):
    from app.io import arenas as arenas_io
    base = tmp_path / "arenas"
    base.mkdir()
    arenas_io.write_definition(slug="a1", name="A1", definition_text="x",
                                industry="i", battleground_focus="f", base=base)
    narratives = {"a1": {"participants": "安集 vs Dupont"}}
    source_meta = {"source_id": "s1", "institution": "X", "date": "2026-01-01",
                   "sha8": "abcd1234"}
    agg.write_arena_narrative(narratives, source_meta, base=base)
    md = arenas_io.read_narrative("a1", "participants", base=base)
    assert "安集 vs Dupont" in md


def test_write_company_narrative_appends_block(tmp_path):
    from app.io import company as company_io
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(ticker="600519", market="SSE", name="Moutai",
                              industry_slugs=[], base=base)
    narratives = {"SSE_600519": {"moat": "品牌+渠道+产能"}}
    source_meta = {"source_id": "年报-2024-deadbeef", "institution": "年报",
                   "date": "2024-12-31", "sha8": "deadbeef"}
    agg.write_company_narrative(narratives, source_meta, base=base)
    md = company_io.read_narrative("600519", "SSE", "moat", base=base)
    assert "品牌+渠道" in md


def test_write_narrative_skips_empty_string(tmp_path):
    """Empty narrative dims must not trigger an 'empty block' append —
    empty str/None means 'dim not covered by this report'."""
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="x", name="X", scope="", base=base)
    narratives = {"x": {"market_size": "", "technology": None, "lifecycle": "Mature"}}
    source_meta = {"source_id": "s1", "institution": "X", "date": "2026-01-01",
                   "sha8": "abcd1234"}
    agg.write_industry_narrative(narratives, source_meta, base=base)
    md_m = industry_io.read_narrative("x", "market_size", base=base)
    md_t = industry_io.read_narrative("x", "technology", base=base)
    md_l = industry_io.read_narrative("x", "lifecycle", base=base)
    # skeleton only for empty; new block only for lifecycle
    assert "来源" not in md_m
    assert "来源" not in md_t
    assert "Mature" in md_l
```

- [ ] **Step 2: Implement**

```python
def _is_blank_block(s) -> bool:
    return s is None or (isinstance(s, str) and not s.strip())


def write_industry_narrative(
    narratives: dict[str, dict[str, str]],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    """narratives shape: {industry_slug: {dim: md_block, ...}, ...}.
    Appends one source block per non-empty (slug, dim). Returns count written."""
    from app.io import industry as industry_io

    count = 0
    for slug, by_dim in (narratives or {}).items():
        if not by_dim:
            continue
        for dim, block in by_dim.items():
            if _is_blank_block(block):
                continue
            industry_io.append_narrative_block(slug, dim, block, source_meta, base=base)
            count += 1
    return count


def write_arena_narrative(
    narratives: dict[str, dict[str, str]],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    """narratives shape: {arena_slug: {dim: md_block, ...}}."""
    from app.io import arenas as arenas_io

    count = 0
    for slug, by_dim in (narratives or {}).items():
        if not by_dim:
            continue
        for dim, block in by_dim.items():
            if _is_blank_block(block):
                continue
            arenas_io.append_narrative_block(slug, dim, block, source_meta, base=base)
            count += 1
    return count


def write_company_narrative(
    narratives: dict[str, dict[str, str]],
    source_meta: dict,
    *,
    base: Path | None = None,
) -> int:
    """narratives shape: {company_key (MARKET_TICKER): {dim: md_block, ...}}."""
    from app.io import company as company_io

    count = 0
    for key, by_dim in (narratives or {}).items():
        if not by_dim or "_" not in key:
            continue
        market, ticker = key.split("_", 1)
        for dim, block in by_dim.items():
            if _is_blank_block(block):
                continue
            company_io.append_narrative_block(
                ticker, market, dim, block, source_meta, base=base,
            )
            count += 1
    return count
```

- [ ] **Step 3: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_triple.py -v 2>&1 | tail -15 \
  && git add scripts/ingest_aggregate.py tests/test_ingest_aggregate_triple.py && git commit -m "feat(aggregate): write_{industry|arena|company}_narrative helpers

Per-layer narrative dict → Plan 1 append_narrative_block. Blank/None
blocks are skipped (empty dim = 'not covered by this report').
All three share the same source_meta contract (institution / date /
sha8 / source_id) per spec §4.4.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 15: `fact_to_claim` + write_company_claims（走 Plan 1 已有 claims_io.validate_batch）

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Append: `/Users/yangqi/investing/tests/test_ingest_aggregate_triple.py`

**设计：** company 层 key_facts 比较特殊——现有 `write_claims(...)` 已经好用，但它接受的是 digest 格式不太一样的 list。这里加一个 `facts_to_claims_batch(...)` 把 digest key_facts 转为 claims 形状（含 `arena_refs` + `company_dimension_hint`）。

- [ ] **Step 1: Append failing test**

```python
def test_facts_to_claims_converts_fields():
    facts = [{
        "idx": 1,
        "fact_text": "FY2025 营收 1,688 亿元，同比 +14.3%",
        "evidence_quote": "...",
        "target_layer": "company",
        "target_refs": {"ticker": "600519", "market": "SSE"},
        "dimension_hint": "financial_profile",
        "subject_tag_hint": "revenue_growth",
        "company_dimension_hint": "financial_profile",
        "timeframe": "FY2025",
        "confidence": "high",
        "arena_refs": ["arena-x"],
    }]
    claims = agg.facts_to_claims(facts)
    assert len(claims) == 1
    c = claims[0]
    assert c["claim_text"] == "FY2025 营收 1,688 亿元，同比 +14.3%"
    assert c["subject_tag"] == "revenue_growth"
    assert c["company_dimension_hint"] == "financial_profile"
    assert c["arena_refs"] == ["arena-x"]
    # evidence must be [{text, type}] (claim schema)
    assert isinstance(c["evidence"], list)
    assert c["evidence"][0]["text"].startswith("...") or c["evidence"][0]["text"] == "..."


def test_facts_to_claims_groups_by_company():
    facts = [
        {"idx": 1, "target_layer": "company",
         "target_refs": {"ticker": "600519", "market": "SSE"},
         "fact_text": "A", "evidence_quote": "ea",
         "subject_tag_hint": "tag1", "company_dimension_hint": "moat"},
        {"idx": 2, "target_layer": "company",
         "target_refs": {"ticker": "000858", "market": "SSE"},
         "fact_text": "B", "evidence_quote": "eb",
         "subject_tag_hint": "tag1", "company_dimension_hint": "moat"},
    ]
    groups = agg.group_company_facts(facts)
    assert set(groups.keys()) == {("600519", "SSE"), ("000858", "SSE")}
    assert len(groups[("600519", "SSE")]) == 1
    assert len(groups[("000858", "SSE")]) == 1
```

- [ ] **Step 2: Implement**

```python
def facts_to_claims(facts: list[dict]) -> list[dict]:
    """Convert company-layer digest facts to claim dicts accepted by
    claims_io.validate_batch (and subsequently append_batch)."""
    out: list[dict] = []
    for f in facts:
        if f.get("target_layer") not in ("company", "cross"):
            continue
        refs = f.get("target_refs") or {}
        if not (refs.get("ticker") and refs.get("market")):
            continue
        out.append({
            "claim_text": f.get("fact_text"),
            "subject_tag": f.get("subject_tag_hint"),
            "polarity": f.get("polarity", "neutral"),
            "claim_type": (
                "quantitative" if f.get("value_numeric") is not None
                else "qualitative"
            ),
            "timeframe": f.get("timeframe"),
            "evidence": [{"text": f.get("evidence_quote") or "", "type": "primary"}],
            "confidence": f.get("confidence", "medium"),
            "arena_refs": f.get("arena_refs") or [],
            "company_dimension_hint": f.get("company_dimension_hint"),
        })
    return out


def group_company_facts(facts: list[dict]) -> dict[tuple[str, str], list[dict]]:
    """Return {(ticker, market): [facts]} for every company-layer fact."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for f in facts:
        if f.get("target_layer") not in ("company", "cross"):
            continue
        refs = f.get("target_refs") or {}
        if not (refs.get("ticker") and refs.get("market")):
            continue
        groups.setdefault((refs["ticker"], refs["market"]), []).append(f)
    return groups
```

- [ ] **Step 3: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_triple.py -v 2>&1 | tail -15 \
  && git add scripts/ingest_aggregate.py tests/test_ingest_aggregate_triple.py && git commit -m "feat(aggregate): facts_to_claims + group_company_facts

Converts digest company-layer facts (+cross) to claim shape compatible
with claims_io.validate_batch (evidence: list[{text,type}]; polarity
default neutral; claim_type inferred from value_numeric). arena_refs
and company_dimension_hint flow through untouched (Plan 1 claims_io
validates the latter against COMPANY_DIMENSIONS).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 16: autobuild helpers — `ensure_industry_exists` / `ensure_company_exists`

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Create: `/Users/yangqi/investing/tests/test_ingest_aggregate_autobuild.py`

**语义：** 这两个 helper 本身不调 AskUserQuestion——它们**只决定**"目录存在吗？不存在就建"。**主 agent 在 Plan 3 的 workflow 里**先跟用户确认 slug/name/scope（industry）或 name/currency（company），确认后再调这些 helper。本 plan 只写下层写入逻辑 + 前置存在性检查 + 记录"autobuilt"标记以便 Plan 3 上报给用户。

- [ ] **Step 1: Write failing test**

```python
from scripts import ingest_aggregate as agg


def test_ensure_industry_exists_creates_when_missing(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    result = agg.ensure_industry_exists(
        slug="cn-new-industry",
        name="中国新行业",
        scope="主题",
        base=base,
    )
    assert result["autobuilt"] is True
    assert result["slug"] == "cn-new-industry"
    assert (base / "cn-new-industry" / "meta.yaml").is_file()
    # 11 narrative skeletons
    for dim in ("market-size", "competition", "valuation"):
        assert (base / "cn-new-industry" / f"{dim}.md").is_file()


def test_ensure_industry_exists_noop_when_present(tmp_path):
    from app.io import industry as industry_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="existing", name="E", scope="", base=base)
    result = agg.ensure_industry_exists(
        slug="existing", name="E", scope="", base=base,
    )
    assert result["autobuilt"] is False


def test_ensure_company_exists_creates_when_missing(tmp_path):
    base = tmp_path / "companies"
    base.mkdir()
    result = agg.ensure_company_exists(
        ticker="688019", market="SSE", name="安集科技",
        industry_slugs=["cn-cmp-material"],
        currency="CNY",
        base=base,
    )
    assert result["autobuilt"] is True
    assert (base / "SSE_688019" / "meta.md").is_file()


def test_ensure_company_exists_noop_when_present(tmp_path):
    from app.io import company as company_io
    base = tmp_path / "companies"
    base.mkdir()
    company_io.create_company(ticker="600519", market="SSE", name="Moutai",
                              industry_slugs=[], base=base)
    result = agg.ensure_company_exists(
        ticker="600519", market="SSE", name="Moutai",
        industry_slugs=[], currency="CNY",
        base=base,
    )
    assert result["autobuilt"] is False
```

- [ ] **Step 2: Implement**

```python
def ensure_industry_exists(
    *, slug: str, name: str, scope: str = "", base: Path | None = None,
) -> dict:
    """If industry slug dir missing → create it via industry_io.create_industry.
    Returns {slug, autobuilt: bool}. Caller (main agent) can surface
    autobuilt=True to the user ('I just made a new industry slug for you').
    """
    from app.io import industry as industry_io

    try:
        industry_io.read_meta(slug, base=base)
        return {"slug": slug, "autobuilt": False}
    except FileNotFoundError:
        industry_io.create_industry(slug=slug, name=name, scope=scope, base=base)
        return {"slug": slug, "autobuilt": True}


def ensure_company_exists(
    *, ticker: str, market: str, name: str,
    industry_slugs: list[str] | None = None,
    currency: str = "USD",
    base: Path | None = None,
) -> dict:
    """If companies/{market}_{ticker}/ missing → create via
    company_io.create_company. Returns {key, autobuilt}."""
    from app.io import company as company_io

    key = f"{market}_{ticker}"
    dir_path = (base or company_io.cfg.COMPANIES_DIR) / key
    if dir_path.exists():
        return {"key": key, "autobuilt": False}
    company_io.create_company(
        ticker=ticker, market=market, name=name,
        industry_slugs=industry_slugs or [],
        currency=currency, base=base,
    )
    return {"key": key, "autobuilt": True}
```

- [ ] **Step 3: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_autobuild.py -v 2>&1 | tail -15 \
  && git add scripts/ingest_aggregate.py tests/test_ingest_aggregate_autobuild.py && git commit -m "feat(aggregate): autobuild helpers ensure_{industry,company}_exists

Implements the 'autobuild-meta' and 'autobuild-industry-slug' rules:
when digest routes a fact to a missing slug/company, ingest flow creates
the skeleton inline instead of erroring. Returns {..., autobuilt: bool}
so the main agent can surface the fact to the user in Step 11 report.

Plan 3 workflows: AskUserQuestion confirms slug/name/scope BEFORE
calling these helpers; the helper itself is pure filesystem plumbing.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 17: `propose_arena_bootstrap` — 把 digest 的 proposed_arenas 转 arena-create 参数

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Append: `/Users/yangqi/investing/tests/test_ingest_aggregate_autobuild.py`

- [ ] **Step 1: Append failing test**

```python
def test_propose_arena_bootstrap_normalizes_slug():
    proposed = [
        {"tentative_slug": "CN-CMP-Slurry-Domestic-Substitution",
         "battleground_focus": "国产 CMP 抛光液挑战 Dupont/Cabot/Versum",
         "tentative_participants": [
             {"name": "安集", "role": "challenger"},
             {"name": "Dupont", "role": "incumbent"},
         ],
         "parent_industry_slug": "cn-cmp-material"},
    ]
    out = agg.propose_arena_bootstrap(proposed)
    assert len(out) == 1
    a = out[0]
    assert a["slug"] == "cn-cmp-slurry-domestic-substitution"  # lowercased
    assert a["industry"] == "cn-cmp-material"
    assert a["battleground_focus"] == "国产 CMP 抛光液挑战 Dupont/Cabot/Versum"
    assert a["participants"] == [
        {"name": "安集", "role": "challenger"},
        {"name": "Dupont", "role": "incumbent"},
    ]


def test_propose_arena_bootstrap_drops_missing_focus():
    proposed = [
        {"tentative_slug": "good", "battleground_focus": "focus",
         "parent_industry_slug": "i", "tentative_participants": []},
        {"tentative_slug": "bad-no-focus", "battleground_focus": "",
         "parent_industry_slug": "i", "tentative_participants": []},
    ]
    out = agg.propose_arena_bootstrap(proposed)
    assert [a["slug"] for a in out] == ["good"]


def test_bootstrap_arena_creates_definition_and_skeletons(tmp_path):
    """After user approves, this helper actually writes arena files."""
    from app.io import arenas as arenas_io
    from app import config as cfg
    base = tmp_path / "arenas"
    base.mkdir()
    proposal = {
        "slug": "cn-test-arena",
        "name": "测试战场",
        "industry": "cn-cmp-material",
        "battleground_focus": "国产化之战",
        "participants": [{"name": "A", "role": "challenger"}],
    }
    agg.bootstrap_arena(proposal, base=base)
    # 5 narrative skeletons (excluding definition which is already written)
    for dim in cfg.ARENA_DIMENSIONS:
        if dim == "definition":
            continue
        assert (base / "cn-test-arena" / f"{dim.replace('_', '-')}.md").is_file()
    # definition.md frontmatter
    r = arenas_io.read_definition("cn-test-arena", base=base)
    fm = r["frontmatter"]
    assert fm["industry"] == "cn-cmp-material"
    assert fm["battleground_focus"] == "国产化之战"
```

- [ ] **Step 2: Implement**

```python
def propose_arena_bootstrap(proposed: list[dict]) -> list[dict]:
    """Normalize digest proposed_arenas to arena-create args for the main agent
    to surface to the user. Lower-cases slug; drops proposals without
    battleground_focus. Returns list of {slug, name, industry, battleground_focus,
    participants}.
    """
    out: list[dict] = []
    for p in proposed or []:
        slug_raw = (p.get("tentative_slug") or "").strip().lower()
        focus = (p.get("battleground_focus") or "").strip()
        industry = (p.get("parent_industry_slug") or "").strip()
        if not slug_raw or not focus or not industry:
            continue
        participants = p.get("tentative_participants") or []
        # Synthesize a display name from focus if absent
        out.append({
            "slug": slug_raw,
            "name": p.get("name") or focus[:40],
            "industry": industry,
            "battleground_focus": focus,
            "participants": participants,
        })
    return out


def bootstrap_arena(proposal: dict, *, base: Path | None = None) -> None:
    """After user approves, actually create the arena (definition + 5 dim
    narrative skeletons). Wrapper around arenas_io.write_definition."""
    from app.io import arenas as arenas_io

    arenas_io.write_definition(
        slug=proposal["slug"],
        name=proposal["name"],
        definition_text=proposal["battleground_focus"],
        participants=proposal.get("participants") or [],
        industry=proposal["industry"],
        battleground_focus=proposal["battleground_focus"],
        base=base,
    )
```

- [ ] **Step 3: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_autobuild.py -v 2>&1 | tail -15 \
  && git add scripts/ingest_aggregate.py tests/test_ingest_aggregate_autobuild.py && git commit -m "feat(aggregate): propose_arena_bootstrap + bootstrap_arena

Normalizes digest proposed_arenas to arena-create args (lower-case
slug, require battleground_focus + parent_industry); bootstrap_arena
writes definition.md frontmatter (industry + battleground_focus)
and 5 narrative skeletons via Plan 1 arenas_io.write_definition.

Main agent in Plan 3 runs AskUserQuestion between propose and
bootstrap; helpers themselves are pure.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 18: figure_contexts writer — 把 preprocess 的 figure_contexts 落到 industry slug

**Files:**
- Modify: `/Users/yangqi/investing/scripts/ingest_aggregate.py`
- Append: `/Users/yangqi/investing/tests/test_ingest_aggregate_triple.py`

- [ ] **Step 1: Append failing test**

```python
def test_write_figure_contexts_attaches_source_id(tmp_path):
    from app.io import industry as industry_io
    from app.io import figure_contexts as fc_io
    base = tmp_path / "industries"
    base.mkdir()
    industry_io.create_industry(slug="cn-cmp-material", name="X", scope="", base=base)

    preprocess_contexts = [
        {"id": "fig-001", "page": None,
         "caption": "图表1: 全球市场规模",
         "surrounding_text": "2025 市场规模 33.8 亿美元",
         "section_name": "market_size"},
    ]
    source_meta = {"source_id": "行研-X-2026-03-10-abcd1234", "institution": "X",
                   "date": "2026-03-10", "sha8": "abcd1234"}
    n = agg.write_figure_contexts(
        slug="cn-cmp-material",
        contexts=preprocess_contexts,
        source_meta=source_meta,
        base=base,
    )
    assert n == 1
    rows = fc_io.read_figure_contexts("cn-cmp-material", base=base)
    assert rows[0]["source_id"] == "行研-X-2026-03-10-abcd1234"
    assert rows[0]["caption"].startswith("图表1")
```

- [ ] **Step 2: Implement**

```python
def write_figure_contexts(
    *,
    slug: str,
    contexts: list[dict],
    source_meta: dict,
    base: Path | None = None,
) -> int:
    """Stamp source_id on each preprocess figure_context and append to
    industries/{slug}/figure_contexts.jsonl."""
    from app.io import figure_contexts as fc_io

    enriched = []
    for c in contexts or []:
        enriched.append({**c, "source_id": source_meta["source_id"]})
    return fc_io.append_figure_contexts(slug, enriched, base=base)
```

- [ ] **Step 3: PASS + Commit**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_triple.py -v 2>&1 | tail -15 \
  && git add scripts/ingest_aggregate.py tests/test_ingest_aggregate_triple.py && git commit -m "feat(aggregate): write_figure_contexts stamps source_id + appends per-slug

Wraps Plan 2 app.io.figure_contexts.append_figure_contexts. Main agent
calls this once per industry slug a report touches (typically 1).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase E: Fix-forward discipline — failure-mode tests

### Task 19: Fix-forward case — UNKNOWN_N sections on industry reports

**Files:**
- Append: `/Users/yangqi/investing/tests/test_preprocess_industry_type.py`
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/templates/a-share-industry.yaml` (extend normalize table as documented)

**目标：** 当 preprocess 对某类行业研报产生大比例 UNKNOWN_N（比如"技术演进"作为 "3.1 技术路线对比" 出现），修复的正确位置是 **template 的 `section_normalize` 表**（加 key），不是业务代码或 per-doc workaround。写一个 regression test 锁住这个语义。

- [ ] **Step 1: Append failing test**

```python
def test_preprocess_industry_technology_alias_normalized(tmp_path):
    """Fix-forward regression: '技术路线对比' / '技术演进' / '技术趋势' should all
    normalize to the `technology` dim. If someone adds a new Chinese alias
    used by a specific broker, add it to a-share-industry.yaml's
    section_normalize — NOT with a per-doc hack."""
    report = tmp_path / "r.md"
    report.write_text(
        "# 行业研报\n\n"
        "三、技术演进\n正文 A。\n\n"
        "四、技术路线对比\n正文 B。\n\n"
        "五、技术趋势\n正文 C。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    pre.main([str(report), "--type", "industry", "--market", "a-share", "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    names = [s["name"] for s in data["sections"]]
    tech_count = names.count("technology")
    # "技术演进" is in the yaml already; "技术路线对比" and "技术趋势" must also map
    assert tech_count >= 2, f"expected ≥2 technology sections, got names={names}"
```

- [ ] **Step 2: Run — FAIL** (only "技术演进" mapped)

- [ ] **Step 3: Fix — extend `section_normalize` in `a-share-industry.yaml`**

Add lines:
```yaml
  技术路线: technology
  技术路线对比: technology
  技术趋势: technology
```

- [ ] **Step 4: Run — PASS**

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add .claude/skills/ingest/templates/a-share-industry.yaml tests/test_preprocess_industry_type.py && git commit -m "fix(ingest): expand technology aliases in a-share-industry template

Fix-forward discipline: preprocess UNKNOWN sections on industry reports
are fixed by extending the template's section_normalize (or the
regex patterns) — never by per-doc workarounds. Regression test
locks three common aliases ('技术演进' / '技术路线对比' / '技术趋势')
to the technology dim.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 20: Fix-forward case — dispatch failure on duplicate section names

**Files:**
- Append: `/Users/yangqi/investing/tests/test_preprocess_industry_type.py`

**目标：** 若一份研报正文里出现两次 `一、市场空间`（目录 + 正文）→ preprocess 的 `_dedupe_toc` 应该保留正文段；锁住这个行为以防 regression。

- [ ] **Step 1: Append test**

```python
def test_dedup_toc_keeps_longest_section(tmp_path):
    report = tmp_path / "r.md"
    # "一、市场空间" appears twice: once in TOC (very short body), once in body
    report.write_text(
        "目录\n一、市场空间\n二、竞争格局\n三、技术演进\n\n"
        "一、市场空间\n2025 年全球 CMP 抛光材料市场规模 33.8 亿美元，"
        "CAGR 9%。产品分为抛光液和抛光垫两大类。\n\n"
        "二、竞争格局\n龙头 Dupont 市占 75%。\n",
        encoding="utf-8",
    )
    out = tmp_path / "out.json"
    pre.main([str(report), "--type", "industry", "--market", "a-share", "--out", str(out)])
    data = json.loads(out.read_text(encoding="utf-8"))
    market_size = [s for s in data["sections"] if s["name"] == "market_size"]
    # _dedupe_toc keeps the one with longest body
    assert len(market_size) == 1
    assert "33.8" in market_size[0]["text"]
```

- [ ] **Step 2: Run — PASS** (likely already works; test is regression-locking)

- [ ] **Step 3: Commit**

```bash
cd /Users/yangqi/investing && git add tests/test_preprocess_industry_type.py && git commit -m "test(preprocess): regression-lock _dedupe_toc keeps longest section

When TOC repeats a section name, preprocess must keep the real body
(longest) and drop the TOC entry. Without this, the industry digest
would see 'market_size' with empty text and miss the actual TAM data.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Phase F: End-to-end unit pipeline

### Task 21: Unit e2e — simulated digest JSON → three-layer writes

**Files:**
- Append: `/Users/yangqi/investing/tests/test_ingest_aggregate_triple.py`

- [ ] **Step 1: Append big-ish integration test**

```python
def test_e2e_industry_digest_full_pipeline(tmp_path):
    """Simulate the full Plan 3 workflow (except the LLM call):
       1. create industry via autobuild helper
       2. receive digest JSON
       3. route_key_facts → three buckets
       4. write each bucket to the right layer via helpers
       5. assert disk state"""
    from app.io import industry as industry_io
    from app.io import arenas as arenas_io
    from app.io import company as company_io
    from app.io import figure_contexts as fc_io

    ind_base = tmp_path / "industries"
    arena_base = tmp_path / "arenas"
    comp_base = tmp_path / "companies"
    for p in (ind_base, arena_base, comp_base):
        p.mkdir()

    # Step 1: autobuild industry
    agg.ensure_industry_exists(
        slug="cn-cmp-material", name="CMP", scope="半导体抛光",
        base=ind_base,
    )

    # Step 2: simulated digest JSON
    digest = {
        "key_facts": [
            {"idx": 1, "target_layer": "industry",
             "target_refs": {"industry_slug": "cn-cmp-material"},
             "dimension_hint": "market_size", "field_hint": "tam_global",
             "value_numeric": 33.8, "unit": "usd_bn",
             "timeframe": "2025", "time_type": "actual",
             "metric_type": "atomic", "confidence": "high",
             "fact_text": "2025 TAM 33.8B USD",
             "evidence_quote": "...原文引用..."},
            {"idx": 2, "target_layer": "company",
             "target_refs": {"ticker": "688019", "market": "SSE"},
             "dimension_hint": "moat",
             "subject_tag_hint": "moat", "company_dimension_hint": "moat",
             "fact_text": "安集 CMP 抛光液技术领先",
             "evidence_quote": "原文 X",
             "confidence": "high"},
        ],
        "narratives": {
            "industry": {"cn-cmp-material": {
                "market_size": "2025 年全球 CMP 市场 ~34 亿美元，CAGR 9%。"
            }},
            "arena": {},
            "company": {"SSE_688019": {
                "moat": "安集的核心护城河是 CMP 抛光液的多年工艺积累。"
            }},
        },
        "proposed_arenas": [
            {"tentative_slug": "cn-cmp-slurry-domestic-substitution",
             "battleground_focus": "国产 CMP 抛光液挑战 Dupont",
             "tentative_participants": [
                 {"name": "安集", "role": "challenger"},
                 {"name": "Dupont", "role": "incumbent"},
             ],
             "parent_industry_slug": "cn-cmp-material"},
        ],
    }

    source_meta = {"source_id": "行研-国金-2026-03-10-abcd1234",
                   "institution": "国金", "date": "2026-03-10",
                   "sha8": "abcd1234", "source_file": "cmp.pdf"}

    # Step 3: route
    buckets = agg.route_key_facts(digest["key_facts"])

    # Step 4a: write observations
    n_obs = agg.write_industry_observations(
        buckets["industry"], source_meta,
        extracted_by="t", extracted_at="2026-04-26T00:00:00Z",
        base=ind_base,
    )
    assert n_obs == 1

    # Step 4b: write industry narrative
    # Note: digest shape is narratives.industry.{slug}.{dim}; our writer expects
    # {slug:{dim:block}} so pass the inner dict directly.
    n_nar = agg.write_industry_narrative(
        digest["narratives"]["industry"],
        source_meta, base=ind_base,
    )
    assert n_nar == 1

    # Step 4c: autobuild company + write company narrative
    agg.ensure_company_exists(
        ticker="688019", market="SSE", name="安集科技",
        industry_slugs=["cn-cmp-material"], currency="CNY",
        base=comp_base,
    )
    n_cn = agg.write_company_narrative(
        digest["narratives"]["company"],
        source_meta, base=comp_base,
    )
    assert n_cn == 1

    # Step 4d: bootstrap proposed arena (simulate user approval)
    proposals = agg.propose_arena_bootstrap(digest["proposed_arenas"])
    assert len(proposals) == 1
    agg.bootstrap_arena(proposals[0], base=arena_base)

    # Assertions — disk state
    assert len(industry_io.read_observations("cn-cmp-material", base=ind_base)) == 1
    assert "CAGR 9%" in industry_io.read_narrative(
        "cn-cmp-material", "market_size", base=ind_base)
    assert "护城河" in company_io.read_narrative("688019", "SSE", "moat", base=comp_base)
    arena_def = arenas_io.read_definition("cn-cmp-slurry-domestic-substitution",
                                          base=arena_base)
    assert arena_def["frontmatter"]["industry"] == "cn-cmp-material"
    assert arena_def["frontmatter"]["battleground_focus"] == "国产 CMP 抛光液挑战 Dupont"
```

- [ ] **Step 2: Run — PASS**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/test_ingest_aggregate_triple.py::test_e2e_industry_digest_full_pipeline -v 2>&1 | tail -20
```

- [ ] **Step 3: Commit**

```bash
cd /Users/yangqi/investing && git add tests/test_ingest_aggregate_triple.py && git commit -m "test(aggregate): e2e unit test simulates full digest → three-layer write

Fakes a digest JSON blob (what Plan 3's workflow would get from the LLM
subagent), runs ensure_industry → route_key_facts → write_industry_obs
→ write_industry_narrative → ensure_company → write_company_narrative
→ propose_arena → bootstrap_arena, asserts disk state. Any regression
in the plumbing caught here before Plan 3 starts real-LLM dispatch.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 22: Full pytest + source-id-rules 更新 + doc drift check

**Files:**
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/source-id-rules.yaml` — 加 `industry-research`
- Modify: `/Users/yangqi/investing/.claude/skills/ingest/section-routing.yaml` — 可选：加 industry-generic 通道（但实际 digest 不走 section-routing）

- [ ] **Step 1: Edit `source-id-rules.yaml`**

Add line under `formats:`:
```yaml
  industry-research:  "行研-{institution}-{date}-{sha8}"
```

Update `field_sources:` if needed (already covers institution / publish_date / sha8).

- [ ] **Step 2: Edit `section-routing.yaml` — add industry-generic fallback**

```yaml
industry-generic:
  _fallback:
    action: extract
    subagent: industry-digest   # single-subagent dispatch, not section-level
    targets: [observations, narrative, proposed_arenas]
    note: 行业研报不走 section-per-subagent；整份报告喂一个 industry-digest
  # All listed section names are advisory — aggregator reads the whole
  # digest output regardless of how preprocess sliced.
  market_size:     {action: extract, subagent: industry-digest, targets: [observations, narrative]}
  competition:     {action: extract, subagent: industry-digest, targets: [observations, narrative]}
  value_chain:     {action: extract, subagent: industry-digest, targets: [narrative]}
  technology:      {action: extract, subagent: industry-digest, targets: [narrative]}
  regulation:      {action: extract, subagent: industry-digest, targets: [narrative]}
  drivers:         {action: extract, subagent: industry-digest, targets: [narrative]}
  lifecycle:       {action: extract, subagent: industry-digest, targets: [narrative]}
  risks:           {action: extract, subagent: industry-digest, targets: [narrative]}
  valuation:       {action: extract, subagent: industry-digest, targets: [narrative]}
```

- [ ] **Step 3: Full pytest**

```bash
cd /Users/yangqi/investing && .venv/bin/pytest tests/ 2>&1 | tail -30
```

Expected: all Plan 2 new tests green; Plan 1 tests still green; any pre-existing test that broke must be looked at (likely not — Plan 2 is additive).

- [ ] **Step 4: Manual smoke — 全链路 dry run**

```bash
cd /Users/yangqi/investing && .venv/bin/python <<'PY'
from pathlib import Path
import tempfile, json
from scripts import preprocess_report as pre
from scripts import ingest_aggregate as agg
from app.io import industry as industry_io

with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    (base / "industries").mkdir()

    # 1) preprocess
    report = base / "r.md"
    report.write_text(
        "国金证券\n2026 年 3 月 10 日\n\n"
        "摘要：2025 CMP 市场 33.8 亿美元。安集(SSE 688019)。\n\n"
        "一、市场空间\n\n图表1: 市场规模\n2025 规模 33.8 亿美元。\n\n"
        "二、竞争格局\nDupont 75%。\n",
        encoding="utf-8"
    )
    pre.main([str(report), "--type", "industry", "--market", "a-share",
              "--out", str(base / "pp.json")])
    data = json.loads((base / "pp.json").read_text(encoding="utf-8"))
    assert "figure_contexts" in data
    assert "detected_tickers" in data
    assert any(t["ticker"] == "688019" for t in data["detected_tickers"])

    # 2) autobuild + simulated digest write
    agg.ensure_industry_exists(slug="cn-cmp-material", name="CMP",
                                scope="", base=base / "industries")
    source_meta = {"source_id": "行研-国金-2026-03-10-abcd1234",
                   "institution": "国金", "date": "2026-03-10",
                   "sha8": "abcd1234"}
    # Stamp & write figure_contexts
    agg.write_figure_contexts(
        slug="cn-cmp-material",
        contexts=data["figure_contexts"],
        source_meta=source_meta,
        base=base / "industries",
    )
    # Fake 1 observation
    agg.write_industry_observations([{
        "idx": 1, "target_layer": "industry",
        "target_refs": {"industry_slug": "cn-cmp-material"},
        "dimension_hint": "market_size", "field_hint": "tam_global",
        "value_numeric": 33.8, "unit": "usd_bn", "timeframe": "2025",
        "time_type": "actual", "metric_type": "atomic", "confidence": "high",
        "fact_text": "TAM 33.8B", "evidence_quote": "原文",
    }], source_meta, extracted_by="t", extracted_at="2026-04-26T00:00:00Z",
       base=base / "industries")

    print("SMOKE OK: observations=",
          len(industry_io.read_observations("cn-cmp-material", base=base/"industries")),
          "figure_contexts=", len((base/"industries"/"cn-cmp-material"/"figure_contexts.jsonl").read_text().splitlines()))
PY
```

Expected: `SMOKE OK: observations= 1 figure_contexts= 1` (or more, depending on figure count).

- [ ] **Step 5: Commit**

```bash
cd /Users/yangqi/investing && git add .claude/skills/ingest/source-id-rules.yaml .claude/skills/ingest/section-routing.yaml && git commit -m "feat(ingest): register industry-research source_id format + routing fallback

source-id-rules.yaml adds '行研-{institution}-{date}-{sha8}' so Plan 3's
industry-report workflow can call the centralized lookup. section-routing
gets an industry-generic bucket whose only real subagent is industry-digest
(one subagent reads whole report) — industry reports do NOT split by
section; the entry is informational for aggregators that still want a
per-name hint.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 6: Final summary commit**

```bash
cd /Users/yangqi/investing && git log --oneline -30 | head -30
```

Expected: ~22 Plan 2 commits. Report commit hash range to user.

---

## Plan 2 完成验证清单

跑过 Plan 2 后以下应成立：

- [x] `app/io/figure_contexts.py` 存在；`REQUIRED_KEYS` 7 项；`append_figure_contexts` / `read_figure_contexts` / `filter_by_*` 可用
- [x] `scripts/preprocess_report.py` CLI 接受 `--type industry`；输出 JSON 含 `figure_contexts` / `detected_tickers` / `report_abstract` / `financial_line_rows`（annual/quarterly 才有最后一项）
- [x] `.claude/skills/ingest/templates/a-share-industry.yaml` + `us-industry.yaml` 存在；form_detection / section_detection / institution 规则齐全
- [x] `.claude/skills/ingest/prompts/digest/_common.md` + 4 份 per-type digest prompt 存在；contract test 锁住必含字段（target_layer / dimension_hint / arena_refs / evidence_quote / figure_contexts 等）
- [x] `scripts/ingest_aggregate.py` 新增：`route_key_facts` / `fact_to_observation` / `write_industry_observations` / `write_industry_narrative` / `write_arena_narrative` / `write_company_narrative` / `facts_to_claims` / `group_company_facts` / `ensure_industry_exists` / `ensure_company_exists` / `propose_arena_bootstrap` / `bootstrap_arena` / `write_figure_contexts`
- [x] 旧的 `aggregate` / `dedup_claims` / `build_claims_batch` / `write_claims` / `write_financials` / cross-checks 保留（annual/quarterly/sell-side 现有 workflow 继续用）
- [x] `source-id-rules.yaml` 含 `industry-research` 格式
- [x] 全量 pytest 绿（Plan 1 + Plan 2 共 ~40 个新增 test 全部 pass）
- [x] 冒烟脚本（Step 4 of Task 22）跑通：preprocess → ensure_industry → write observations/figure_contexts 三段接得上
- [x] autobuild 语义：digest 路由到不存在的 industry/company → `ensure_*` helper 创建 + 返回 `autobuilt=True` 供主 agent 报告给用户
- [x] fix-forward 语义：preprocess UNKNOWN_N 过多的修法锁在 template `section_normalize` 的 regression test 里，不许走 per-doc 分支

---

## 不做（Plan 3/4/5 scope）

- `.claude/skills/ingest/SKILL.md` 的更新（支持范围放开到行业研报；描述改为三层产出）
- 4 个 workflow md 的改造（industry-report.md / annual-report.md 升级 / quarterly-report.md 升级 / sell-side-note.md 升级）
- 主 agent 在对话里真正 dispatch digest-extract subagent（走 `Agent(Explore)`）
- AskUserQuestion 交互环节：industry slug 确认 / proposed_arenas 是否 bootstrap / 用户审 narrative blocks
- 所有 `app/routes/*` 路由 + 模板（三层页面、cross-ref 聚合、跨源 spread badge）
- 真实报告（化学机械抛光行业 pdf / 茅台年报）的端到端集成测试
- LLM API / SDK 的任何集成（按标准规则永远不进 scripts/）

---

## 风险清单

| # | 风险 | 缓解 |
|---|---|---|
| R1 | digest prompt 被 LLM 返回的 JSON 里 `target_layer` 拼错（如 `industry-layer` / `industries`）→ 被 `route_key_facts` 静默丢 | Plan 2 的 `route_key_facts` 已处理：不匹配 4 个 literal 就 drop；主 agent 在 Plan 3 的 workflow 里应统计"dropped 条数" 并 Ask 用户是否接受 |
| R2 | `figure_contexts` 的 `page` 字段当前为 None（PDF 页号未接线）→ 页面 UI 无法"跳到图表原页" | 标已知 TODO；Plan 4 渲染可暂不展示页号；后续 v2 补入 PyMuPDF 的 `page.number` |
| R3 | `extract_financial_line_rows` 匹配 "营业收入" 时若同一行没有数字（表头行）会被跳过；但若正文"营业收入持续增长"也命中前缀 → false-positive 行 | 数字必要性已加 (`_NUMERIC_RE` 检测)；若仍有噪音，下一步加"数字列数 ≥2"过滤 |
| R4 | `detect_tickers` 的 A 股前缀分类（0/3 → SZSE，6 → SSE, 8/9 → BSE）不覆盖 688XXX（科创板）→ 目前也是 SSE（对）；但 4XX / 5XX 无规则 → 当前会落到 "unknown" 不产出 | 当前规则覆盖 >95% 现役代码；遇到新板块加 case；fix-forward |
| R5 | autobuild-meta 在 ingest 中途 error 会留半成品 company 目录 → 下次 ingest 以为"存在"但 meta/narrative 不完整 | `ensure_company_exists` 依赖 `company_io.create_company` 的原子性（Plan 1 已保证：目录存在 → raise）；若用户要 retry，需手动 `rm -rf companies/{key}` — 在 risk register 里记录该操作 |
| R6 | 行业研报 digest 的 token 量大（长报告 > 50 页 → 全文输入 + figure_contexts 可能撑爆 context window）| Plan 2 范围不处理；Plan 3 workflow 里加"长文触发 section-chunking" 检测 + 分批；spec §11 已登记为 v2 风险 |
| R7 | `figure_contexts` 的 regex 把 "表 3：" 之后的非图表性质文本也误归为 caption（如"表 3：公司主要客户名单"不是定量图）| 当前策略是**全收**，由 digest prompt 的 LLM 判断值不值得抽；误抽的 surrounding_text 被 digest 跳过即可 |

---

## 回滚策略

**整体回滚**：`git revert` 到 Plan 2 第一个 commit 的上游 commit（Plan 1 的最后 commit）。Plan 2 所有改动是 additive（新加文件 + `scripts/ingest_aggregate.py` 末尾追加函数 + `scripts/preprocess_report.py` 新增 helper + template 新加），revert 不会破坏 Plan 1 的 IO 层。

**局部回滚**：
- Phase A (figure_contexts IO)：revert Task 1 commit；`app/io/figure_contexts.py` + test 删掉即可，没有其它文件依赖
- Phase B (preprocess 扩展)：revert Tasks 2–7；旧 CLI `--type {annual|quarterly|sell-side}` 仍可用
- Phase C (prompt 契约)：prompts 是纯文本，revert 删文件即可
- Phase D (aggregate 分拣)：revert Tasks 12–18；旧 `aggregate` / `write_claims` / `write_financials` 未变
- Phase E (fix-forward tests)：纯测试回滚风险低
- Phase F (e2e + routing/source-id 更新)：source-id-rules / section-routing 的修改 revert 即可

---

## 自审

**Spec 覆盖检查：**
- §4.8 figure_contexts — ✅ IO + preprocess 抽取 + aggregate 落盘 (Tasks 1, 4, 18)
- §5.1 统一 digest + 主 agent 分拣架构 — ✅ 4 份 digest prompt + aggregate 分拣 helpers (Tasks 8-11, 12-18)
- §5.2 行业研报 workflow 的 preprocess+digest 部分 — ✅ `--type industry` 分支 + industry-digest prompt + proposed_arena 机制 (Tasks 2, 3, 9, 17)
- §5.3 年报 workflow 的 preprocess+digest 部分 — ✅ financial_line_rows 抽取 + annual-digest prompt (Tasks 6, 10)
- §5.4 季报 — ✅ quarterly-digest prompt (Task 10)
- §5.5 卖方研报 — ✅ sell-side-digest prompt (Task 10)
- §5.6 arena bootstrap — ✅ propose_arena_bootstrap + bootstrap_arena (Task 17)
- User memory "LLM-in-conversation" 硬规 — ✅ 所有 scripts 不 import openai/anthropic；prompt 只定义契约 (Task 11 contract test 不调 LLM)
- User memory "autobuild-meta on ingest" — ✅ `ensure_industry_exists` / `ensure_company_exists` 目录缺失时自动建 (Task 16)
- User memory "autobuild-industry-slug" — ✅ 同上 ensure_industry_exists
- User memory "fix-forward" — ✅ Task 19 (template section_normalize 扩展) + Task 20 (_dedupe_toc regression)

**Plan 1 API 兼容性检查：**
- `industry_io.create_industry / append_observations / append_narrative_block / dedup_observations` — Plan 2 aggregate 调用这些；未修改签名
- `arenas_io.write_definition(..., industry=, battleground_focus=)` — Plan 2 bootstrap_arena 调用；Plan 1 已支持这两个 kwarg
- `company_io.create_company(..., industry_slugs=[...])` — Plan 2 ensure_company_exists 调用
- `claims_io.validate_batch(...)` — Plan 2 现有 `write_claims` 通过 `validate_batch` 自动吃 arena_refs + company_dimension_hint（Plan 1 Task 20 已支持）
- `financials.load_alias_map / FINANCIAL_COLUMNS` — Plan 2 `extract_financial_line_rows` 调用

**Placeholder 扫描：** 无 TBD / TODO / "similar to" / "add error handling" 占位符。所有代码步骤都给出完整实现示例。

**可能的小现场判断题：**
1. Task 4 的 `_FIGURE_CAPTION_PATTERNS` 对中英文混排场景的鲁棒性：实际研报里偶见 "图表 1/Figure 1" 中英双语 caption，当前 regex 独立匹配各自一次 → 可能产两条 figure_context。现场遇到再收敛（去重 by surrounding_text hash）
2. Task 6 的 `extract_financial_line_rows` alias 匹配用 `prefix_re` anchored 到行首；但若某公司的 MD&A 表格在每行前加了"注释：" 前缀 → 跳过匹配。现场遇到时加正则 `^[\\s注注释].*` 前缀白名单
3. Task 16 的 `ensure_company_exists` 签名接受 `currency` — Plan 1 create_company 已默认 USD；非 US 公司主 agent 在 Plan 3 workflow 里应按 market 硬编码 CNY/HKD

这些都属于 engineer 按注释处理的现场题。

---

**Plan 完成并写入 `docs/superpowers/plans/2026-04-26-plan2-ingest-pipeline.md`。下一步等 engineer 执行完 Plan 2，再切 Plan 3（workflow md 升级 + SKILL.md 支持范围扩大）。**
