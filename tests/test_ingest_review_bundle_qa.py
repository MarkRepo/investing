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
                "reasoning_chain": ["政策推动新增装机需求持续增长。", "因此储能设备采购量有望扩大，相关供应商受益。"],
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
        "schema_fit_review": {
            "fits_current_schema": True,
            "missing_schema_fields": [],
            "extra_fields_needed": [],
            "notes": "",
        },
        "write_status": "not_applicable_phase1",
    }


def test_missing_insight_blocks_returns_error():
    bundle = valid_bundle()
    bundle["insight_blocks"] = []

    warnings = qa.check_review_bundle_shape(bundle)

    assert any(w["rule"] == "missing_insight_blocks" and w["severity"] == "error" for w in warnings)


def test_missing_source_digest_returns_error():
    bundle = valid_bundle()
    bundle.pop("source_digest")

    warnings = qa.check_review_bundle_shape(bundle)

    assert any(w["rule"] == "missing_source_digest" and w["severity"] == "error" for w in warnings)


def test_missing_synthesis_returns_error():
    bundle = valid_bundle()
    bundle.pop("synthesis")

    warnings = qa.check_review_bundle_shape(bundle)

    assert any(w["rule"] == "missing_synthesis" and w["severity"] == "error" for w in warnings)


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


def test_evidence_quote_not_found_in_short_preprocess_warns_about_pdf_text_loss():
    bundle = valid_bundle()
    preprocess = {
        "sections": [
            {"action": "keep", "text": "这里没有对应证据。"},
        ]
    }

    warnings = qa.check_fact_evidence_quotes(bundle, preprocess)

    assert any(w["rule"] == "evidence_quote_not_found" and w["severity"] == "warning" for w in warnings)
    assert any("PDF→text" in w["detail"] for w in warnings)


def test_evidence_quote_not_found_in_normal_preprocess_omits_pdf_text_loss_hint():
    bundle = valid_bundle()
    preprocess = {
        "sections": [
            {"action": "keep", "text": "这里没有对应证据。" * 5000},
        ]
    }

    warnings = qa.check_fact_evidence_quotes(bundle, preprocess)

    assert any(w["rule"] == "evidence_quote_not_found" and w["severity"] == "warning" for w in warnings)
    assert all("PDF→text" not in w["detail"] for w in warnings)


def test_valid_bundle_returns_no_warnings_when_quote_matches_preprocess():
    preprocess = {
        "sections": [
            {"action": "keep", "text": "2025 年新增装机提升，需求改善。"},
        ]
    }

    warnings = qa.check_ingest_review_bundle(valid_bundle(), preprocess)

    assert warnings == []



def test_fact_text_candidate_company_name_missing_from_evidence_quote_returns_warning():
    bundle = valid_bundle()
    bundle["company_candidates"] = [
        {
            "ticker": "600363",
            "market": "SSE",
            "name": "联创光电",
            "exposure_type": "thematic_related",
            "confidence": "medium",
            "source_block_ids": ["ib-001"],
            "verification_questions": ["收入占比是多少？"],
        }
    ]
    bundle["atomic_facts"][0] = {
        "fact_id": "fact-001",
        "linked_block_id": "ib-001",
        "fact_text": "报告首页列出联创光电，股票代码为 600363.SH。",
        "evidence_quote": "600363.SH 人民币53.50  增持  西部超导",
        "confidence": "medium",
    }

    warnings = qa.check_fact_quote_consistency(bundle)

    assert any(w["rule"] == "fact_text_entity_missing_from_quote" and w["target"] == "atomic_facts.fact-001" for w in warnings)
    assert any("联创光电" in w["detail"] for w in warnings)


def test_company_like_technical_term_without_candidate_does_not_warn():
    bundle = valid_bundle()
    bundle["atomic_facts"][0] = {
        "fact_id": "fact-001",
        "linked_block_id": "ib-001",
        "fact_text": "高温超导磁体是聚变装置的关键技术路线。",
        "evidence_quote": "磁体是聚变装置的关键技术路线",
        "confidence": "medium",
    }

    warnings = qa.check_fact_quote_consistency(bundle)

    assert warnings == []


def test_six_digit_quantity_without_exchange_suffix_is_not_treated_as_ticker():
    bundle = valid_bundle()
    bundle["atomic_facts"][0] = {
        "fact_id": "fact-001",
        "linked_block_id": "ib-001",
        "fact_text": "示范项目年发电量达到 123456 兆瓦时。",
        "evidence_quote": "示范项目年发电量达到 兆瓦时",
        "confidence": "medium",
    }

    warnings = qa.check_fact_quote_consistency(bundle)

    assert warnings == []


