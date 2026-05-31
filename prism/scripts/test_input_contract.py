"""Tests for Stage 1 scaffolding: input_contract, set_decomposition, findings rings."""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import input_contract as ic
from prism.scripts import topic as topic_io
from prism.scripts import outputs as outputs_io
from prism.scripts import findings as findings_io
from prism.scripts.manifest import add_material, create_manifest, list_by_ring


# ─────────────────────────── input_contract ───────────────────────────

def test_contract_completeness():
    """每 type 合同非空、code 唯一、ring 合法、served_by 可分类。"""
    for t in ("company", "industry", "arena"):
        items = ic.required_inputs(t)
        assert items, f"{t} empty contract"
        codes = [i["code"] for i in items]
        assert len(codes) == len(set(codes)), f"{t} duplicate codes"
        assert ic.ring_codes(t) == set(codes)
        for it in items:
            assert it["ring"] in (1, 2, 3, 4, 5, 6), it
            assert it["label"]
            assert it["served_by"], it
            # 每项至少能被一类源满足
            assert ic.is_material_served(it) or ic.is_api_served(it), it


def test_contract_hard_undersupplies():
    """三项真·欠供齐全（plan 认定）。"""
    assert ic.hard_undersupply_codes("company") == {
        "mgmt-capital-alloc", "consensus", "historical-mirror"}
    assert "industry-mirror" in ic.hard_undersupply_codes("industry")
    assert "arena-mirror" in ic.hard_undersupply_codes("arena")


def test_contract_unknown_type():
    assert ic.required_inputs("nonsense") == []
    assert ic.ring_codes("nonsense") == set()
    assert ic.get_item("company", "biz-moat-unit-econ") is not None
    assert ic.get_item("company", "nope") is None


# ─────────────────────────── fixture ───────────────────────────

@pytest.fixture
def tmp_topic(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    slug, variant = "test-decomp", "test"
    (tmpdir / "topics" / slug / variant).mkdir(parents=True)
    topic_io.create_topic(
        slug=slug, display_name="T", topic_type="company",
        question="Q?", geo="US", depth="quick", variant=variant,
        short_name="T", ticker="US_T",
    )
    create_manifest(slug, variant)
    yield slug, variant, tmpdir
    shutil.rmtree(tmpdir)


# ─────────────────────────── set_decomposition ───────────────────────────

def test_read_topic_decomposition_default(tmp_topic):
    slug, variant, _ = tmp_topic
    data = topic_io.read_topic(slug, variant)
    assert data["decomposition"] == {
        "current_version": None, "last_updated": None, "history": []}


def test_set_decomposition_versioning(tmp_topic):
    slug, variant, tmpdir = tmp_topic
    topic_io.set_decomposition(slug, variant, version=0, summary="命门1=良率",
                               stage_set_at="00-research-pending")
    topic_io.set_decomposition(slug, variant, version=1, summary="命门1=良率;命门2=认证",
                               stage_set_at="04-synthesizing",
                               convergence_status="converged",
                               changelog="added 命门2 (车厂认证), 证据=findings mat-x")
    data = topic_io.read_topic(slug, variant)
    decomp = data["decomposition"]
    assert decomp["current_version"] == 1
    assert len(decomp["history"]) == 2
    assert decomp["history"][0]["version"] == 0
    assert decomp["history"][1]["convergence_status"] == "converged"
    assert "changelog" in decomp["history"][1]
    assert decomp["last_updated"] is not None


def test_set_decomposition_bad_status(tmp_topic):
    slug, variant, _ = tmp_topic
    with pytest.raises(ValueError):
        topic_io.set_decomposition(slug, variant, version=0, summary="x",
                                   stage_set_at="00", convergence_status="bogus")


def test_list_decomposition_files(tmp_topic):
    slug, variant, tmpdir = tmp_topic
    base = tmpdir / "topics" / slug / variant
    assert outputs_io.list_decomposition_files(slug, variant) == []
    (base / "decomposition_v0.md").write_text("v0", encoding="utf-8")
    (base / "decomposition_v1.md").write_text("v1", encoding="utf-8")
    assert outputs_io.list_decomposition_files(slug, variant) == [0, 1]
    # _relative_output_paths picks the latest
    paths = topic_io._relative_output_paths(slug, variant)
    assert paths.get("decomposition", "").endswith("decomposition_v1.md")


# ─────────────────────────── rings (manifest + findings) ───────────────────────────

def test_add_material_rings_and_list_by_ring(tmp_topic):
    slug, variant, _ = tmp_topic
    add_material(slug=slug, filename="r1.md", source_type="annual-report",
                 variant=variant, rings=["mgmt-capital-alloc", "financial-arc"])
    # dedup-merge: re-add same filename with a new ring → union
    add_material(slug=slug, filename="r1.md", source_type="annual-report",
                 variant=variant, rings=["biz-moat-unit-econ"])
    hits = list_by_ring(slug, variant, "mgmt-capital-alloc")
    assert len(hits) == 1
    assert set(hits[0]["rings"]) == {
        "mgmt-capital-alloc", "financial-arc", "biz-moat-unit-econ"}
    assert list_by_ring(slug, variant, "consensus") == []


def test_findings_inherit_rings_from_manifest(tmp_topic):
    slug, variant, tmpdir = tmp_topic
    mat_id = add_material(slug=slug, filename="r1.md", source_type="sell-side-note",
                          variant=variant, rings=["consensus"])
    # finding file WITHOUT rings frontmatter → inherits from manifest
    out_dir = tmpdir / "topics" / slug / variant / "outputs"
    (out_dir / f"findings_{mat_id}.md").write_text(
        "- 一致预期 EPS 2026 = 3.2\n", encoding="utf-8")
    items = findings_io.list_all_findings(slug, variant)
    assert len(items) == 1
    assert items[0]["rings"] == ["consensus"]
    # index renders rings
    idx = findings_io.build_findings_index(slug, variant, write=False)
    assert "rings=[consensus]" in idx


def test_default_report_rings_type_aware():
    """F10：报告默认 rings 按 topic.type 映射；company 行为字节不变。"""
    # industry / arena 用各自合同 code
    assert ic.default_report_rings("annual", "industry") == [
        "industry-financial-arc", "value-chain-profit-pool"]
    assert ic.default_report_rings("announcement", "industry") == ["industry-financial-arc"]
    assert ic.default_report_rings("annual", "arena") == [
        "peer-comparison-financials", "peer-valuation-anchor"]
    # company（默认/兜底）不变——回归护栏
    assert ic.default_report_rings("annual", "company") == [
        "financial-arc", "mgmt-capital-alloc", "biz-moat-unit-econ"]
    assert ic.default_report_rings("annual") == [
        "financial-arc", "mgmt-capital-alloc", "biz-moat-unit-econ"]
    assert ic.default_report_rings("prospectus", "company") == [
        "biz-moat-unit-econ", "financial-arc", "mgmt-capital-alloc"]
    # 映射出的 code 必须落在各自合同内（与 gap A 轴闭合：F10 标对 + F15 数得到）
    assert set(ic.default_report_rings("annual", "industry")) <= ic.ring_codes("industry")
    assert set(ic.default_report_rings("annual", "arena")) <= ic.ring_codes("arena")
