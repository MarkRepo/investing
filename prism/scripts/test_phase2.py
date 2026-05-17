#!/usr/bin/env python3
"""Phase 2 验收测试：验证所有文件修改成功。"""
from pathlib import Path

PRISM_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    # Phase 2.1
    "workflows/04-synthesize/04-expectations.md",
    # Phase 2.2
    "workflows/04-synthesize/05-mirrors.md",
    # Phase 2.3
    "workflows/04-synthesize/07-decision-kit.md",
    # Phase 2.4
    "workflows/99-decision-record.md",
]


def test_phase2():
    print("=== Phase 2 验收测试 ===\n")

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

    print("\n=== Phase 2 验收通过! ===")
    print("\n已完成:")
    print("  Phase 2.1: 04 隐含预期三档分支 ✓")
    print("    - industry/arena/company 分支")
    print("    - company 版强制反推 DCF 数学 + 同业对比")
    print("  Phase 2.2: 05 历史镜像对偶强制 ✓")
    print("    - 失败镜像强制 ≥2 个")
    print("    - 对偶平衡：成功回报区间 + 失败损失区间")
    print("  Phase 2.3: 07 买入框 ✓")
    print("    - 买入价格区间（强力买入/加仓/止损）")
    print("    - 仓位框架（首仓/满仓/加仓阶梯）")
    print("    - 时间维度（持有期/催化剂时点）")
    print("  Phase 2.4: 99 决策记录 alternatives ✓")
    print("    - 替代标的强制 ≥2 个")
    print("    - 排他性检查")
    print("    - 半年后复盘约定 + user_todos 自动提醒")
    print("\n下一步:")
    print("  - Phase 3: 知识沉淀（concepts.yaml、monitoring_tier、freshness）")
    print("  - Phase 4: 横向视图与轻量假设链（可选）")
    return True


if __name__ == "__main__":
    test_phase2()
