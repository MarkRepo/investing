"""Tests for /lens/{scope}/{slug_or_key} routes — investment lens views."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Set up a minimal project tree and return a TestClient."""
    # Required directories and files
    (tmp_path / "companies").mkdir()
    (tmp_path / "watchlist").mkdir()
    (tmp_path / "portfolio").mkdir()
    (tmp_path / "portfolio" / "rules.md").write_text("# rules\n")
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    (tmp_path / "industries").mkdir()
    (tmp_path / "arenas").mkdir()
    (tmp_path / "macro").mkdir()
    (tmp_path / "data").mkdir()
    shutil.copytree(REPO_ROOT / "controlled-vocab", tmp_path / "controlled-vocab")

    monkeypatch.chdir(tmp_path)
    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "TEMPLATES_DIR", tmp_path / "templates")
    monkeypatch.setattr(cfg, "WATCHLIST_DIR", tmp_path / "watchlist")
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    monkeypatch.setattr(cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    monkeypatch.setattr(cfg, "ARENAS_DIR", tmp_path / "arenas")
    monkeypatch.setattr(cfg, "MACRO_DIR", tmp_path / "macro")
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", tmp_path / "controlled-vocab")

    from main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def _setup_industry(tmp_path: Path, slug: str = "test-industry") -> None:
    """Write a minimal industry meta.yaml."""
    ind_dir = tmp_path / "industries" / slug
    ind_dir.mkdir(parents=True, exist_ok=True)
    (ind_dir / "meta.yaml").write_text(
        f"name: Test Industry\nslug: {slug}\nscope: global\n",
        encoding="utf-8",
    )


def _setup_arena(tmp_path: Path, slug: str = "test-arena") -> None:
    """Write a minimal arena definition.md."""
    arena_dir = tmp_path / "arenas" / slug
    arena_dir.mkdir(parents=True, exist_ok=True)
    (arena_dir / "definition.md").write_text(
        f"---\nname: Test Arena\n---\n\nArena definition body.\n",
        encoding="utf-8",
    )


def _setup_company(tmp_path: Path, market: str = "SSE", ticker: str = "603011") -> None:
    """Write a minimal company meta.md."""
    key = f"{market}_{ticker}"
    co_dir = tmp_path / "companies" / key
    co_dir.mkdir(parents=True, exist_ok=True)
    (co_dir / "meta.md").write_text(
        f"---\nname: Test Company\ncurrency: CNY\n---\n",
        encoding="utf-8",
    )


def _setup_bundle_registry(tmp_path: Path, slug: str = "test-industry") -> None:
    """Write bundle_registry.jsonl and a minimal bundle JSON."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    entry = {
        "source_id": "行研-test-2025-01-01-abcd1234",
        "sha8": "abcd1234",
        "source_type": "industry_report",
        "institution": "Test",
        "publish_date": "2025-01-01",
        "bundle_path": f"industries/{slug}/bundles/abcd1234.json",
        "source_file_path": f"industries/{slug}/sources/test.pdf",
        "ingested_at": "2026-01-01T00:00:00+00:00",
        "touched": {
            "industries": [slug],
            "arenas": ["test-arena"],
            "companies": ["SSE_603011"],
        },
    }
    (data_dir / "bundle_registry.jsonl").write_text(
        json.dumps(entry) + "\n", encoding="utf-8"
    )
    bundle = {
        "synthesis": {
            "one_sentence": "Test thesis sentence.",
            "cannot_conclude": ["Cannot conclude X."],
            "investment_questions": ["Question A?"],
        },
        "insight_blocks": [
            {
                "id": "ib-001",
                "title": "Market insight",
                "summary": "Market summary.",
                "archive_routing_hints": {"dimension_hint": "market_size"},
                "evidence_strength": "medium",
                "block_type": "market_size",
                "source_page_range": "1",
                "reasoning_chain": [],
                "block_relations": [],
            }
        ],
        "atomic_facts": [],
        "stage_gates": [],
        "arena_candidates": [
            {
                "candidate_id": "ac-001",
                "tentative_slug": "test-arena",
                "name": "Test Arena",
                "battleground_focus": "Test focus.",
                "participant_tickers": [],
                "confidence": "medium",
                "linked_block_ids": [],
                "verification_questions": [],
                "parent_industry_slug": slug,
            }
        ],
        "company_candidates": [
            {
                "ticker": "603011",
                "market": "SSE",
                "name": "Test Co",
                "exposure_type": "direct_supplier",
                "confidence": "medium",
                "source_block_ids": [],
                "verification_questions": ["Q1?"],
            }
        ],
        "claim_candidates": [],
    }
    bundle_path = tmp_path / "industries" / slug / "bundles" / "abcd1234.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")


def _setup_claims(tmp_path: Path) -> None:
    """Write minimal claims JSONL files."""
    claims_dir = tmp_path / "data" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    base_claim = {
        "claim_id": "clm-industry-0001",
        "claim_text": "Thesis claim.",
        "claim_type": "thesis",
        "dimension_hint": "technology",
        "scope_type": "industry",
        "scope_ref": "test-industry",
        "status": "active",
        "confidence": "medium",
        "as_of": "2025-01-01",
        "supporting_evidence": [],
        "related_claims": [],
        "state_log": [],
        "review_by": None,
        "user_override": None,
        "created_at": "2026-01-01T00:00:00+00:00",
        "last_updated": "2026-01-01T00:00:00+00:00",
        "schema_version": "phase2-v1",
    }
    (claims_dir / "industries.jsonl").write_text(json.dumps(base_claim) + "\n")
    (claims_dir / "arenas.jsonl").write_text("")
    (claims_dir / "companies.jsonl").write_text("")
    (claims_dir / "cross_cutting.jsonl").write_text("")
    (claims_dir / ".counters.json").write_text(json.dumps({"industry": 1}))


# ---------------------------------------------------------------------------
# Industry lens tests
# ---------------------------------------------------------------------------

def test_industry_lens_200(client, tmp_path):
    _setup_industry(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/industry/test-industry")
    assert r.status_code == 200


def test_industry_lens_contains_all_8_labels(client, tmp_path):
    _setup_industry(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/industry/test-industry")
    assert r.status_code == 200
    text = r.text
    for label in ["核心论点", "需求", "供给与竞争", "利润池", "单位经济", "阶段门槛", "催化剂时间线", "风险与反证"]:
        assert label in text, f"Missing label: {label!r}"


def test_industry_lens_404_for_unknown(client, tmp_path):
    _setup_claims(tmp_path)
    r = client.get("/lens/industry/nonexistent-industry")
    assert r.status_code == 404


def test_industry_lens_has_archive_link(client, tmp_path):
    _setup_industry(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/industry/test-industry")
    assert "/industries/test-industry" in r.text


# ---------------------------------------------------------------------------
# Arena lens tests
# ---------------------------------------------------------------------------

def test_arena_lens_200(client, tmp_path):
    _setup_arena(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/arena/test-arena")
    assert r.status_code == 200


def test_arena_lens_contains_all_7_labels(client, tmp_path):
    _setup_arena(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/arena/test-arena")
    assert r.status_code == 200
    text = r.text
    for label in ["战场定义", "玩家与位置", "决胜变量", "证据计分板", "阶段门槛", "拐点", "公司影响"]:
        assert label in text, f"Missing label: {label!r}"


def test_arena_lens_404_for_unknown(client, tmp_path):
    _setup_claims(tmp_path)
    r = client.get("/lens/arena/nonexistent-arena")
    assert r.status_code == 404


def test_arena_lens_has_archive_link(client, tmp_path):
    _setup_arena(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/arena/test-arena")
    assert "/arenas/test-arena" in r.text


# ---------------------------------------------------------------------------
# Company lens tests
# ---------------------------------------------------------------------------

def test_company_lens_200(client, tmp_path):
    _setup_company(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/company/SSE_603011")
    assert r.status_code == 200


def test_company_lens_contains_all_9_labels(client, tmp_path):
    _setup_company(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/company/SSE_603011")
    assert r.status_code == 200
    text = r.text
    for label in ["业务敞口", "论点契合", "护城河执行", "财务质量", "增长驱动", "阶段门槛状态", "估值预期", "催化剂与风险", "待答问题"]:
        assert label in text, f"Missing label: {label!r}"


def test_company_lens_400_for_bad_key(client, tmp_path):
    _setup_claims(tmp_path)
    r = client.get("/lens/company/BADFORMAT")
    assert r.status_code == 400


def test_company_lens_has_archive_link(client, tmp_path):
    _setup_company(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/company/SSE_603011")
    assert "/companies/SSE_603011" in r.text


# ---------------------------------------------------------------------------
# Bundle excerpt links point to /bundles/{sha8}
# ---------------------------------------------------------------------------

def test_industry_lens_bundle_links_point_to_bundles(client, tmp_path):
    _setup_industry(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/lens/industry/test-industry")
    assert r.status_code == 200
    # The bundle sha8 is "abcd1234" from the fixture
    assert "/bundles/abcd1234" in r.text


# ---------------------------------------------------------------------------
# Archive detail pages contain /lens/... links
# ---------------------------------------------------------------------------

def test_industry_detail_has_lens_link(client, tmp_path):
    _setup_industry(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/industries/test-industry")
    assert r.status_code == 200
    assert "/lens/industry/test-industry" in r.text


def test_arena_detail_has_lens_link(client, tmp_path):
    _setup_arena(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/arenas/test-arena")
    assert r.status_code == 200
    assert "/lens/arena/test-arena" in r.text


def test_company_detail_has_lens_link(client, tmp_path):
    _setup_company(tmp_path)
    _setup_bundle_registry(tmp_path)
    _setup_claims(tmp_path)

    r = client.get("/companies/SSE_603011")
    assert r.status_code == 200
    assert "/lens/company/SSE_603011" in r.text
