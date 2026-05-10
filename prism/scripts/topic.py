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
    data = {
        "slug": slug,
        "display_name": display_name,
        "type": topic_type,
        "created": _now_iso(),
        "status": "active",
        "stage": "00-init",
        "scope": scope,
        "outputs_state": {key: dict(_DEFAULT_OUTPUT_STATE) for key in _OUTPUT_KEYS},
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
    return _read_yaml(path)


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
            # Scan all variant subdirs
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
