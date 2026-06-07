# 宏观层（利率/流动性/汇率）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 prism 中新增一个 `macro` type 的横切宏观层（方案 C）：一个 `global-macro-rates-liquidity` topic，产出大白话入门读本（primer）+ 三体制活读数（regime_read）+ 传导地图 sidecar（transmission_map），并在 dashboard 顶部渲染宏观 banner。

**Architecture:** 复用 prism 现有 topic/dashboard 机器。`macro` 作为新 type 接入三张映射表（outputs / case / sidecar），**刻意不进 `_TYPE_TIER`**——宏观是横切层，不参与 company<arena<industry 漏斗父子关系。dashboard 把 macro 从行业/竞技场收集器排除，单独渲染 Section 0 banner（读 transmission_map.yaml 的 `regime` + `holdings`）。MVP 不改任何现有 case 的 DCF。

**Tech Stack:** Python 3（prism/scripts，pytest + monkeypatch 隔离 PRISM_ROOT，PyYAML），Markdown workflow docs，prism CRUD 脚本（零 LLM）。

**Spec:** `docs/superpowers/specs/2026-06-07-macro-rates-liquidity-layer-design.md`

---

## File Structure

| 文件 | 职责 | 动作 |
|------|------|------|
| `prism/scripts/topic.py` | 三张 type 映射表加 `macro` 条目 | Modify |
| `prism/scripts/test_macro_type.py` | macro type 的 schema/flow/排除性回归 | Create |
| `prism/scripts/dashboard.py` | macro sidecar 加载 + banner 收集/渲染 + 从非公司行排除 macro | Modify |
| `prism/scripts/test_dashboard_macro.py` | banner 收集/渲染/排除 回归 | Create |
| `prism/workflows/04-synthesize/_macro_regime.md` | macro 合成路径文档（如何产 primer/regime_read/transmission_map） | Create |
| `.claude/skills/prism/SKILL.md` | 路由表加 macro type 分派 | Modify |
| `prism/topics/global-macro-rates-liquidity/opus4.8/...` | 实体 topic + 三份产出（内容创作） | Create |

---

## Task 0: 建分支

当前在默认分支 `main` 且有无关 WIP。每个后续 Task 只 `git add` 自己改的具体文件，绝不 `git add -A`，避免卷入用户未提交的 prism 改动。

- [ ] **Step 1: 建并切到 feature 分支**

Run:
```bash
cd /Users/yangqi/investing && git checkout -b feat/macro-layer
```
Expected: `Switched to a new branch 'feat/macro-layer'`

---

## Task 1: topic.py 接入 `macro` type（三张映射表）

**Files:**
- Modify: `prism/scripts/topic.py`（`_DECISION_CHAIN_OUTPUTS` 第 26-30 行；`_CASE_BY_TYPE` 第 1709-1713 行；`_SIDECAR_BY_TYPE` 第 1715-1719 行）
- Test: `prism/scripts/test_macro_type.py`

**关键设计：** `macro` 不加进 `_TYPE_TIER`（第 1706 行）。后果（均为期望行为）：`suggest_relatives` 因 `my_tier/otier is None` 跳过 macro → 它永不作为父/子候选出现；`next_stage` 因 macro 既非 company 也非 industry/arena → 落 `else` 默认 7 阶段流水线。

- [ ] **Step 1: 跑 gitnexus 影响分析（CLAUDE.md 强制）**

Run（在对话里调 MCP 工具，非 shell）：`gitnexus_impact({target: "create_topic", direction: "upstream"})`
预期：列出 create_topic 的调用方与受影响 process；向用户汇报 risk level。若 HIGH/CRITICAL 必须先告警再继续。

- [ ] **Step 2: 写失败测试**

