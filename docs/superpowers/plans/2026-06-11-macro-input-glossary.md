# 宏观全输入源门外汉词典（gloss 层）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 macro_inputs 每个输入源配三层门外汉词条（定义/为什么看/怎么用），机读单一真相源，生成姊妹词典文件 + Web 表可展开，覆盖闸门机械保证零遗漏。

**Architecture:** gloss 作为 `gloss:{define,read,use}` + `family` 两字段写进 `macro_inputs.yaml`（唯一真相源），`macro_registry.py` 登记+校验+缺漏检测；新零-LLM 生成器 `input_glossary.py` 按族系渲染 `outputs/00b_input_glossary.md` 并向 `00_primer.md` §1 注入指向；同一份 gloss 喂进现有 Web 输入源表。覆盖靠 pytest 门禁（填充期软列出、补齐后硬失败）。

**Tech Stack:** Python 3.14 / PyYAML / pytest / FastAPI + Jinja2（现有栈，不引新依赖）。

**Spec:** `docs/superpowers/specs/2026-06-11-macro-input-glossary-design.md`

**约定参数:** slug=`global-macro-rates-liquidity` variant=`opus4.8`（下文命令直接用这对）。

---

## 文件结构

| 文件 | 职责 | 动作 |
|------|------|------|
| `prism/scripts/macro_registry.py` | gloss/family schema + 校验 + 缺漏检测 | Modify |
| `prism/scripts/input_glossary.py` | 零-LLM 生成器：渲染词典 md + 注入 primer 指向 | Create |
| `prism/scripts/outputs.py` | 注册 `00b_input_glossary` 输出键（nav + viewer） | Modify |
| `app/routes/prism.py` | `prism_macro_inputs` 传 `grouped_inputs` | Modify |
| `app/templates/prism/macro_inputs.html` | 族系分组 + 行内可展开 gloss | Modify |
| `prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml` | 每条加 `family`+`gloss`（内容波次） | Modify |
| `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md` | §1 注入指向标记（一次性） | Modify |
| `tests/test_macro_input_glossary.py` | schema/生成器/缺漏/门禁测试 | Create |

---

## Task 1: schema — family/gloss 校验 + 缺漏检测

**Files:**
- Modify: `prism/scripts/macro_registry.py`
- Test: `tests/test_macro_input_glossary.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_macro_input_glossary.py
import tempfile, shutil
from pathlib import Path
import pytest
from prism.scripts import macro_registry as mr


@pytest.fixture
def reg(monkeypatch):
    tmp = Path(tempfile.mkdtemp())
    monkeypatch.setattr(mr, "_PRISM_ROOT", tmp)
    slug, variant = "t-macro", "v"
    mr.create_registry(slug, variant)
    yield slug, variant
    shutil.rmtree(tmp)


def _good_entry(**over):
    e = {
        "name": "JOLTS", "tier": "A", "cadence_type": "event",
        "targets": ["rates"], "mechanism": "CD", "importance": "confirming",
        "causal_sentence": "空缺度量松紧→反应函数→利率。",
        "family": "增长就业",
        "gloss": {"define": "BLS 月度职位空缺/离职率调查",
                   "read": "空缺/离职越高=就业越紧",
                   "use": "离职回落=就业降温→Fed 有降息空间→利好成长"},
    }
    e.update(over)
    return e


def test_valid_family_and_gloss_pass(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry())
    assert mr.validate_registry(slug, variant) == []


def test_unknown_family_rejected(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry(family="瞎写的族"))
    errs = mr.validate_registry(slug, variant)
    assert any("family" in e for e in errs)


def test_partial_gloss_rejected(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry(gloss={"define": "x"}))
    errs = mr.validate_registry(slug, variant)
    assert any("gloss" in e for e in errs)


def test_inputs_missing_gloss_lists_incomplete(reg):
    slug, variant = reg
    mr.upsert_input(slug, variant, _good_entry(name="有词条"))
    bare = _good_entry(name="缺词条")
    bare.pop("gloss"); bare.pop("family")
    mr.upsert_input(slug, variant, bare)
    missing = mr.inputs_missing_gloss(mr.read_registry(slug, variant))
    assert missing == ["缺词条"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_macro_input_glossary.py -q`
