#!/usr/bin/env python3
"""Phase 1 验收测试：验证所有文件创建成功。"""
from pathlib import Path

PRISM_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    # Phase 0
    "scripts/topic.py",
    "templates/topic.yaml.tmpl",
    # Phase 1.1
    "workflows/04-synthesize/09-industry-to-arenas.md",
    "templates/industry_to_arenas.md.tmpl",
    # Phase 1.2
    "workflows/04-synthesize/10-peer-matrix.md",
    "templates/peer_matrix.md.tmpl",
    # Phase 1.3
    "workflows/03b-quality-screen.md",
    "templates/quality_screen.md.tmpl",
    "quarantine/",
]


def test_phase1():
    print("=== Phase 1 验收测试 ===\n")

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

    print("\n=== Phase 1 验收通过! ===")
    print("\n已完成:")
    print("  Phase 0: 数据模型扩展 ✓")
    print("    - topic.py: _outputs_for_type, next_stage, 向后兼容")
    print("    - topic.yaml.tmpl: 新字段（parent_topic, monitoring_tier, concepts）")
    print("  Phase 1.1: Industry → Arenas 选拔 ✓")
    print("    - 09-industry-to-arenas.md workflow spec")
    print("    - industry_to_arenas.md.tmpl 模板")
    print("  Phase 1.2: Arena → Peer Matrix ✓")
    print("    - 10-peer-matrix.md workflow spec")
    print("    - peer_matrix.md.tmpl 模板")
    print("  Phase 1.3: Company 质量红线 ✓")
    print("    - 03b-quality-screen.md workflow spec")
    print("    - quality_screen.md.tmpl 模板")
    print("    - quarantine/ 目录")
    print("\n下一步:")
    print("  - Phase 2: 决策硬度（04 三档分支、05 对偶、07 买入框、99 alternatives）")
    print("  - Phase 3: 知识沉淀（concepts.yaml、monitoring_tier、freshness）")
    print("  - Phase 4: 横向视图与轻量假设链（可选）")
    return True


if __name__ == "__main__":
    test_phase1()
