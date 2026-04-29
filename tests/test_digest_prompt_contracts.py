from pathlib import Path
import pytest

PROMPT_DIR = Path(__file__).resolve().parent.parent / ".claude/skills/ingest/prompts/digest"
DOC_PROMPT_DIR = Path(__file__).resolve().parent.parent / "docs/prompts"


def _read(name: str) -> str:
    return (PROMPT_DIR / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", [
    "_common.md",
    "industry-digest.md",
    "annual-digest.md",
    "quarterly-digest.md",
    "sell-side-digest.md",
])
def test_prompt_file_exists_and_nonempty(name):
    assert (PROMPT_DIR / name).is_file(), f"missing {name}"
    assert len(_read(name).strip()) > 500, f"{name} too short"


def test_common_declares_schema_keys():
    md = _read("_common.md")
    # key schema tokens that MUST appear
    for tok in ("key_facts", "narratives", "proposed_arenas", "flags",
                "target_layer", "dimension_hint", "arena_refs",
                "evidence_quote", "figure_contexts", "known_arenas"):
        assert tok in md, f"_common.md missing schema token {tok!r}"


def test_common_declares_dimension_ref():
    md = _read("_common.md")
    assert "INDUSTRY_DIMENSIONS" in md or "dimension_ref" in md
    # all 11 industry dim keys should be textually present somewhere
    for dim in ("market_size", "lifecycle", "value_chain", "competition",
                "drivers", "technology", "regulation", "benchmark",
                "risks", "valuation"):
        assert dim in md, f"_common.md missing industry dim {dim}"


def test_industry_digest_declares_figure_context_priority():
    md = _read("industry-digest.md")
    assert "figure_contexts" in md
    assert "atomic observation" in md or "atomic" in md


def test_quarterly_digest_limits_narrative_dims():
    md = _read("quarterly-digest.md")
    assert "financial_profile" in md
    assert "catalysts" in md
    # Must state that other dims are not produced
    assert "不产出" in md or "不列 key" in md or "两维" in md


def test_sell_side_digest_declares_valuation_mandatory():
    md = _read("sell-side-digest.md")
    assert "valuation" in md
    assert "目标价" in md or "target_price" in md


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