Expected: FAIL（`CANONICAL_FAMILIES`/`inputs_missing_gloss` 不存在 + 校验未拒非法值）

- [ ] **Step 3: Implement in `macro_registry.py`**

在枚举区（`VALID_*` 旁，约 line 59 后）加 canonical 族系（**顺序即展示顺序**）：

```python
# 输入源族系（input_glossary 词典/Web 表分组键，顺序=展示顺序，单一真相）
CANONICAL_FAMILIES = (
    "增长就业", "通胀", "货币政策", "流动性·数量", "利率·曲线结构",
    "信用与风险偏好", "资金面咬合", "汇率·跨境套利",
    "中国货币·流动性", "中国增长·外需", "跨资产代理",
)
```

在 `validate_registry` 的 per-entry 循环里（`for e in data["inputs"]:` 内，return 前）加：

```python
        fam = e.get("family")
        if fam is not None and fam not in CANONICAL_FAMILIES:
            errors.append(f"[{name}] family 非法: {fam!r}（须在 CANONICAL_FAMILIES 内）")
        g = e.get("gloss")
        if g is not None:
            if not isinstance(g, dict):
                errors.append(f"[{name}] gloss 须为 dict")
            else:
                for k in ("define", "read", "use"):
                    if not str(g.get(k) or "").strip():
                        errors.append(f"[{name}] gloss 缺 {k}（三键 define/read/use 须齐全非空）")
```

在模块函数区（`validate_registry` 后）加缺漏检测：

```python
def inputs_missing_gloss(registry: dict) -> list[str]:
    """列出「被追踪却缺 gloss/family」的 input name（覆盖闸门 + 生成器共用）。零 LLM。

    被追踪=登记表 inputs 全集（含 monitoring=false 的 CIP 腿）。
    缺=无 family，或 gloss 三键(define/read/use)任一空缺。
    """
    missing = []
    for e in registry.get("inputs") or []:
        g = e.get("gloss") or {}
        ok = e.get("family") and all(str(g.get(k) or "").strip() for k in ("define", "read", "use"))
        if not ok:
            missing.append(e.get("name", "<无名>"))
    return missing
```

并在模块顶部 docstring 的 schema 列表补两行（`name` 块附近）：

```
  family         输入源族系（CANONICAL_FAMILIES 之一），词典/Web 表分组键
  gloss          {define, read, use} 门外汉三层词条（定义/为什么看/怎么用），与 causal_sentence 并存
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_macro_input_glossary.py -q`
Expected: PASS（4 passed）

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/macro_registry.py tests/test_macro_input_glossary.py
git commit -m "feat(prism): macro_inputs 加 family/gloss schema 校验 + 缺漏检测"
```

---

## Task 2: 生成器核心 — 按族系渲染词典正文

**Files:**
- Create: `prism/scripts/input_glossary.py`
- Test: `tests/test_macro_input_glossary.py`（追加）

- [ ] **Step 1: Write the failing test（追加到测试文件）**

```python
def test_build_body_groups_by_family_order(reg):
    slug, variant = reg
    from prism.scripts import input_glossary as ig
    mr.upsert_input(slug, variant, _good_entry(name="核心PCE", family="通胀",
        gloss={"define": "Fed 首选通胀尺", "read": "通胀粘不粘", "use": "超预期→偏鹰→压成长"}))
    mr.upsert_input(slug, variant, _good_entry(name="JOLTS", family="增长就业"))
    body = ig.build_body(mr.read_registry(slug, variant))
    # 族系标题按 CANONICAL_FAMILIES 顺序：增长就业 在 通胀 之前
    assert body.index("### 增长就业") < body.index("### 通胀")
    # 三层都渲染
    assert "BLS 月度职位空缺" in body and "离职回落" in body


