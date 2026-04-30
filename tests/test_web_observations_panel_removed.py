"""Test that the industry observations panel and route are removed.

Task 8: remove observations UI while preserving narrative, linked arenas,
linked tickers, figure contexts, and flags.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.io import industry as industry_io
from app.routes import industries as industries_route


def _make_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setattr(industry_io.cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(industries_route.cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    industry_io.create_industry(
        slug="cn-nuclear-fusion",
        name="核聚变",
        scope="CN",
        base=tmp_path,
    )
    app = FastAPI()
    app.include_router(industries_route.router)
    return TestClient(app)


def test_industry_detail_no_longer_renders_observations_panel(tmp_path, monkeypatch):
    """GET /industries/cn-nuclear-fusion must not render the observations panel."""
    client = _make_client(tmp_path, monkeypatch)

    response = client.get("/industries/cn-nuclear-fusion")

    assert response.status_code == 200
    # The exact observations section heading must be gone.
    assert "观察（observations" not in response.text
    # The link to the cross-source aggregation route must be gone.
    assert "/industries/cn-nuclear-fusion/observations" not in response.text
    # The table that listed observation rows must be gone (field/值/时段 header set).
    assert "observations_total" not in response.text


def test_industry_observations_route_is_gone(tmp_path, monkeypatch):
    """GET /industries/cn-nuclear-fusion/observations must return 404."""
    client = _make_client(tmp_path, monkeypatch)

    response = client.get("/industries/cn-nuclear-fusion/observations")

    assert response.status_code == 404
