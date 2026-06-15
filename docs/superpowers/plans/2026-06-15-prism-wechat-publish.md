# prism 产出「公众号版」一键发布 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 prism 的 primer / case 产出生成「纯显示层清洗 + 内联样式」的微信公众号版，提供一键复制富文本的预览页，不改动任何现有产出内容或渲染路径。

**Architecture:** 新增独立纯函数模块 `prism/scripts/wechat_export.py`（清洗 → 渲染 → 追加 K# 对照表 → bs4 内联样式）+ 新路由 `…/{output_key}/wechat` + 新模板 `prism/wechat.html`（含复制按钮）。现有 `read_output_html`/`render_markdown`/`output.html` 零改动，仅给 `output.html` 纯增一个条件链接。全流程零 LLM、纯确定性、可重放。

**Tech Stack:** Python 3、Python-Markdown（现有 `outputs.render_markdown`）、BeautifulSoup4（已在 requirements）、FastAPI + Jinja2、pytest。

**前置（执行前先做）：** 当前在 `main` 且 working tree 有与本任务无关的改动。先开分支隔离：
```bash
git checkout -b feat/prism-wechat-publish
```
本计划每个 commit 都只 `git add` 本任务涉及的具体文件，绝不 `git add -A`，以免扫入无关改动。

**清洗契约（设计依据，所有 strip 函数遵守）：**
- 去除：`mat-XXXXXX` 引用（含 `[]`/`()`/`（）`/裸/斜杠连写 `mat-aaaaaa/bbbbbb`）、`> 🧪 承重充分性` banner、`> **vN changelog` 修订史块、`> 读者画像…` blockquote、`本文假定读者已读…` 阅读假定行、反引号包裹的产出 key/文件名、文末 `## 来源说明`/`## 信息来源`/`## 数据来源` 整段。
- 保留：`K#`（命门编号）原样在正文 + 文末自动追加 `K#` 对照表；`Q#`（日历季度）完全不动；所有实质分析散文一字不改。

---

### Task 1: 模块骨架 + `strip_mat_refs`

**Files:**
- Create: `prism/scripts/wechat_export.py`
- Test: `prism/scripts/test_wechat_export.py`

- [ ] **Step 1: 写失败测试**

Create `prism/scripts/test_wechat_export.py`:

```python
"""wechat_export 纯函数单测。零 LLM、零 I/O（除显式读真实 topic 的集成测试）。"""
from prism.scripts import wechat_export as wx


def test_strip_mat_refs_bracketed():
    assert wx.strip_mat_refs("毛利率 87.1%[mat-50b810]、净利率 49%。") == "毛利率 87.1%、净利率 49%。"


def test_strip_mat_refs_consecutive_brackets():
    assert wx.strip_mat_refs("双杀[mat-50b810][mat-6dcbc7]。") == "双杀。"


def test_strip_mat_refs_fullwidth_paren():
    assert wx.strip_mat_refs("已坐实（mat-4d2cb9）。") == "已坐实。"


def test_strip_mat_refs_bare_with_space():
    assert wx.strip_mat_refs("洋河 mat-c27f59 领先。") == "洋河 领先。"


def test_strip_mat_refs_slash_joined():
    assert wx.strip_mat_refs("洋河 mat-c27f59/44114b、古井 mat-08c1da/ef1ded。") == "洋河、古井。"


def test_strip_mat_refs_idempotent():
    once = wx.strip_mat_refs("毛利率[mat-50b810]、成交额（mat-6dcbc7）、裸 mat-7d7192。")
    assert wx.strip_mat_refs(once) == once


def test_strip_mat_refs_keeps_non_ref_text():
    # 不误删正文里非引用的普通词（'material' / 'format' 含 'mat' 但非 mat-XXXXXX）
    assert wx.strip_mat_refs("material 与 format 不动。") == "material 与 format 不动。"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -q`
Expected: FAIL（`ModuleNotFoundError` 或 `AttributeError: module 'wechat_export' has no attribute 'strip_mat_refs'`）。

- [ ] **Step 3: 写最小实现**

Create `prism/scripts/wechat_export.py`:

