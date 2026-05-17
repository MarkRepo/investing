"""Create, read, and update topic.yaml files. Zero LLM calls."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PRISM_ROOT = Path(__file__).resolve().parent.parent

# 基础输出 keys（所有 type 都有）
_BASE_OUTPUT_KEYS = [
    "01_business_panorama",
    "02_cycle_positioning",
    "03_narrative_ecology",
    "04_implied_expectations",
    "05_historical_mirrors",
    "06_risk_blindspots",
    "07_decision_kit",
    "08_living_feed",
]

# 按 topic.type 的输出 keys
_INDUSTRY_EXTRA_KEYS = ["09_industry_to_arenas"]
_ARENA_EXTRA_KEYS = ["10_peer_matrix"]
_COMPANY_EXTRA_KEYS = ["00_quality_screen"]

_DEFAULT_OUTPUT_STATE = {"version": 0, "last_updated": None, "status": "pending", "data_freshness": None}


def _infer_market(ticker: str, geo: str) -> str:
    """推断股票代码所属市场。CN 股根据首位数推断，其他默认 US。"""
    if not ticker:
        return ""
    if geo != "CN":
        return "US"
    if ticker[0] in ("6", "9", "5"):
        return "SSE"
    elif ticker[0] in ("0", "3"):
        return "SZSE"
    elif ticker[0] == "8":
        return "BSE"
    return "US"


def _outputs_for_type(topic_type: str) -> list[str]:
    if topic_type == "industry":
        return _BASE_OUTPUT_KEYS + _INDUSTRY_EXTRA_KEYS
    elif topic_type == "arena":
        return _BASE_OUTPUT_KEYS + _ARENA_EXTRA_KEYS
    elif topic_type == "company":
        return ["00_quality_screen"] + _BASE_OUTPUT_KEYS
    else:
        return _BASE_OUTPUT_KEYS


def next_stage(topic_type: str, current_stage: str) -> str | None:
    if current_stage in ("done", "quarantined"):
        return None

    if topic_type == "industry":
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "09-arena-shortlist",
            "done",
        ]
    elif topic_type == "arena":
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "10-peer-matrix",
            "done",
        ]
    elif topic_type == "company":
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "00-quality-screen",
            "04-synthesizing",
            "done",
        ]
    else:
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "done",
        ]

    try:
        idx = flow.index(current_stage)
        if idx + 1 < len(flow):
            return flow[idx + 1]
        return None
    except ValueError:
        for stage in flow:
            if stage > current_stage:
                return stage
        return None


def _topics_dir() -> Path:
    return PRISM_ROOT / "topics"


def _topic_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant，例如 'sonnet' 或 'qwen3.6-plus'")
    return _topics_dir() / slug / variant / "topic.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_topic(
    slug: str,
    display_name: str,
    topic_type: str,
    question: str,
    geo: str,
    depth: str,
    variant: str,
    ticker: str | None = None,
    parent_topic: str | None = None,
    concepts: list[str] | None = None,
    monitoring_tier: str = "dormant",
) -> Path:
    path = _topic_path(slug, variant)
    if path.exists():
        raise FileExistsError(f"Topic already exists: {slug}/{variant}")
    scope = {
        "geo": geo,
        "question": question,
        "depth": depth,
    }
    if ticker:
        scope["ticker"] = ticker
        scope["market"] = _infer_market(ticker, geo)
    data = {
        "slug": slug,
        "display_name": display_name,
        "type": topic_type,
        "created": _now_iso(),
        "status": "active",
        "stage": "00-init",
        "parent_topic": parent_topic,
        "monitoring_tier": monitoring_tier,
        "concepts": concepts or [],
        "scope": scope,
        "outputs_state": {key: dict(_DEFAULT_OUTPUT_STATE) for key in _outputs_for_type(topic_type)},
        "next_actions": ["运行 workflow 01-build-roadmap"],
        "user_todos": [],
        "monitoring": {"enabled": False, "cadence": "daily"},
    }
    _write_yaml(path, data)
    (path.parent / "outputs").mkdir(exist_ok=True)
    return path


def read_topic(slug: str, variant: str) -> dict:
    path = _topic_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}/{variant}")
    data = _read_yaml(path)
    data.setdefault("parent_topic", None)
    data.setdefault("monitoring_tier", "dormant")
    data.setdefault("concepts", [])
    if "outputs_state" in data:
        for key, state in data["outputs_state"].items():
            state.setdefault("data_freshness", None)
    return data


def update_topic(slug: str, variant: str, **fields) -> None:
    data = read_topic(slug, variant)
    data.update(fields)
    _write_yaml(_topic_path(slug, variant), data)


def set_stage(slug: str, stage: str, variant: str) -> None:
    update_topic(slug, variant, stage=stage)


def set_output_status(slug: str, output_key: str, status: str, variant: str, version: int | None = None) -> None:
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["status"] = status
    entry["last_updated"] = _now_iso()
    if version is not None:
        entry["version"] = version
    _write_yaml(_topic_path(slug, variant), data)


def set_next_actions(slug: str, actions: list[str], variant: str) -> None:
    update_topic(slug, variant, next_actions=actions)


def set_user_todos(slug: str, todos: list[str], variant: str) -> None:
    update_topic(slug, variant, user_todos=todos)


def set_concepts(slug: str, concepts: list[str], variant: str) -> None:
    update_topic(slug, variant, concepts=concepts)


def set_monitoring_tier(slug: str, tier: str, variant: str) -> None:
    if tier not in ("deep", "watch", "dormant"):
        raise ValueError(f"Invalid tier: {tier}, must be deep/watch/dormant")
    update_topic(slug, variant, monitoring_tier=tier)


def set_data_freshness(slug: str, output_key: str, freshness: str, variant: str) -> None:
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["data_freshness"] = freshness
    entry["last_updated"] = _now_iso()
    _write_yaml(_topic_path(slug, variant), data)


def list_variants(slug: str) -> list[str]:
    """List all model variant names under a topic slug."""
    slug_dir = _topics_dir() / slug
    if not slug_dir.is_dir():
        return []
    variants = []
    for sub in slug_dir.iterdir():
        if sub.is_dir() and (sub / "topic.yaml").is_file():
            variants.append(sub.name)
    return sorted(variants)


def list_topics(variant: str | None = None) -> list[dict]:
    """List all topics.

    Without variant: list all variants from all topics.
    With variant: only scan that variant under each topic slug.
    """
    root = _topics_dir()
    if not root.exists():
        return []
    results = []
    for slug_dir in root.iterdir():
        if not slug_dir.is_dir():
            continue
        if variant:
            path = slug_dir / variant / "topic.yaml"
            if path.is_file():
                try:
                    topic = _read_yaml(path)
                    topic["variant"] = variant
                    results.append(topic)
                except Exception:
                    pass
        else:
            for sub in slug_dir.iterdir():
                if sub.is_dir() and (sub / "topic.yaml").is_file():
                    try:
                        topic = _read_yaml(sub / "topic.yaml")
                        topic["variant"] = sub.name
                        results.append(topic)
                    except Exception:
                        pass
    results.sort(key=lambda t: t.get("created", ""), reverse=True)
    return results


def get_parent_materials_dir(slug: str, variant: str) -> Path | None:
    """If this topic has a parent_topic, return the parent's shared materials directory."""
    try:
        topic = read_topic(slug, variant)
        parent = topic.get("parent_topic")
        if parent:
            return _topics_dir() / parent / "materials"
    except Exception:
        pass
    return None


def list_parent_materials(slug: str, variant: str) -> list[str]:
    """List material filenames from the parent topic's materials directory."""
    parent_dir = get_parent_materials_dir(slug, variant)
    if parent_dir and parent_dir.is_dir():
        return sorted([p.name for p in parent_dir.iterdir() if p.is_file()])
    return []


def find_child_topics(parent_slug: str, variant: str | None = None) -> list[dict]:
    """Find all topics whose parent_topic matches parent_slug."""
    children = []
    for t in list_topics(variant=variant):
        if t.get("parent_topic") == parent_slug:
            children.append(t)
    return children