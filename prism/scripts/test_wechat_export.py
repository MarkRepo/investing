"""wechat_export 纯函数单测。零 LLM、零 I/O（除显式读真实 topic 的集成测试）。"""
import pytest

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


def test_strip_tier_name_mapping_pointer():
    # 档名↔dashboard/sidecar 内部映射指针（blockquote）删除
    src = ("正文。\n\n> **档名映射（dashboard 对齐）**：深挖=deep / 观察=watch / 淘汰=eliminated。\n\n"
           "> **档名↔sidecar 映射（dashboard 对齐用）**：深研档 = `shortlist`。\n\n续。")
    out = wx.strip_blockquote_lines(src)
    assert "档名" not in out and "dashboard" not in out
    assert "正文。" in out and "续。" in out


def test_strip_inline_tier_mapping_keeps_definition():
    # 混合行：保留 tier 定义（内容），只删末尾「档名↔sidecar：…」内部映射子句
    src = "> **tier = 卡位/质量 × 当前定价**（不是只按好坏排）。档名↔sidecar：深研=`shortlist`/观察=`watch`/淘汰=`eliminated`。"
    out = wx.strip_inline_tier_mapping(src)
    assert "tier = 卡位/质量 × 当前定价" in out
    assert "不是只按好坏排" in out
    assert "档名" not in out and "shortlist" not in out


def test_strip_inline_tier_mapping_absent():
    src = "> **tier = 卡位/质量 × 当前定价**（不是只按好坏排）。"
    assert wx.strip_inline_tier_mapping(src) == src


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


def test_strip_inline_output_refs_sidecar_pointer_paren_only():
    # 标题尾「（→ sidecar key）」整体是内部指针 → 删空括号后只剩标题
    src = "### kill 触发条件（→ sidecar kill_criteria）"
    assert wx.strip_inline_output_refs(src) == "### kill 触发条件"


def test_strip_inline_output_refs_sidecar_pointer_mixed_paren():
    # 括号里前半是内容、后半是指针 → 只删指针，保留内容
    src = "### 仓位框架（首仓参考④的 EV → sidecar position_framework）"
    assert wx.strip_inline_output_refs(src) == "### 仓位框架（首仓参考④的 EV）"


def test_strip_inline_output_refs_keeps_bare_sidecar_word():
    # 裸词 sidecar（无 → key 指针）不误删
    src = "这个 sidecar 设计很巧。"
    assert wx.strip_inline_output_refs(src) == src


def test_strip_inline_output_refs_pure_key_paren():
    # 括号内只含产出 key（非反引号）→ 整个括号删除
    assert wx.strip_inline_output_refs("# 中国商业航天 · 投资决策链（i_industry_case）") == "# 中国商业航天 · 投资决策链"
    assert wx.strip_inline_output_refs("拿起决策链 case（i_industry_case）不被挡住") == "拿起决策链 case不被挡住"


def test_strip_inline_output_refs_keeps_content_paren():
    # 括号内是内容（无 key）→ 不动
    assert wx.strip_inline_output_refs("### 仓位框架（首仓参考④的 EV）") == "### 仓位框架（首仓参考④的 EV）"


def test_strip_inline_output_refs_file_pointer_paren():
    # 括号内含「见 内部文件」指针（非纯 key）→ 整括号删，保留前面正文
    src = "K6 次高端弹性vs陷阱（完整定义与现状见 thesis_v1 §4）。"
    assert wx.strip_inline_output_refs(src) == "K6 次高端弹性vs陷阱。"


def test_build_toc_md_lists_h2_as_bullets():
    text = "# 标题\n\n## 0. 起点\n\n正文\n\n## 1. 飞轮\n\n## 2. 估值\n"
    toc = wx.build_toc_md(text)
    assert toc.startswith("## 目录")
    assert "- 0. 起点" in toc and "- 1. 飞轮" in toc and "- 2. 估值" in toc
    # 不重新编号（标题自带序号），用无序列表
    assert "1. 0. 起点" not in toc


def test_build_toc_md_strips_emphasis_in_titles():
    text = "## 环① **看懂**（理解闸门）\n\n## 环② 定价\n\n## 环③ 假设\n"
    toc = wx.build_toc_md(text)
    assert "- 环① 看懂（理解闸门）" in toc  # ** 去掉
    assert "*" not in toc


def test_build_toc_md_skips_when_too_few_sections():
    assert wx.build_toc_md("# 标题\n\n## 只有一节\n\n正文") == ""


def test_to_wechat_html_has_toc_after_title():
    out = wx.to_wechat_html("global-futu", "opus4.8", "00_primer")
    assert "目录" in out


def test_strip_self_check_chain():
    # industry 文末 链体检（self-check）整段删除
    src = "## 环⑥\n\n正文。\n\n## 链体检（self-check）\n\n①看懂 ✓ / ②定价 ✓\n"
    out = wx.strip_self_check_sections(src)
    assert "链体检" not in out and "①看懂" not in out
    assert "## 环⑥" in out and "正文。" in out


def test_strip_self_check_tier_consistency():
    # arena 文末 tier ↔ 一致性说明（dashboard 对齐）整段删除
    src = "## 环⑥\n\n正文。\n\n## tier ↔ 综合分一致性说明（dashboard 对齐）\n\nscore 排序同向。\n"
    out = wx.strip_self_check_sections(src)
    assert "一致性说明" not in out and "score 排序" not in out
    assert "## 环⑥" in out and "正文。" in out


def test_strip_self_check_bounded_by_next_h2():
    # 只删命名段，相邻小节保留
    src = "## 链体检\n\n自检。\n\n## 真正文\n\nY。"
    out = wx.strip_self_check_sections(src)
    assert "链体检" not in out and "自检" not in out
    assert "## 真正文" in out and "Y。" in out


def test_strip_self_check_absent():
    src = "## 正文\n\n没有自检段。"
    assert wx.strip_self_check_sections(src) == src


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