def test_build_body_marks_missing(reg):
    slug, variant = reg
    from prism.scripts import input_glossary as ig
    bare = _good_entry(name="缺条"); bare.pop("gloss"); bare.pop("family")
    mr.upsert_input(slug, variant, bare)
    body = ig.build_body(mr.read_registry(slug, variant))
    assert "尚缺 1 条" in body and "缺条" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_macro_input_glossary.py -q`
Expected: FAIL（`input_glossary` 模块不存在）

- [ ] **Step 3: Implement `prism/scripts/input_glossary.py`**

```python
"""macro_inputs → 门外汉输入源词典 markdown（仿 observability_render，零 LLM）。

build_body(registry)        → 按 CANONICAL_FAMILIES 分组的词典正文（不含 frontmatter）
build_glossary_md(slug,var) → 完整文件（frontmatter + body），写 outputs/00b_input_glossary.md
inject_primer_pointer(...)  → 向 00_primer.md §1 标记间注入指向句
spec: 2026-06-11-macro-input-glossary-design.md
"""
from __future__ import annotations
from pathlib import Path
from prism.scripts import macro_registry as mr

_PRISM_ROOT = Path(__file__).resolve().parent.parent

# 输入 name → primer §1 概念词条锚（显式映射，不做模糊匹配）。仅列有对应概念的。
CONCEPT_LINKS = {
    "HY OAS": "信用利差", "IG OAS": "信用利差",
    "净流动性(=资产−TGA−RRP)": "净流动性",
    "USDJPY / 日元 carry": "carry（套息）",
}

def _tier_rank(e: dict) -> int:
    return {"A": 0, "B": 1, "C": 2}.get(e.get("tier"), 9)

def build_body(registry: dict) -> str:
    inputs = registry.get("inputs") or []
    by_fam: dict[str, list] = {f: [] for f in mr.CANONICAL_FAMILIES}
    for e in inputs:
        fam = e.get("family")
        if fam in by_fam and (e.get("gloss") or {}).get("define"):
            by_fam[fam].append(e)
    lines: list[str] = []
    missing = mr.inputs_missing_gloss(registry)
    if missing:
        lines.append(f"> ⚠ 覆盖未完成：尚缺 {len(missing)} 条 gloss/family — "
                     + "、".join(missing) + "\n")
    for fam in mr.CANONICAL_FAMILIES:
        items = sorted(by_fam[fam], key=lambda e: (_tier_rank(e), e["name"]))
        if not items:
            continue
        lines.append(f"### {fam}\n")
        for e in items:
            g = e["gloss"]
            link = ""
            if e["name"] in CONCEPT_LINKS:
                link = f" · 机制见 primer 词条「{CONCEPT_LINKS[e['name']]}」"
            lines.append(f"**{e['name']}**（{e.get('tier','?')}）")
            lines.append(f"- 是什么：{g['define']}")
            lines.append(f"- 为什么看：{g['read']}")
            lines.append(f"- 怎么用：{g['use']}{link} · [表内追踪](macro-inputs)\n")
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_macro_input_glossary.py -q`
Expected: PASS（6 passed）

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/input_glossary.py tests/test_macro_input_glossary.py
git commit -m "feat(prism): input_glossary 生成器核心——按族系渲染词典正文"
```

---

## Task 3: 生成器输出 — 写 00b 文件 + 注入 primer 指向

**Files:**
- Modify: `prism/scripts/input_glossary.py`
- Modify: `prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md`（一次性加标记）
- Test: `tests/test_macro_input_glossary.py`（追加）

- [ ] **Step 1: 一次性给 primer §1 加注入标记**

在 `00_primer.md` §1「术语表」标题行 `## 1. 术语表（大白话词典 …）` 的**正下方**插入：

