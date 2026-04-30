import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from scripts import ingest_match


def _bundle():
    return {
        "source_digest": {"source_id": "src-001", "source_date": "2024-12-31"},
        "claim_candidates": [
            {
                "candidate_id": "cc-001",
                "claim_text": "茅台品牌溢价来自白酒文化根基",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "claim_type": "judgment",
                "dimension_hint": "moat",
                "confidence": "medium_high",
                "as_of": "2024-12-31",
                "direction_on_source": "supports",
                "supporting_block_ids": ["ib-001"],
            }
        ],
    }


def test_cmd_match_writes_pending_file_with_empty_registry(tmp_path):
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    out = tmp_path / "pending" / "match-src-001.json"

    rc = ingest_match.cmd_match(
        Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["source_id"] == "src-001"
    assert data["bundle_ref"] == str(bundle_path)
    assert data["matching_engine_version"] == "phase2-v1"
    assert data["decisions_required"][0]["candidate_id"] == "cc-001"
    assert data["decisions_required"][0]["top_matches"] == []
    assert data["decisions_required"][0]["decision"] is None
    assert data["summary_stats"] == {
        "total_candidates": 1,
        "with_matches": 0,
        "no_matches_suggest_new": 1,
        "high_confidence_matches": 0,
    }


def test_cmd_match_uses_scope_filtered_registry_claims(tmp_path):
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="src-old",
        block_ids=["ib-old"],
        fact_ids=["fact-old"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="茅台品牌溢价来自白酒消费文化",
        scope_type="company",
        scope_ref="SZSE_000858",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2023-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()), encoding="utf-8")
    out = tmp_path / "pending" / "match-src-001.json"

    rc = ingest_match.cmd_match(
        Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    matches = data["decisions_required"][0]["top_matches"]
    assert [m["claim_id"] for m in matches] == ["clm-company-0001"]
    assert data["summary_stats"]["with_matches"] == 1