Create `prism/scripts/test_macro_type.py`:
```python
"""macro type 接入回归：schema / 默认产出集 / case+sidecar 映射 / 排除 tier 漏斗 / 默认 stage flow。"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts.topic import (
    create_topic,
    read_topic,
    next_stage,
    suggest_relatives,
    _outputs_for_type,
    _CASE_BY_TYPE,
    _SIDECAR_BY_TYPE,
    _TYPE_TIER,
)


@pytest.fixture
def tmp_topics(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    yield tmpdir
    shutil.rmtree(tmpdir)


def test_macro_creates_without_ticker(tmp_topics):
    create_topic(
        slug="global-macro-rates-liquidity", display_name="宏观层",
        topic_type="macro", question="利率/流动性/汇率体制趋势",
        geo="GLOBAL", depth="deep", variant="opus4.8",
        search_terms=["利率", "流动性", "汇率"],
    )
    data = read_topic("global-macro-rates-liquidity", "opus4.8")
    assert data["type"] == "macro"
    assert "ticker" not in data["scope"]


def test_macro_canonical_outputs(tmp_topics):
    assert _outputs_for_type("macro") == ["00_primer", "m_regime_read"]


def test_macro_case_and_sidecar_mapping():
    assert _CASE_BY_TYPE["macro"] == "m_regime_read"
    assert _SIDECAR_BY_TYPE["macro"] == "transmission_map.yaml"


def test_macro_not_in_tier_hierarchy():
    assert "macro" not in _TYPE_TIER


def test_macro_uses_default_stage_flow():
    assert next_stage("macro", "00-init") == "01-roadmap"
    assert next_stage("macro", "04-post-synthesis") == "05-critic-review"
    assert next_stage("macro", "05-critic-review") == "done"


def test_macro_never_suggested_as_relative(tmp_topics):
    create_topic(
        slug="global-macro-rates-liquidity", display_name="宏观层",
        topic_type="macro", question="Q", geo="GLOBAL", depth="deep",
        variant="v", search_terms=["利率"],
    )
    create_topic(
        slug="cn-test-co", display_name="X", topic_type="company",
        question="Q", geo="CN", depth="deep", variant="v",
        short_name="X", ticker="SSE_600519",
    )
    res = suggest_relatives("cn-test-co", "v")
    slugs = [c["slug"] for c in res["parent_candidates"] + res["child_candidates"]]
    assert "global-macro-rates-liquidity" not in slugs
```

- [ ] **Step 3: 跑测试确认失败**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_macro_type.py -v`
Expected: FAIL — `test_macro_canonical_outputs`（macro 走 unknown 兜底返回 `["00_primer","08_living_feed"]`）、`test_macro_case_and_sidecar_mapping`（KeyError）等。

- [ ] **Step 4: 改 `_DECISION_CHAIN_OUTPUTS`**

在 `prism/scripts/topic.py` 第 29 行 `"arena": [...]` 后加一行：
```python
    "arena": ["00_primer", "a_arena_case", "08_living_feed"],
    "macro": ["00_primer", "m_regime_read"],
}
```

- [ ] **Step 5: 改 `_CASE_BY_TYPE`**

第 1709-1713 行 `_CASE_BY_TYPE` 加 macro：
```python
_CASE_BY_TYPE = {
    "company": "c_investment_case",
    "industry": "i_industry_case",
    "arena": "a_arena_case",
    "macro": "m_regime_read",
}
```

- [ ] **Step 6: 改 `_SIDECAR_BY_TYPE`**

第 1715-1719 行 `_SIDECAR_BY_TYPE` 加 macro：
```python
_SIDECAR_BY_TYPE = {
    "company": "07_decision_kit.yaml",
    "industry": "industry_to_arenas.yaml",
    "arena": "peer_matrix.yaml",
    "macro": "transmission_map.yaml",
}
```

- [ ] **Step 7: 跑测试确认通过**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_macro_type.py -v`
Expected: PASS（6 个测试全绿）

