#!/usr/bin/env python3
"""辅助脚本：创建 doubao2.0code topic。"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prism.scripts.topic import create_topic
from prism.scripts.manifest import create_manifest

# 创建 topic
print("创建 topic...")
try:
    create_topic(
        slug="cn-commercial-space",
        display_name="中国商业航天",
        topic_type="industry",
        question="中国商业航天的发射与卫星制造环节的商业模式、竞争格局及破局点在哪里？",
        geo="CN",
        depth="deep",
        variant="doubao2.0code",
        concepts=["商业航天"],
        monitoring_tier="watch",
    )
except FileExistsError:
    print("topic 已存在，跳过创建")

# 创建 manifest
print("创建 manifest...")
create_manifest("cn-commercial-space", "doubao2.0code")

print("✅ 初始化完成")
