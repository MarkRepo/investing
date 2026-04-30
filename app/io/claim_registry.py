from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

CLAIM_SCHEMA_VERSION = "phase2-v1"
SCOPE_FILES = {
    "industry": "industries.jsonl",
    "arena": "arenas.jsonl",
    "company": "companies.jsonl",
    "cross_cutting": "cross_cutting.jsonl",
}
CLAIM_TYPES = {"thesis", "judgment", "risk", "scenario", "gate_assessment"}
CONFIDENCE_VALUES = {"high", "medium_high", "medium", "medium_low", "low"}
EVIDENCE_DIRECTIONS = {"supports", "refutes", "neutral"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        tmp.write(text)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    _atomic_write_text(path, text)


def build_evidence_entry(
    *,
    source_id: str,
    block_ids: list[str],
    fact_ids: list[str],
    direction: str,
    now: str,
) -> dict[str, Any]:
    if direction not in EVIDENCE_DIRECTIONS:
        raise ValueError(f"invalid evidence direction: {direction}")
    return {
        "source_id": source_id,
        "block_ids": block_ids,
        "fact_ids": fact_ids,
        "direction": direction,
        "weight": 1.0,
        "added_at": now,
        "added_by": "ingest",
    }


class ClaimRegistry:
    def __init__(self, base: Path):
        self.base = Path(base)
        self.claims_dir = self.base / "claims"
        self.counters_path = self.claims_dir / ".counters.json"
        self._claims_by_id: dict[str, dict[str, Any]] = {}
        self._by_scope: dict[tuple[str, str], list[str]] = {}
        self._rows_by_scope_type: dict[str, list[dict[str, Any]]] = {}
        self._counters: dict[str, int] = {}
        self._load_all()

    def _load_all(self) -> None:
        if self.counters_path.exists():
            self._counters = json.loads(self.counters_path.read_text(encoding="utf-8"))
        for scope_type, filename in SCOPE_FILES.items():
            rows = _read_jsonl(self.claims_dir / filename)
            self._rows_by_scope_type[scope_type] = rows
            for claim in rows:
                claim_id = claim["claim_id"]
                self._claims_by_id[claim_id] = claim
                key = (claim["scope_type"], claim.get("scope_ref", ""))
                self._by_scope.setdefault(key, []).append(claim_id)

    def _claim_path(self, scope_type: str) -> Path:
        if scope_type not in SCOPE_FILES:
            raise ValueError(f"invalid scope_type: {scope_type}")
        return self.claims_dir / SCOPE_FILES[scope_type]

    def _next_id(self, scope_type: str) -> str:
        current = int(self._counters.get(scope_type, 0)) + 1
        self._counters[scope_type] = current
        return f"clm-{scope_type}-{current:04d}"

    def _persist_scope(self, scope_type: str) -> None:
        _write_jsonl(self._claim_path(scope_type), self._rows_by_scope_type.get(scope_type, []))
        _atomic_write_text(
            self.counters_path,
            json.dumps(self._counters, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        )

    def find_by_id(self, claim_id: str) -> dict[str, Any] | None:
        return self._claims_by_id.get(claim_id)

    def claims_for_scope(self, scope_type: str, scope_ref: str) -> list[dict[str, Any]]:
        ids = self._by_scope.get((scope_type, scope_ref), [])
        return [self._claims_by_id[claim_id] for claim_id in ids]

    def all_claims_for_scope_type(self, scope_type: str) -> list[dict[str, Any]]:
        if scope_type not in SCOPE_FILES:
            raise ValueError(f"invalid scope_type: {scope_type}")
        return list(self._rows_by_scope_type.get(scope_type, []))

    def create_claim(
        self,
        *,
        claim_text: str,
        scope_type: str,
        scope_ref: str,
        claim_type: str,
        dimension_hint: str,
        confidence: str,
        as_of: str,
        evidence: dict[str, Any],
        trigger: str,
        trigger_ref: str,
        now: str,
    ) -> dict[str, Any]:
        if claim_type not in CLAIM_TYPES:
            raise ValueError(f"invalid claim_type: {claim_type}")
        if confidence not in CONFIDENCE_VALUES:
            raise ValueError(f"invalid confidence: {confidence}")
        claim_id = self._next_id(scope_type)
        claim = {
            "claim_id": claim_id,
            "claim_text": claim_text,
            "scope_type": scope_type,
            "scope_ref": scope_ref,
            "claim_type": claim_type,
            "dimension_hint": dimension_hint,
            "status": "active",
            "confidence": confidence,
            "as_of": as_of,
            "review_by": None,
            "supporting_evidence": [evidence],
            "related_claims": [],
            "state_log": [
                {
                    "timestamp": now,
                    "from_status": None,
                    "to_status": "active",
                    "trigger": trigger,
                    "trigger_ref": trigger_ref,
                }
            ],
            "user_override": None,
            "created_at": now,
            "last_updated": now,
            "schema_version": CLAIM_SCHEMA_VERSION,
        }
        self._rows_by_scope_type.setdefault(scope_type, []).append(claim)
        self._claims_by_id[claim_id] = claim
        self._by_scope.setdefault((scope_type, scope_ref), []).append(claim_id)
        self._persist_scope(scope_type)
        return claim