```python
"""微信公众号版产出生成（纯显示层清洗 + 内联样式）。零 LLM、纯函数、可重放。

与 outputs.read_output_html 的区别：后者是系统内 canonical 视图（保留 mat 引用并链到
诊断页）；本模块产出的是发给公众号的独立文章——去掉对独立阅读无意义的引用 / QA banner /
修订史 / 内部指针 / 出处账本，保留 K# 并在文末追加对照表，最后把样式内联以适配公众号
编辑器（会丢弃 <style>/class/id）。绝不改动任何源文件或现有渲染路径。
"""
from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

from . import outputs as outputs_io

_PRISM_ROOT = Path(__file__).resolve().parent.parent

# 开放微信版的产出 key（领域入门 + 三类决策链 case）。
WECHAT_OUTPUT_KEYS = ("00_primer", "c_investment_case", "i_industry_case", "a_arena_case")

# 一个 mat 引用「核」：mat-6位hex，可后接斜杠连写的 6 位 hex（mat-aaaaaa/bbbbbb）。
_MAT_RUN = r"mat-[0-9a-f]{6}(?:/[0-9a-f]{6})*"
# 括号包裹（[]/()/全角（））+ 可选前导空白 → 整体吃掉。
_BRACKETED_MAT = re.compile(r"[ \t]*[\[\(（]\s*" + _MAT_RUN + r"\s*[\]\)）]")
# 裸引用 + 可选前导空白。
_BARE_MAT = re.compile(r"[ \t]*" + _MAT_RUN)


def strip_mat_refs(text: str) -> str:
    """去除正文里的 mat-XXXXXX 资料引用（四种写法 + 斜杠连写），并收拾残留空白/悬空标点。幂等。"""
    text = _BRACKETED_MAT.sub("", text)
    text = _BARE_MAT.sub("", text)
    # 收拾残留：标点前空格、空括号、双空格。
    text = re.sub(r"[ \t]+([，。、；：！？）】」』])", r"\1", text)
    text = re.sub(r"([（【「『])[ \t]+", r"\1", text)
    text = re.sub(r"（\s*）|\(\s*\)|\[\s*\]", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -q`
Expected: PASS（7 passed）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/wechat_export.py prism/scripts/test_wechat_export.py
git commit -m "feat(prism/wechat): 新增 wechat_export 模块骨架 + strip_mat_refs"
```

---

### Task 2: blockquote 行级清洗（banner / changelog / 读者画像 / 阅读假定）

**Files:**
- Modify: `prism/scripts/wechat_export.py`
- Test: `prism/scripts/test_wechat_export.py`

- [ ] **Step 1: 写失败测试（追加到测试文件末尾）**

```python
def test_strip_critic_banner():
    src = "标题\n\n> 🧪 **承重充分性（05-critic 第4轮）**：够。\n\n正文。"
    assert "承重充分性" not in wx.strip_blockquote_lines(src)
    assert "正文。" in wx.strip_blockquote_lines(src)


def test_strip_changelog_blocks():
    src = "标题\n\n> **v6 changelog（05-critic 第3轮）**：改了环④。\n> **v5 changelog**：改了环②。\n\n正文。"
    out = wx.strip_blockquote_lines(src)
    assert "changelog" not in out
    assert "正文。" in out


def test_strip_reader_profile():
    src = "# Primer\n\n> 读者画像：你会看 PE、市值，读完应能拿起本 topic 的 case。\n\n## 0. 正文"
    out = wx.strip_blockquote_lines(src)
    assert "读者画像" not in out
    assert "## 0. 正文" in out


def test_strip_reading_assumption():
    src = "> 本文假定读者已读 `00_primer.md`（不重教）。\n\n正文。"
    out = wx.strip_blockquote_lines(src)
    assert "本文假定读者已读" not in out
    assert "正文。" in out


def test_strip_blockquote_lines_keeps_normal_quotes():
    # 普通 blockquote（术语锚定、提示）不误删
    src = "> 术语锚定：bps = 0.01%。\n\n正文。"
    assert "术语锚定" in wx.strip_blockquote_lines(src)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -k blockquote -q`
Expected: FAIL（`AttributeError: ... 'strip_blockquote_lines'`）。

- [ ] **Step 3: 写实现（追加到 `wechat_export.py`）**

```python
# 需整行删除的 blockquote：banner / 修订史 / 读者画像 / 阅读假定。均为 `> …` 单行内部架子。
# 锚定行首 `>` + 特征前缀，普通 blockquote（术语锚定/提示/引述）不命中。
_DROP_BLOCKQUOTE_PATTERNS = (
    re.compile(r"^\s*>\s*🧪"),                       # 承重充分性 banner
    re.compile(r"^\s*>\s*\*\*v\d+\s*changelog", re.I),  # vN changelog 修订史
    re.compile(r"^\s*>\s*读者画像"),                  # primer 读者画像
    re.compile(r"^\s*>\s*本文假定读者"),              # case 阅读假定指针
)


def strip_blockquote_lines(text: str) -> str:
    """整行删除内部架子型 blockquote（banner/changelog/读者画像/阅读假定）。
    只命中行首 `>` + 特征前缀，普通 blockquote 不动。"""
    kept = [
        line for line in text.split("\n")
        if not any(p.match(line) for p in _DROP_BLOCKQUOTE_PATTERNS)
    ]
    return "\n".join(kept)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -q`
Expected: PASS（12 passed）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/wechat_export.py prism/scripts/test_wechat_export.py
git commit -m "feat(prism/wechat): strip_blockquote_lines 去 banner/changelog/读者画像/阅读假定"
```

