"""渲染层归一化测试：表格前缺空行时仍应出 <table>（GFM tables 扩展硬要求空行）。"""
from prism.scripts.outputs import (
    render_markdown,
    _normalize_md_tables,
    _normalize_md_lists,
    _strip_frontmatter,
)


def _renders_table(md: str) -> bool:
    return "<table>" in render_markdown(md)


def test_table_after_bold_label_no_blank_line():
    md = "**带数字的反推**：\n| 维度 | 值 |\n|------|------|\n| A | 1 |\n"
    assert _renders_table(md)


def test_table_after_blockquote_no_blank_line():
    # blockquote 行后紧跟非 > 前缀的表格：补空行后表格应脱离引用块独立渲染
    md = "> **EV**：某段引用文字。\n| 情形 | 概率 |\n|---|---|\n| Bear | 30% |\n"
    html = render_markdown(md)
    assert "<table>" in html
    # 表格不应被吞进 blockquote
    assert "<blockquote>" not in html or "</blockquote>" in html.split("<table>")[0]


def test_table_already_has_blank_line_still_renders():
    md = "**标签**：\n\n| 维度 | 值 |\n|------|------|\n| A | 1 |\n"
    assert _renders_table(md)


def test_does_not_insert_blank_inside_fenced_code():
    md = "```\n**标签**：\n| a | b |\n|---|---|\n```\n"
    html = render_markdown(md)
    # fenced 代码块里的管道文本应原样保留，不得渲染成 <table>
    assert "<table>" not in html


def test_setext_heading_underline_not_treated_as_table():
    # "Title\n-----" 是 setext h2，分隔行无 '|'，不能被当成表格分隔而插空行
    md = "标题\n-----\n正文。\n"
    html = render_markdown(md)
    assert "<h2" in html


def test_normalizer_is_idempotent():
    md = "**标签**：\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    once = _normalize_md_tables(md)
    twice = _normalize_md_tables(once)
    assert once == twice


# ── frontmatter 剥除（render_markdown 无 meta 扩展，否则 YAML 头被当正文渲染）──

def test_leading_frontmatter_stripped_from_render():
    md = (
        "---\n"
        "slug: global-macro-rates-liquidity\n"
        "output_key: 00_primer\n"
        "companion: m_regime_read.md / transmission_map.yaml\n"
        "---\n"
        "# 标题\n\n正文段落。\n"
    )
    html = render_markdown(md)
    # 后台记账字段与泄露的后台文件名都不应出现在网页正文
    assert "slug:" not in html
    assert "output_key" not in html
    assert "transmission_map.yaml" not in html
    assert "m_regime_read.md" not in html
    # 真正的正文照常渲染
    assert "正文段落" in html
    assert "<h1" in html


def test_no_frontmatter_passthrough_unchanged():
    md = "# 普通文档\n\n一段正文。\n"
    assert render_markdown(md) == render_markdown(md)  # 稳定
    assert "普通文档" in render_markdown(md)


def test_leading_hr_not_treated_as_frontmatter():
    # 开头是 `---` 水平线/分隔，但块内没有 key: value —— 不能被当 frontmatter 吃掉
    md = "---\n这是正文不是元数据\n---\n后面还有正文。\n"
    out = _strip_frontmatter(md)
    assert "这是正文不是元数据" in out


def test_strip_frontmatter_idempotent():
    md = "---\nslug: x\ntype: macro-primer\n---\n正文。\n"
    once = _strip_frontmatter(md)
    twice = _strip_frontmatter(once)
    assert once == twice
    assert "slug" not in once


# ── 列表归一化（段落紧跟列表漏空行 → python-markdown 把 `- ` 当段落文本）──────

def test_list_glued_to_paragraph_renders_as_ul():
    # 粗体标题行紧跟 `- ` 项、中间漏空行：补空行后应渲染成真正的 <ul>/<li>
    md = "**标题**：3.5%\n- `这是什么`：总锚。\n- `为什么看它`：发动机。\n"
    html = render_markdown(md)
    assert "<ul>" in html
    assert "<li><code>这是什么</code>" in html
    assert "- <code>这是什么</code>" not in html  # 不得留字面短横线


def test_already_spaced_list_unchanged():
    md = "段落。\n\n- 甲\n- 乙\n"
    html = render_markdown(md)
    assert "<ul>" in html
    assert html.count("<li>") == 2


def test_consecutive_list_items_stay_tight():
    # 连续列表项之间不应被插空行（避免无谓的 loose-list <p> 包裹）
    md = "段落。\n\n- 甲\n- 乙\n- 丙\n"
    norm = _normalize_md_lists(md)
    assert "\n\n- 乙" not in norm
    assert "\n\n- 丙" not in norm


def test_list_normalizer_skips_fenced_code():
    md = "```\n文字\n- 不是列表\n```\n"
    html = render_markdown(md)
    assert "<ul>" not in html
    assert "- 不是列表" in html


def test_list_normalizer_leaves_hr_and_indented_alone():
    # 顶层 `---` 水平线不是列表项；缩进的延续行后不强插空行（不拆嵌套/延续）
    md = "正文\n---\n更多正文\n"
    assert _normalize_md_lists(md) == md
    nested = "- 父项\n  续行文字\n  - 子项\n"
    assert _normalize_md_lists(nested) == nested


def test_list_normalizer_idempotent():
    md = "**标题**\n- 甲\n- 乙\n"
    once = _normalize_md_lists(md)
    twice = _normalize_md_lists(once)
    assert once == twice