- [ ] **Step 8: 跑全量 topic 回归确认零破坏**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_topic_ticker.py prism/scripts/test_topic_phase0.py prism/scripts/test_relatives.py -v`
Expected: PASS（既有行为不变）

- [ ] **Step 9: detect_changes + commit**

Run: `gitnexus_detect_changes()`（确认只动了 topic.py 的预期符号）
```bash
cd /Users/yangqi/investing && git add prism/scripts/topic.py prism/scripts/test_macro_type.py && git commit -m "feat(prism): add macro topic type (outputs/case/sidecar maps, excluded from tier funnel)"
```

---

## Task 2: dashboard.py 渲染宏观 banner

**Files:**
- Modify: `prism/scripts/dashboard.py`（加 `_load_macro_sidecar`、`_sidecar_loader_for` 加 macro 分支、`_collect_non_company_rows` 排除 macro、新增 `_collect_macro_banner`、`_render_dashboard` 加 banner 段、`build` 串联）
- Test: `prism/scripts/test_dashboard_macro.py`

**transmission_map.yaml schema（banner 消费契约）：**
```yaml
slug: global-macro-rates-liquidity
variant: opus4.8
generated: "2026-06-07T00:00:00Z"
regime:
  rates:     {state: "下行", note: "美联储转向在即"}
  liquidity: {state: "偏松", note: "净流动性回升"}
  fx:        {state: "人民币承压", note: "中美利差倒挂"}
  composite: "温和宽松早期"
  conviction: 5.5
holdings:
  - {slug: cn-popmart, display_name: 泡泡玛特, duration: long, rate_beta: high,
     usd_exposure: low, liquidity_beta: high, exposure_score: high,
     regime_favor: [复苏, 全面宽松], regime_hurt: [滞胀, 全面收紧],
     plain: "高 PE 成长，利率一升风险偏好一降先挨打"}