---

### Task 3: 结构清洗（文末出处段 + 内联文件名/产出 key 引用）

**Files:**
- Modify: `prism/scripts/wechat_export.py`
- Test: `prism/scripts/test_wechat_export.py`

- [ ] **Step 1: 写失败测试（追加）**

```python
def test_strip_sources_section_to_eof():
    src = "## 8. 估值\n\n正文。\n\n## 来源说明\n\n| 来源 | 占比 |\n|---|---|\n引用 mat：mat-50b810。"
    out = wx.strip_sources_section(src)
    assert "来源说明" not in out
    assert "引用 mat" not in out
    assert "## 8. 估值" in out and "正文。" in out


def test_strip_sources_section_bounded_by_next_h2():
    # 信息来源 后还有 链体检：只删 信息来源 段，链体检 保留（交验证步定夺）
    src = "## 正文\n\nX。\n\n## 信息来源\n\n- findings：mat-b01cff。\n\n## 链体检\n\nY。"
    out = wx.strip_sources_section(src)
    assert "信息来源" not in out and "findings" not in out
    assert "## 链体检" in out and "Y。" in out


def test_strip_sources_section_absent():
    src = "## 正文\n\n没有出处段。"
    assert wx.strip_sources_section(src) == src


def test_strip_inline_output_refs():
    src = "见 `c_investment_case` 与 `00_primer.md`，详见 `thesis_v5.md`。"
    out = wx.strip_inline_output_refs(src)
    for tok in ("c_investment_case", "00_primer", "thesis_v5", "`"):
        assert tok not in out


def test_strip_inline_output_refs_keeps_normal_code():
    src = "用 `ROIC` 与 `funded account` 这两个词。"
    assert wx.strip_inline_output_refs(src) == src
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -k "sources_section or inline_output" -q`
Expected: FAIL（缺函数）。

- [ ] **Step 3: 写实现（追加）**

```python
# 文末出处/方法论段标题（每个从其标题删到下一个 H2 或 EOF，故不会吞掉相邻别的小节）。
_SOURCES_HEADING = re.compile(r"^#{2,3}\s*(来源说明|信息来源|数据来源)\s*$")
_H2 = re.compile(r"^#{2}\s")

# 反引号包裹的内部产出 key / 文件名（c_investment_case / 00_primer(.md) / thesis_vN(.md) /
# _prism_reading_guide.md / *_decision_kit / a_arena_case / i_industry_case 等）。
_INLINE_OUTPUT_REF = re.compile(
    r"`\s*(?:_prism_reading_guide|thesis_v\d+|decomposition_v\d+|roadmap"
    r"|\d{2}[a-z]?_[a-z_]+|[cia]_[a-z_]+case|[a-z_]*decision_kit"
    r"|peer_matrix|industry_to_arenas)(?:\.\w+)?\s*`"
)


def strip_sources_section(text: str) -> str:
    """删除文末「来源说明/信息来源/数据来源」整段：从其标题删到下一个 H2 标题或文末。
    只删命名段本身，不波及相邻小节（如 industry case 的 链体检）。"""
    lines = text.split("\n")
    start = next((i for i, l in enumerate(lines) if _SOURCES_HEADING.match(l)), None)
    if start is None:
        return text
    end = next((j for j in range(start + 1, len(lines)) if _H2.match(lines[j])), len(lines))
    del lines[start:end]
    # 收尾去掉因删段尾留下的多余空行
    return "\n".join(lines).rstrip() + "\n"


def strip_inline_output_refs(text: str) -> str:
    """去除反引号包裹的内部产出 key / 文件名引用（独立文章里是文件名乱码）。
    普通行内代码（业务术语 `ROIC` 等）不命中。"""
    text = _INLINE_OUTPUT_REF.sub("", text)
    # 删后常见残留：成对空括号、悬空「与 」「，」之类——只收拾明确的空括号。
    text = re.sub(r"（\s*）|\(\s*\)", "", text)
    return text
```

> 注：`strip_inline_output_refs` 只删反引号包裹的产出 key；不对裸词做全局替换，避免误伤分析散文（保守边界）。删后偶有「见  与 」之类轻微残句，由 Task 10 人工验证逐篇核。

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -q`
Expected: PASS（17 passed）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/wechat_export.py prism/scripts/test_wechat_export.py
git commit -m "feat(prism/wechat): strip_sources_section + strip_inline_output_refs"
```

---

### Task 4: K# 对照表（从 thesis 抽维度 + 生成 markdown）

**Files:**
- Modify: `prism/scripts/wechat_export.py`
- Test: `prism/scripts/test_wechat_export.py`

- [ ] **Step 1: 写失败测试（追加）**

```python
def test_build_k_legend_md_real_futu():
    # 真实 topic：正文里 K1/K2/K3 应能从 thesis_v5 抽出含义并成表
    body = "命门 K1 是总开关，K2 监管尾部，K3 引擎独立性。"
    md = wx.build_k_legend_md(body, "global-futu", "opus4.8")
    assert "命门编号对照" in md
    assert "K1" in md and "K2" in md and "K3" in md
    assert "| 编号 | 含义 |" in md


