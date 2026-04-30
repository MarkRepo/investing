import json
from argparse import Namespace

from scripts import ingest_apply, ingest_match, ingest_qa


def test_phase2_minimal_match_apply_evaluation_chain(tmp_path):
    bundle = {
        "bundle_version": "v2-phase1",
        "source_digest": {
            "source_id": "src-001",
            "source_date": "2024-12-31",
            "scope_type": "company",
            "scope_ref": "SSE_600519",
        },
        "insight_blocks": [{"id": "ib-001", "title": "品牌", "dimension_hint": "moat"}],
        "atomic_facts": [{"fact_id": "fact-001", "linked_block_id": "ib-001", "fact_text": "事实", "evidence_quote": "原文 A。", "source_page": 1, "confidence": "medium"}],
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
        "company_candidates": [],
        "stage_gates": [],
        "synthesis": {"one_sentence": "s", "what_we_know": [], "what_is_plausible": [], "cannot_conclude": [], "investment_questions": []},
        "schema_fit_review": {"fits_current_schema": True, "missing_schema_fields": [], "extra_fields_needed": [], "notes": ""},
    }
    preprocess = {
        "meta": {"preprocess_version": "v2-phase1"},
        "sections": [{"name": "S1", "text": "原文 A。"}],
        "preprocess_metadata": {"page_count": 1, "extracted_pages": [{"page": 1, "text_quality": "ok"}], "extraction_warnings": []},
        "figure_contexts": [],
    }
    bundle_path = tmp_path / "bundle.json"
    preprocess_path = tmp_path / "preprocess.json"
    match_path = tmp_path / "pending" / "match-src-001.json"
    eval_path = tmp_path / "evaluation.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    preprocess_path.write_text(json.dumps(preprocess, ensure_ascii=False), encoding="utf-8")

    assert ingest_match.cmd_match(Namespace(bundle=str(bundle_path), registry_base=str(tmp_path), out=str(match_path))) == 0
    match = json.loads(match_path.read_text(encoding="utf-8"))
    match["decisions_required"][0]["decision"] = "new"
    match["decisions_required"][0]["decision_reason"] = "无可挂接旧命题"
    match_path.write_text(json.dumps(match, ensure_ascii=False), encoding="utf-8")

    assert ingest_apply.cmd_apply(Namespace(match=str(match_path), bundle=str(bundle_path), registry_base=str(tmp_path))) == 0
    assert ingest_qa.cmd_evaluation_init(Namespace(bundle=str(bundle_path), preprocess=str(preprocess_path), match=str(match_path), out=str(eval_path))) == 0

    claim_lines = (tmp_path / "claims" / "companies.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(claim_lines) == 1
    evaluation = json.loads(eval_path.read_text(encoding="utf-8"))
    assert evaluation["matching_metrics"]["decisions"]["new"] == 1
    assert (tmp_path / "pending" / "archive-writes-src-001.json").exists()