```
`exposure_score: high` 决定该持仓是否进 banner 的"最暴露"列表。

- [ ] **Step 1: 跑 gitnexus 影响分析**

Run: `gitnexus_impact({target: "build", direction: "upstream"})` 与 `gitnexus_impact({target: "_render_dashboard", direction: "upstream"})`
预期：列出 dashboard 重建触发点（topic.py `_trigger_dashboard`、web 路由）。向用户汇报 risk。

- [ ] **Step 2: 写失败测试**

Create `prism/scripts/test_dashboard_macro.py`:
```python
"""宏观 banner 回归：sidecar 加载 / banner 收集 / 渲染 / 从非公司行排除 macro。"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts import topic as topic_io
from prism.scripts import dashboard


@pytest.fixture
def macro_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    topic_io.create_topic(
        slug="global-macro-rates-liquidity", display_name="宏观层",
        topic_type="macro", question="Q", geo="GLOBAL", depth="deep",
        variant="opus4.8", search_terms=["利率"],
    )
    sidecar = {
        "slug": "global-macro-rates-liquidity", "variant": "opus4.8",
        "generated": "2026-06-07T00:00:00Z",
        "regime": {
            "rates": {"state": "下行", "note": "美联储转向在即"},
            "liquidity": {"state": "偏松", "note": "净流动性回升"},
            "fx": {"state": "人民币承压", "note": "中美利差倒挂"},
            "composite": "温和宽松早期",
            "conviction": 5.5,
        },
        "holdings": [
            {"slug": "cn-popmart", "display_name": "泡泡玛特",
             "exposure_score": "high", "plain": "高PE成长，利率敏感"},
            {"slug": "cn-premium-baijiu", "display_name": "白酒",
             "exposure_score": "low", "plain": "防御"},
        ],
    }
    out = tmpdir / "topics" / "global-macro-rates-liquidity" / "opus4.8" / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "transmission_map.yaml").write_text(
        yaml.dump(sidecar, allow_unicode=True, sort_keys=False), encoding="utf-8")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_load_macro_sidecar(macro_env):
    sc = dashboard._load_macro_sidecar("global-macro-rates-liquidity", "opus4.8")
    assert sc["regime"]["composite"] == "温和宽松早期"


def test_collect_macro_banner(macro_env):
    banner = dashboard._collect_macro_banner()
    assert banner is not None
    assert banner["regime"]["composite"] == "温和宽松早期"
    assert [h["slug"] for h in banner["exposed"]] == ["cn-popmart"]


def test_banner_rendered(macro_env):
    company_rows = dashboard._collect_company_rows()
    other_rows = dashboard._collect_non_company_rows()
    banner = dashboard._collect_macro_banner()
    md = dashboard._render_dashboard(company_rows, other_rows, banner)
    assert "## 🌐 宏观体制" in md
    assert "温和宽松早期" in md
    assert "泡泡玛特" in md


def test_macro_excluded_from_other_rows(macro_env):
    other_rows = dashboard._collect_non_company_rows()
    assert all(r["type"] != "macro" for r in other_rows)


def test_no_macro_topic_banner_none(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()
    try:
        assert dashboard._collect_macro_banner() is None
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
```

- [ ] **Step 3: 跑测试确认失败**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_dashboard_macro.py -v`
Expected: FAIL — `_load_macro_sidecar` / `_collect_macro_banner` 不存在（AttributeError），`_render_dashboard` 只接 2 个参数（TypeError）。

- [ ] **Step 4: 加 `_load_macro_sidecar`**

在 `prism/scripts/dashboard.py` 第 49 行（`_load_arena_sidecar` 之后）加：
```python
def _load_macro_sidecar(slug: str, variant: str) -> dict | None:
    path = PRISM_ROOT / "topics" / slug / variant / "outputs" / "transmission_map.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
```

- [ ] **Step 5: `_sidecar_loader_for` 加 macro 分支**

在第 211-217 行函数里，`if topic_type == "arena":` 分支后加：
```python
    if topic_type == "macro":
        return _load_macro_sidecar
```

- [ ] **Step 6: `_collect_non_company_rows` 排除 macro**

第 328-330 行循环里把跳过条件从只跳 company 改为也跳 macro：
```python
    for topic in list_topics():
        if topic.get("type") in ("company", "macro"):
            continue
        slug_variants.setdefault(topic["slug"], []).append(topic)
```

- [ ] **Step 7: 加 `_collect_macro_banner`**

在 `_collect_non_company_rows`（第 380 行 return 之后）后新增：
```python
def _collect_macro_banner() -> dict | None:
    """收集唯一 macro topic 的体制读数 + 高暴露持仓，供 dashboard Section 0 banner。

    只取第一个 macro slug（设计上只期望一个宏观层）。无 macro topic 或无
    transmission_map.yaml → 返回 None（banner 整段不渲染）。
    """
    from prism.scripts.topic import list_topics
    slug_variants: dict[str, list[dict]] = {}
    for topic in list_topics():
        if topic.get("type") != "macro":
            continue
        slug_variants.setdefault(topic["slug"], []).append(topic)
    if not slug_variants:
        return None
    slug, topics = sorted(slug_variants.items())[0]
    topic = _canonical_variant(topics)
    variant = topic.get("variant", "")
    sidecar = _load_macro_sidecar(slug, variant)
    if not sidecar:
        return None
    holdings = sidecar.get("holdings", []) or []
    exposed = [h for h in holdings if h.get("exposure_score") == "high"]
    return {
        "slug": slug,
        "variant": variant,
        "display_name": topic.get("display_name", slug),
        "regime": sidecar.get("regime", {}) or {},
        "exposed": exposed,
        "freshness_days": _days_stale(sidecar.get("generated")),
    }
```

- [ ] **Step 8: `_render_dashboard` 加 banner 段 + 改签名**

把第 413 行签名改为：
```python
def _render_dashboard(company_rows: list[dict], other_rows: list[dict], macro: dict | None = None) -> str:
```
在 header 摘要块之后（第 425 行 `f"",` 结束、`# ── Section 1` 之前）插入 banner 渲染：
```python
    # ── Section 0: 宏观体制 banner ───────────────────────────────────────────
    if macro:
        rg = macro["regime"]
        fr = {"freshness_days": macro["freshness_days"],
              "freshness_emoji": _freshness_emoji(macro["freshness_days"])}
        lines += [
            "## 🌐 宏观体制",
            "",
            f"> [{macro['display_name']}](/prism/{macro['slug']}/{macro['variant']})　{_fmt_freshness(fr)}",
            "",
            "| 维度 | 体制 | 说明 |",
            "|------|------|------|",
            f"| 利率 | {rg.get('rates', {}).get('state', '—')} | {rg.get('rates', {}).get('note', '—')} |",
            f"| 流动性 | {rg.get('liquidity', {}).get('state', '—')} | {rg.get('liquidity', {}).get('note', '—')} |",
            f"| 汇率 | {rg.get('fx', {}).get('state', '—')} | {rg.get('fx', {}).get('note', '—')} |",
            "",
        ]
        composite = rg.get("composite")
        if composite:
            conv = rg.get("conviction")
            conv_str = f"（强度 {conv}）" if conv is not None else ""
            lines += [f"**综合判断{conv_str}**：{composite}", ""]
        if macro["exposed"]:
            names = "、".join(h.get("display_name", h.get("slug", "")) for h in macro["exposed"])
            lines += [f"**当前体制最暴露持仓**：{names}", ""]
        lines += ["---", ""]
```

- [ ] **Step 9: `build()` 串联 banner**

第 739-744 行 `build()` 改为：
```python
def build() -> Path:
    """Build dashboard.md and return its path."""
    company_rows = _collect_company_rows()
    other_rows = _collect_non_company_rows()
    macro = _collect_macro_banner()
    content = _render_dashboard(company_rows, other_rows, macro)
    DASHBOARD_PATH.write_text(content, encoding="utf-8")
```

- [ ] **Step 10: 跑测试确认通过**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_dashboard_macro.py -v`
Expected: PASS（5 个测试全绿）

- [ ] **Step 11: 跑既有 dashboard 相关回归**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_render_markdown.py prism/scripts/test_stage_progress.py -v`
Expected: PASS（`_render_dashboard` 新增的 macro 默认 None，既有调用零影响）

- [ ] **Step 12: detect_changes + commit**

Run: `gitnexus_detect_changes()`
```bash
cd /Users/yangqi/investing && git add prism/scripts/dashboard.py prism/scripts/test_dashboard_macro.py && git commit -m "feat(prism): render macro regime banner on dashboard (Section 0)"
```

---

## Task 3: 合成路径文档 `_macro_regime.md`

**Files:**
- Create: `prism/workflows/04-synthesize/_macro_regime.md`

这是 macro type 的合成 workflow（对标 `_arena_funnel.md`）。定义"理解先行 + 因果链"的产出流程，零代码、纯指令文档。

- [ ] **Step 1: 读参照文档**

Run: `cd /Users/yangqi/investing && sed -n '1,60p' prism/workflows/04-synthesize/_arena_funnel.md`
目的：对齐既有合成文档的语气、Step 结构、脚本调用惯例（set_output_referenced_mats / set_output_critic_passed / set_thesis / set_decomposition）。

- [ ] **Step 2: 写 `_macro_regime.md`**

Create `prism/workflows/04-synthesize/_macro_regime.md`，必须包含以下小节（每节给出可执行指令，非占位）：

1. **触发**：`「合成 {slug}」且 topic.type==macro` → 读本文档。
2. **因果链总纲**：L1 输入源 → L2 驱动变量（增长/通胀/政策反应/财政）→ L3 三体制（利率/流动性/汇率）→ L4 传导/决策。（引 spec §3。）
3. **Step 1 亲属 hook**：调 `get_relative_outputs` —— macro 无亲属时退化独立合成（macro 不在 tier 漏斗内，正常返回 parent=None/children=[]）。
4. **Step 2 产 `00_primer.md`（入门读本）**：
   - frontmatter `depth: deep`。
   - 必含小节：术语表（大白话）、L1→L4 因果链讲解、三体制各自小框架、四条传导渠道、**「根本争议」节（5-7 条）**、**「自检清单」节**（满足 `primer_quality_gate` 的 deep 地板：正文 ≥6000 字 + 含「争议」+ 含「自检」）。
   - 美/全球为主线，中国第二节。
   - 收尾：先 `set_output_critic_passed(slug,'00_primer',variant)` 再 `set_output_status(slug,'00_primer','fresh',variant,version=1)`（否则 deep 软门禁降级 draft）。
5. **Step 3 产 `m_regime_read.md`（三体制活读数）**：
   - 三体制各一节，每节：关键输入指标 → 内部逻辑 → 输出形态 + **每指标三句注解**（`这是什么 / 为什么看它 / 现在说明什么`）。
   - 顶部「综合判断 + 强度分（0-10）」。
   - 收尾 `set_output_referenced_mats(slug,'m_regime_read',mat_ids,variant)` + `set_output_status(...,'fresh',version=1)`。
6. **Step 4 产 `transmission_map.yaml`（传导地图）**：严格按 Task 2 的 schema 写 `regime` 块 + `holdings` 数组（覆盖 dashboard 现有持仓）。落盘后调 `set_output_referenced_mats(slug,'transmission_map',mat_ids,variant)` 触发 dashboard 重建。
7. **Step 5 thesis/decomposition**：`set_thesis`（三体制综合判断，summary≤120 字）+ `set_decomposition`（命门=当前最不确定的宏观岔口）。
8. **数据来源约定**：美国指标走 FRED（公开）/ web 搜索；中国指标走 web/exa（统计局/央行/Wind 转载）。MVP 允许手动快照，须在 regime_read 标注 `data_freshness`。

- [ ] **Step 3: commit**

```bash
cd /Users/yangqi/investing && git add prism/workflows/04-synthesize/_macro_regime.md && git commit -m "docs(prism): add macro regime synthesis workflow (_macro_regime.md)"
```

---

## Task 4: SKILL.md 路由接入 macro

**Files:**
- Modify: `.claude/skills/prism/SKILL.md`（第 16 行「合成」路由行；第 29 行 Prism Root outputs 描述）

- [ ] **Step 1: 改「合成」路由行**

第 16 行末尾（`arena → \`a_arena_case.md\`` 之后）追加 macro 分派：
```
；macro → `04-synthesize/_macro_regime.md`（横切宏观层：primer 读本 + m_regime_read 三体制活读数 + transmission_map 传导地图）
```

- [ ] **Step 2: 改 Prism Root outputs 描述**

第 29 行 outputs 说明里，sidecar 列举处追加：`macro \`transmission_map\``；case 列举处追加：`macro \`m_regime_read\``。

- [ ] **Step 3: commit**

```bash
cd /Users/yangqi/investing && git add .claude/skills/prism/SKILL.md && git commit -m "docs(prism): route macro topic type to _macro_regime synthesis"
```

---

## Task 5: 建实体 topic + 创作三份产出（MVP 内容）

**Files:**
- Create: `prism/topics/global-macro-rates-liquidity/opus4.8/{topic.yaml, outputs/00_primer.md, outputs/m_regime_read.md, outputs/transmission_map.yaml}`

> 这是宏观层的首个真实产出，也是用户的学习交付物。内容创作在对话里完成，数据用 web_search/exa 取 2026-06 当期值（date=2026-06-07）。**先确认 dashboard 现有持仓清单**作为 transmission_map 的 holdings 全集。

- [ ] **Step 1: 列出当前持仓全集**

Run: `cd /Users/yangqi/investing && python3 -c "from prism.scripts.topic import list_topics; [print(t['slug'], t.get('type')) for t in list_topics() if t.get('type')=='company']"`
预期：得到 company 持仓 slug 清单（泡泡玛特/拼多多/富途/茅台/泸州老窖等）→ transmission_map.holdings 必须逐一覆盖。

- [ ] **Step 2: 建 topic**

Run:
```bash
cd /Users/yangqi/investing && python3 -c "from prism.scripts.topic import create_topic; create_topic('global-macro-rates-liquidity','宏观层 (利率/流动性/汇率体制)','macro','利率/流动性/汇率三体制趋势及其对组合的传导','GLOBAL','deep','opus4.8', search_terms=['利率','流动性','汇率'])"
```
Expected: 打印 topic.yaml 路径，无报错。

- [ ] **Step 3: 创作 `00_primer.md`（入门读本）**

按 `_macro_regime.md` Step 2 的小节清单创作（web 取背景）。验收：`depth: deep` frontmatter、正文 ≥6000 字、含「争议」节、含「自检」节、覆盖 L1→L4 + 三体制 + 四渠道、美主线+中国第二节、大白话术语表。
落盘后：
```bash
cd /Users/yangqi/investing && python3 -c "from prism.scripts.topic import set_output_critic_passed, set_output_status; set_output_critic_passed('global-macro-rates-liquidity','opus4.8','00_primer'); set_output_status('global-macro-rates-liquidity','00_primer','fresh','opus4.8',version=1)"
```
校验未被降级 draft：
```bash
cd /Users/yangqi/investing && python3 -c "from prism.scripts.topic import read_topic; print(read_topic('global-macro-rates-liquidity','opus4.8')['outputs_state']['00_primer']['status'])"
```
Expected: `fresh`（若打印 `draft` → 补足 争议/自检/字数 后重跑）。

- [ ] **Step 4: 创作 `m_regime_read.md`（三体制活读数）**

按 `_macro_regime.md` Step 3 创作：三体制各一节、每指标三句注解、顶部综合判断+强度。web 取 2026-06 当期指标值。落盘后：
```bash
cd /Users/yangqi/investing && python3 -c "from prism.scripts.topic import set_output_status, set_data_freshness; set_output_status('global-macro-rates-liquidity','m_regime_read','fresh','opus4.8',version=1); set_data_freshness('global-macro-rates-liquidity','m_regime_read','2026-06-07','opus4.8')"
```

- [ ] **Step 5: 创作 `transmission_map.yaml`**

严格按 Task 2 schema：`regime` 块（rates/liquidity/fx 各 state+note、composite、conviction）+ `holdings`（Step 1 的每个持仓一条，4 标签 + regime_favor/hurt + plain + exposure_score）。落盘到 `outputs/transmission_map.yaml`，然后触发 dashboard 重建：
```bash
cd /Users/yangqi/investing && python3 -c "from prism.scripts.topic import set_output_referenced_mats; set_output_referenced_mats('global-macro-rates-liquidity','transmission_map',[],'opus4.8')"
```

- [ ] **Step 6: 重建并核验 dashboard banner**

Run: `cd /Users/yangqi/investing && python3 -m prism.scripts.dashboard && grep -n "🌐 宏观体制" prism/dashboard.md`
Expected: 命中 banner 标题行；目视确认三体制表 + 综合判断 + 最暴露持仓正确。

- [ ] **Step 7: 推进 stage 到完成**

Run:
```bash
cd /Users/yangqi/investing && python3 -c "from prism.scripts.topic import set_stage; set_stage('global-macro-rates-liquidity','done','opus4.8')"
```

- [ ] **Step 8: commit**

```bash
cd /Users/yangqi/investing && git add prism/topics/global-macro-rates-liquidity prism/dashboard.md && git commit -m "feat(prism): seed macro layer topic — primer + regime read + transmission map"
```

---

## Task 6: 收尾验证

- [ ] **Step 1: 全量 macro 相关测试**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_macro_type.py prism/scripts/test_dashboard_macro.py -v`
Expected: PASS（全绿）

- [ ] **Step 2: 不回归既有套件（topic + dashboard 渲染）**

Run: `cd /Users/yangqi/investing && python -m pytest prism/scripts/test_topic_ticker.py prism/scripts/test_topic_phase0.py prism/scripts/test_relatives.py prism/scripts/test_render_markdown.py -v`
Expected: PASS

- [ ] **Step 3: detect_changes 总核**

Run: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})`
Expected: 受影响符号限于 topic.py 三张表 + dashboard.py banner 链路，无意外扩散。

- [ ] **Step 4: 汇报 + 决定合并方式**

向用户汇报：banner 截图/文本、primer 字数与 gate 状态、测试结果。询问是否 merge `feat/macro-layer` 到 main / 开 PR。

---

## 验收标准（对齐 spec §8）

- 用户能看懂 `m_regime_read.md` 里每个指标在说什么（三句注解齐全）。
- 三体制读数给出一句综合判断 + 强度分。
- dashboard 顶部 banner 渲染体制 + 最暴露持仓。
- `transmission_map.yaml` 覆盖全部现有 company 持仓。
- macro type 与现有 topic/dashboard 机器同构（web 自动反映），且不进 tier 漏斗、不污染 relink 候选。
- 既有测试套件零回归。
