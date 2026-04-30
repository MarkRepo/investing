"""Test that the company detail page reads claims from ClaimRegistry."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.io import company as company_io
from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.routes import companies as companies_route


def test_company_detail_shows_registry_claims(tmp_path, monkeypatch):
    """GET /companies/SSE_603011 should surface claims seeded in ClaimRegistry."""
    # Redirect all IO to tmp_path.
    monkeypatch.setattr(companies_route.cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(companies_route.cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(company_io.cfg, "COMPANIES_DIR", tmp_path / "companies")

    # Create company.
    company_io.create_company(
        ticker="603011",
        market="SSE",
        name="中核科技",
        industry_slugs=[],
        currency="CNY",
        base=tmp_path,
    )

    # Seed a claim in ClaimRegistry.
    registry = ClaimRegistry(tmp_path)
    evidence = build_evidence_entry(
        source_id="source-1",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction="supports",
        now="2026-04-30T12:00:00+00:00",
    )
    registry.create_claim(
        claim_text="公司具备主题相关性",
        scope_type="company",
        scope_ref="SSE_603011",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2024-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="match-source-1.json#cc-001",
        now="2026-04-30T12:00:00+00:00",
    )

    app = FastAPI()
    app.include_router(companies_route.router)
    client = TestClient(app)

    response = client.get("/companies/SSE_603011")

    assert response.status_code == 200
    assert "公司具备主题相关性" in response.text
    # Source badge must link back to the review bundle.
    assert "/bundles/source-1" in response.text
    assert "source-1" in response.text