```markdown
<!-- BEGIN auto:gloss-pointer -->
> 📖 以上为**概念/机制**词典。每个具体**输入源**（NFP/JOLTS/SLOOS/CIP 基差/克强指标…）的「定义·为什么看·怎么用」见姊妹文件 [输入源词典](00b_input_glossary)（按族系分组，机读自动生成）。
<!-- END auto:gloss-pointer -->
```

- [ ] **Step 2: Write the failing test（追加）**

```python
def test_inject_pointer_replaces_between_markers(tmp_path):
    from prism.scripts import input_glossary as ig
    p = tmp_path / "00_primer.md"
    p.write_text("# P\n## 1. 术语表\n<!-- BEGIN auto:gloss-pointer -->\nOLD\n<!-- END auto:gloss-pointer -->\n## 2. 下一节\n", encoding="utf-8")
    ig.inject_primer_pointer(p, "NEWLINE")
    out = p.read_text(encoding="utf-8")
    assert "NEWLINE" in out and "OLD" not in out
    assert "## 2. 下一节" in out  # 标记外正文不动


def test_inject_pointer_missing_markers_raises(tmp_path):
    from prism.scripts import input_glossary as ig
    p = tmp_path / "00_primer.md"
    p.write_text("# P\n无标记\n", encoding="utf-8")
    import pytest as _pt
    with _pt.raises(ValueError):
        ig.inject_primer_pointer(p, "X")
```

- [ ] **Step 3: 在 `input_glossary.py` 追加实现**

```python
_BEGIN = "<!-- BEGIN auto:gloss-pointer -->"
_END = "<!-- END auto:gloss-pointer -->"

def inject_primer_pointer(primer_path: Path, pointer_md: str) -> None:
    """幂等替换 primer §1 标记间内容。标记缺失则报错（须先一次性加标记）。"""
    text = primer_path.read_text(encoding="utf-8")
    if _BEGIN not in text or _END not in text:
        raise ValueError(f"primer 缺注入标记 {_BEGIN}/{_END}，须先一次性加入")
    pre, rest = text.split(_BEGIN, 1)
    _, post = rest.split(_END, 1)
    primer_path.write_text(f"{pre}{_BEGIN}\n{pointer_md}\n{_END}{post}", encoding="utf-8")

def build_glossary_md(slug: str, variant: str) -> str:
    reg = mr.read_registry(slug, variant)
    fm = ("---\n"
          f"slug: {slug}\nvariant: {variant}\noutput_key: 00b_input_glossary\n"
          "type: macro-input-glossary\nversion: 1\n"
          "title: 输入源词典 — 每个宏观输入「定义·为什么看·怎么用」\n"
          "companion: 00_primer.md / m_regime_read.md\n"
          "note: 本文件由 prism.scripts.input_glossary 机读自动生成，勿手改；改 macro_inputs.yaml 的 gloss 字段后重跑。\n"
          "---\n\n# 输入源词典\n\n"
          "> 配套 [领域入门 §1](00_primer)（概念/机制词典）。本文逐**输入源**讲「是什么/为什么看/怎么用」，按族系分组，源自 macro_inputs 登记表的 gloss 字段。\n\n")
    return fm + build_body(reg)

def write_glossary(slug: str, variant: str) -> Path:
    out = _PRISM_ROOT / "topics" / slug / variant / "outputs" / "00b_input_glossary.md"
    out.write_text(build_glossary_md(slug, variant), encoding="utf-8")
    primer = _PRISM_ROOT / "topics" / slug / variant / "outputs" / "00_primer.md"
    if primer.exists():
        ptr = ("> 📖 以上为**概念/机制**词典。每个具体**输入源**的「定义·为什么看·怎么用」"
               "见姊妹文件 [输入源词典](00b_input_glossary)（按族系分组，机读自动生成）。")
        inject_primer_pointer(primer, ptr)
    return out

if __name__ == "__main__":
    import sys
    slug, variant = sys.argv[1], sys.argv[2]
    print("written:", write_glossary(slug, variant))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_macro_input_glossary.py -q`
