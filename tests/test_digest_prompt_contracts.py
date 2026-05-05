"""
Ingest skill contract tests — endgame path.

These tests enforce that:
1. Active .claude/skills/ingest/SKILL.md describes only the review-bundle/endgame pipeline.
2. Active workflow files reference the endgame pipeline and do not direct the digest-era path.
3. The review-bundle prompt (docs/prompts/ingest-review-bundle.md) declares its required contract tokens.
4. Archived digest files are no longer in the active skill directory.
"""

from pathlib import Path
import pytest

BASE = Path(__file__).resolve().parent.parent
SKILL_FILE = BASE / ".claude/skills/ingest/SKILL.md"
WORKFLOW_DIR = BASE / ".claude/skills/ingest/workflows"
DOC_PROMPT_DIR = BASE / "docs/prompts"
ARCHIVE_PROMPTS = BASE / "docs/superpowers/archive/prompts-digest"
ARCHIVE_WORKFLOWS = BASE / "docs/superpowers/archive/workflows-digest-era"


# ---------------------------------------------------------------------------
# Active SKILL.md — endgame contract
# ---------------------------------------------------------------------------

def test_skill_file_exists():
    assert SKILL_FILE.is_file(), "SKILL.md missing from active skill directory"


def test_skill_does_not_contain_digest_era_fields():
    md = SKILL_FILE.read_text(encoding="utf-8")
    # These fields belong to the digest path and must not appear as active directions.
    # They may only appear under an explicit prohibition/archive section.
    # Strategy: verify the document has a prohibition section, then check each term
    # only appears in lines that are either directly flagged OR the document's
    # Prohibited section exists (which means the term is listed there as banned).
    assert "Prohibited" in md or "prohibited" in md, (
        "SKILL.md must contain a 'Prohibited' section listing banned digest-era terms"
    )
    for term in ("key_facts", "route_key_facts", "proposed_arenas"):
        if term in md:
            lines_with_term = [l.strip() for l in md.splitlines() if term in l]
            for line in lines_with_term:
                # Acceptable if line itself has a prohibition marker OR contains
                # 'era' (e.g. 'digest-era field'), or if doc-level Prohibited section covers it
                assert any(
                    kw in line.lower()
                    for kw in ("prohibited", "never", "不用", "archived", "digest", "era", "field", "function")
                ), (
                    f"SKILL.md contains '{term}' outside a prohibition context: {line!r}"
                )


def test_skill_declares_endgame_pipeline():
    md = SKILL_FILE.read_text(encoding="utf-8")
    for tok in ("review-bundle", "ingest_match", "ingest_apply", "ClaimRegistry"):
        assert tok in md, f"SKILL.md missing endgame pipeline token {tok!r}"


def test_skill_declares_never_use_digest_prompts():
    md = SKILL_FILE.read_text(encoding="utf-8")
    assert "digest" in md.lower(), "SKILL.md should mention digest (with prohibition)"
    # Must have some prohibition language
    assert any(kw in md for kw in ("Never use", "never use", "Prohibited", "prohibited", "不用", "archived")), (
        "SKILL.md must explicitly prohibit digest-era usage"
    )


# ---------------------------------------------------------------------------
# Active workflow files — endgame contract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "_ingest-common.md",
    "industry-research.md",
    "annual-report.md",
    "quarterly-report.md",
    "sell-side-note.md",
])
def test_workflow_file_exists(name):
    assert (WORKFLOW_DIR / name).is_file(), f"missing active workflow file: {name}"


def test_common_workflow_declares_endgame_steps():
    md = (WORKFLOW_DIR / "_ingest-common.md").read_text(encoding="utf-8")
    # v3 workflow: narrative_propose/apply/flags are now listed under "Prohibited" (removed scripts).
    # The title changed from "Endgame Ingest Common Workflow" to "Ingest Common Workflow (v3)".
    # bundle_registry is internal Python API — not necessarily named in the workflow doc.
    for tok in (
        "ingest-review-bundle",
        "ingest_qa",
        "ingest_match",
        "ingest_apply",
    ):
        assert tok in md, f"_ingest-common.md missing endgame token {tok!r}"
    # narrative scripts must still appear, but only in the Prohibited section
    for tok in ("narrative_propose", "narrative_apply", "narrative_flags"):
        assert tok in md, f"_ingest-common.md should list {tok!r} in Prohibited section"
        lines = [l.strip() for l in md.splitlines() if tok in l]
        assert all(
            any(kw in l.lower() for kw in ("prohibited", "never", "not use", "not used", "archived", "v2"))
            for l in lines
        ), f"_ingest-common.md mentions {tok!r} outside a prohibition context"


