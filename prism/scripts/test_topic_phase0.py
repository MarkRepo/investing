#!/usr/bin/env python3
"""测试 Phase 0 数据模型扩展功能。"""
import tempfile
import shutil
from pathlib import Path
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from prism.scripts.topic import (
    create_topic,
    read_topic,
    set_concepts,
    set_monitoring_tier,
    set_data_freshness,
    next_stage,
    _outputs_for_type,
)


def test_phase0():
    print("=== Phase 0 数据模型扩展测试 ===\n")

    # 创建临时 topics 目录
    with tempfile.TemporaryDirectory() as tmpdir:
        # 临时替换 _topics_dir
        from prism.scripts import topic
        original_topics_dir = topic._topics_dir
        topic._topics_dir = lambda: Path(tmpdir)

        try:
            # 1. 测试 _outputs_for_type
            print("1. 测试 _outputs_for_type:")
            print(f"   industry: {_outputs_for_type('industry')}")
            print(f"   arena:    {_outputs_for_type('arena')}")
            print(f"   company:  {_outputs_for_type('company')}")
            print(f"   generic:  {_outputs_for_type('generic')}")
            print("   ✓ ok\n")

            # 2. 测试 next_stage
            print("2. 测试 next_stage:")
            for t in ["industry", "arena", "company"]:
                print(f"   {t}:")
                s = "00-init"
                while s:
                    next_s = next_stage(t, s)
                    print(f"      {s} → {next_s or 'done'}")
                    s = next_s
            print("   ✓ ok\n")

            # 3. 测试 create_topic with new fields
            print("3. 测试 create_topic:")

            # 创建 industry topic
            path = create_topic(
                slug="test-industry",
                display_name="测试行业",
                topic_type="industry",
                question="这个行业怎么样？",
                geo="cn",
                depth="deep",
                variant="sonnet",
                parent_topic=None,
                concepts=["测试概念1", "测试概念2"],
                monitoring_tier="watch",
            )
            print(f"   已创建 industry topic: {path}")

            # 读取并验证
            data = read_topic("test-industry", "sonnet")
            assert data["parent_topic"] is None
            assert data["monitoring_tier"] == "watch"
            assert data["concepts"] == ["测试概念1", "测试概念2"]
            # file-first：建 topic 不再预置任何产出槽，outputs_state 为空 {}。
            # 产出落地时惰性注册；首次合成枚举由 list_affected_outputs 用
            # _outputs_for_type 补 canonical（见 outputs.list_affected_outputs）。
            assert data["outputs_state"] == {}, "file-first：建表时不应预置产出槽"
            print("   ✓ industry topic 字段正确")

            # 创建 company topic
            path = create_topic(
                slug="test-company",
                display_name="测试公司",
                topic_type="company",
                question="这家公司怎么样？",
                geo="cn",
                depth="deep",
                variant="sonnet",
                parent_topic="test-industry",
                short_name="测试公司",
                ticker="SSE_688331",
            )
            data = read_topic("test-company", "sonnet")
            assert data["parent_topic"] == "test-industry"
            assert data["monitoring_tier"] == "dormant"  # 默认
            # file-first：company 同样空 seed（产出落地才注册）
            assert data["outputs_state"] == {}, "file-first：建表时不应预置产出槽"
            print("   ✓ company topic 字段正确\n")

            # 4. 测试 set_* 函数
            print("4. 测试 set_* 函数:")
            set_concepts("test-company", ["新概念1", "新概念2"], "sonnet")
            data = read_topic("test-company", "sonnet")
            assert data["concepts"] == ["新概念1", "新概念2"]
            print("   ✓ set_concepts ok")

            set_monitoring_tier("test-company", "deep", "sonnet")
            data = read_topic("test-company", "sonnet")
            assert data["monitoring_tier"] == "deep"
            print("   ✓ set_monitoring_tier ok")

            set_data_freshness("test-company", "c_investment_case", "2026-Q1", "sonnet")
            data = read_topic("test-company", "sonnet")
            assert data["outputs_state"]["c_investment_case"]["data_freshness"] == "2026-Q1"
            print("   ✓ set_data_freshness ok\n")

            print("=== 所有测试通过! ===")

        finally:
            # 恢复原始 _topics_dir
            topic._topics_dir = original_topics_dir


if __name__ == "__main__":
    test_phase0()
