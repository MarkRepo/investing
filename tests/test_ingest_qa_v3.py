"""Tests for ingest_qa v3 bundle validation (C1-C9 checks)."""
import json
import pytest
from scripts.ingest_qa import check_v3_bundle, main


def _valid_bundle() -> dict:
    return {
        "schema_version": "v3",
        "meta": {
            "source_id": "test-src-001",
            "source_title": "测试研报",
            "institution": "测试机构",
            "published_at": "2025-01-01",
            "source_type": "industry_report",
            "primary_scope": {"kind": "industry", "ref": "cn-nuclear-fusion"},
            "touches": {
                "industries": ["cn-nuclear-fusion"],
                "companies": ["SSE_603011"],
                "arenas": [],
                "brands": [],
            },
        },
        "claims": [
            {
                "id": "c1",
                "text": "磁体在产业链中占金额敞口最高",
                "type": "thesis",
                "scope": "industry/cn-nuclear-fusion",
                "direction": 1,
                "confidence": "high",
                "evidence": [{"quote": "磁体占24.9%", "page": 5, "why": "直接数字支撑"}],
                "relations": [{"to": "c2", "kind": "leads_to"}],
                "semantic_key": "磁体 金额敞口 最高",
                "as_of": "2025-01-01",
            },
            {
                "id": "c2",
                "text": "磁体供应商受益于聚变商业化",
                "type": "catalyst",
                "scope": "company/SSE_603011",
                "direction": 1,
                "confidence": "medium",
                "evidence": [{"quote": "国内磁体供应商已承接订单", "page": 8, "why": "公司层面印证"}],
                "relations": [],
                "semantic_key": "磁体供应商 受益 商业化",
                "as_of": "2025-01-01",
            },
        ],
        "summary": {
            "one_liner": "聚变产业链中磁体环节价值最高",
            "threads": [{"title": "磁体产业链", "claim_ids": ["c1", "c2"]}],
            "cannot_conclude": [],
        },
        "notes": {"skipped_sections": [], "weak_evidence": []},
    }


class TestC1SchemaVersion:
    def test_valid_v3_passes_c1(self):
        issues = check_v3_bundle(_valid_bundle())
        codes = [i["code"] for i in issues]
        assert "schema_version_mismatch" not in codes

    def test_v2_bundle_fails_c1(self):
        b = _valid_bundle()
        b["schema_version"] = "v2-phase1"
        issues = check_v3_bundle(b)
        assert any(i["code"] == "schema_version_mismatch" for i in issues)
        assert all(i["level"] == "error" for i in issues)  # early return, only c1 error


class TestC2TopKeys:
    def test_missing_summary_is_error(self):
        b = _valid_bundle()
        del b["summary"]
        issues = check_v3_bundle(b)
        assert any(i["code"] == "missing_top_key:summary" for i in issues)


class TestC3MetaFields:
    def test_missing_institution_is_error(self):
        b = _valid_bundle()
        del b["meta"]["institution"]
        issues = check_v3_bundle(b)
        assert any(i["code"] == "meta_missing:institution" for i in issues)

    def test_invalid_source_type_is_error(self):
        b = _valid_bundle()
        b["meta"]["source_type"] = "bogus"
        issues = check_v3_bundle(b)
        assert any(i["code"] == "invalid_source_type" for i in issues)


class TestC4ClaimsCount:
    def test_empty_claims_is_error(self):
        b = _valid_bundle()
        b["claims"] = []
        issues = check_v3_bundle(b)
        assert any(i["code"] == "no_claims" for i in issues)

    def test_under_extraction_warning(self):
        b = _valid_bundle()
        # 3000 chars ≈ 2 pages, 2 claims → ratio=1.0, no warning
        # force ratio < 0.25: 1 claim for ~20 pages (30000 chars)
        b["claims"] = [b["claims"][0]]
        md = "x" * 30000
        issues = check_v3_bundle(b, md)
        assert any(i["code"] == "under_extraction" for i in issues)


