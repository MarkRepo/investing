#!/usr/bin/env python3
"""更新 topic.yaml 到 Phase 0 schema"""
import yaml
from pathlib import Path
from datetime import datetime, timezone

PRISM_ROOT = Path(__file__).resolve().parent.parent
TOPIC_PATH = PRISM_ROOT / "topics" / "cn-commercial-space" / "doubao2.0code" / "topic.yaml"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# 读取旧 topic
with open(TOPIC_PATH, encoding="utf-8") as f:
    topic = yaml.safe_load(f)

# Phase 0 新增字段
topic["parent_topic"] = None
topic["monitoring_tier"] = "watch"
topic["concepts"] = ["商业航天"]

# 更新 outputs_state，加上 data_freshness 默认值，以及 industry_to_arenas sidecar
base_output_state = {"version": 1, "last_updated": now_iso(), "status": "fresh", "data_freshness": "2026-01"}

# 为现有 outputs 加上 data_freshness
for key, state in topic["outputs_state"].items():
    state.setdefault("data_freshness", "2026-01")

# 加上 industry_to_arenas（旧名 09_industry_to_arenas 已退休）
topic["outputs_state"]["industry_to_arenas"] = {
    "version": 1,
    "last_updated": now_iso(),
    "status": "fresh",
    "data_freshness": "2026-01"
}

# 更新 stage（industry 流：04-synthesizing → 04-post-synthesis → 05-critic-review → done）
topic["stage"] = "05-critic-review"

# 更新 next_actions
topic["next_actions"] = [
    "09-industry-to-arenas 已完成，可选择为深挖档创建 arena topic",
    "或继续进入日常监控"
]

# 更新 user_todos
topic["user_todos"] = [
    "Phase 0-3 的 prism 漏斗改造已在本 topic 上应用（新 schema + 09-industry-to-arenas 产出）",
    "可选择：为深挖档（可复用火箭发射链、卫星通信相控阵与终端）创建 arena topic",
    "或运行 06-daily-monitor 进行日常监控"
]

# 写回
with open(TOPIC_PATH, "w", encoding="utf-8") as f:
    yaml.dump(topic, f, allow_unicode=True, sort_keys=False)

print(f"已更新 topic.yaml: {TOPIC_PATH}")
print(f"新字段: parent_topic={topic['parent_topic']}, monitoring_tier={topic['monitoring_tier']}, concepts={topic['concepts']}")
print(f"outputs_state 新增: industry_to_arenas")
print(f"stage: {topic['stage']}")