Expected: PASS（8 passed）

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/input_glossary.py tests/test_macro_input_glossary.py prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md
git commit -m "feat(prism): input_glossary 写 00b 文件 + 幂等注入 primer 指向"
```

---

## Task 4: 注册 00b 输出键（nav + viewer）

**Files:**
- Modify: `prism/scripts/outputs.py:130`（`_EXTRA_OUTPUTS_LABELS`）
- Test: `tests/test_macro_input_glossary.py`（追加）

- [ ] **Step 1: Write the failing test（追加）**

```python
def test_glossary_key_registered():
    from prism.scripts import outputs as o
    keys = [k for k, _ in o._EXTRA_OUTPUTS_LABELS]
    assert "00b_input_glossary" in keys
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_macro_input_glossary.py::test_glossary_key_registered -q`
Expected: FAIL

- [ ] **Step 3: Implement** — 在 `_EXTRA_OUTPUTS_LABELS` 列表加一行：

```python
    ("00b_input_glossary", "输入源词典"),
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_macro_input_glossary.py::test_glossary_key_registered -q`
Expected: PASS

> 说明：`list_outputs` 对 `_EXTRA_OUTPUTS_LABELS` 用「文件存在才列」逻辑（outputs.py:217），`read_output_html`/`prism_output` 按 `{key}.md` 通用读取——故无需新路由，文件生成后即出现在 nav 且可点开。

- [ ] **Step 5: Commit**

```bash
git add prism/scripts/outputs.py tests/test_macro_input_glossary.py
git commit -m "feat(prism): 注册 00b_input_glossary 输出键（nav+viewer 复用）"
```

---

## Task 5: Web 路由 — 传 grouped_inputs

**Files:**
- Modify: `app/routes/prism.py:712-770`（`prism_macro_inputs`）
- Test: `tests/test_macro_input_glossary.py`（追加，直接测纯函数）

为避免在 route 里写分组逻辑导致难测，把分组抽成 `input_glossary.py` 纯函数复用。

- [ ] **Step 1: Write the failing test（追加）**

```python
def test_group_by_family_orders_and_buckets_unknown():
    from prism.scripts import input_glossary as ig
    inputs = [
        {"name": "a", "family": "通胀"},
        {"name": "b", "family": "增长就业"},
        {"name": "c", "family": None},
    ]
    grouped = ig.group_by_family(inputs)
    labels = [fam for fam, _ in grouped]
    assert labels[0] == "增长就业" and "通胀" in labels
    # 未知/缺 family 落「其他」桶，且在最后
    assert labels[-1] == "其他"
    assert [i["name"] for i in dict(grouped)["其他"]] == ["c"]
```

- [ ] **Step 2: Run to verify fail**

Run: `python -m pytest tests/test_macro_input_glossary.py::test_group_by_family_orders_and_buckets_unknown -q`
Expected: FAIL（`group_by_family` 不存在）

- [ ] **Step 3: Implement `group_by_family` in `input_glossary.py`**

```python
def group_by_family(inputs: list[dict]) -> list[tuple[str, list[dict]]]:
    """按 CANONICAL_FAMILIES 顺序分组；未知/缺 family 落「其他」桶置末。保序、不丢条。"""
    buckets: dict[str, list] = {f: [] for f in mr.CANONICAL_FAMILIES}
    other: list[dict] = []
    for e in inputs:
        fam = e.get("family")
        (buckets[fam] if fam in buckets else other).append(e)
    out = [(f, buckets[f]) for f in mr.CANONICAL_FAMILIES if buckets[f]]
    if other:
        out.append(("其他", other))
    return out
