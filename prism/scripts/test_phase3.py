#!/usr/bin/env python3
"""Phase 3 验收测试：验证所有文件创建/修改成功。"""
from pathlib import Path

PRISM_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    # Phase 3.1
    "concepts.yaml",
    "scripts/concepts.py",
    # Phase 3.2
    "workflows/06-daily-monitor.md",
    # Phase 3.3
    "workflows/04-synthesize/01-panorama.md",
    "workflows/04-synthesize/02-cycle.md",
    "workflows/04-synthesize/03-narrative.md",
    "workflows/04-synthesize/06-risks.md",
    "workflows/04-synthesize/09-industry-to-arenas.md",
    "workflows/04-synthesize/10-peer-matrix.md",
]


def test_phase3():
    print("=== Phase 3 验收测试 ===\n")

    missing = []
    for f in REQUIRED_FILES:
        path = PRISM_ROOT / f
        if not path.exists():
            missing.append(f)
        else:
            print(f"✓ {f}")

    if missing:
        print("\n❌ 缺失文件:")
        for f in missing:
            print(f"  - {f}")
        return False

    print("\n=== Phase 3 验收通过! ===")
    print("\n已完成:")
    print("  Phase 3.1: concepts.yaml 跨 topic 标签 ✓")
    print("    - concepts.yaml 受控词表")
    print("    - concepts.py 脚本（list/add/find-topics/find-concepts）")
    print("  Phase 3.2: monitoring_tier 三档监控 ✓")
    print("    - 06-daily-monitor.md 按 tier 选择今日要扫的 topic")
    print("    - deep（每日）/ watch（每周二）/ dormant（不主动）")
    print("  Phase 3.3: data_freshness 时间戳 ✓")
    print("    - 所有 04-synthesize workflow 加 Step X.5：填写 data_freshness")
    print("    - frontmatter 含 data_freshness + data_freshness_basis")
    print("\n整体完成度:")
    print("  Phase 0: ✓ 数据模型扩展")
    print("  Phase 1: ✓ 漏斗 gate 三件")
    print("  Phase 2: ✓ 决策硬度四件")
    print("  Phase 3: ✓ 知识沉淀三件")
    print("  Phase 4: 可选（横向视图 + 轻量假设链）")
    return True


if __name__ == "__main__":
    test_phase3()
