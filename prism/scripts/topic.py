"""Create, read, and update topic.yaml files. Zero LLM calls."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent

_OUTPUT_KEYS = [
    "01_business_panorama",
    "02_cycle_positioning",
    "03_narrative_ecology",
    "04_implied_expectations",
    "05_historical_mirrors",
    "06_risk_blindspots",
    "07_decision_kit",
    "08_living_feed",
]

_DEFAULT_OUTPUT_STATE = {"version": 0, "last_updated": None, "status": "pending"}


def _topics_dir() -> Path:
    return _PRISM_ROOT / "topics"


def _topic_path(slug: str) -> Path:
    return _topics_dir() / slug / "topic.yaml"


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
) -> Path:
    path = _topic_path(slug)
    if path.exists():
        raise FileExistsError(f"Topic already exists: {slug}")
    data = {
        "slug": slug,
        "display_name": display_name,
        "type": topic_type,
        "created": _now_iso(),
        "status": "active",
        "stage": "00-init",
        "scope": {
            "geo": geo,
            "question": question,
            "depth": depth,
        },
        "outputs_state": {key: dict(_DEFAULT_OUTPUT_STATE) for key in _OUTPUT_KEYS},
        "next_actions": ["运行 workflow 01-build-roadmap"],
        "user_todos": [],
        "monitoring": {"enabled": False, "cadence": "daily"},
    }
    _write_yaml(path, data)
    (path.parent / "outputs").mkdir(exist_ok=True)
    return path


def read_topic(slug: str) -> dict:
    path = _topic_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}")
    return _read_yaml(path)


def update_topic(slug: str, **fields) -> None:
    data = read_topic(slug)
    data.update(fields)
    _write_yaml(_topic_path(slug), data)


def set_stage(slug: str, stage: str) -> None:
    update_topic(slug, stage=stage)


def set_output_status(slug: str, output_key: str, status: str, version: int | None = None) -> None:
    data = read_topic(slug)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["status"] = status
    entry["last_updated"] = _now_iso()
    if version is not None:
        entry["version"] = version
    _write_yaml(_topic_path(slug), data)


def set_next_actions(slug: str, actions: list[str]) -> None:
    update_topic(slug, next_actions=actions)


def set_user_todos(slug: str, todos: list[str]) -> None:
    update_topic(slug, user_todos=todos)


def list_topics() -> list[dict]:
    root = _topics_dir()
    if not root.exists():
        return []
    results = []
    for d in root.iterdir():
        path = d / "topic.yaml"
        if path.is_file():
            try:
                results.append(_read_yaml(path))
            except Exception:
                pass
    results.sort(key=lambda t: t.get("created", ""), reverse=True)
    return results
