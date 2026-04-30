import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.io import company as company_io
from app.routes import companies as companies_route


def test_company_detail_displays_narrative_flags(tmp_path, monkeypatch):
    # Redirect company IO to tmp_path.
    monkeypatch.setattr(companies_route.cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(company_io.cfg, "COMPANIES_DIR", tmp_path / "companies")
    company_io.create_company(
        ticker="600519",
        market="SSE",
        name="贵州茅台",
        industry_slugs=[],
        currency="CNY",
        base=tmp_path,
    )
    flags_path = tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl"
    flags_path.write_text(
        json.dumps(
            {
                "flag_id": "nf-0001",
                "created_at": "2026-04-30T12:00:00+00:00",
                "dimension": "moat",
                "segment_ref": "moat.md#np-001",
                "supported_by_claim": "clm-company-0001",
                "scope_type": "company",
                "scope_ref": "SSE_600519",
                "flag_level": "critical",
                "reason": "supporting claim retired",
                "dismissed": False,
                "superseded_by": None,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    app = FastAPI()
    app.include_router(companies_route.router)
    client = TestClient(app)

    response = client.get("/companies/SSE_600519")

    assert response.status_code == 200
    assert "needs review" in response.text
    assert "supporting claim retired" in response.text
    assert "clm-company-0001" in response.text
