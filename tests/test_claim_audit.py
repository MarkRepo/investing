"""Tests for monthly claim audit sampler."""
from pathlib import Path

import pytest

from app import config as cfg
from app.io import claims


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", tmp_path / "controlled-vocab")
    (tmp_path / "companies").mkdir()
    return tmp_path


def _seed(env: Path, market: str, ticker: str, n: int, month: str) -> None:
    (env / "companies" / f"{market}_{ticker}").mkdir()
    path = env / "companies" / f"{market}_{ticker}" / "claims.jsonl"
    import json
    with path.open("w") as f:
        for i in range(n):
            obj = {
                "id": f"{ticker}-{i:04d}",
                "source_id": f"src-{i}",
                "claim_text": f"claim {i}",
                "subject_tag": "revenue_growth",
                "polarity": "bull",
                "claim_type": "qualitative",
                "extracted_at": f"{month}-15T00:00:00Z",
            }
            f.write(json.dumps(obj) + "\n")


def test_iter_all_claims_tags_company(env):
    _seed(env, "US", "AAA", 3, "2026-03")
    _seed(env, "US", "BBB", 2, "2026-04")
    out = claims.iter_all_claims(base=env)
    markets = {(c["_market"], c["_ticker"]) for c in out}
    assert markets == {("US", "AAA"), ("US", "BBB")}
    assert len(out) == 5


def test_audit_sample_filters_by_month(env):
    _seed(env, "US", "AAA", 10, "2026-03")
    _seed(env, "US", "BBB", 10, "2026-04")
    result = claims.audit_sample(month="2026-03", pct=0.20, base=env)
    assert result["total"] == 20
    assert result["pool"] == 10
    assert len(result["sample"]) == 2
    for c in result["sample"]:
        assert c["extracted_at"].startswith("2026-03")


def test_audit_sample_deterministic_per_month(env):
    _seed(env, "US", "AAA", 20, "2026-03")
    a = claims.audit_sample(month="2026-03", pct=0.25, base=env)
    b = claims.audit_sample(month="2026-03", pct=0.25, base=env)
    a_ids = [c["id"] for c in a["sample"]]
    b_ids = [c["id"] for c in b["sample"]]
    assert a_ids == b_ids


def test_audit_sample_all_claims_when_no_month(env):
    _seed(env, "US", "AAA", 10, "2026-03")
    _seed(env, "US", "BBB", 10, "2026-04")
    result = claims.audit_sample(month=None, pct=0.10, base=env)
    assert result["pool"] == 20
    assert len(result["sample"]) == 2


def test_audit_sample_rejects_bad_pct(env):
    with pytest.raises(ValueError):
        claims.audit_sample(pct=0, base=env)
    with pytest.raises(ValueError):
        claims.audit_sample(pct=1.5, base=env)


def test_audit_sample_empty_pool(env):
    result = claims.audit_sample(month="2099-01", pct=0.10, base=env)
    assert result["pool"] == 0
    assert result["sample"] == []
