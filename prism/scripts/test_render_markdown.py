"""渲染层归一化测试：表格前缺空行时仍应出 <table>（GFM tables 扩展硬要求空行）。"""
from prism.scripts.outputs import render_markdown, _normalize_md_tables


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
