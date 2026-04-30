from __future__ import annotations

from typing import Any

DIMENSION_TO_ARCHIVE: dict[tuple[str, str], tuple[str, int]] = {
    ("company", "moat"): ("archive/layer8/company/{scope_ref}/moat.jsonl", 8),
    ("company", "demand"): ("archive/layer8/company/{scope_ref}/demand.jsonl", 8),
    ("industry", "demand"): ("archive/layer11/industry/{scope_ref}/demand.jsonl", 11),
    ("arena", "competition"): ("archive/layer6/arena/{scope_ref}/competition.jsonl", 6),
}


def suggest_archive_target(scope_type: str, scope_ref: str, dimension_hint: str) -> dict[str, Any] | None:
    mapping = DIMENSION_TO_ARCHIVE.get((scope_type, dimension_hint))
    if mapping is None:
        return None
    template, layer = mapping
    return {
        "archive_layer": layer,
        "archive_path": template.format(scope_ref=scope_ref),
        "action": "append",
    }