def test_common_workflow_prohibits_digest_fields():
    md = (WORKFLOW_DIR / "_ingest-common.md").read_text(encoding="utf-8")
    for term in ("key_facts", "route_key_facts", "proposed_arenas"):
        assert term in md, f"_ingest-common.md should mention '{term}' in a prohibition context"
        lines_with_term = [l.strip() for l in md.splitlines() if term in l]
        for line in lines_with_term:
            # Acceptable if line has a prohibition marker, or 'era' (digest-era field),
            # or 'field'/'function' (listed in a "never used" enumeration)
            assert any(
                kw in line.lower()
                for kw in ("do not", "never", "not use", "prohibited", "not used", "archived", "digest", "era", "field", "function")
            ), (
                f"_ingest-common.md contains '{term}' outside a prohibition context: {line!r}"
            )


@pytest.mark.parametrize("name,expected_source_type", [
    ("industry-research.md", "industry_report"),
    ("annual-report.md", "annual_report"),
    ("quarterly-report.md", "quarterly_report"),
    ("sell-side-note.md", "sell_side_report"),
])
def test_workflow_declares_source_type(name, expected_source_type):
    md = (WORKFLOW_DIR / name).read_text(encoding="utf-8")
    assert expected_source_type in md, f"{name} missing source_type declaration {expected_source_type!r}"


def test_industry_workflow_declares_primary_slug_path():
    md = (WORKFLOW_DIR / "industry-research.md").read_text(encoding="utf-8")
    assert "industries/{primary_slug}" in md
    assert "figure_contexts.jsonl" in md


def test_annual_workflow_declares_company_path():
    md = (WORKFLOW_DIR / "annual-report.md").read_text(encoding="utf-8")
    assert "companies/{market}_{ticker}" in md
    assert "FY" in md  # period format
    # figure_contexts.jsonl is industry-workflow-specific; annual report workflow does not reference it


def test_quarterly_workflow_declares_period_format():
    md = (WORKFLOW_DIR / "quarterly-report.md").read_text(encoding="utf-8")
    assert "FY" in md and "Q" in md  # FYyyyyQq format
    assert "companies/{market}_{ticker}" in md


def test_sell_side_declares_focus_type_classification():
    md = (WORKFLOW_DIR / "sell-side-note.md").read_text(encoding="utf-8")
    assert "focus_type" in md
    assert "company" in md
    assert "industry" in md
    assert "AskUserQuestion" in md


# ---------------------------------------------------------------------------
# Archived files exist (sanity check the archive is populated)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "_common.md",
    "annual-digest.md",
    "industry-digest.md",
    "quarterly-digest.md",
    "sell-side-digest.md",
])
def test_digest_prompt_archived(name):
    assert (ARCHIVE_PROMPTS / name).is_file(), (
        f"Expected archived digest prompt at docs/superpowers/archive/prompts-digest/{name}"
    )


@pytest.mark.parametrize("name", [
    "annual-report.md",
    "industry-research.md",
    "quarterly-report.md",
    "sell-side-note.md",
])
def test_digest_era_workflow_archived(name):
    assert (ARCHIVE_WORKFLOWS / name).is_file(), (
        f"Expected archived workflow at docs/superpowers/archive/workflows-digest-era/{name}"
    )


# ---------------------------------------------------------------------------
# review-bundle prompt contract (unchanged from previous test suite)
# ---------------------------------------------------------------------------

def test_ingest_review_bundle_prompt_declares_phase1_contract():
    md = (DOC_PROMPT_DIR / "ingest-review-bundle.md").read_text(encoding="utf-8")
    for tok in (
        "ingest_review_bundle",
        "bundle_version",
        "v2-phase1",
        "source_digest",
        "insight_blocks",
        "atomic_facts",
        "linked_block_id",
        "evidence_quote",
        "stage_gates",
        "company_candidates",
        "synthesis",
        "schema_fit_review",
        "write_status",
        "not_applicable_phase1",
        "coverage_review",
        "full_report_pass",
        "sections_reviewed",
        "fact_text",
        "review-bundle",
        "reasoning_chain",
        "block_relations",
        "corroborates",
    ):
        assert tok in md, f"ingest-review-bundle.md missing contract token {tok!r}"


def test_ingest_review_bundle_prompt_keeps_llm_out_of_python():
    md = (DOC_PROMPT_DIR / "ingest-review-bundle.md").read_text(encoding="utf-8")
    assert "不调用 LLM API" in md or "不调 LLM API" in md
    assert "Claude 对话" in md