def test_build_k_legend_md_no_k_in_body():
    # 正文无 K# → 不生成图例
    assert wx.build_k_legend_md("纯散文，无编号。", "global-futu", "opus4.8") == ""


def test_build_k_legend_md_no_thesis():
    # 不存在的 topic → 静默返回空
    assert wx.build_k_legend_md("提到 K1。", "no-such-slug", "no-variant") == ""
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -k k_legend -q`
Expected: FAIL（缺函数）。

- [ ] **Step 3: 写实现（追加）**

```python
def parse_thesis_k_meanings(slug: str, variant: str) -> dict[str, str]:
    """从该 variant 最新 thesis_v{N}.md 的 K# 表抽 {K#: 含义}。

    容忍多种表格格式：首格可能是 `K1` 或带装饰的 `**命门1 / K1**`；取首格含 K# 的行，
    第二格（去 ** 后）作为含义。与 outputs.extract_k_status 同源（锚定 K# 表格行）。
    无 thesis / 无表 → 返回 {}（绝不抛错）。
    """
    versions = outputs_io.list_thesis_files(slug, variant)
    if not versions:
        return {}
    path = _PRISM_ROOT / "topics" / slug / variant / f"thesis_v{max(versions)}.md"
    if not path.is_file():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        m = re.search(r"\bK\d+\b", cells[0])
        if not m or m.group(0) in out:
            continue
        meaning = re.sub(r"\*\*", "", cells[1]).strip()
        if meaning and not set(meaning) <= set("-: "):  # 跳过分隔行 |---|
            out[m.group(0)] = meaning
    return out


def build_k_legend_md(body_text: str, slug: str, variant: str) -> str:
    """为正文中出现的 K# 生成「命门编号对照」markdown 表。正文无 K# / 抽不到含义 → 返回 ""。"""
    ks = sorted(set(re.findall(r"\bK\d+\b", body_text)), key=lambda k: int(k[1:]))
    if not ks:
        return ""
    meanings = parse_thesis_k_meanings(slug, variant)
    rows = [(k, meanings[k]) for k in ks if k in meanings]
    if not rows:
        return ""
    lines = ["## 命门编号对照（K#）", "", "| 编号 | 含义 |", "|---|---|"]
    lines += [f"| {k} | {meaning} |" for k, meaning in rows]
    return "\n".join(lines)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -q`
Expected: PASS（20 passed）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/wechat_export.py prism/scripts/test_wechat_export.py
git commit -m "feat(prism/wechat): parse_thesis_k_meanings + build_k_legend_md"
```

---

### Task 5: bs4 内联样式

**Files:**
- Modify: `prism/scripts/wechat_export.py`
- Test: `prism/scripts/test_wechat_export.py`

- [ ] **Step 1: 写失败测试（追加）**

```python
def test_inline_styles_adds_style_and_strips_class_id():
    html = '<h2 class="x" id="y">标题</h2><p>正文</p>'
    out = wx.inline_styles(html)
    assert 'style="' in out
    assert "class=" not in out and "id=" not in out


def test_inline_styles_table_and_code():
    html = "<table><tr><th>列</th><td>值</td></tr></table><p><code>x</code></p>"
    out = wx.inline_styles(html)
    assert "border-collapse" in out          # table 样式
    assert out.count("border:1px solid") >= 2  # th + td


def test_inline_styles_no_style_or_script_blocks():
    out = wx.inline_styles("<p>x</p>")
    assert "<style" not in out and "<script" not in out
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -k inline_styles -q`
Expected: FAIL（缺函数）。

- [ ] **Step 3: 写实现（追加）**

