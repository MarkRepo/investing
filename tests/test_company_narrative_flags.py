import json
from argparse import Namespace

from app.io.claim_registry import ClaimRegistry, build_evidence_entry
from app.io.narrative_proposals import read_narrative_flags, scan_narrative_flags
from scripts import company_narrative_flags


def _claim(registry, *, status="active", direction="supports"):
    evidence = build_evidence_entry(
        source_id="src-001",
        block_ids=["ib-001"],
        fact_ids=["fact-001"],
        direction=direction,
        now="2026-04-30T12:00:00+00:00",
    )
    claim = registry.create_claim(
        claim_text="品牌力支撑长期毛利率",
        scope_type="company",
        scope_ref="SSE_600519",
        claim_type="judgment",
        dimension_hint="moat",
        confidence="medium_high",
        as_of="2025-12-31",
        evidence=evidence,
        trigger="created",
        trigger_ref="seed",
        now="2026-04-30T12:00:00+00:00",
    )
    if status != "active":
        claim["status"] = status
        registry._rewrite_claim(claim)
    return claim


def _write_segment(tmp_path, claim_id, dim="moat"):
    narr_dir = tmp_path / "companies" / "SSE_600519" / "narratives"
    narr_dir.mkdir(parents=True, exist_ok=True)
    (narr_dir / f"{dim.replace('_', '-')}.md").write_text(
        "# heading\n\n"
        "### 护城河\n\n"
        "status: active\n"
        "last_written: 2026-04-30\n"
        f"supported_by_claims: [{claim_id}]\n"
        "source_ids: [src-001]\n"
        "proposal_id: np-001\n\n"
        "正文。\n",
        encoding="utf-8",
    )


def test_scan_company_flags_no_flag_for_active(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry)
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:00:00+00:00",
    )

    assert flags == []
    assert read_narrative_flags("company", "SSE_600519", base=tmp_path) == []


def test_scan_company_flags_writes_critical_for_retired(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    flags = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:00:00+00:00",
    )

    assert len(flags) == 1
    assert flags[0]["flag_level"] == "critical"
    assert flags[0]["reason"] == "supporting claim retired"
    assert flags[0]["scope_type"] == "company"
    assert flags[0]["scope_ref"] == "SSE_600519"
    stored = read_narrative_flags("company", "SSE_600519", base=tmp_path)
    assert len(stored) == 1


def test_scan_company_flags_dedups_on_rerun(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, direction="refutes")
    _write_segment(tmp_path, claim["claim_id"])

    first = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:00:00+00:00",
    )
    second = scan_narrative_flags(
        registry=registry,
        base=tmp_path,
        scope_type="company",
        scope_ref="SSE_600519",
        now="2026-04-30T12:01:00+00:00",
    )

    assert len(first) == 1
    assert first[0]["flag_level"] == "significant"
    assert second == []


def test_company_narrative_flags_cli(tmp_path):
    registry = ClaimRegistry(tmp_path)
    claim = _claim(registry, status="retired")
    _write_segment(tmp_path, claim["claim_id"])

    rc = company_narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            market="SSE",
            ticker="600519",
        )
    )

    assert rc == 0
    flag_file = tmp_path / "companies" / "SSE_600519" / "narrative-flags.jsonl"
    rows = [json.loads(line) for line in flag_file.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["reason"] == "supporting claim retired"