```

- [ ] **Step 4: Run to verify pass** — `... -q` Expected: PASS

- [ ] **Step 5: Wire into route** — 在 `prism_macro_inputs` 的 `TemplateResponse` context（`app/routes/prism.py` ~761）加一行（import 复用顶部 `from prism.scripts import ...` 风格，在函数内 import）：

```python
    from prism.scripts import input_glossary as ig
    grouped_inputs = ig.group_by_family(inputs)
```

并在返回的 dict 里加 `"grouped_inputs": grouped_inputs,`（保留原 `"inputs": inputs` 不动——alerts/fetch_errs 等 section 仍用扁平 `inputs`）。

- [ ] **Step 6: Smoke check route imports**

Run: `python -c "import app.routes.prism"`
Expected: 无报错

- [ ] **Step 7: Commit**

```bash
git add app/routes/prism.py prism/scripts/input_glossary.py tests/test_macro_input_glossary.py
git commit -m "feat(prism): macro-inputs 路由传 grouped_inputs（按族系）"
```

---

## Task 6: Web 模板 — 族系分组 + 行内可展开 gloss

**Files:**
- Modify: `app/templates/prism/macro_inputs.html:180-260`（主输入表）

- [ ] **Step 1: 改主表为族系分组 + 唯一锚 + gloss 展开**

把 `app/templates/prism/macro_inputs.html` 的主表循环（`{% for inp in inputs %}` … 对应 `</tbody>`）替换为按 `grouped_inputs` 的嵌套循环，并用 `namespace` 维持全局唯一行号（原 `loop.index0` 在嵌套下不唯一）。在 `<tbody>` 之后、原 `{% for inp in inputs %}` 之前改成：

```jinja
  {% set ns = namespace(i=-1) %}
  {% for fam, fam_inputs in grouped_inputs %}
    <tr class="family-header"><td colspan="13"><b>{{ fam }}</b> <span class="hint">· {{ fam_inputs|length }} 项</span></td></tr>
    {% for inp in fam_inputs %}
      {% set ns.i = ns.i + 1 %}
      {% set d = diff.get(inp.name) %}
      {% set lb_gap = inp.importance == 'load_bearing' and not (d and d.used) %}
      <tr id="input-{{ ns.i }}" data-used="{{ '1' if d and d.used else '0' }}" data-lbunused="{{ '1' if lb_gap else '0' }}"{% if lb_gap %} class="lb-unused-row"{% endif %}>
        <td><code>{{ inp.name }}</code>
          {% if inp.note %}<div class="note-caveat" title="口径/代理说明">ⓘ {{ inp.note }}</div>{% endif %}
          {% if inp.gloss and inp.gloss.define %}
          <details class="gloss-box"><summary>门外汉词条</summary>
            <div class="gloss-line"><b>是什么</b>：{{ inp.gloss.define }}</div>
            <div class="gloss-line"><b>为什么看</b>：{{ inp.gloss.read }}</div>
            <div class="gloss-line"><b>怎么用</b>：{{ inp.gloss.use }}</div>
          </details>
          {% else %}<div class="hint gloss-todo">词条待补</div>{% endif %}
        </td>
```

**注意**：从原 `<td>{{ inp.tier or '—' }}</td>` 起到该行 `</tr>` 的其余单元格**原样保留**，只是把循环体里所有 `loop.index0` 改成 `ns.i`（监控表单的 `anchor` 隐藏字段同改）。结尾把原单层 `{% endfor %}` 改为两层：

```jinja
    {% endfor %}
  {% endfor %}
