from pathlib import Path

import pytest

from app.io import competence


def _fake_vocab(tmp_path: Path) -> None:
    (tmp_path / "controlled-vocab").mkdir()
    (tmp_path / "controlled-vocab" / "competence-sector").mkdir()
    (tmp_path / "controlled-vocab" / "competence-core.yaml").write_text(
        "universal_questions:\n"
        "  - {id: q1_what, label: 做什么, prompt: p1}\n"
        "  - {id: q2_revenue_model, label: 怎么赚钱, prompt: p2}\n"
        "  - {id: q3_unit_economics, label: 单位经济, prompt: p3}\n"
        "  - {id: q4_customer_profile, label: 客户画像, prompt: p4}\n"
        "  - {id: q5_customer_acquisition, label: 获客模式, prompt: p5}\n"
        "  - {id: q6_value_chain, label: 上下游, prompt: p6}\n"
        "  - {id: q7_competition, label: 竞争, prompt: p7}\n"
        "  - {id: q8_moat, label: 护城河, prompt: p8}\n"
        "  - {id: q9_capital_intensity, label: 资本, prompt: p9}\n"
        "  - {id: q10_cycle, label: 周期, prompt: p10}\n"
        "  - {id: q11_regulation, label: 监管, prompt: p11}\n"
        "  - {id: q12_fatal_risk, label: 致命, prompt: p12}\n"
    )
    (tmp_path / "controlled-vocab" / "competence-sector" / "consumer.yaml").write_text(
        "sector: consumer\nlabel: 消费品\n"
        "sector_questions:\n"
        "  - {id: brand_power, label: 品牌力, prompt: bp}\n"
        "  - {id: channel_structure, label: 渠道, prompt: cs}\n"
        "  - {id: pricing_power, label: 定价权, prompt: pp}\n"
        "  - {id: generational_shift, label: 代际, prompt: gs}\n"
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    _fake_vocab(tmp_path)
    from app import config as cfg

    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", tmp_path / "controlled-vocab")
    monkeypatch.setattr(cfg, "SECTOR_VOCAB_DIR", tmp_path / "controlled-vocab" / "competence-sector")
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    (tmp_path / "companies").mkdir()
    return tmp_path


def test_score_all_specific_passes(env):
    u, s = competence._load_questions("consumer")
    ans = {q["id"]: "specific" for q in u}
    ans.update({q["id"]: "specific" for q in s})
    result = competence.score_competence(ans, u, s)
    assert result["universal_score"] == 12.0
    assert result["sector_score"] == 4.0
    assert result["in_competence"] is True
    assert result["gaps"] == []


def test_score_mixed_gap_list(env):
    u, s = competence._load_questions("consumer")
    ans = {q["id"]: "specific" for q in u[:8]}
    for q in u[8:]:
        ans[q["id"]] = "vague"
    for q in s[:3]:
        ans[q["id"]] = "specific"
    ans[s[3]["id"]] = "unanswered"

    result = competence.score_competence(ans, u, s)
    assert result["universal_score"] == 8 + 4 * 0.5
    assert result["sector_score"] == 3.0
    assert result["in_competence"] is True  # boundary: u=10 >=8, s=3 >=3
    assert s[3]["id"] in result["gaps"]
    assert u[8]["id"] in result["gaps"]


def test_score_below_threshold(env):
    u, s = competence._load_questions("consumer")
    ans = {q["id"]: "specific" for q in u[:7]}  # 7 < 8
    ans.update({q["id"]: "specific" for q in s})
    result = competence.score_competence(ans, u, s)
    assert result["universal_score"] == 7
    assert result["in_competence"] is False


def test_write_then_read_roundtrip(env):
    answers = {
        "q1_what": {"label": "做什么", "level": "specific", "text": "做男性健康远程处方"},
        "q3_unit_economics": {"label": "单位经济", "level": "vague", "text": "订阅模式"},
        "brand_power": {"label": "品牌力", "level": "specific", "text": "千禧世代认知"},
    }
    competence.write_competence(
        ticker="HIMS",
        market="US",
        sector="consumer",
        check_date="2026-04-23",
        answers=answers,
        base=env,
    )

    doc = competence.read_competence("HIMS", "US", base=env)
    assert doc["frontmatter"]["ticker"] == "HIMS"
    assert doc["frontmatter"]["in_competence"] is False
    assert "q1_what" in doc["answers"]
    assert doc["answers"]["q1_what"]["level"] == "specific"
    assert "男性健康" in doc["answers"]["q1_what"]["text"]
    assert doc["answers"]["q3_unit_economics"]["level"] == "vague"
    assert doc["answers"]["brand_power"]["level"] == "specific"


def test_write_rejects_unknown_sector(env):
    with pytest.raises(ValueError):
        competence.write_competence(
            ticker="X", market="US", sector="unknown",
            check_date="2026-04-23", answers={}, base=env,
        )
