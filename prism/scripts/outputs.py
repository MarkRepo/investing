"""Query output state for topics. Zero LLM calls."""
from __future__ import annotations

from pathlib import Path

import markdown as _md
import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

_OUTPUT_KEYS_LABELS = [
    ("01_business_panorama", "商业全景"),
    ("02_cycle_positioning", "周期定位"),
    ("03_narrative_ecology", "叙事谱系"),
    ("04_implied_expectations", "隐含预期与观点光谱"),
    ("05_historical_mirrors", "历史镜像"),
    ("06_risk_blindspots", "风险盲点"),
    ("07_decision_kit", "决策辅助"),
    ("08_living_feed", "信息流时间线"),
]


def _topic_dir(slug: str) -> Path:
    return _PRISM_ROOT / "topics" / slug


def _read_topic_yaml(slug: str) -> dict:
    path = _topic_dir(slug) / "topic.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def list_outputs(slug: str) -> list[dict]:
    data = _read_topic_yaml(slug)
    outputs_state = data.get("outputs_state", {})
    result = []
    for key, label in _OUTPUT_KEYS_LABELS:
        state = outputs_state.get(key, {"version": 0, "last_updated": None, "status": "pending"})
        out_path = _topic_dir(slug) / "outputs" / f"{key}.md"
        result.append({
            "key": key,
            "label": label,
            "status": state.get("status", "pending"),
            "version": state.get("version", 0),
            "last_updated": state.get("last_updated"),
            "file_exists": out_path.is_file(),
        })
    return result


def read_output_html(slug: str, output_key: str) -> str:
    out_path = _topic_dir(slug) / "outputs" / f"{output_key}.md"
    if not out_path.is_file():
        raise FileNotFoundError(f"Output not yet generated: {output_key}")
    raw = out_path.read_text(encoding="utf-8")
    return _md.markdown(raw, extensions=["tables", "fenced_code"])