```python
# 公众号编辑器会丢弃 <style>/class/id，故逐标签内联。这张表是 WeChat-safe 的最小可保留集。
_WECHAT_STYLES = {
    "h1": "font-size:22px;font-weight:700;margin:24px 0 16px;line-height:1.4;",
    "h2": "font-size:19px;font-weight:700;margin:22px 0 12px;line-height:1.4;border-bottom:1px solid #eee;padding-bottom:6px;",
    "h3": "font-size:17px;font-weight:600;margin:18px 0 10px;line-height:1.4;",
    "p": "font-size:15px;line-height:1.75;margin:14px 0;color:#333;",
    "ul": "margin:12px 0;padding-left:22px;",
    "ol": "margin:12px 0;padding-left:22px;",
    "li": "font-size:15px;line-height:1.75;margin:6px 0;color:#333;",
    "blockquote": "border-left:3px solid #cbd5e0;padding:4px 14px;margin:14px 0;color:#666;background:#f7f8fa;",
    "table": "border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;",
    "th": "border:1px solid #ddd;padding:7px 10px;background:#f5f5f5;font-weight:600;text-align:left;",
    "td": "border:1px solid #ddd;padding:7px 10px;",
    "code": "background:#f2f2f2;padding:1px 5px;border-radius:3px;font-size:13px;",
    "pre": "background:#f6f6f6;padding:12px;border-radius:4px;overflow-x:auto;font-size:13px;",
    "strong": "font-weight:700;",
    "em": "font-style:italic;",
    "hr": "border:none;border-top:1px solid #e2e2e2;margin:22px 0;",
    "a": "color:#576b95;text-decoration:none;",
}


def inline_styles(html: str) -> str:
    """把渲染后 HTML 的样式逐标签内联，并删除 class/id（公众号会丢弃）。无 <style>/<script>。"""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        style = _WECHAT_STYLES.get(tag.name)
        if style:
            tag["style"] = style + tag.get("style", "")
        tag.attrs.pop("class", None)
        tag.attrs.pop("id", None)
    return str(soup)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -q`
Expected: PASS（23 passed）。

- [ ] **Step 5: 提交**

```bash
git add prism/scripts/wechat_export.py prism/scripts/test_wechat_export.py
git commit -m "feat(prism/wechat): inline_styles（bs4 逐标签内联 + 去 class/id）"
```

---

### Task 6: 编排 `clean_markdown` + `to_wechat_html`（真实 topic 集成测试）

**Files:**
- Modify: `prism/scripts/wechat_export.py`
- Test: `prism/scripts/test_wechat_export.py`

- [ ] **Step 1: 写失败测试（追加）**

```python
import pytest


@pytest.mark.parametrize("slug,variant,key", [
    ("global-futu", "opus4.8", "00_primer"),
    ("global-futu", "opus4.8", "c_investment_case"),
])
def test_to_wechat_html_real_topic_clean(slug, variant, key):
    out = wx.to_wechat_html(slug, variant, key)
    # ① 无 mat 引用残留
    assert "mat-" not in out
    # ② 无内部架子
    assert "承重充分性" not in out
    assert "changelog" not in out
    assert "来源说明" not in out and "信息来源" not in out
    # ③ 已内联样式、无 class/id/style 块
    assert 'style="' in out
    assert "<style" not in out and "<script" not in out
    # ④ K# 对照表已追加（futu 正文含 K#）
    assert "命门编号对照" in out


def test_to_wechat_html_stable_replayable():
    a = wx.to_wechat_html("global-futu", "opus4.8", "00_primer")
    b = wx.to_wechat_html("global-futu", "opus4.8", "00_primer")
    assert a == b  # 纯函数、可重放


def test_to_wechat_html_missing_output_raises():
    with pytest.raises(FileNotFoundError):
        wx.to_wechat_html("global-futu", "opus4.8", "00_primer_does_not_exist")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -k to_wechat_html -q`
Expected: FAIL（缺函数）。

- [ ] **Step 3: 写实现（追加）**

```python
def clean_markdown(raw: str) -> str:
    """对原始 .md 文本做全部 markdown 层清洗（渲染前）。纯函数、幂等。"""
    text = outputs_io._strip_frontmatter(raw)
    text = strip_sources_section(text)
    text = strip_blockquote_lines(text)
    text = strip_inline_output_refs(text)
    text = strip_mat_refs(text)
    return text


def to_wechat_html(slug: str, variant: str, output_key: str) -> str:
    """生成某产出的微信公众号版自包含内联样式 HTML 片段。纯函数、零 LLM、可重放。

    流水线：读 .md → markdown 层清洗 → 追加 K# 对照表 → render_markdown（不 linkify）→ bs4 内联样式。
    """
    out_path = _PRISM_ROOT / "topics" / slug / variant / "outputs" / f"{output_key}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Output not found: {slug}/{variant}/{output_key}")
    text = clean_markdown(out_path.read_text(encoding="utf-8"))
    legend_md = build_k_legend_md(text, slug, variant)
    if legend_md:
        text = text.rstrip() + "\n\n" + legend_md + "\n"
    html = outputs_io.render_markdown(text)  # 复用现有渲染；不调 linkify_mat_refs
    return inline_styles(html)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py -q`
Expected: PASS（28 passed）。

- [ ] **Step 5: 回归保护——确认现有 outputs 测试不受影响**

Run: `.venv/bin/python -m pytest prism/scripts/test_outputs.py prism/scripts/test_render_markdown.py -q`
Expected: PASS（现有产出渲染零影响）。

