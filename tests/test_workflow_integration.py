"""End-to-end integration test for the 15-step ingest endgame pipeline.

Covers the automatable portion: arena/industry/company autobuild →
ingest_match → ingest_apply → narrative_propose → narrative_apply →
narrative_flags → bundle persistence.

Steps skipped (require LLM or human interaction):
- Step 1 preprocess: mocked via fixture bundle.json
- Step 2 LLM review-bundle dispatch: not automatable, replaced by mock bundle
- Step 3 QA: optional, skipped for brevity
- Step 8 pending review: simulated by editing the match file in-place
- Step 11 proposal review: simulated by editing the proposals file in-place
- Step 15 report: not testable

See spec: docs/superpowers/specs/2026-04-30-ingest-endgame-replacement-design.md §11.4
"""
from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from app.io.bundle_registry import get_bundle, persist_bundle
from app.io.claim_registry import ClaimRegistry
from scripts import ingest_aggregate as agg
from scripts import ingest_apply, ingest_match, narrative_apply, narrative_flags, narrative_propose

SOURCE_ID = "test-source-1"
ARENA_SLUG = "test-arena-slug"
INDUSTRY_SLUG = "test-industry"


def _mock_bundle() -> dict:
    return {
        "source_digest": {
            "source_id": SOURCE_ID,
            "source_type": "industry_report",
            "source_title": "测试报告",
            "source_date": "2026-04-15",
            "institution": "测试机构",
        },
        "insight_blocks": [
            {"id": "ib-001", "title": "赛道竞争格局", "dimension_hint": "competitive_position"},
            {"id": "ib-002", "title": "参与者分析", "dimension_hint": "participants"},
        ],
        "atomic_facts": [
            {
                "fact_id": "fact-001",
                "linked_block_id": "ib-001",
                "fact_text": "测试赛道竞争格局趋于集中",
                "confidence": "medium",
            },
            {
                "fact_id": "fact-002",
                "linked_block_id": "ib-002",
                "fact_text": "测试赛道参与者超过十家",
                "confidence": "medium",
            },
        ],
        "claim_candidates": [
            {
                "candidate_id": "cc-001",
                "claim_text": "测试赛道竞争格局正在快速集中",
                "scope_type": "arena",
                "scope_ref": ARENA_SLUG,
                "claim_type": "judgment",
                "dimension_hint": "competitive_position",
                "confidence": "medium",
                "as_of": "2026-04-15",
                "supporting_block_ids": ["ib-001"],
                "direction_on_source": "supports",
            }
        ],
        "arena_candidates": [
            {
                "candidate_id": "ac-001",
                "tentative_slug": ARENA_SLUG,
                "name": "测试赛道",
                "parent_industry_slug": INDUSTRY_SLUG,
                "battleground_focus": "测试用的赛道焦点描述，围绕核心竞争要素展开。",
            }
        ],
        "company_candidates": [],
        "synthesis": {},
    }


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_endgame_pipeline_skeleton_e2e(tmp_path: Path) -> None:
    bundle = _mock_bundle()
    bundle_path = tmp_path / "bundle.json"
    _write_json(bundle_path, bundle)

    # ── Step 4: arena autobuild (bootstrap_arena_from_candidate) ──────────────
    arena_candidate = bundle["arena_candidates"][0]
    agg.bootstrap_arena_from_candidate(arena_candidate, base=tmp_path)
    arena_dir = tmp_path / "arenas" / ARENA_SLUG
    assert arena_dir.exists(), "arena dir should be created"
    # Seed the participants narrative stub so narrative_propose can read an excerpt
    (arena_dir / "participants.md").write_text(
        "# participants\n\n", encoding="utf-8"
    )

    # ── Step 5: industry autobuild ─────────────────────────────────────────────
    result_ind = agg.ensure_industry_exists(
        slug=INDUSTRY_SLUG, name="测试行业", base=tmp_path
    )
    assert result_ind["autobuilt"] is True
    assert (tmp_path / "industries" / INDUSTRY_SLUG).exists()

    # ── Step 6: company autobuild (no company claim in this test, quick smoke) ─
    result_co = agg.ensure_company_exists(
        ticker="TEST001", market="SSE", name="测试公司",
        industry_slugs=[INDUSTRY_SLUG], base=tmp_path,
    )
    assert result_co["autobuilt"] is True

    # ── Step 7: ingest_match (writes pending_review file) ─────────────────────
    match_path = tmp_path / "pending" / f"match-{SOURCE_ID}.json"
    rc = ingest_match.cmd_match(
        Namespace(
            bundle=str(bundle_path),
            registry_base=str(tmp_path),
            out=None,
            auto_out=None,
            pending_out=str(match_path),
        )
    )
    assert rc == 0, "ingest_match should succeed"
    assert match_path.exists(), "match file should be written"

    # ── Step 8 sim: set decisions on pending file ─────────────────────────────
    match_data = json.loads(match_path.read_text(encoding="utf-8"))
    for row in match_data["decisions_required"]:
        row["decision"] = "new"
        row["decision_reason"] = "形成新命题"
    _write_json(match_path, match_data)

    # ── Step 9: ingest_apply ──────────────────────────────────────────────────
    applied_path = tmp_path / "applied.jsonl"
    rc = ingest_apply.cmd_apply(
        Namespace(
            bundle=str(bundle_path),
            registry_base=str(tmp_path),
            match=str(match_path),
            decisions=None,
            applied_out=str(applied_path),
        )
    )
    assert rc == 0, "ingest_apply should succeed"

    # Verify ClaimRegistry has the claim under the right scope
    registry = ClaimRegistry(tmp_path)
    arena_claims = registry.claims_for_scope("arena", ARENA_SLUG)
    assert len(arena_claims) == 1, "one arena claim should exist"
    claim = arena_claims[0]
    assert claim["claim_text"] == "测试赛道竞争格局正在快速集中"
    assert claim["status"] == "active"
    claim_id = claim["claim_id"]

    # Verify applied.jsonl rows
    assert applied_path.exists(), "applied.jsonl should exist"
    applied_rows = [
        json.loads(line)
        for line in applied_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(applied_rows) == 1
    assert applied_rows[0]["candidate_id"] == "cc-001"
    assert applied_rows[0]["action"] == "new"
    assert applied_rows[0]["scope_type"] == "arena"
    assert applied_rows[0]["scope_ref"] == ARENA_SLUG

    # ── Step 10: narrative_propose ────────────────────────────────────────────
    proposals_path = tmp_path / "data" / "pending" / f"narrative-proposals-{SOURCE_ID}.json"
    rc = narrative_propose.cmd_propose(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            source_id=SOURCE_ID,
            scope="arena",
            ref=ARENA_SLUG,
            arena=None,
            out=str(proposals_path),
        )
    )
    assert rc == 0, "narrative_propose should succeed"
    assert proposals_path.exists(), "proposals file should be written"

    proposals_data = json.loads(proposals_path.read_text(encoding="utf-8"))
    assert proposals_data["source_id"] == SOURCE_ID
    assert len(proposals_data["proposals"]) >= 1

    # ── Step 11 sim: approve all proposals, fill body ─────────────────────────
    for proposal in proposals_data["proposals"]:
        proposal["decision"] = "approve"
        proposal["decision_reason"] = "claim 支撑明确，内容合理"
        if not proposal.get("body"):
            proposal["body"] = f"测试叙事内容：{proposal.get('dimension', '未知维度')}分析。"
        # ensure supported_by_claims is present (required for apply validation)
        if not proposal.get("supported_by_claims"):
            proposal["supported_by_claims"] = [claim_id]
    _write_json(proposals_path, proposals_data)

    # ── Step 12: figure_contexts (quick smoke for company) ────────────────────
    contexts = [{"page": 1, "kind": "figure", "caption": "图1", "nearby_text": "测试图表"}]
    source_meta = {"source_id": SOURCE_ID, "source_title": "测试报告", "source_date": "2026-04-15"}
    n = agg.write_figure_contexts_for_company("SSE_TEST001", contexts, source_meta, base=tmp_path)
    assert n == 1

    # ── Step 13: narrative_apply ──────────────────────────────────────────────
    rc = narrative_apply.cmd_apply(
        Namespace(
            proposals=str(proposals_path),
            registry_base=str(tmp_path),
            base=str(tmp_path),
        )
    )
    assert rc == 0, "narrative_apply should succeed"

    # Verify archive: the proposal should be moved to archive
    archive_path = tmp_path / "data" / "pending" / "archive" / proposals_path.name
    assert archive_path.exists(), "proposals should be archived after apply"

    # Verify at least one dimension narrative file was updated
    first_proposal = proposals_data["proposals"][0]
    narrative_md = arena_dir / f"{first_proposal['dimension'].replace('_', '-')}.md"
    assert narrative_md.exists(), f"narrative md {narrative_md} should exist"
    narrative_text = narrative_md.read_text(encoding="utf-8")
    assert first_proposal["body"] in narrative_text, "approved body should appear in narrative"

    # ── Step 13b: narrative_flags ─────────────────────────────────────────────
    rc = narrative_flags.cmd_flags(
        Namespace(
            registry_base=str(tmp_path),
            base=str(tmp_path),
            scope="arena",
            ref=ARENA_SLUG,
            arena=None,
        )
    )
    assert rc == 0, "narrative_flags should succeed"

    # ── Step 14: bundle persist + registry ───────────────────────────────────
    source_file = tmp_path / "arenas" / ARENA_SLUG / "sources" / "test-report.pdf"
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(b"%PDF-1.4 mock")

    entry = persist_bundle(
        bundle,
        source_file_path=source_file,
        touched={"industries": [INDUSTRY_SLUG], "arenas": [ARENA_SLUG], "companies": []},
        base=tmp_path,
    )

    # Verify bundle registry
    registry_path = tmp_path / "data" / "bundle_registry.jsonl"
    assert registry_path.exists(), "bundle_registry.jsonl should exist"
    registry_entry = get_bundle(SOURCE_ID, base=tmp_path)
    assert registry_entry is not None, "bundle registry entry should exist"
    assert registry_entry["source_id"] == SOURCE_ID
    assert registry_entry["source_type"] == "industry_report"

    # Verify persisted bundle JSON exists on disk
    bundle_json_path = tmp_path / entry["bundle_path"]
    assert bundle_json_path.exists(), "persisted bundle JSON should exist"
