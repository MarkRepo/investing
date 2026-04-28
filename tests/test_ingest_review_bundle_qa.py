import json
from scripts import ingest_qa as qa


def valid_bundle() -> dict:
    return {
        "bundle_version": "v2-phase1",
        "source_digest": {
            "source_id": "src-1",
            "source_quality": "medium_high",
            "evidence_strength": "medium",
        },
        "insight_blocks": [
            {
                "id": "ib-001",
                "block_type": "demand_driver",
                "title": "需求驱动",
                "source_page_range": "1-2",
                "summary": "需求增长来自政策和经济性。",
                "evidence_strength": "medium",
                "reasoning_chain": ["政策支持", "经济性改善"],
            }
        ],
        "atomic_facts": [
            {
                "fact_id": "fact-001",
                "linked_block_id": "ib-001",
                "fact_text": "2025 年新增装机提升。",
                "evidence_quote": "2025 年新增装机提升",
                "source_page": 1,
                "confidence": "medium",
            }
        ],
        "stage_gates": [],
        "company_candidates": [],
        "synthesis": {
            "one_sentence": "储能需求改善，但仍需验证经济性。",
            "evidence_strength": "medium",
            "what_we_know": ["新增装机提升。"],
            "what_is_plausible": [],
            "what_needs_verification": [],
            "investment_questions": [],
            "cannot_conclude": [],
        },
        "schema_fit_review": {},
        "write_status": "not_applicable_phase1",
    }


def test_missing_insight_blocks_returns_error():
    bundle = valid_bundle()
    bundle["insight_blocks"] = []

    warnings = qa.check_review_bundle_shape(bundle)

    assert any(w["rule"] == "missing_insight_blocks" and w["severity"] == "error" for w in warnings)


def test_fact_without_linked_block_id_returns_error():
    bundle = valid_bundle()
    bundle["atomic_facts"][0].pop("linked_block_id")

    warnings = qa.check_fact_block_links(bundle)

    assert any(w["rule"] == "fact_missing_linked_block" and w["severity"] == "error" for w in warnings)


def test_fact_linked_to_nonexistent_block_returns_error():
    bundle = valid_bundle()
    bundle["atomic_facts"][0]["linked_block_id"] = "ib-missing"

    warnings = qa.check_fact_block_links(bundle)

    assert any(w["rule"] == "fact_unknown_linked_block" and w["severity"] == "error" for w in warnings)


def test_fact_without_evidence_quote_returns_error():
    bundle = valid_bundle()
    bundle["atomic_facts"][0]["evidence_quote"] = ""

    warnings = qa.check_fact_block_links(bundle)

    assert any(w["rule"] == "fact_missing_evidence_quote" and w["severity"] == "error" for w in warnings)


def test_evidence_quote_not_found_in_preprocess_text_returns_warning():
    bundle = valid_bundle()
    preprocess = {
        "sections": [
            {"action": "keep", "text": "这里没有对应证据。"},
        ]
    }

    warnings = qa.check_fact_evidence_quotes(bundle, preprocess)

    assert any(w["rule"] == "evidence_quote_not_found" and w["severity"] == "warning" for w in warnings)
    assert any("PDF→text" in w["detail"] for w in warnings)


def test_valid_bundle_returns_no_warnings_when_quote_matches_preprocess():
    preprocess = {
        "sections": [
            {"action": "keep", "text": "2025 年新增装机提升，需求改善。"},
        ]
    }

    warnings = qa.check_ingest_review_bundle(valid_bundle(), preprocess)

    assert warnings == []


def test_high_confidence_fact_from_chart_heavy_page_returns_warning():
    bundle = valid_bundle()
    bundle["atomic_facts"][0]["confidence"] = "high"
    preprocess = {
        "sections": [{"action": "keep", "text": "2025 年新增装机提升。"}],
        "preprocess_metadata": {
            "extracted_pages": [
                {"page": 1, "text_quality": "high", "image_heavy": False, "chart_heavy": True, "table_heavy": False},
            ]
        },
    }

    warnings = qa.check_preprocess_risk_confidence(bundle, preprocess)

    assert any(w["rule"] == "high_confidence_fact_from_risky_page" and w["severity"] == "warning" for w in warnings)


def test_high_confidence_candidate_from_risky_page_returns_warning():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
            "confidence": "high",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
        }
    ]
    preprocess = {
        "sections": [{"action": "keep", "text": "2025 年新增装机提升。"}],
        "preprocess_metadata": {
            "extracted_pages": [
                {"page": 1, "text_quality": "low", "image_heavy": False, "chart_heavy": False, "table_heavy": False},
            ]
        },
    }

    warnings = qa.check_preprocess_risk_confidence(bundle, preprocess)

    assert any(w["rule"] == "high_confidence_candidate_from_risky_page" and w["target"] == "company_candidates.SSE_688019" for w in warnings)