def test_fact_text_ticker_missing_from_evidence_quote_returns_warning():
    bundle = valid_bundle()
    bundle["atomic_facts"][0] = {
        "fact_id": "fact-001",
        "linked_block_id": "ib-001",
        "fact_text": "报告首页列出安泰科技，股票代码为 688122.SH。",
        "evidence_quote": "安泰科技 人民币43.68  买入",
        "confidence": "medium",
    }

    warnings = qa.check_fact_quote_consistency(bundle)

    assert any(w["rule"] == "fact_text_entity_missing_from_quote" and "688122" in w["detail"] for w in warnings)


def test_fact_text_company_and_ticker_present_in_quote_returns_no_consistency_warning():
    bundle = valid_bundle()
    bundle["atomic_facts"][0] = {
        "fact_id": "fact-001",
        "linked_block_id": "ib-001",
        "fact_text": "报告首页列出安泰科技，股票代码为 688122.SH。",
        "evidence_quote": "688122.SH 人民币43.68  买入  安泰科技",
        "confidence": "medium",
    }

    warnings = qa.check_fact_quote_consistency(bundle)

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


def test_block_missing_block_type_returns_error():
    bundle = valid_bundle()
    bundle["insight_blocks"][0].pop("block_type", None)
    bundle["insight_blocks"][0]["block_type"] = ""

    warnings = qa.check_insight_blocks(bundle)

    assert any(w["rule"] == "block_missing_block_type" and w["severity"] == "error" for w in warnings)


def test_block_single_item_reasoning_chain_returns_warning():
    bundle = valid_bundle()
    bundle["insight_blocks"][0]["reasoning_chain"] = ["只有一条"]

    warnings = qa.check_insight_blocks(bundle)

    assert any(w["rule"] == "block_shallow_reasoning_chain" and w["severity"] == "warning" for w in warnings)


def test_block_two_item_reasoning_chain_passes():
    bundle = valid_bundle()
    bundle["insight_blocks"][0]["reasoning_chain"] = ["观察：数据如此", "因此投资含义如彼"]

    warnings = qa.check_insight_blocks(bundle)

    assert not any(w["rule"] == "block_shallow_reasoning_chain" for w in warnings)


def test_block_relations_unknown_block_returns_error():
    bundle = valid_bundle()
    bundle["insight_blocks"][0]["block_relations"] = [
        {"block_id": "ib-999", "relation": "premise_for"}
    ]

    warnings = qa.check_insight_blocks(bundle)

    assert any(w["rule"] == "block_relations_unknown_block" and w["severity"] == "error" for w in warnings)


def test_block_relations_invalid_relation_returns_warning():
    bundle = valid_bundle()
    bundle["insight_blocks"][0]["block_relations"] = [
        {"block_id": "ib-001", "relation": "vaguely_related"}
    ]

    warnings = qa.check_insight_blocks(bundle)

    assert any(w["rule"] == "block_relations_invalid_relation" and w["severity"] == "warning" for w in warnings)


def test_block_relations_self_reference_returns_error():
    bundle = valid_bundle()
    bundle["insight_blocks"][0]["block_relations"] = [
        {"block_id": "ib-001", "relation": "premise_for"}
    ]

    warnings = qa.check_insight_blocks(bundle)

    assert any(w["rule"] == "block_relations_unknown_block" and w["severity"] == "error" for w in warnings)


def test_block_relations_valid_passes():
    bundle = valid_bundle()
    bundle["insight_blocks"].append({
        "id": "ib-002",
        "block_type": "risk",
        "title": "风险",
        "summary": "风险说明。",
        "evidence_strength": "medium",
        "reasoning_chain": ["观察", "含义"],
    })
    bundle["insight_blocks"][0]["block_relations"] = [
        {"block_id": "ib-002", "relation": "corroborates"}
    ]

    warnings = qa.check_insight_blocks(bundle)

    assert not any(w["rule"].startswith("block_relations_") for w in warnings)


def test_claim_candidate_missing_required_field_returns_error():
    bundle = valid_bundle()
    bundle["claim_candidates"] = [
        {
            "candidate_id": "cc-001",
            "scope_type": "industry",
            "claim_type": "thesis",
            "supporting_block_ids": ["ib-001"],
            "direction_on_source": "supports",
            "as_of": "2026-04-30",
        }
    ]

    warnings = qa.check_claim_candidates(bundle)

    assert any(w["rule"] == "claim_candidate_missing_field" and w["severity"] == "error" for w in warnings)
    assert any("claim_text" in w["detail"] for w in warnings)


def test_claim_candidate_invalid_scope_type_returns_error():
    bundle = valid_bundle()
    bundle["claim_candidates"] = [
        {
            "candidate_id": "cc-001",
            "claim_text": "储能需求增长",
            "scope_type": "random",
            "claim_type": "thesis",
            "supporting_block_ids": ["ib-001"],
            "direction_on_source": "supports",
            "as_of": "2026-04-30",
        }
    ]

    warnings = qa.check_claim_candidates(bundle)

    assert any(w["rule"] == "claim_candidate_invalid_scope_type" and w["severity"] == "error" for w in warnings)


