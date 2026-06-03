"""stage_progress() —— topic.stage 收敛成读者向 7 大阶段进度（单一事实源）。

替代曾经在数退休产出槽的 n/m 数字。验证：每个真实 stage 映射到正确大阶段 +
读者向 label + state；done/quarantined/未开工/未知 stage 的边界。
"""
from prism.scripts.topic import STAGE_PHASE_NAMES, stage_progress


def test_done_is_terminal_green():
    p = stage_progress("done")
    assert p["state"] == "done"
    assert p["phase_index"] == p["total"] == len(STAGE_PHASE_NAMES) == 7
    assert p["label"] == "已完成"


def test_quarantined_is_special():
    p = stage_progress("quarantined")
    assert p["state"] == "quarantined"
    assert p["label"] == "已隔离"


def test_00_init_is_not_started():
    p = stage_progress("00-init")
    assert p["state"] == "not_started"
    assert p["phase_index"] == 1
    assert p["label"] == "未开工"


def test_empty_or_none_is_not_started():
    for s in ("", None, "   "):
        p = stage_progress(s)
        assert p["state"] == "not_started"
        assert p["phase_index"] == 0


def test_known_stages_map_to_right_phase():
    # (stage, expected phase_index, expected label)
    cases = [
        ("01-roadmap", 2, "规划中"),
        ("01-roadmap-pending", 2, "规划中"),
        ("01-roadmap-reopen", 2, "规划补缺"),
        ("02-gather-materials", 3, "收料中"),
        ("03-extracting", 4, "抽取中"),
        ("00-quality-screen", 4, "质量筛查"),
        ("04-synthesizing", 5, "合成中"),
        ("04-synthesizing-done", 5, "合成中"),
        ("04-post-synthesis", 5, "合成收尾"),
        ("05-critic-review", 6, "评审中"),
        ("09-arena-shortlist", 6, "竞技场选拔"),
        ("10-peer-matrix", 6, "同行矩阵"),
    ]
    for stage, idx, label in cases:
        p = stage_progress(stage)
        assert p["phase_index"] == idx, f"{stage} → phase {p['phase_index']} != {idx}"
        assert p["label"] == label, f"{stage} → label {p['label']!r} != {label!r}"
        assert p["state"] == "in_progress"
        assert p["total"] == 7


def test_company_industry_arena_share_phase6():
    # 三类 type 的"定稿"阶段都归到第 6 大阶段（type-agnostic 进度条对齐）
    assert stage_progress("05-critic-review")["phase_index"] == 6   # company
    assert stage_progress("09-arena-shortlist")["phase_index"] == 6  # industry
    assert stage_progress("10-peer-matrix")["phase_index"] == 6      # arena


def test_unknown_stage_graceful():
    p = stage_progress("99-some-future-stage")
    assert p["state"] == "unknown"
    assert p["label"] == "99-some-future-stage"  # 原串兜底，不抛
    assert p["total"] == 7


def test_phase_names_are_seven():
    assert STAGE_PHASE_NAMES == ["立项", "规划", "收料", "抽取", "合成", "定稿", "完成"]
