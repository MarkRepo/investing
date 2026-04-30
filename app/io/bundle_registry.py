from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import app.config as cfg


def _base(base: Path | None = None) -> Path:
    if base is not None:
        return Path(base)
    return cfg.BASE_PATH


def _registry_path(base: Path | None = None) -> Path:
    return _base(base) / "data" / "bundle_registry.jsonl"


def append_registry(entry: dict[str, Any], base: Path | None = None) -> None:
    path = _registry_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def list_bundles(filters: dict[str, Any] | None = None, base: Path | None = None) -> list[dict[str, Any]]:
    path = _registry_path(base)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    if filters:
        if "type" in filters:
            rows = [r for r in rows if r.get("source_type") == filters["type"]]
        if "institution" in filters:
            rows = [r for r in rows if r.get("institution") == filters["institution"]]
        if "industry" in filters:
            rows = [
                r for r in rows
                if filters["industry"] in r.get("touched", {}).get("industries", [])
            ]
    rows.sort(key=lambda r: r.get("ingested_at", ""), reverse=True)
    return rows


def get_bundle(source_id: str, base: Path | None = None) -> dict[str, Any] | None:
    for row in list_bundles(base=base):
        if row.get("source_id") == source_id:
            return row
    return None


def load_bundle_json(source_id: str, base: Path | None = None) -> dict[str, Any]:
    entry = get_bundle(source_id, base=base)
    if entry is None:
        raise FileNotFoundError(source_id)
    bundle_path = _base(base) / entry["bundle_path"]
    return json.loads(bundle_path.read_text(encoding="utf-8"))
