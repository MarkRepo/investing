import json
from argparse import Namespace

from scripts import ingest_qa as qa


def _minimal_valid_preprocess():
    return {
        "meta": {"preprocess_version": "v2-phase1"},
        "sections": [{"name": "S1", "text": "原文 A。"}],
        "preprocess_metadata": {
            "page_count": 1,
            "extracted_pages": [{"page": 1, "text_quality": "ok"}],
            "extraction_warnings": [],
        },
        "figure_contexts": [],
    }


def _valid_bundle():
    return {
        "bundle_version": "v2-phase1",
        "source_digest": {
            "source_id": "test-001",
            "source_type": "industry_report",
            "source_date": "2026-04-30",
            "source_quality": "medium",
            "evidence_strength": "medium",
            "coverage_review": {
                "mode": "full_report_pass",
                "sections_total": 1,
                "sections_reviewed": 1,
                "skipped_sections": 0,
                "coverage_notes": [],
            },
        },
        "insight_blocks": [
            {
                "id": "ib-001",
                "block_type": "demand_driver",
                "title": "t",
                "summary": "s",
                "evidence_strength": "medium",
                "reasoning_chain": ["原文观察", "投资含义"],
            }
        ],
        "atomic_facts": [
            {
                "fact_id": "fact-001",
                "linked_block_id": "ib-001",
                "fact_text": "原文 A。",
                "evidence_quote": "原文 A。",
                "source_page": 1,
                "confidence": "medium",
            }
        ],
        "stage_gates": [],
        "company_candidates": [],
        "synthesis": {
            "one_sentence": "s",
            "what_we_know": [],
            "what_is_plausible": [],
            "cannot_conclude": [],
            "investment_questions": [],
        },
        "schema_fit_review": {
            "fits_current_schema": True,
            "missing_schema_fields": [],
            "extra_fields_needed": [],
            "notes": "",
        },
        "qa_warnings": [],
        "write_status": "not_applicable_phase1",
    }


def _bundle_with_known_warnings():
    bundle = _valid_bundle()
    bundle["atomic_facts"][0]["linked_block_id"] = "ib-999"
    return bundle


def test_evaluation_init_produces_skeleton_from_qa(tmp_path):
    bundle = _bundle_with_known_warnings()
    preprocess = _minimal_valid_preprocess()
    bpath = tmp_path / "bundle.json"
    bpath.write_text(json.dumps(bundle), encoding="utf-8")
    ppath = tmp_path / "preprocess.json"
    ppath.write_text(json.dumps(preprocess), encoding="utf-8")
    out = tmp_path / "evaluation.json"

    rc = qa.cmd_evaluation_init(Namespace(bundle=str(bpath), preprocess=str(ppath), match=None, out=str(out)))

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["bundle_ref"] == "test-001"
    assert data["method_layers_run"] == ["L1"]
    assert set(data["dimension_ratings"]) == {
        "coverage_fidelity",
        "reasoning_quality",
        "calibration",
        "narrative",
        "claim_extraction_quality",
        "matching_accuracy",
        "claim_lifecycle_discipline",
    }
    for dim in data["dimension_ratings"].values():
        assert dim["trend"] is None and dim["notes"] == ""
    assert "system_fit" in data and "phase2_readiness" in data and "phase3_readiness" in data
    assert data["matching_metrics"] == {}
    assert data["eval_prompt_version"] == "phase2-v1"
    assert len(data["defects"]) >= 1
    assert any(d["category"] == "fact_unknown_linked_block" for d in data["defects"])


def test_evaluation_init_produces_skeleton_with_no_warnings(tmp_path):
    bpath = tmp_path / "bundle.json"
    bpath.write_text(json.dumps(_valid_bundle()), encoding="utf-8")
    ppath = tmp_path / "preprocess.json"
    ppath.write_text(json.dumps(_minimal_valid_preprocess()), encoding="utf-8")
    out = tmp_path / "evaluation.json"

    rc = qa.cmd_evaluation_init(Namespace(bundle=str(bpath), preprocess=str(ppath), match=None, out=str(out)))

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["defects"] == []


def test_evaluation_init_with_match_adds_matching_metrics(tmp_path):
    bpath = tmp_path / "bundle.json"
    bpath.write_text(json.dumps(_valid_bundle()), encoding="utf-8")
    ppath = tmp_path / "preprocess.json"
    ppath.write_text(json.dumps(_minimal_valid_preprocess()), encoding="utf-8")
    match = {
        "decisions_required": [
            {
                "candidate_id": "cc-001",
                "top_matches": [{"claim_id": "clm-company-0001", "score": 0.82, "high_confidence": True}],
                "decision": "new",
            },
            {
                "candidate_id": "cc-002",
                "top_matches": [{"claim_id": "clm-company-0002", "score": 0.27, "high_confidence": False}],
                "decision": "attach",
            },
            {
                "candidate_id": "cc-003",
                "top_matches": [],
                "decision": "split",
            },
        ]
    }
    mpath = tmp_path / "match.json"
    mpath.write_text(json.dumps(match), encoding="utf-8")
    out = tmp_path / "evaluation.json"

    rc = qa.cmd_evaluation_init(
        Namespace(bundle=str(bpath), preprocess=str(ppath), match=str(mpath), out=str(out))
    )

    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["matching_metrics"] == {
        "total_candidates": 3,
        "decisions": {"attach": 1, "new": 1, "split": 1, "skip": 0},
        "high_confidence_matches_not_attached": 1,
        "low_confidence_matches_attached": 1,
    }
