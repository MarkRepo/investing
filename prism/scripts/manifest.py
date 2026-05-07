"""Material manifest for a research topic. Zero LLM calls."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent


def _topics_dir() -> Path:
    return _PRISM_ROOT / "topics"


def _manifest_path(slug: str) -> Path:
    return _topics_dir() / slug / "manifest.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_manifest(slug: str) -> Path:
    path = _manifest_path(slug)
    data = {"slug": slug, "updated": _now_iso(), "materials": []}
    _write_yaml(path, data)
    return path


def read_manifest(slug: str) -> dict:
    path = _manifest_path(slug)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found for topic: {slug}")
    return _read_yaml(path)


def add_material(slug: str, filename: str, source_type: str, notes: str = "") -> str:
    data = read_manifest(slug)
    mat_id = f"mat-{uuid.uuid4().hex[:6]}"
    data["materials"].append({
        "id": mat_id,
        "filename": filename,
        "source_type": source_type,
        "added": _now_iso(),
        "processed": False,
        "notes": notes,
    })
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug), data)
    return mat_id


def mark_processed(slug: str, mat_id: str) -> None:
    data = read_manifest(slug)
    for mat in data["materials"]:
        if mat["id"] == mat_id:
            mat["processed"] = True
            break
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug), data)


def list_unprocessed(slug: str) -> list[dict]:
    return [m for m in read_manifest(slug)["materials"] if not m["processed"]]


def material_count(slug: str) -> dict:
    materials = read_manifest(slug)["materials"]
    processed = sum(1 for m in materials if m["processed"])
    return {"total": len(materials), "processed": processed, "unprocessed": len(materials) - processed}