def test_claim_candidate_supporting_block_id_not_in_bundle_returns_error():
    bundle = valid_bundle()
    bundle["claim_candidates"] = [
        {
            "candidate_id": "cc-001",
            "claim_text": "储能需求增长",
            "scope_type": "industry",
            "claim_type": "thesis",
            "supporting_block_ids": ["ib-999"],
            "direction_on_source": "supports",
            "as_of": "2026-04-30",
        }
    ]

    warnings = qa.check_claim_candidates(bundle)

    assert any(w["rule"] == "claim_candidate_broken_link" and w["severity"] == "error" for w in warnings)


def test_claim_candidate_as_of_mismatches_source_date_returns_warning():
    bundle = valid_bundle()
    bundle["source_digest"]["source_date"] = "2026-04-30"
    bundle["claim_candidates"] = [
        {
            "candidate_id": "cc-001",
            "claim_text": "储能需求增长",
            "scope_type": "industry",
            "claim_type": "thesis",
            "supporting_block_ids": ["ib-001"],
            "direction_on_source": "supports",
            "as_of": "2026-04-29",
        }
    ]

    warnings = qa.check_claim_candidates(bundle)

    assert any(w["rule"] == "claim_candidate_as_of_mismatch" and w["severity"] == "warning" for w in warnings)


def test_claim_candidate_claim_text_not_atomic_returns_warning():
    bundle = valid_bundle()
    bundle["claim_candidates"] = [
        {
            "candidate_id": "cc-001",
            "claim_text": "A 增长。B 衰退。",
            "scope_type": "industry",
            "claim_type": "thesis",
            "supporting_block_ids": ["ib-001"],
            "direction_on_source": "supports",
            "as_of": "2026-04-30",
        }
    ]

    warnings = qa.check_claim_candidates(bundle)

    assert any(w["rule"] == "claim_candidate_claim_text_not_atomic" and w["severity"] == "warning" for w in warnings)


def test_claim_candidate_english_multi_sentence_returns_warning():
    bundle = valid_bundle()
    bundle["claim_candidates"] = [
        {
            "candidate_id": "cc-001",
            "claim_text": "A is growing. B is declining.",
            "scope_type": "industry",
            "claim_type": "thesis",
            "supporting_block_ids": ["ib-001"],
            "direction_on_source": "supports",
            "as_of": "2026-04-30",
        }
    ]

    warnings = qa.check_claim_candidates(bundle)

    assert any(w["rule"] == "claim_candidate_claim_text_not_atomic" and w["severity"] == "warning" for w in warnings)


def test_valid_claim_candidates_pass():
    bundle = valid_bundle()
    bundle["source_digest"]["source_date"] = "2026-04-30"
    bundle["claim_candidates"] = [
        {
            "candidate_id": "cc-001",
            "claim_text": "储能需求增长",
            "scope_type": "industry",
            "scope_ref": "cn-energy-storage",
            "claim_type": "thesis",
            "dimension_hint": "drivers",
            "supporting_block_ids": ["ib-001"],
            "direction_on_source": "supports",
            "confidence": "medium",
            "as_of": "2026-04-30",
        }
    ]

    warnings = qa.check_claim_candidates(bundle)

    assert warnings == []


def test_schema_fit_review_missing_required_keys_returns_warning():
    bundle = valid_bundle()
    bundle["schema_fit_review"] = {"missing_schema_fields": [], "extra_fields_needed": [], "notes": ""}

    warnings = qa.check_schema_fit_review(bundle)

    assert any(w["rule"] == "schema_fit_review_incomplete" and w["severity"] == "warning" for w in warnings)


def test_schema_fit_review_fits_false_without_details_returns_warning():
    bundle = valid_bundle()
    bundle["schema_fit_review"] = {
        "fits_current_schema": False,
        "missing_schema_fields": [],
        "extra_fields_needed": [],
        "notes": "",
    }

    warnings = qa.check_schema_fit_review(bundle)

    assert any(w["rule"] == "schema_fit_review_fits_false_without_details" and w["severity"] == "warning" for w in warnings)


def test_valid_schema_fit_review_passes_true_case():
    bundle = valid_bundle()

    warnings = qa.check_schema_fit_review(bundle)

    assert warnings == []


def test_valid_schema_fit_review_passes_false_case():
    bundle = valid_bundle()
    bundle["schema_fit_review"] = {
        "fits_current_schema": False,
        "missing_schema_fields": [],
        "extra_fields_needed": [
            {"proposed_field": "pipeline_stage", "rationale": "需要阶段", "example_evidence": "处于临床 II 期"}
        ],
        "notes": "需要扩展",
    }

    warnings = qa.check_schema_fit_review(bundle)

    assert warnings == []
