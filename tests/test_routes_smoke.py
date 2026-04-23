"""Smoke tests for HTTP routes. Uses a tmp_path-backed working directory so
we don't touch the real companies/ tree.
"""
import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Run the app against an isolated working directory under tmp_path.

    We copy ``templates/`` so create_company can render, then monkeypatch
    the config constants that point at companies/ and templates/.
    """
    repo = Path(__file__).resolve().parent.parent
    shutil.copytree(repo / "templates", tmp_path / "templates")
    (tmp_path / "companies").mkdir()

    # Patch config paths to the tmp working dir BEFORE importing the app.
    monkeypatch.chdir(tmp_path)
    from app import config as cfg

    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    monkeypatch.setattr(cfg, "COMPANIES_DIR", tmp_path / "companies")
    monkeypatch.setattr(cfg, "TEMPLATES_DIR", tmp_path / "templates")
    (tmp_path / "watchlist").mkdir()
    monkeypatch.setattr(cfg, "WATCHLIST_DIR", tmp_path / "watchlist")
    (tmp_path / "portfolio").mkdir()
    (tmp_path / "portfolio" / "rules.md").write_text("# rules\n- line 1\n")
    monkeypatch.setattr(cfg, "PORTFOLIO_DIR", tmp_path / "portfolio")
    shutil.copytree(repo / "controlled-vocab", tmp_path / "controlled-vocab")
    monkeypatch.setattr(cfg, "CONTROLLED_VOCAB_DIR", tmp_path / "controlled-vocab")
    monkeypatch.setattr(cfg, "SECTOR_VOCAB_DIR", tmp_path / "controlled-vocab" / "competence-sector")
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    monkeypatch.setattr(cfg, "JOURNAL_DIR", tmp_path / "journal")
    (tmp_path / "industries").mkdir()
    monkeypatch.setattr(cfg, "INDUSTRIES_DIR", tmp_path / "industries")
    (tmp_path / "macro").mkdir()
    monkeypatch.setattr(cfg, "MACRO_DIR", tmp_path / "macro")
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cfg, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(cfg, "FINANCIALS_DB", tmp_path / "data" / "financials.db")

    from main import app

    return TestClient(app)


def test_home(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "投资决策系统" in r.text


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_companies_empty(client):
    r = client.get("/companies")
    assert r.status_code == 200
    assert "还没有公司" in r.text


def test_new_company_form(client):
    r = client.get("/companies/new")
    assert r.status_code == 200
    assert "ticker" in r.text
    assert "consumer" in r.text


def test_create_company_end_to_end(client):
    r = client.post(
        "/companies/new",
        data={
            "ticker": "HIMS",
            "market": "US",
            "name": "Hims & Hers",
            "sector": "consumer",
            "currency": "USD",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/companies/US_HIMS"

    r2 = client.get("/companies/US_HIMS")
    assert r2.status_code == 200
    assert "Hims &amp; Hers" in r2.text or "Hims & Hers" in r2.text

    r3 = client.get("/companies")
    assert "HIMS" in r3.text
    assert "consumer" in r3.text


def test_create_company_rejects_bad_sector(client):
    r = client.post(
        "/companies/new",
        data={
            "ticker": "X",
            "market": "US",
            "name": "x",
            "sector": "fake",
            "currency": "USD",
        },
    )
    assert r.status_code == 400


def test_create_company_duplicate(client):
    payload = {
        "ticker": "DUP",
        "market": "US",
        "name": "dup",
        "sector": "saas",
        "currency": "USD",
    }
    client.post("/companies/new", data=payload)
    r = client.post("/companies/new", data=payload)
    assert r.status_code == 400


def test_v0_edit_roundtrip(client):
    client.post(
        "/companies/new",
        data={
            "ticker": "RT",
            "market": "US",
            "name": "rt",
            "sector": "saas",
            "currency": "USD",
        },
    )
    r = client.get("/companies/US_RT/v0")
    assert r.status_code == 200
    assert "差异化观点" in r.text
    assert "必须自己写" in r.text

    r2 = client.post(
        "/companies/US_RT/v0",
        data={
            "entry_date": "2026-04-23",
            "position_size_pct": 5.0,
            "status": "active",
            "sec1": "简洁买入逻辑。",
            "sec2": "## 2. 差异化观点（二阶思维）\n- 观点 A",
            "sec3": "",
            "sec4": "",
            "sec5": "",
            "sec6": "",
            "sec7": "",
        },
        follow_redirects=False,
    )
    assert r2.status_code == 303

    r3 = client.get("/companies/US_RT/v0")
    assert "简洁买入逻辑" in r3.text
    assert "观点 A" in r3.text
    assert 'value="active" selected' in r3.text or "selected>active" in r3.text


def test_watchlist_add_and_move(client):
    r = client.get("/watchlist")
    assert r.status_code == 200
    assert "prefilter" in r.text

    # Add with a date_added far in the past so seasoning is always satisfied
    r2 = client.post(
        "/watchlist/add/prefilter",
        data={
            "date_added": "2020-01-01",
            "ticker": "HIMS",
            "source_type": "product_experience",
            "source": "daily use",
            "notes": "",
        },
        follow_redirects=False,
    )
    assert r2.status_code == 303

    r3 = client.get("/watchlist")
    assert "HIMS" in r3.text

    long_reason = "具体理由写得足够长 " * 4  # >30 chars
    r4 = client.post(
        "/watchlist/move",
        data={
            "ticker": "HIMS",
            "from_stage": "prefilter",
            "to_stage": "researching",
            "started": "2026-04-30",
            "gap_focus": "unit economics",
            "gate_competence": "yes",
            "reason_gate_competence": long_reason,
            "gate_mispricing": "yes",
            "reason_gate_mispricing": long_reason,
            "gate_genuine_interest": "yes",
            "reason_gate_genuine_interest": long_reason,
        },
        follow_redirects=False,
    )
    assert r4.status_code == 303

    r5 = client.get("/watchlist")
    assert "HIMS" in r5.text


def test_watchlist_move_rejects_missing_gate(client):
    client.post(
        "/watchlist/add/prefilter",
        data={
            "date_added": "2020-01-01",
            "ticker": "GATE",
            "source_type": "quant_screen",
            "source": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    r = client.post(
        "/watchlist/move",
        data={
            "ticker": "GATE",
            "from_stage": "prefilter",
            "to_stage": "researching",
            "started": "2026-04-30",
        },
    )
    assert r.status_code == 400
    assert "gate" in r.text.lower()


def test_watchlist_move_rejects_fresh_prefilter(client):
    import datetime as _dt
    recent = _dt.date.today() - _dt.timedelta(days=2)
    client.post(
        "/watchlist/add/prefilter",
        data={
            "date_added": recent.isoformat(),
            "ticker": "FRESH",
            "source_type": "qual_radar",
            "source": "",
            "notes": "",
        },
        follow_redirects=False,
    )
    long_reason = "具体理由写得足够长 " * 4
    r = client.post(
        "/watchlist/move",
        data={
            "ticker": "FRESH",
            "from_stage": "prefilter",
            "to_stage": "researching",
            "started": "2026-04-30",
            "gate_competence": "yes", "reason_gate_competence": long_reason,
            "gate_mispricing": "yes", "reason_gate_mispricing": long_reason,
            "gate_genuine_interest": "yes", "reason_gate_genuine_interest": long_reason,
        },
    )
    assert r.status_code == 400
    assert "7 days" in r.text or "day" in r.text.lower()


def test_watchlist_add_rejects_bad_source_type(client):
    r = client.post(
        "/watchlist/add/prefilter",
        data={
            "date_added": "2020-01-01",
            "ticker": "X",
            "source_type": "news",  # invalid
            "source": "bloomberg",
            "notes": "",
        },
    )
    assert r.status_code == 400


def test_v0_preview(client):
    client.post(
        "/companies/new",
        data={
            "ticker": "PV",
            "market": "US",
            "name": "pv",
            "sector": "saas",
            "currency": "USD",
        },
    )
    r = client.get("/companies/US_PV/v0/preview")
    assert r.status_code == 200
    assert "<h1>" in r.text  # markdown rendered H1


def test_competence_end_to_end(client):
    client.post(
        "/companies/new",
        data={"ticker": "CM", "market": "US", "name": "cm", "sector": "consumer", "currency": "USD"},
    )
    r = client.get("/companies/US_CM/competence")
    assert r.status_code == 200
    assert "q1_what" in r.text
    assert "brand_power" in r.text  # consumer sector question
    assert "门禁阈值" in r.text

    # Fill all universal + sector as specific → should pass gate
    form_data = {}
    for qid in ["q1_what", "q2_revenue_model", "q3_unit_economics", "q4_customer_profile",
                "q5_customer_acquisition", "q6_value_chain", "q7_competition", "q8_moat",
                "q9_capital_intensity", "q10_cycle", "q11_regulation", "q12_fatal_risk"]:
        form_data[f"{qid}__level"] = "specific"
        form_data[f"{qid}__text"] = f"ans-{qid}"
    for qid in ["brand_power", "channel_structure", "pricing_power", "generational_shift"]:
        form_data[f"{qid}__level"] = "specific"
        form_data[f"{qid}__text"] = f"ans-{qid}"
    r2 = client.post("/companies/US_CM/competence", data=form_data, follow_redirects=False)
    assert r2.status_code == 303

    r3 = client.get("/companies/US_CM/competence")
    assert "通过" in r3.text
    assert "12" in r3.text  # universal score


def test_valuation_end_to_end(client):
    client.post(
        "/companies/new",
        data={"ticker": "VL", "market": "US", "name": "vl", "sector": "saas", "currency": "USD"},
    )
    r = client.get("/companies/US_VL/valuation")
    assert r.status_code == 200

    r2 = client.post(
        "/companies/US_VL/valuation",
        data={
            "valuation_date": "2026-04-23",
            "bull_price": 40, "base_price": 25, "bear_price": 12,
            "prob_bull": 0.25, "prob_base": 0.5, "prob_bear": 0.25,
            "current_price": 17,
            "discount_rate": 0.09,
            "body": "## 结论\n有安全边际",
        },
        follow_redirects=False,
    )
    assert r2.status_code == 303

    r3 = client.get("/companies/US_VL/valuation")
    assert "25.5" in r3.text  # weighted
    assert "可买" in r3.text  # BUY tier


def test_research_add_claim_and_upload(client):
    client.post(
        "/companies/new",
        data={"ticker": "RS", "market": "US", "name": "rs", "sector": "saas", "currency": "USD"},
    )
    r = client.get("/research/US_RS")
    assert r.status_code == 200
    assert "claims" in r.text

    r2 = client.post(
        "/research/US_RS/claim",
        data={
            "claim_text": "2026 Q1 用户同比 +30%",
            "subject_tag": "revenue_growth",
            "polarity": "bull",
            "claim_type": "quantitative",
            "timeframe": "2026Q1",
            "source_id": "MS-2026-04",
            "evidence_text": "公司 Q1 电话会",
        },
        follow_redirects=False,
    )
    assert r2.status_code == 303

    r3 = client.get("/research/US_RS")
    assert "RS-0001" in r3.text
    assert "revenue_growth" in r3.text

    # upload a source
    r4 = client.post(
        "/research/US_RS/source",
        files={"file": ("note.md", b"# hello\ncontent", "text/markdown")},
        follow_redirects=False,
    )
    assert r4.status_code == 303
    r5 = client.get("/research/US_RS")
    assert "note.md" in r5.text


def test_research_batch_import_end_to_end(client):
    client.post(
        "/companies/new",
        data={"ticker": "BI", "market": "US", "name": "bi", "sector": "saas", "currency": "USD"},
    )
    payload = (
        '{"source_id": "MS-2026-04-10", '
        '"source_file": "ms.md", '
        '"extracted_by": "claude-opus-4-7", '
        '"claims": ['
        '  {"claim_text": "Q1 付费用户 +30%", "subject_tag": "revenue_growth",'
        '   "polarity": "bull", "claim_type": "quantitative",'
        '   "evidence_text": "公司披露 Q1 220 万"},'
        '  {"claim_text": "毛利率扩张 200bps", "subject_tag": "gross_margin",'
        '   "polarity": "bull", "claim_type": "quantitative"}'
        ']}'
    )
    r = client.post(
        "/research/US_BI/batch-import",
        data={"claims_json": payload},
        follow_redirects=False,
    )
    assert r.status_code == 303

    r2 = client.get("/research/US_BI")
    assert "BI-0001" in r2.text
    assert "BI-0002" in r2.text
    assert "revenue_growth" in r2.text
    assert "gross_margin" in r2.text


def test_research_batch_import_rejects_invalid_tag(client):
    client.post(
        "/companies/new",
        data={"ticker": "BJ", "market": "US", "name": "bj", "sector": "saas", "currency": "USD"},
    )
    payload = (
        '[{"claim_text": "x", "subject_tag": "made_up_tag",'
        ' "polarity": "bull", "claim_type": "qualitative"}]'
    )
    r = client.post(
        "/research/US_BJ/batch-import",
        data={"claims_json": payload},
    )
    assert r.status_code == 400
    assert "校验失败" in r.text
    assert "not in controlled-vocab" in r.text
    # Nothing should have been imported
    r2 = client.get("/research/US_BJ")
    assert "claims（0 条）" in r2.text


def test_research_batch_import_rejects_malformed_json(client):
    client.post(
        "/companies/new",
        data={"ticker": "BK", "market": "US", "name": "bk", "sector": "saas", "currency": "USD"},
    )
    r = client.post(
        "/research/US_BK/batch-import",
        data={"claims_json": "{not json"},
    )
    assert r.status_code == 400
    assert "not valid JSON" in r.text


def test_research_batch_atomic_no_partial_import(client):
    # Mixed valid + invalid → whole batch rejected
    client.post(
        "/companies/new",
        data={"ticker": "BL", "market": "US", "name": "bl", "sector": "saas", "currency": "USD"},
    )
    payload = (
        '[{"claim_text": "ok", "subject_tag": "revenue_growth",'
        '  "polarity": "bull", "claim_type": "qualitative"},'
        ' {"claim_text": "bad", "subject_tag": "bogus",'
        '  "polarity": "bull", "claim_type": "qualitative"}]'
    )
    r = client.post(
        "/research/US_BL/batch-import",
        data={"claims_json": payload},
    )
    assert r.status_code == 400
    r2 = client.get("/research/US_BL")
    assert "claims（0 条）" in r2.text  # neither claim was written


def test_prompt_doc_served(client):
    r = client.get("/prompts/claim-extraction.md")
    assert r.status_code == 200
    assert "Claim 抽取 Prompt" in r.text


def test_portfolio_rules_edit_and_violation_warning(client):
    # Edit rules
    r = client.post(
        "/portfolio/rules",
        data={
            "max_single_pct": "15",
            "max_sector_pct": "",
            "min_cash_pct": "20",
            "body": "# 说明\n单仓不超过 15%",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    # Read back edit form
    r2 = client.get("/portfolio/rules")
    assert "15" in r2.text
    assert "单仓不超过 15%" in r2.text

    # Add a position that violates both rules
    client.post(
        "/portfolio/position",
        data={
            "ticker": "AAPL",
            "market": "US",
            "entry_date": "2025-01-05",
            "avg_cost": "150",
            "shares": "10",
            "position_pct": "30",
        },
    )
    port = client.get("/portfolio")
    assert "组合级规则违规" in port.text
    assert "US:AAPL" in port.text


def test_competence_map_empty(client):
    r = client.get("/competence-map")
    assert r.status_code == 200
    assert "年度能力优势图" in r.text


def test_regime_index_empty(client):
    r = client.get("/regime")
    assert r.status_code == 200
    assert "市场钟摆" in r.text


def test_regime_edit_and_save(client):
    r = client.post(
        "/regime/2026-Q1",
        data={
            "valuation_percentile": "78",
            "credit_spread_bps": "95",
            "vix_level": "14.5",
            "retail_sentiment": "greedy",
            "macro_reaction": "tolerant",
            "verdict": "hot",
            "position_hint": "控制新开仓",
            "cash_floor_hint": "20",
            "body": "估值偏高",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    # Read back
    r2 = client.get("/regime/2026-Q1")
    assert "估值偏高" in r2.text
    assert "hot" in r2.text
    # And should appear on index
    r3 = client.get("/regime")
    assert "2026-Q1" in r3.text


def test_regime_rejects_bad_verdict(client):
    r = client.post(
        "/regime/2026-Q1",
        data={
            "valuation_percentile": "",
            "credit_spread_bps": "",
            "vix_level": "",
            "retail_sentiment": "",
            "macro_reaction": "",
            "verdict": "boiling",
            "position_hint": "",
            "cash_floor_hint": "",
            "body": "",
        },
    )
    assert r.status_code == 400
    assert "verdict" in r.text


def test_catalysts_page_empty(client):
    r = client.get("/catalysts")
    assert r.status_code == 200
    assert "催化剂日历" in r.text


def test_catalysts_add_then_surfaces_on_home(client, tmp_path, monkeypatch):
    # Pretend today is 2026-04-20; add a catalyst 2 days out
    import app.io.catalysts as cat_io
    from datetime import date
    orig_upcoming = cat_io.upcoming
    monkeypatch.setattr(cat_io, "upcoming", lambda **kw: orig_upcoming(today=date(2026, 4, 20), **kw))

    r = client.post(
        "/catalysts/add",
        data={
            "date": "2026-04-22",
            "title": "HIMS Q1",
            "kind": "earnings",
            "ticker": "US_HIMS",
            "industry": "",
            "note": "",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    home = client.get("/")
    assert "未来 7 天催化剂" in home.text
    assert "HIMS Q1" in home.text


def test_catalysts_rejects_bad_date(client):
    r = client.post(
        "/catalysts/add",
        data={"date": "tomorrow", "title": "x", "kind": "earnings", "ticker": "", "industry": "", "note": ""},
    )
    assert r.status_code == 400
    assert "YYYY-MM-DD" in r.text


def test_review_index_empty(client):
    r = client.get("/review")
    assert r.status_code == 200
    assert "季度复盘" in r.text


def test_review_detail_bad_quarter(client):
    r = client.get("/review/not-a-quarter")
    assert r.status_code == 400


def test_review_quarter_detail_empty(client):
    r = client.get("/review/2026-Q1")
    assert r.status_code == 200
    assert "2026-Q1" in r.text


def test_performance_empty_page(client):
    r = client.get("/performance")
    assert r.status_code == 200
    assert "业绩度量" in r.text


def test_performance_benchmark_import_then_compare(client):
    # Import a benchmark so /performance shows the table section
    paste = "2025-01-31 SPY 500\n2025-02-28 SPY 510\n"
    r = client.post(
        "/performance/benchmark-import",
        data={"paste": paste, "benchmark": "SPY"},
    )
    assert r.status_code == 200
    assert "SPY" in r.text
    # With no prices, compare section is empty-friendly
    r2 = client.get("/performance?benchmark=SPY")
    assert r2.status_code == 200
    assert "尚未有重叠月份" in r2.text or "累计组合" in r2.text


def test_prompts_index_lists_all_docs(client):
    r = client.get("/prompts")
    assert r.status_code == 200
    # Index should mention every prompt file shipped in docs/prompts/
    assert "claim-extraction.md" in r.text
    assert "profile-extraction.md" in r.text
    assert "meta-extraction.md" in r.text
    assert "consensus-map.md" in r.text
    # And link to raw markdown
    assert 'href="/prompts/claim-extraction.md"' in r.text


def test_journal_end_to_end(client):
    # First need a company so V0 snapshot exists
    client.post(
        "/companies/new",
        data={"ticker": "JL", "market": "US", "name": "jl", "sector": "saas", "currency": "USD"},
    )
    r = client.get("/journal")
    assert r.status_code == 200
    assert "还没有决策记录" in r.text

    r2 = client.post(
        "/journal/new",
        data={
            "ticker": "JL", "market": "US", "action": "buy",
            "entry_date": "2026-04-23", "price": 19.0, "position_change": 5,
        },
        follow_redirects=False,
    )
    assert r2.status_code == 303
    assert r2.headers["location"] == "/journal/2026-04-23-JL-buy"

    r3 = client.get("/journal/2026-04-23-JL-buy")
    assert r3.status_code == 200
    assert "V0 快照" in r3.text
    assert "偏见自查" in r3.text

    # Save scores + flag bias
    r4 = client.post(
        "/journal/2026-04-23-JL-buy",
        data={
            "process_quality": 4, "process_rigor": 3,
            "process_rule_adherence": 5, "process_emotional_control": 4,
            "bias_emotional_tie": "yes",
            "bias_reason_emotional_tie": "短",  # too short, will flag
            "bias_source_balance": "no",
            "bias_proving_thesis": "no",
            "bias_swap_test": "no",
            "sec1": "买 5%", "sec2": "", "sec3": "平静",
            "sec5": "a\nb\nc\nd\ne", "sec6": "战争恐慌", "sec7": "纪律到位", "sec8": "",
        },
        follow_redirects=False,
    )
    assert r4.status_code == 303

    r5 = client.get("/journal/2026-04-23-JL-buy")
    assert "决策暂停 24 小时" in r5.text
    assert "emotional_tie" in r5.text

    r6 = client.get("/journal")
    assert "JL" in r6.text
    assert "buy" in r6.text


def test_journal_stale_v0_snapshot_detected(client):
    client.post(
        "/companies/new",
        data={"ticker": "ST", "market": "US", "name": "st", "sector": "saas", "currency": "USD"},
    )
    client.post(
        "/journal/new",
        data={
            "ticker": "ST", "market": "US", "action": "buy",
            "entry_date": "2026-04-23", "price": 1, "position_change": 1,
        },
    )
    # Now edit the V0 — should cause detail page to show "V0 已修改"
    client.post(
        "/companies/US_ST/v0",
        data={
            "entry_date": "2026-04-23", "position_size_pct": 5, "status": "active",
            "sec1": "new", "sec2": "", "sec3": "", "sec4": "",
            "sec5": "", "sec6": "", "sec7": "",
        },
    )
    r = client.get("/journal/2026-04-23-ST-buy")
    assert "V0 已修改" in r.text


def test_prices_and_triggers_end_to_end(client):
    client.post(
        "/companies/new",
        data={"ticker": "TR", "market": "US", "name": "tr", "sector": "saas", "currency": "USD"},
    )
    # Create 2 triggers: a buy at 15, a trim at 30
    r = client.post(
        "/companies/US_TR/triggers",
        data={"trigger_price": "15.00", "action": "first_entry"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    client.post(
        "/companies/US_TR/triggers",
        data={"trigger_price": "30.00", "action": "trim"},
    )

    r2 = client.get("/companies/US_TR/triggers")
    assert "first_entry" in r2.text
    assert "trim" in r2.text
    assert "armed" in r2.text

    # Post price below 15 → first_entry should fire
    r3 = client.post(
        "/prices",
        data={"date": "2026-04-23", "paste": "TR 14.50\nNVDA 450.20"},
    )
    assert r3.status_code == 200
    assert "新触发" in r3.text
    assert "first_entry" in r3.text
    # Only 1 new trigger (trim didn't fire; 30 still armed)
    assert "1" in r3.text

    # Check portfolio dashboard picks up price (no position yet so no P&L)
    client.post(
        "/portfolio/position",
        data={"ticker": "TR", "market": "US", "entry_date": "2026-04-01",
              "avg_cost": "12", "shares": "100", "position_pct": "5"},
    )
    r4 = client.get("/portfolio")
    assert "TR" in r4.text
    assert "14.50" in r4.text
    # (14.50 - 12) / 12 = +20.8%
    assert "+20.8%" in r4.text

    # Home card shows fired trigger
    r5 = client.get("/")
    assert "价格触发" in r5.text
    assert "TR" in r5.text

    # Delete fired trigger
    rows = r2.text  # to get trigger ids we'd need the IDs; instead re-read triggers list
    r6 = client.get("/companies/US_TR/triggers")
    # Find any trigger id form action pattern
    import re as _re
    ids = _re.findall(r"/triggers/(\d+)/delete", r6.text)
    assert ids
    client.post(f"/companies/US_TR/triggers/{ids[0]}/delete")
    r7 = client.get("/companies/US_TR/triggers")
    # After deleting one, fewer triggers remain
    assert r7.text.count("first_entry") + r7.text.count("trim") < r6.text.count("first_entry") + r6.text.count("trim")


def test_prices_rejects_gracefully(client):
    r = client.post(
        "/prices",
        data={"date": "2026-04-23", "paste": "JUNK\nNVDA 450"},
    )
    assert r.status_code == 200
    assert "解析错误" in r.text
    assert "JUNK" in r.text


def test_trigger_rejects_bad_action(client):
    client.post(
        "/companies/new",
        data={"ticker": "TX", "market": "US", "name": "tx", "sector": "saas", "currency": "USD"},
    )
    r = client.post(
        "/companies/US_TX/triggers",
        data={"trigger_price": "15", "action": "nonsense"},
    )
    assert r.status_code == 400


def test_earnings_review_end_to_end(client):
    # Empty state first
    r = client.get("/earnings-review")
    assert r.status_code == 200
    assert "没有待对照" in r.text

    # Create a company + import financials → should appear as pending
    client.post(
        "/companies/new",
        data={"ticker": "ER", "market": "US", "name": "er", "sector": "saas", "currency": "USD"},
    )
    csv_bytes = (
        b"period,period_type,revenue,gross_profit,operating_income,net_income,"
        b"total_assets,total_equity,operating_cashflow,shares_outstanding\n"
        b"2024Q4,quarterly,1000,400,200,150,5000,2000,180,100\n"
    )
    client.post(
        "/earnings-review",  # harmless GET target; next call is the import
    )
    client.post(
        "/companies/US_ER/financials/import",
        files={"file": ("er-q4.csv", csv_bytes, "text/csv")},
    )

    r2 = client.get("/earnings-review")
    assert "ER" in r2.text
    assert "2024Q4" in r2.text
    assert "从未" in r2.text

    # Home page also surfaces the pending item
    r3 = client.get("/")
    assert "财报对照" in r3.text
    assert "ER" in r3.text

    # Detail page shows V0 sections + financials
    r4 = client.get("/earnings-review/US_ER")
    assert r4.status_code == 200
    assert "2024Q4" in r4.text
    assert "V0 §5" in r4.text
    assert "V0 §6" in r4.text

    # Mark reviewed → clears from pending list
    r5 = client.post(
        "/earnings-review/US_ER/mark",
        data={"period": "2024Q4"},
        follow_redirects=False,
    )
    assert r5.status_code == 303

    r6 = client.get("/earnings-review")
    assert "ER" not in r6.text or "没有待对照" in r6.text
    # Home page no longer shows pending section
    r7 = client.get("/")
    assert "财报对照" not in r7.text


def test_earnings_review_detail_404(client):
    r = client.get("/earnings-review/US_NOPE")
    assert r.status_code == 404


def test_valuation_rejects_bad_probs(client):
    client.post(
        "/companies/new",
        data={"ticker": "VB", "market": "US", "name": "vb", "sector": "saas", "currency": "USD"},
    )
    r = client.post(
        "/companies/US_VB/valuation",
        data={
            "valuation_date": "2026-04-23",
            "bull_price": 40, "base_price": 25, "bear_price": 12,
            "prob_bull": 0.4, "prob_base": 0.5, "prob_bear": 0.25,
            "current_price": 17, "discount_rate": 0.09, "body": "",
        },
    )
    assert r.status_code == 400


def test_competence_gate_warn_shows_on_detail_when_not_passing(client):
    client.post(
        "/companies/new",
        data={"ticker": "GW", "market": "US", "name": "gw", "sector": "saas", "currency": "USD"},
    )
    r = client.get("/companies/US_GW")
    # Fresh company has unfilled competence → should show gate warning
    assert "能力圈未通过" in r.text


def test_financials_empty_page(client):
    client.post(
        "/companies/new",
        data={"ticker": "FN", "market": "US", "name": "fn", "sector": "saas", "currency": "USD"},
    )
    r = client.get("/companies/US_FN/financials")
    assert r.status_code == 200
    assert "CSV 导入" in r.text
    assert "还没有财务数据" in r.text


def test_financials_csv_import_end_to_end(client):
    client.post(
        "/companies/new",
        data={"ticker": "FI", "market": "US", "name": "fi", "sector": "saas", "currency": "USD"},
    )

    csv_bytes = (
        b"period,period_type,revenue,gross_profit,operating_income,net_income,"
        b"total_assets,total_equity,operating_cashflow,shares_outstanding\n"
        b"2024Q4,quarterly,1000,400,200,150,5000,2000,180,100\n"
        b"2024A,annual,3500,1400,700,500,5000,2000,650,100\n"
    )
    r = client.post(
        "/companies/US_FI/financials/import",
        files={"file": ("fi-2024.csv", csv_bytes, "text/csv")},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/companies/US_FI/financials"

    r2 = client.get("/companies/US_FI/financials")
    assert r2.status_code == 200
    assert "2024A" in r2.text
    assert "2024Q4" in r2.text
    # gross margin 400/1000 = 40.0% and ROE 150/2000 = 7.5%
    assert "40.0%" in r2.text
    assert "7.5%" in r2.text
    assert "fi-2024.csv" in r2.text


def test_financials_rejects_bad_csv(client):
    client.post(
        "/companies/new",
        data={"ticker": "BAD", "market": "US", "name": "bad", "sector": "saas", "currency": "USD"},
    )
    r = client.post(
        "/companies/US_BAD/financials/import",
        files={"file": ("bad.csv", b"period,revenue\n2024Q4,1000\n", "text/csv")},
    )
    assert r.status_code == 400


def test_financials_404_for_unknown_company(client):
    r = client.get("/companies/US_NOPE/financials")
    assert r.status_code == 404


def test_portfolio_end_to_end(client):
    r = client.get("/portfolio")
    assert r.status_code == 200
    assert "总仓位" in r.text
    assert "还没有持仓" in r.text

    # Create a company first so V0 exists
    client.post(
        "/companies/new",
        data={"ticker": "PF", "market": "US", "name": "pf", "sector": "saas", "currency": "USD"},
    )

    r2 = client.post(
        "/portfolio/position",
        data={
            "ticker": "PF",
            "market": "US",
            "entry_date": "2026-04-23",
            "avg_cost": "10",
            "shares": "50",
            "position_pct": "5",
        },
        follow_redirects=False,
    )
    assert r2.status_code == 303

    r3 = client.get("/portfolio")
    assert "PF" in r3.text
    assert "5.0%" in r3.text  # total position

    # V0 should have been promoted to active
    r4 = client.get("/companies/US_PF/v0")
    assert "active" in r4.text


def test_industries_index_empty(client):
    r = client.get("/industries")
    assert r.status_code == 200
    assert "consumer" in r.text
    assert "saas" in r.text


def test_industries_sector_edit_round_trip(client):
    r = client.get("/industries/consumer")
    assert r.status_code == 200

    r2 = client.post(
        "/industries/consumer/landscape",
        data={"source_type": "annual_report_xref", "body": "## 供需\n白酒集中度上升。\n"},
        follow_redirects=False,
    )
    assert r2.status_code == 303

    r3 = client.get("/industries/consumer")
    assert "白酒集中度上升" in r3.text
    assert "annual_report_xref" in r3.text


def test_industries_rejects_bad_sector(client):
    r = client.get("/industries/unknown")
    assert r.status_code == 404
    r2 = client.get("/industries/consumer/bogus")
    assert r2.status_code == 404


def test_meta_edit_round_trip(client):
    r = client.post(
        "/companies/new",
        data={"ticker": "META1", "market": "US", "name": "Meta Co", "sector": "consumer"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    edit = client.get("/companies/US_META1/meta")
    assert edit.status_code == 200
    assert "Meta Co" in edit.text

    save = client.post(
        "/companies/US_META1/meta",
        data={
            "name": "Meta Co Updated",
            "industry_primary": "consumer",
            "themes": "ai, platforms",
            "listed_date": "2012-05-18",
            "currency": "USD",
            "website": "https://meta.example",
            "body": "# Meta Co\n- 主营：social\n",
        },
        follow_redirects=False,
    )
    assert save.status_code == 303

    detail = client.get("/companies/US_META1")
    assert "Meta Co Updated" in detail.text
    assert "<code>ai</code>" in detail.text
    assert "<code>platforms</code>" in detail.text


def test_meta_rejects_bad_industry(client):
    client.post(
        "/companies/new",
        data={"ticker": "BAD1", "market": "US", "name": "Bad", "sector": "consumer"},
        follow_redirects=False,
    )
    r = client.post(
        "/companies/US_BAD1/meta",
        data={"name": "Bad", "industry_primary": "unknown_sector", "body": ""},
    )
    assert r.status_code == 400


def test_profile_edit_requires_source(client):
    client.post(
        "/companies/new",
        data={"ticker": "PROF1", "market": "US", "name": "Prof", "sector": "consumer"},
        follow_redirects=False,
    )

    # GET page renders even with no source uploaded
    r = client.get("/companies/US_PROF1/profile/2026")
    assert r.status_code == 200
    assert "sources/" in r.text or "必选" in r.text or "为空" in r.text

    # POST without source_file → 400
    r2 = client.post(
        "/companies/US_PROF1/profile/2026",
        data={"source_file": "", "source": "annual_report", "body": "x"},
    )
    assert r2.status_code == 400


def test_discipline_empty(client):
    r = client.get("/discipline")
    assert r.status_code == 200
    assert "自律指标" in r.text


def test_research_audit_empty(client):
    r = client.get("/research-audit")
    assert r.status_code == 200
    assert "Claim 抽检" in r.text


def test_profile_edit_accepts_uploaded_source(client, tmp_path):
    client.post(
        "/companies/new",
        data={"ticker": "PROF2", "market": "US", "name": "Prof2", "sector": "saas"},
        follow_redirects=False,
    )
    # drop a source file directly on disk
    src = tmp_path / "companies" / "US_PROF2" / "sources" / "2026-annual.md"
    src.write_text("# 年报\n", encoding="utf-8")

    r = client.post(
        "/companies/US_PROF2/profile/2026",
        data={
            "source_file": "sources/2026-annual.md",
            "source": "annual_report",
            "body": "## 业务构成\n核心 SaaS。\n",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303

    detail = client.get("/companies/US_PROF2")
    assert "profile-2026.md" in detail.text
    assert "2026-annual.md" in detail.text