class TestC5ClaimFields:
    def test_invalid_type_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["type"] = "scenario"
        issues = check_v3_bundle(b)
        assert any("type_invalid" in i["code"] for i in issues)

    def test_invalid_direction_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["direction"] = 2
        issues = check_v3_bundle(b)
        assert any("direction_invalid" in i["code"] for i in issues)

    def test_invalid_confidence_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["confidence"] = "medium_high"
        issues = check_v3_bundle(b)
        assert any("confidence_invalid" in i["code"] for i in issues)

    def test_invalid_scope_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["scope"] = "garbage"
        issues = check_v3_bundle(b)
        assert any("scope_invalid" in i["code"] for i in issues)

    def test_missing_evidence_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["evidence"] = []
        issues = check_v3_bundle(b)
        assert any("no_evidence" in i["code"] for i in issues)

    def test_evidence_missing_quote_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["evidence"][0]["quote"] = ""
        issues = check_v3_bundle(b)
        assert any("no_quote" in i["code"] for i in issues)

    def test_semantic_key_too_long_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["semantic_key"] = "a" * 21
        issues = check_v3_bundle(b)
        assert any("semantic_key_invalid" in i["code"] for i in issues)

    def test_risk_type_positive_direction_is_warning(self):
        b = _valid_bundle()
        b["claims"][0]["type"] = "risk"
        b["claims"][0]["direction"] = 1
        issues = check_v3_bundle(b)
        assert any("risk_with_positive_direction" in i["code"] for i in issues)


class TestC6Relations:
    def test_broken_relation_ref_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["relations"][0]["to"] = "c999"
        issues = check_v3_bundle(b)
        assert any("broken_ref" in i["code"] for i in issues)

    def test_invalid_relation_kind_is_error(self):
        b = _valid_bundle()
        b["claims"][0]["relations"][0]["kind"] = "causes"
        issues = check_v3_bundle(b)
        assert any("invalid_kind" in i["code"] for i in issues)


class TestC7IsolatedRatio:
    def test_excessive_isolated_is_warning(self):
        b = _valid_bundle()
        # Add 5 isolated claims alongside 2 linked ones → 5/7 > 20%
        for i in range(3, 8):
            b["claims"].append({
                "id": f"c{i}", "text": f"claim {i}", "type": "judgment",
                "scope": "industry/cn-nuclear-fusion", "direction": 0,
                "confidence": "medium", "evidence": [{"quote": "x", "page": 1, "why": "y"}],
                "relations": [], "semantic_key": f"key{i}", "as_of": "2025-01-01",
            })
        issues = check_v3_bundle(b)
        assert any(i["code"] == "excessive_isolated_claims" for i in issues)


class TestC8Summary:
    def test_missing_one_liner_is_error(self):
        b = _valid_bundle()
        del b["summary"]["one_liner"]
        issues = check_v3_bundle(b)
        assert any(i["code"] == "summary_missing_one_liner" for i in issues)

    def test_unknown_claim_in_thread_is_error(self):
        b = _valid_bundle()
        b["summary"]["threads"][0]["claim_ids"].append("c999")
        issues = check_v3_bundle(b)
        assert any("thread_unknown_claim" in i["code"] for i in issues)


class TestC9ScopeTouches:
    def test_scope_not_in_touches_is_warning(self):
        b = _valid_bundle()
        b["claims"][0]["scope"] = "industry/cn-pet-industry"
        # cn-pet-industry not in touches.industries
        issues = check_v3_bundle(b)
        assert any("scope_not_in_touches" in i["code"] for i in issues)


class TestValidBundle:
    def test_valid_bundle_has_no_issues(self):
        b = _valid_bundle()
        issues = check_v3_bundle(b)
        assert issues == [], f"Expected no issues, got: {issues}"


class TestCLI:
    def test_review_bundle_cli_pass(self, tmp_path):
        b = _valid_bundle()
        bp = tmp_path / "bundle.json"
        bp.write_text(json.dumps(b))
        rc = main(["review-bundle", "--bundle", str(bp)])
        assert rc == 0

    def test_review_bundle_cli_fail_v2(self, tmp_path):
        b = _valid_bundle()
        b["schema_version"] = "v2"
        bp = tmp_path / "bundle.json"
        bp.write_text(json.dumps(b))
        rc = main(["review-bundle", "--bundle", str(bp)])
        assert rc == 1
