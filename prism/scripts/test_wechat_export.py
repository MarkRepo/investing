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
