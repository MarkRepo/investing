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
    ]
    for stage, idx, label in cases:
        p = stage_progress(stage)
        assert p["phase_index"] == idx, f"{stage} → phase {p['phase_index']} != {idx}"
        assert p["label"] == label, f"{stage} → label {p['label']!r} != {label!r}"
        assert p["state"] == "in_progress"
        assert p["total"] == 7


def test_company_industry_arena_share_phase6():
    # 三类 type 第 6 阶段统一为 05-critic-review（评审）——退休名 09/10 已删，
    # 走未知兜底（按数字前缀尽力猜，不再是合法节点）。
    p = stage_progress("05-critic-review")
    assert p["phase_index"] == 6 and p["label"] == "评审中"
    # 大阶段第 6 名已从「定稿」改为「评审」
    from prism.scripts.topic import STAGE_PHASE_NAMES
    assert STAGE_PHASE_NAMES[5] == "评审"
    # 退休的旧 stage 名不再映射为 in_progress 的合法第 6 阶段
    assert stage_progress("09-arena-shortlist")["state"] == "unknown"
    assert stage_progress("10-peer-matrix")["state"] == "unknown"


def test_unknown_stage_graceful():
    p = stage_progress("99-some-future-stage")
    assert p["state"] == "unknown"
    assert p["label"] == "99-some-future-stage"  # 原串兜底，不抛
    assert p["total"] == 7


def test_phase_names_are_seven():
    assert STAGE_PHASE_NAMES == ["立项", "规划", "收料", "抽取", "合成", "评审", "完成"]
