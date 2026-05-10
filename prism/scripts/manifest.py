"""Material manifest for a research topic. Zero LLM calls."""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

_PRISM_ROOT = Path(__file__).resolve().parent.parent


def _topics_dir() -> Path:
    return _PRISM_ROOT / "topics"


def _materials_dir(slug: str) -> Path:
    return _topics_dir() / slug / "materials"


def _manifest_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant，例如 'sonnet' 或 'qwen3.6-plus'")
    return _topics_dir() / slug / variant / "manifest.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_manifest(slug: str, variant: str) -> Path:
    path = _manifest_path(slug, variant)
    data = {"slug": slug, "variant": variant, "updated": _now_iso(), "materials": []}
    _write_yaml(path, data)
    # Create materials directory (shared across variants)
    _materials_dir(slug).mkdir(parents=True, exist_ok=True)
    return path


def read_manifest(slug: str, variant: str) -> dict:
    path = _manifest_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found for topic: {slug}/{variant}")
    return _read_yaml(path)


def get_material_path(slug: str, filename: str) -> Path | None:
    """Find material file in priority order:
    1. prism/topics/{slug}/materials/{filename}
    2. prism/inbox/manual/{filename}
    3. prism/inbox/auto/{filename}
    """
    locations = [
        _materials_dir(slug) / filename,
        _PRISM_ROOT / "inbox" / "manual" / filename,
        _PRISM_ROOT / "inbox" / "auto" / filename,
    ]
    for loc in locations:
        if loc.exists():
            return loc
    return None


def add_material(
    slug: str,
    filename: str,
    source_type: str,
    variant: str,
    notes: str = "",
    source_path: Path | None = None,
) -> str:
    """Add a material to the manifest.
    If source_path is provided, copies the file to topic's materials directory.
    """
    data = read_manifest(slug, variant)
    mat_id = f"mat-{uuid.uuid4().hex[:6]}"

    # Copy file if source_path provided
    if source_path and source_path.exists():
        materials_dir = _materials_dir(slug)
        materials_dir.mkdir(parents=True, exist_ok=True)
        dest_path = materials_dir / source_path.name
        if not dest_path.exists():
            shutil.copy2(source_path, dest_path)
        # Use the actual filename (might be different from input)
        filename = dest_path.name

    data["materials"].append({
        "id": mat_id,
        "filename": filename,
        "source_type": source_type,
        "added": _now_iso(),
        "processed": False,
        "notes": notes,
    })
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug, variant), data)
    return mat_id


def mark_processed(slug: str, mat_id: str, variant: str) -> None:
    data = read_manifest(slug, variant)
    for mat in data["materials"]:
        if mat["id"] == mat_id:
            mat["processed"] = True
            break
    data["updated"] = _now_iso()
    _write_yaml(_manifest_path(slug, variant), data)


def list_unprocessed(slug: str, variant: str) -> list[dict]:
    return [m for m in read_manifest(slug, variant)["materials"] if not m["processed"]]


def material_count(slug: str, variant: str) -> dict:
    materials = read_manifest(slug, variant)["materials"]
    processed = sum(1 for m in materials if m["processed"])
    return {"total": len(materials), "processed": processed, "unprocessed": len(materials) - processed}
