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

    def _rewrite_claim(self, claim: dict[str, Any]) -> None:
        scope_type = claim["scope_type"]
        rows = self._rows_by_scope_type.get(scope_type, [])
        for idx, row in enumerate(rows):
            if row["claim_id"] == claim["claim_id"]:
                rows[idx] = claim
                self._claims_by_id[claim["claim_id"]] = claim
                self._persist_scope(scope_type)
                return
        raise KeyError(claim["claim_id"])

    def append_evidence(self, claim_id: str, evidence: dict[str, Any], *, now: str) -> dict[str, Any]:
        claim = self.find_by_id(claim_id)
        if claim is None:
            raise KeyError(claim_id)
        claim["supporting_evidence"].append(evidence)
        claim["last_updated"] = now
        self._rewrite_claim(claim)
        return claim

    def split_claim(
        self,
        claim_id: str,
        *,
        new_claim_specs: list[dict[str, Any]],
        now: str,
    ) -> list[dict[str, Any]]:
        original = self.find_by_id(claim_id)
        if original is None:
            raise KeyError(claim_id)
        if original.get("status") != "active":
            raise ValueError(f"cannot split non-active claim: {claim_id}")

        new_claims = []
        for spec in new_claim_specs:
            new_claim = self.create_claim(
                claim_text=spec["claim_text"],
                scope_type=spec["scope_type"],
                scope_ref=spec["scope_ref"],
                claim_type=spec["claim_type"],
                dimension_hint=spec["dimension_hint"],
                confidence=spec["confidence"],
                as_of=spec["as_of"],
                evidence=spec["evidence"],
                trigger="split_from",
                trigger_ref=claim_id,
                now=now,
            )
            new_claims.append(new_claim)

        original["status"] = "retired"
        original["last_updated"] = now
        original["state_log"].append(
            {
                "timestamp": now,
                "from_status": "active",
                "to_status": "retired",
                "trigger": "split",
                "trigger_ref": claim_id,
                "split_to_claim_ids": [claim["claim_id"] for claim in new_claims],
            }
        )
        self._rewrite_claim(original)
        return new_claims

    def list_claims(
        self,
        scope_type: str | None = None,
        scope_ref: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return claims filtered by scope_type and/or scope_ref.

        - Both provided: return claims_for_scope(scope_type, scope_ref)
        - scope_type only: return all_claims_for_scope_type(scope_type)
        - Neither: return all claims across all scope files
        """
        if scope_type is not None and scope_ref is not None:
            return self.claims_for_scope(scope_type, scope_ref)
        if scope_type is not None:
            return self.all_claims_for_scope_type(scope_type)
        # no filter — return everything
        all_rows: list[dict[str, Any]] = []
        for rows in self._rows_by_scope_type.values():
            all_rows.extend(rows)
        return all_rows

    def append_audit_event(self, event: dict[str, Any]) -> None:
        path = self.base / "audit" / "claim-events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")

    def check_integrity(self) -> list[str]:
        warnings: list[str] = []
        seen_ids: set[str] = set()
        max_by_scope: dict[str, int] = {}
        for scope_type, rows in self._rows_by_scope_type.items():
            for claim in rows:
                claim_id = claim["claim_id"]
                if claim_id in seen_ids:
                    warnings.append(f"duplicate claim_id: {claim_id}")
                seen_ids.add(claim_id)
                suffix = int(claim_id.rsplit("-", 1)[1])
                max_by_scope[scope_type] = max(max_by_scope.get(scope_type, 0), suffix)
                for evidence in claim.get("supporting_evidence", []):
                    if not evidence.get("source_id"):
                        warnings.append(f"empty evidence source_id: {claim_id}")
                if claim.get("status") == "retired" and claim.get("state_log", [])[-1].get("trigger") != "split":
                    warnings.append(f"retired claim without split log: {claim_id}")
        for scope_type, max_id in max_by_scope.items():
            counter = int(self._counters.get(scope_type, 0))
            if counter != max_id:
                warnings.append(f"counter mismatch for {scope_type}: counter={counter} max_id={max_id}")
        return warnings
