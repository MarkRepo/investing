import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.io import industry as industry_io
from app.routes import industries as industries_route


def test_industry_detail_displays_narrative_flags(tmp_path, monkeypatch):
    monkeypatch.setattr(industry_io.cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(industries_route.cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    industry_io.create_industry(
        slug="cn-power-equipment",
        name="中国电力设备",
        scope="CN",
        base=tmp_path,
    )
    flags_path = tmp_path / "industries" / "cn-power-equipment" / "narrative-flags.jsonl"
    flags_path.write_text(
        json.dumps(
            {
                "flag_id": "nf-0001",
                "created_at": "2026-04-30T12:00:00+00:00",
                "dimension": "lifecycle",
                "segment_ref": "lifecycle.md#np-001",
                "supported_by_claim": "clm-industry-0001",
                "scope_type": "industry",
                "scope_ref": "cn-power-equipment",
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
    app.include_router(industries_route.router)
    client = TestClient(app)

    response = client.get("/industries/cn-power-equipment")

    assert response.status_code == 200
    assert "needs review" in response.text
    assert "supporting claim retired" in response.text
    assert "clm-industry-0001" in response.text
