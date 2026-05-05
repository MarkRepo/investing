"""Smoke tests for scripts/render_views.py — verify frontmatter presence and basic rendering."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.render_views import (
    render_industry_or_arena,
    render_brand,
    render_company,
    render_bundle_insights,
    _bundle_sha8,
)


def _make_registry(tmp_path: Path):
    """Create a minimal ClaimRegistry with a few test claims."""
    from app.io.claim_registry import ClaimRegistry

    registry = ClaimRegistry(tmp_path)
    return registry


def _add_v3_claim(tmp_path: Path, scope_type: str, scope_ref: str, text: str = "测试论点") -> None:
    """Write a v3-format claim directly to the JSONL file."""
    import json
    from app.io.claim_registry import SCOPE_FILES

    claims_dir = tmp_path / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "claim_id": f"{scope_type}-c-2025-0001",
        "schema_version": "v3",
        "scope_type": scope_type,
        "scope_ref": scope_ref,
        "text": text,
        "type": "thesis",
        "direction": 1,
        "confidence": "high",
        "semantic_key": "测试 key",
        "evidence": [{"quote": "这是引用文本", "page": 3, "why": "直接支撑", "source_id": "src-001"}],
        "sources": [{"source_id": "src-001", "institution": "测试机构", "as_of": "2025-01-01"}],
        "relations": [],
        "first_seen_at": "2025-01-01T00:00:00+00:00",
        "last_updated_at": "2025-01-01T00:00:00+00:00",
    }
    jsonl_path = claims_dir / SCOPE_FILES[scope_type]
    with jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class TestRenderIndustry:
    def test_narrative_has_frontmatter(self, tmp_path):
        _add_v3_claim(tmp_path, "industry", "cn-test-industry")
        from app.io.claim_registry import ClaimRegistry

        registry = ClaimRegistry(tmp_path)
        out = render_industry_or_arena(
            scope_type="industry",
            scope_ref="cn-test-industry",
            registry=registry,
            base=tmp_path,
        )
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "scope_type: industry" in content
        assert "scope_ref: cn-test-industry" in content
        assert "last_rendered:" in content
        assert "claim_count: 1" in content

    def test_narrative_contains_claim_text(self, tmp_path):
        _add_v3_claim(tmp_path, "industry", "cn-test-industry", text="核聚变商业化将至")
        from app.io.claim_registry import ClaimRegistry

        registry = ClaimRegistry(tmp_path)
        out = render_industry_or_arena(
            scope_type="industry",
            scope_ref="cn-test-industry",
            registry=registry,
            base=tmp_path,
        )
        content = out.read_text(encoding="utf-8")
        assert "核聚变商业化将至" in content
        assert "## 主要论点" in content

    def test_narrative_empty_registry_no_error(self, tmp_path):
        from app.io.claim_registry import ClaimRegistry

        registry = ClaimRegistry(tmp_path)
        out = render_industry_or_arena(
            scope_type="industry",
            scope_ref="cn-empty-industry",
            registry=registry,
            base=tmp_path,
        )
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "scope_type: industry" in content
        assert "claim_count: 0" in content


class TestRenderArena:
    def test_arena_narrative_path(self, tmp_path):
        _add_v3_claim(tmp_path, "arena", "cn-test-arena")
        from app.io.claim_registry import ClaimRegistry

        registry = ClaimRegistry(tmp_path)
        out = render_industry_or_arena(
            scope_type="arena",
            scope_ref="cn-test-arena",
            registry=registry,
            base=tmp_path,
        )
        assert out == tmp_path / "arenas" / "cn-test-arena" / "narrative.md"
        assert "scope_type: arena" in out.read_text(encoding="utf-8")


class TestRenderBrand:
    def test_brand_brief_has_frontmatter(self, tmp_path):
        _add_v3_claim(tmp_path, "brand", "玛氏")
        from app.io.claim_registry import ClaimRegistry

        registry = ClaimRegistry(tmp_path)
        out = render_brand(scope_ref="玛氏", registry=registry, base=tmp_path)
        assert out == tmp_path / "brands" / "玛氏" / "brief.md"
        content = out.read_text(encoding="utf-8")
        assert "scope_type: brand" in content
        assert "scope_ref: 玛氏" in content


class TestRenderCompany:
    def test_dashboard_has_frontmatter(self, tmp_path):
        _add_v3_claim(tmp_path, "company", "SSE_600519")
        from app.io.claim_registry import ClaimRegistry

        registry = ClaimRegistry(tmp_path)
        out = render_company(scope_ref="SSE_600519", registry=registry, base=tmp_path)
        assert out == tmp_path / "companies" / "SSE_600519" / "dashboard.md"
        content = out.read_text(encoding="utf-8")
        assert "ticker: SSE_600519" in content
        assert "## 观点矩阵" in content
        assert "## 风险一览" in content

    def test_dashboard_empty_registry(self, tmp_path):
        from app.io.claim_registry import ClaimRegistry

        registry = ClaimRegistry(tmp_path)
        out = render_company(scope_ref="SSE_999999", registry=registry, base=tmp_path)
        content = out.read_text(encoding="utf-8")
        assert "ticker: SSE_999999" in content


class TestRenderBundleInsights:
    def _make_bundle(self, tmp_path: Path, fname: str = "abcd1234.json") -> Path:
        bundle_dir = tmp_path / "industries" / "cn-test" / "bundles"
        bundle_dir.mkdir(parents=True, exist_ok=True)
        bundle = {
            "source_digest": {
                "source_id": "行研-测试-2025-01-abcd1234",
                "source_title": "测试研报",
                "source_type": "industry_report",
            },
            "synthesis": {
                "one_sentence": "这是一句话主线摘要。",
                "what_we_know": ["已知事实一", "已知事实二"],
                "what_is_plausible": ["推断一"],
                "cannot_conclude": ["不能得出的结论一"],
            },
            "claim_candidates": [
                {
                    "candidate_id": "cc-001",
                    "claim_text": "测试论点文本",
                    "claim_type": "thesis",
                    "confidence": "high",
                    "scope_type": "industry",
                    "scope_ref": "cn-test",
                    "evidence": [{"quote": "这是引用", "page": 1}],
                }
            ],
        }
        path = bundle_dir / fname
        path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        return path

    def test_insights_frontmatter(self, tmp_path):
        bundle_path = self._make_bundle(tmp_path)
        out = render_bundle_insights(bundle_path)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert content.startswith("---")
        assert "source_id:" in content
        assert "synthesized_at:" in content

    def test_insights_contains_one_liner(self, tmp_path):
        bundle_path = self._make_bundle(tmp_path)
        out = render_bundle_insights(bundle_path)
        content = out.read_text(encoding="utf-8")
        assert "这是一句话主线摘要。" in content

    def test_insights_output_path(self, tmp_path):
        bundle_path = self._make_bundle(tmp_path, "abcd1234.json")
        out = render_bundle_insights(bundle_path)
        assert out == bundle_path.parent / "insights" / "abcd1234.md"

    def test_insights_cannot_conclude(self, tmp_path):
        bundle_path = self._make_bundle(tmp_path)
        out = render_bundle_insights(bundle_path)
        content = out.read_text(encoding="utf-8")
        assert "不能得出的结论一" in content

    def test_insights_high_confidence_evidence(self, tmp_path):
        bundle_path = self._make_bundle(tmp_path)
        out = render_bundle_insights(bundle_path)
        content = out.read_text(encoding="utf-8")
        assert "这是引用" in content

    def test_bundle_sha8_plain_hex(self, tmp_path):
        p = tmp_path / "bundles" / "abcd1234.json"
        p.parent.mkdir(parents=True)
        p.touch()
        assert _bundle_sha8(p) == "abcd1234"

    def test_bundle_sha8_long_name(self, tmp_path):
        p = tmp_path / "bundles" / "kpmg-2025-report.json"
        p.parent.mkdir(parents=True)
        p.touch()
        assert _bundle_sha8(p) == "kpmg-2025-report"


class TestCLIMain:
    def test_main_all_empty_registry(self, tmp_path):
        from scripts.render_views import main

        ret = main(["--registry-base", str(tmp_path), "--scope", "all"])
        assert ret == 0

    def test_main_scope_industry_empty(self, tmp_path):
        from scripts.render_views import main

        ret = main(["--registry-base", str(tmp_path), "--scope", "industry"])
        assert ret == 0

    def test_main_bundle_mode(self, tmp_path):
        bundle_dir = tmp_path / "bundles"
        bundle_dir.mkdir()
        bundle_path = bundle_dir / "testfile.json"
        bundle = {
            "source_digest": {"source_id": "src-001", "source_title": "测试"},
            "synthesis": {"one_sentence": "摘要", "cannot_conclude": []},
            "claim_candidates": [],
        }
        bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
        from scripts.render_views import main

        ret = main(["--bundle", str(bundle_path)])
        assert ret == 0
        out = bundle_dir / "insights" / "testfile.md"
        assert out.exists()
