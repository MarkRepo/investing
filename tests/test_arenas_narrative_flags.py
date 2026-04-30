import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import arenas as arenas_route
from app.io import arenas as arenas_io


def test_arena_detail_displays_narrative_flags(tmp_path, monkeypatch):
    monkeypatch.setattr(arenas_route.arenas_io.cfg, "ARENAS_DIR", tmp_path / "arenas")
    arenas_io.write_definition(
        slug="cn-bci-industrialization",
        name="脑机接口产业化",
        definition_text="定义",
        base=tmp_path,
    )
    flags_path = tmp_path / "arenas" / "cn-bci-industrialization" / "narrative-flags.jsonl"
    flags_path.write_text(
        json.dumps(
            {
                "flag_id": "nf-0001",
                "created_at": "2026-04-30T12:00:00+00:00",
                "dimension": "participants",
                "segment_ref": "participants.md#np-001",
                "supported_by_claim": "clm-arena-0001",
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
    app.include_router(arenas_route.router)
    client = TestClient(app)

    response = client.get("/arenas/cn-bci-industrialization")

    assert response.status_code == 200
    assert "needs review" in response.text
    assert "supporting claim retired" in response.text
    assert "clm-arena-0001" in response.text