```

- [ ] **Step 2: 加最小样式**（在该模板 `<style>` 段末尾，约 line 397 附近同级处）：

```css
  .family-header td { background:#f3f6fb; border-top:2px solid #d6deea; font-size:.92em; }
  .gloss-box { margin-top:.3em; font-size:.82em; }
  .gloss-box summary { cursor:pointer; color:#2a5db0; }
  .gloss-line { margin:.15em 0; line-height:1.4; }
  .gloss-todo { font-size:.78em; color:#b08; }
```

- [ ] **Step 3: 渲染冒烟测**（需本地起服务；若无则跳到 Step 4 的离线断言）

Run: `python -c "import app.routes.prism"` 再人工开 `/prism/global-macro-rates-liquidity/opus4.8/macro-inputs` 目视：族系分组出现、点「门外汉词条」展开三层。

- [ ] **Step 4: 离线模板断言（无需起服务）**

```bash
python -c "
import jinja2, pathlib
env=jinja2.Environment(loader=jinja2.FileSystemLoader('app/templates'))
src=pathlib.Path('app/templates/prism/macro_inputs.html').read_text()
env.parse(src); print('template parse OK')
"
```
Expected: `template parse OK`（语法不破）

- [ ] **Step 5: Commit**

```bash
git add app/templates/prism/macro_inputs.html
git commit -m "feat(prism): macro-inputs 表族系分组 + 行内可展开门外汉词条"
```

---

## Task 7: 覆盖闸门 pytest（软列出 → 补齐后硬失败）

**Files:**
- Test: `tests/test_macro_input_glossary.py`（追加，跑真实登记表）

- [ ] **Step 1: 加门禁测试（初始 xfail，填充未完成时不红 CI）**

```python
import pytest

REAL_SLUG, REAL_VARIANT = "global-macro-rates-liquidity", "opus4.8"

@pytest.mark.xfail(reason="gloss 填充进行中，补齐后删此 xfail 转硬门禁", strict=False)
def test_real_registry_full_gloss_coverage():
    from prism.scripts import macro_registry as m
    reg = m.read_registry(REAL_SLUG, REAL_VARIANT)
    missing = m.inputs_missing_gloss(reg)
    assert missing == [], f"尚缺 {len(missing)} 条 gloss/family：{missing}"
```

- [ ] **Step 2: Run（应 xfail，不红）**

Run: `python -m pytest tests/test_macro_input_glossary.py -q`
Expected: PASS + 1 xfailed

- [ ] **Step 3: Commit**

```bash
git add tests/test_macro_input_glossary.py
git commit -m "test(prism): gloss 覆盖闸门（填充期 xfail，补齐后转硬门禁）"
```

> Task 11 末尾全部填齐后回到本测试**删掉 `@pytest.mark.xfail` 装饰器**，门禁转硬：此后任何新输入忘写 gloss → 测试红。

---

## Task 8-11: 内容波次 — 撰写 gloss + family（真正的工作量）

> 这四个任务是**内容撰写**，共用同一套机械流程与撰写准则。每波：编辑 `macro_inputs.yaml` 给该波输入补 `family` + `gloss` → 跑校验 → 跑生成器 → 看缺漏递减 → commit。

**撰写准则（rubric，逐条遵守）：**
- `define`（是什么）：指标本体定义。缩写首次出现给中英全名 + 发布机构 + 频率。例：「JOLTS＝美国劳工部(BLS)月度职位空缺与离职率调查」。
- `read`（为什么看）：它在宏观链里测什么、读哪个方向。大白话、给类比优先。例：「离职率是打工人敢不敢主动跳槽的信心温度计」。
- `use`（怎么用）：高/低、走阔/收窄各意味什么 + 影响什么判断/哪类持仓。**必须可上手**。例：「离职回落+空缺降＝就业降温→Fed 有降息空间→利好长久期成长；反之偏鹰压成长」。
- 每句 ≤ 60 字；不与 `causal_sentence` 逐字重复（那是机制句，这是教学句）。
- `family` 取 `CANONICAL_FAMILIES` 之一（见 Task 1）。CIP 合成腿（Spot/远期点/各币 OIS）归 `汇率·跨境套利`，`use` 注明「供 X 基差合成、不单独读」。
- 准确性优先：拿不准的指标先查 macro_inputs 该条的 `note`/`source_url`/`causal_sentence`，不编。

**每波的机械收尾（four steps，每波都跑）：**

- [ ] **A. 校验** `python -c "from prism.scripts.macro_registry import validate_registry as v; e=v('global-macro-rates-liquidity','opus4.8'); print(e or 'OK')"` → 期望 `OK`
- [ ] **B. 生成** `python -m prism.scripts.input_glossary global-macro-rates-liquidity opus4.8` → 打印 `written: …/00b_input_glossary.md`
- [ ] **C. 看缺漏递减** `python -c "from prism.scripts.macro_registry import read_registry as r, inputs_missing_gloss as m; print(len(m(r('global-macro-rates-liquidity','opus4.8'))), '条待补')"`
- [ ] **D. Commit** `git add prism/topics/global-macro-rates-liquidity/opus4.8/macro_inputs.yaml prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00b_input_glossary.md prism/topics/global-macro-rates-liquidity/opus4.8/outputs/00_primer.md && git commit -m "content(prism): 输入源 gloss 波N（<族系/tier>）"`

### Task 8 — 波 1：tier A 且 importance=load_bearing
选取：`python -c "from prism.scripts.macro_registry import read_registry as r; [print(e['name']) for e in r('global-macro-rates-liquidity','opus4.8')['inputs'] if e.get('tier')=='A' and e.get('importance')=='load_bearing']"`
- [ ] 给上述每条写 `family`+`gloss` → 跑 A/B/C/D。

### Task 9 — 波 2：tier A 且 importance=confirming
选取同上把过滤改 `importance=='confirming'`。
- [ ] 写 → A/B/C/D。

### Task 10 — 波 3：tier B 全部
选取过滤 `tier=='B'`。
- [ ] 写 → A/B/C/D。

### Task 11 — 波 4：tier C + CIP 合成腿 + 其余 background
选取过滤 `tier=='C'` 以及 monitoring.enabled=false 的腿。
- [ ] 写 → A/B/C/D。
- [ ] **收尾**：确认 `inputs_missing_gloss` 返回 0；回 `tests/test_macro_input_glossary.py` 删 `test_real_registry_full_gloss_coverage` 的 `@pytest.mark.xfail` 行 → 跑 `python -m pytest tests/test_macro_input_glossary.py -q` 期望全 PASS（门禁转硬）→ commit：

```bash
git add tests/test_macro_input_glossary.py
git commit -m "test(prism): gloss 覆盖补齐，覆盖闸门转硬门禁"
```

---

## 收尾校验（全部任务后）

- [ ] `python -m pytest tests/test_macro_input_glossary.py -q` → 全 PASS、无 xfail
- [ ] `python -m prism.scripts.input_glossary global-macro-rates-liquidity opus4.8` 二次运行幂等（`git diff` 仅时间戳级/无变化）
- [ ] 目视 `/prism/global-macro-rates-liquidity/opus4.8/00b_input_glossary` 与 `…/macro-inputs`：词典分族系、Web 表可展开、primer §1 有指向链
- [ ] `npx gitnexus analyze` 刷新索引（本期动了 macro_registry/outputs/prism.py 代码符号）

---

## Self-Review 记录

- **Spec 覆盖**：§2 数据模型→Task1；§3 生成器→Task2/3；§4 族系→Task1(CANONICAL_FAMILIES)；§5 覆盖闸门→Task7+Task11 收尾；§6 Web→Task5/6；§7 撰写波次→Task8-11；§9 验收→收尾校验。无遗漏。
- **占位扫描**：无 TBD；内容波次以 rubric+worked example+机械命令落地（数据类内容无法逐条预写，已给准则与可执行选取/校验命令）。
- **类型一致**：`build_body`/`build_glossary_md`/`write_glossary`/`inject_primer_pointer`/`group_by_family`/`inputs_missing_gloss`/`CANONICAL_FAMILIES`/`CONCEPT_LINKS` 跨任务签名一致；模板字段 `inp.gloss.{define,read,use}`/`grouped_inputs` 与路由/生成器一致。
