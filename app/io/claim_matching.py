from __future__ import annotations

from typing import Any

MATCHING_ENGINE_VERSION = "phase2-v1"
TYPE_COMPATIBLE_PAIRS = {frozenset({"thesis", "judgment"}), frozenset({"risk", "scenario"})}
LOW_SCORE_THRESHOLD = 0.25
HIGH_CONFIDENCE_THRESHOLD = 0.80
TOP_K = 3


def _char_bigrams(text: str) -> set[str]:
    compact = "".join((text or "").split())
    if len(compact) < 2:
        return set()
    return {compact[i : i + 2] for i in range(len(compact) - 1)}


def char_bigram_jaccard(a: str, b: str) -> float:
    left = _char_bigrams(a)
    right = _char_bigrams(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def is_type_compatible(existing_type: str, candidate_type: str) -> bool:
    if existing_type == candidate_type:
        return True
    return frozenset({existing_type, candidate_type}) in TYPE_COMPATIBLE_PAIRS


def dimension_boost(existing_dimension: str, candidate_dimension: str) -> float:
    if existing_dimension == candidate_dimension and existing_dimension:
        return 0.15
    existing_prefix = (existing_dimension or "").split(".", 1)[0]
    candidate_prefix = (candidate_dimension or "").split(".", 1)[0]
    if existing_prefix and existing_prefix == candidate_prefix:
        return 0.05
    return 0.0


def _supporting_source_ids(claim: dict[str, Any]) -> list[str]:
    ids = []
    for evidence in claim.get("supporting_evidence", []) or []:
        source_id = evidence.get("source_id")
        if source_id and source_id not in ids:
            ids.append(source_id)
    return ids


def _snapshot(claim: dict[str, Any]) -> dict[str, Any]:
    return {
        "claim_text": claim.get("claim_text", ""),
        "status": claim.get("status", ""),
        "confidence": claim.get("confidence", ""),
        "as_of": claim.get("as_of", ""),
        "supporting_source_ids": _supporting_source_ids(claim),
    }


def match_candidate(candidate: dict[str, Any], claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    candidate_type = candidate.get("claim_type", "")
    candidate_dimension = candidate.get("dimension_hint", "")
    for claim in claims:
        if claim.get("status") == "retired":
            continue
        existing_type = claim.get("claim_type", "")
        if not is_type_compatible(existing_type, candidate_type):
            continue
        text_score = char_bigram_jaccard(candidate.get("claim_text", ""), claim.get("claim_text", ""))
        boost = dimension_boost(claim.get("dimension_hint", ""), candidate_dimension)
        score = 0.85 * text_score + boost
        if score < LOW_SCORE_THRESHOLD:
            continue
        reasons = [f"text_bigram_jaccard={text_score:.2f}"]
        if boost == 0.15:
            reasons.append(f"same_dimension={candidate_dimension}")
        elif boost == 0.05:
            reasons.append(f"same_dimension_prefix={candidate_dimension.split('.', 1)[0]}")
        if existing_type == candidate_type:
            reasons.append(f"type_match={candidate_type}")
        else:
            reasons.append(f"type_compatible={candidate_type}~{existing_type}")
        match = {
            "claim_id": claim["claim_id"],
            "score": round(score, 4),
            "high_confidence": score >= HIGH_CONFIDENCE_THRESHOLD,
            "reasons": reasons,
            "existing_claim_snapshot": _snapshot(claim),
        }
        scored.append(match)
    scored.sort(key=lambda item: (-item["score"], item["claim_id"]))
    return scored[:TOP_K]