- [ ] **Step 6: 提交**

```bash
git add prism/scripts/wechat_export.py prism/scripts/test_wechat_export.py
git commit -m "feat(prism/wechat): clean_markdown + to_wechat_html 编排 + 真实 topic 集成测试"
```

---

### Task 7: 路由 `…/{output_key}/wechat`

**Files:**
- Modify: `app/routes/prism.py`（import 区 + 在 `@router.get("/{slug}/{variant}/{output_key}")`（约 line 1161）之前插入新路由）

- [ ] **Step 1: 加 import**

在 `app/routes/prism.py` 的 import 区（约 line 22，`from prism.scripts import topic as topic_io` 之后）加：

```python
from prism.scripts import wechat_export as wechat_export
```

- [ ] **Step 2: 在通配输出路由之前插入新路由**

在 `@router.get("/{slug}/{variant}/{output_key}")`（`def prism_output`，约 line 1161）**之前**插入：

```python
@router.get("/{slug}/{variant}/{output_key}/wechat")
def prism_output_wechat(request: Request, slug: str, variant: str, output_key: str):
    """某产出的微信公众号版（纯显示层清洗 + 内联样式 + 复制按钮）。仅 primer/case 开放。"""
    if output_key not in wechat_export.WECHAT_OUTPUT_KEYS:
        raise HTTPException(status_code=404, detail="公众号版仅支持 primer / case 产出")
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Topic {slug!r}/{variant!r} not found")
    try:
        article_html = wechat_export.to_wechat_html(slug, variant, output_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Output {output_key!r} not yet generated")
    outputs = outputs_io.list_outputs(slug, variant)
    current_output = next((o for o in outputs if o["key"] == output_key), None)
    return templates.TemplateResponse(
        request,
        "prism/wechat.html",
        {
            "topic": topic,
            "output_key": output_key,
            "current_output": current_output,
            "variant": variant,
            "article_html": article_html,
        },
    )
```

- [ ] **Step 3: 冒烟验证路由（模板下一任务建，先验路由不 500 于逻辑层）**

先建一个占位模板让本步通过（下一任务替换为正式版）：

```bash
printf '%s' '{% extends "base.html" %}{% block content %}{{ article_html | safe }}{% endblock %}' > app/templates/prism/wechat.html
```

Run:
```bash
.venv/bin/python -c "
from fastapi.testclient import TestClient
from main import app
c = TestClient(app)
r = c.get('/prism/global-futu/opus4.8/00_primer/wechat')
print('status', r.status_code)
assert r.status_code == 200, r.status_code
assert 'mat-' not in r.text
r2 = c.get('/prism/global-futu/opus4.8/07_decision_kit/wechat')
print('non-whitelist status', r2.status_code)
assert r2.status_code == 404
print('OK')
"
```
Expected: `status 200` / `non-whitelist status 404` / `OK`。

- [ ] **Step 4: 提交**

```bash
git add app/routes/prism.py app/templates/prism/wechat.html
git commit -m "feat(prism/wechat): 加 …/{output_key}/wechat 路由（占位模板）"
```

---

### Task 8: 正式模板 `prism/wechat.html`（预览页 + 复制按钮）

**Files:**
- Modify: `app/templates/prism/wechat.html`（替换 Task 7 占位）

- [ ] **Step 1: 写正式模板**

覆盖 `app/templates/prism/wechat.html`：