def test_high_confidence_candidate_from_page_range_middle_risky_page_returns_warning():
    bundle = valid_bundle()
    bundle["insight_blocks"][0]["source_page_range"] = "8-10"
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
            "confidence": "high",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
        }
    ]
    preprocess = {
        "preprocess_metadata": {
            "extracted_pages": [
                {"page": 9, "text_quality": "low", "image_heavy": False, "chart_heavy": False, "table_heavy": False},
            ]
        },
    }

    warnings = qa.check_preprocess_risk_confidence(bundle, preprocess)

    assert any(w["target"] == "company_candidates.SSE_688019" for w in warnings)


def test_uncrossed_stage_gate_without_cannot_conclude_returns_error():
    bundle = valid_bundle()
    bundle["stage_gates"] = [
        {
            "id": "sg-001",
            "gate_type": "unit_economics",
            "title": "经济性闭环",
            "crossed": False,
            "linked_block_ids": ["ib-001"],
        }
    ]

    warnings = qa.check_stage_gate_synthesis(bundle)

    assert any(w["rule"] == "stage_gate_missing_cannot_conclude" and w["severity"] == "error" for w in warnings)


def test_company_candidate_missing_required_fields_returns_errors():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
        }
    ]

    warnings = qa.check_company_candidates(bundle)

    assert any(w["rule"] == "candidate_missing_exposure_type" and w["target"] == "company_candidates.SSE_688019.exposure_type" for w in warnings)
    assert any(w["rule"] == "candidate_missing_source_blocks" and w["target"] == "company_candidates.SSE_688019.source_block_ids" for w in warnings)
    assert any(w["rule"] == "candidate_missing_verification_questions" and w["target"] == "company_candidates.SSE_688019.verification_questions" for w in warnings)


def test_thematic_related_candidate_with_high_confidence_returns_warning():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
            "exposure_type": "thematic_related",
            "confidence": "high",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
        }
    ]

    warnings = qa.check_company_candidates(bundle)

    assert any(w["rule"] == "thematic_related_high_confidence" and w["severity"] == "warning" for w in warnings)


def test_low_evidence_source_with_strong_synthesis_returns_warning():
    bundle = valid_bundle()
    bundle["source_digest"]["evidence_strength"] = "low"
    bundle["synthesis"]["one_sentence"] = "储能需求确定爆发，行业将显著受益。"

    warnings = qa.check_synthesis_discipline(bundle)

    assert any(w["rule"] == "low_evidence_strong_synthesis" and w["severity"] == "warning" for w in warnings)


def test_medium_low_evidence_source_with_strong_synthesis_returns_warning():
    bundle = valid_bundle()
    bundle["source_digest"]["evidence_strength"] = "medium_low"
    bundle["synthesis"]["one_sentence"] = "储能需求确定爆发，行业将显著受益。"

    warnings = qa.check_synthesis_discipline(bundle)

    assert any(w["rule"] == "low_evidence_strong_synthesis" and w["severity"] == "warning" for w in warnings)


def test_candidate_company_overclaimed_in_synthesis_returns_warning():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "688019",
            "market": "SSE",
            "name": "安集科技",
            "exposure_type": "direct_supplier",
            "confidence": "medium",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
        }
    ]
    bundle["synthesis"]["one_sentence"] = "安集科技是确定受益者。"

    warnings = qa.check_synthesis_discipline(bundle)

    assert any(w["rule"] == "candidate_overclaimed_in_synthesis" and w["severity"] == "warning" for w in warnings)


def test_review_bundle_cli_returns_zero_for_valid_bundle(tmp_path, capsys):
    bundle_path = tmp_path / "bundle.json"
    preprocess_path = tmp_path / "preprocess.json"
    bundle_path.write_text(json.dumps(valid_bundle(), ensure_ascii=False), encoding="utf-8")
    preprocess_path.write_text(json.dumps({
        "sections": [{"action": "keep", "text": "2025 年新增装机提升，需求改善。"}],
    }, ensure_ascii=False), encoding="utf-8")

    code = qa.main([
        "review-bundle",
        "--bundle", str(bundle_path),
        "--preprocess", str(preprocess_path),
    ])

    captured = capsys.readouterr()
    assert code == 0
    assert "✓ review bundle QA passed" in captured.out


def test_review_bundle_cli_returns_nonzero_for_warnings(tmp_path, capsys):
    bundle = valid_bundle()
    bundle["insight_blocks"] = []
    bundle_path = tmp_path / "bundle.json"
    preprocess_path = tmp_path / "preprocess.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    preprocess_path.write_text(json.dumps({"sections": []}, ensure_ascii=False), encoding="utf-8")

    code = qa.main([
        "review-bundle",
        "--bundle", str(bundle_path),
        "--preprocess", str(preprocess_path),
    ])

    captured = capsys.readouterr()
    assert code == 1
    assert "# Review bundle QA" in captured.out
    assert "missing_insight_blocks" in captured.out