```html
{% extends "base.html" %}
{% block title %}公众号版 · {{ current_output.label if current_output else output_key }} · {{ topic.display_name }}{% endblock %}
{% block content %}
<nav class="breadcrumb">
  <a href="/prism">研究主题</a> /
  <a href="/prism/{{ topic.slug }}">{{ topic.display_name or topic.slug }}</a> /
  <a href="/prism/{{ topic.slug }}/{{ variant }}/{{ output_key }}">{{ current_output.label if current_output else output_key }}</a> /
  <span>公众号版</span>
</nav>

<div class="wx-toolbar">
  <div class="wx-hint">纯显示层清洗版（去引用/内部架子、保留 K# 并附对照表）。点下方按钮复制富文本，到公众号编辑器直接粘贴。正文内容与系统版完全一致。</div>
  <div class="wx-actions">
    <button id="wx-copy" class="wx-btn">📋 复制到公众号</button>
    <a class="wx-back" href="/prism/{{ topic.slug }}/{{ variant }}/{{ output_key }}">← 返回系统版</a>
  </div>
</div>

<div id="wx-article">
  {{ article_html | safe }}
</div>

<style>
  main { margin-top: 0; }
  .breadcrumb { font-size: 0.85em; color: #888; margin-bottom: 0.5em; }
  .breadcrumb a { color: #555; }
  .wx-toolbar { position: sticky; top: 41px; background: #fafafa; z-index: 9; padding: 0.7em 0; border-bottom: 1px solid #eee; margin-bottom: 1.4em; }
  .wx-hint { font-size: 0.8em; color: #999; margin-bottom: 0.6em; line-height: 1.5; }
  .wx-actions { display: flex; align-items: center; gap: 1em; }
  .wx-btn { font-size: 0.9em; padding: 0.4em 1em; border: 1px solid #07c160; border-radius: 4px; background: #07c160; color: #fff; cursor: pointer; }
  .wx-btn:hover { background: #06ad56; }
  .wx-btn.copied { background: #888; border-color: #888; }
  .wx-back { font-size: 0.85em; color: #576b95; text-decoration: none; }
  /* 正文区靠内联样式保真；这里给个最大宽度模拟公众号阅读宽度 */
  #wx-article { max-width: 677px; margin: 0 auto; }
</style>

<script>
(function () {
  var btn = document.getElementById("wx-copy");
  var article = document.getElementById("wx-article");
  if (!btn || !article) return;
  btn.addEventListener("click", function () {
    var html = article.innerHTML;
    var text = article.innerText;
    function done() {
      btn.textContent = "✓ 已复制";
      btn.classList.add("copied");
      setTimeout(function () { btn.textContent = "📋 复制到公众号"; btn.classList.remove("copied"); }, 2000);
    }
    function fallback() {
      // 退化：选中正文，提示手动 Ctrl/Cmd+C
      var range = document.createRange();
      range.selectNodeContents(article);
      var sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      btn.textContent = "已选中，请按 Ctrl/Cmd+C";
    }
    if (navigator.clipboard && window.ClipboardItem) {
      var item = new ClipboardItem({
        "text/html": new Blob([html], { type: "text/html" }),
        "text/plain": new Blob([text], { type: "text/plain" })
      });
      navigator.clipboard.write([item]).then(done).catch(fallback);
    } else {
      fallback();
    }
  });
})();
</script>
{% endblock %}
```

- [ ] **Step 2: 冒烟验证页面渲染**

Run:
```bash
.venv/bin/python -c "
from fastapi.testclient import TestClient
from main import app
c = TestClient(app)
r = c.get('/prism/global-futu/opus4.8/c_investment_case/wechat')
assert r.status_code == 200, r.status_code
assert 'wx-copy' in r.text and 'id=\"wx-article\"' in r.text
assert '承重充分性' not in r.text and 'changelog' not in r.text
print('OK')
"
```
Expected: `OK`。

- [ ] **Step 3: 提交**

```bash
git add app/templates/prism/wechat.html
git commit -m "feat(prism/wechat): 正式预览页模板 + 一键复制富文本按钮"
```

---

### Task 9: 现有 `output.html` 纯增「公众号版」链接

**Files:**
- Modify: `app/templates/prism/output.html`（`output-meta` 块内，`compare-btn` 之后）

- [ ] **Step 1: 在 `output-meta` 里加条件链接**

在 `app/templates/prism/output.html` 的 `output-meta` div 内，紧接 `{% endif %}`（compare-btn 块的结束）之后、`</div>` 之前，插入：

```html
      {% if output_key in ['00_primer', 'c_investment_case', 'i_industry_case', 'a_arena_case'] %}
      <a href="/prism/{{ topic.slug }}/{{ variant }}/{{ output_key }}/wechat"
         class="compare-btn">公众号版</a>
      {% endif %}
```

> 复用现有 `.compare-btn` 样式，零新 CSS。这是对 `output.html` 的唯一改动，纯增条件链接，不动任何渲染逻辑。

- [ ] **Step 2: 冒烟验证链接出现 / 非白名单不出现**

Run:
```bash
.venv/bin/python -c "
from fastapi.testclient import TestClient
from main import app
c = TestClient(app)
r = c.get('/prism/global-futu/opus4.8/00_primer')
assert '公众号版' in r.text and '/00_primer/wechat' in r.text
print('OK')
"
```
Expected: `OK`。

- [ ] **Step 3: 提交**

```bash
git add app/templates/prism/output.html
git commit -m "feat(prism/wechat): output.html 纯增公众号版入口链接（仅 primer/case）"
```

---

### Task 10: 三类 topic 人工验证 + 收尾

**Files:**（无代码改动，除非验证发现需调整）
- 可能 Modify: `prism/scripts/wechat_export.py`（若验证发现需补 strip 规则）

- [ ] **Step 1: 全测试套件绿**

Run: `.venv/bin/python -m pytest prism/scripts/test_wechat_export.py prism/scripts/test_outputs.py prism/scripts/test_render_markdown.py -q`
Expected: 全 PASS。

- [ ] **Step 2: 导出 6 份产物到临时文件供肉眼核对**

Run:
```bash
.venv/bin/python -c "
from prism.scripts import wechat_export as wx
cases = [
  ('global-futu','opus4.8','00_primer'), ('global-futu','opus4.8','c_investment_case'),
  ('cn-commercial-aerospace','opus4.8','00_primer'), ('cn-commercial-aerospace','opus4.8','i_industry_case'),
  ('cn-premium-baijiu','opus4.8','00_primer'), ('cn-premium-baijiu','opus4.8','a_arena_case'),
]
import pathlib
out = pathlib.Path('/tmp/wx_preview'); out.mkdir(exist_ok=True)
for slug,var,key in cases:
    html = wx.to_wechat_html(slug,var,key)
    f = out / f'{slug}__{key}.html'
    f.write_text('<meta charset=utf-8><div style=\"max-width:677px;margin:0 auto\">'+html+'</div>', encoding='utf-8')
    bad = [t for t in ('mat-','承重充分性','changelog','来源说明','信息来源') if t in html]
    print(f'{f}  | 残留: {bad or \"无\"}  | 字数~{len(html)}')
"
```
Expected: 每份 `残留: 无`。**若某份非空**，记录残留 token，回对应 strip 函数补规则（如出现 `链体检`/`tier ↔ 一致性说明（dashboard 对齐）` 这两个相邻内部小节——把其标题按需加入 `_SOURCES_HEADING`，与用户确认后再改），加单测，重跑 Task 6/10。

- [ ] **Step 2.5: 人工核对（用浏览器打开 /tmp/wx_preview/*.html）**

逐份检查清单：
- ① 全文无 `mat-` 残留；② 无承重充分性 banner；③ 无 vN changelog；④ 无 来源说明/信息来源 出处段；⑤ 无 `00_primer`/`c_investment_case` 等文件名乱码；⑥ Q#（季度，如「Q1 2026」「25Q4」）原样在；⑦ K# 原样在 + 文末有「命门编号对照」表；⑧ 表格/加粗/列表排版正常。
- 特别留意 industry case 的 `## 链体检`、arena case 的 `## tier ↔ 综合分一致性说明（dashboard 对齐）`——这两个相邻内部小节默认**保留**（未在批准范围内），核对时确认是否要追加删除（需用户拍板）。

- [ ] **Step 3: 起服务做一次真实复制粘贴验证（可选但推荐）**

Run（后台起服务）：`.venv/bin/uvicorn main:app --port 8011`
浏览器开 `http://localhost:8011/prism/global-futu/opus4.8/c_investment_case/wechat`，点「📋 复制到公众号」，到公众号编辑器（或任意富文本框）粘贴，确认排版（标题/表格/加粗）保真。

- [ ] **Step 4: 收尾提交 + 推送**

```bash
git add -A prism/scripts/wechat_export.py prism/scripts/test_wechat_export.py
git commit -m "test(prism/wechat): 三类 topic 人工验证通过，按需补 strip 规则" --allow-empty
git push -u origin feat/prism-wechat-publish
```

---

## 自检（写完计划对照 spec）

**Spec 覆盖：**
- §1 清洗清单 → Task 1（mat）/2（banner·changelog·读者画像·阅读假定）/3（来源段·内联文件名）✓
- §1 K# 保留+图例 → Task 4 ✓；Q# 不动 → 无 Q# strip 函数（确认）✓
- §3 模块流水线（清洗→渲染不 linkify→K# 图例→内联） → Task 6 ✓
- §3 inline_styles 删 class/id、无 style/script → Task 5 ✓
- §4.1 路由 + 白名单 404 + 置于通配前 → Task 7 ✓
- §4.2 模板 + 复制按钮（ClipboardItem text/html + 降级） → Task 8 ✓
- §4.3 output.html 纯增条件链接 → Task 9 ✓
- §5 三类 topic 验证（company/industry/arena 各一） → Task 10 ✓
- §6 测试（strip 全覆盖、K# 图例、内联、回归保护、可重放） → Task 1–6 测试 ✓
- §7 YAGNI（不碰 Q#/K# 正文、无新依赖、不开放 sidecar） → 设计遵守 ✓

**占位符扫描：** 无 TBD/TODO；每个代码步给了完整代码与期望输出。

**类型/命名一致性：** `strip_mat_refs`/`strip_blockquote_lines`/`strip_sources_section`/`strip_inline_output_refs`/`parse_thesis_k_meanings`/`build_k_legend_md`/`inline_styles`/`clean_markdown`/`to_wechat_html`/`WECHAT_OUTPUT_KEYS` 在 Task 6 编排与 Task 7 路由中引用一致；模板上下文键 `article_html`/`current_output`/`output_key`/`variant`/`topic` 在 Task 7 路由与 Task 8 模板间一致。
