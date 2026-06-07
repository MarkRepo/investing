"""Regression: macro topic 的 m_regime_read 必须在 web 产出表里可见。

m_regime_read 是 macro type 的决策链 case 文件（见 topic._DECISION_CHAIN_OUTPUTS）。
list_outputs 用 _OUTPUT_KEYS_LABELS 白名单过滤 outputs_state——若 m_regime_read 不在
白名单，即便磁盘有 .md、outputs_state 标 fresh，detail 页也永远不显示它。

同时 sidecar transmission_map（.yaml）必须保持被排除（无独立 md 视图）。
"""
import shutil
import tempfile
from pathlib import Path

import pytest

from prism.scripts import topic as topic_io
from prism.scripts import outputs

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"


@pytest.fixture
def macro_env(monkeypatch):
    tmpdir = Path(tempfile.mkdtemp())
    # topic.py 用 PRISM_ROOT；outputs.py 用 _PRISM_ROOT（带下划线前缀）
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.outputs._PRISM_ROOT", tmpdir)
    (tmpdir / "topics").mkdir()

    topic_io.create_topic(
        slug=SLUG,
        display_name="宏观层",
        topic_type="macro",
        question="Q",
        geo="GLOBAL",
        depth="deep",
        variant=VARIANT,
        search_terms=["利率"],
    )

    out_dir = tmpdir / "topics" / SLUG / VARIANT / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "00_primer.md").write_text("# primer\n\nbody\n", encoding="utf-8")
    (out_dir / "m_regime_read.md").write_text("# regime read\n\nbody\n", encoding="utf-8")

    topic_io.set_output_status(SLUG, "00_primer", "fresh", VARIANT, version=1)
    topic_io.set_output_status(SLUG, "m_regime_read", "fresh", VARIANT, version=1)

    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


def test_m_regime_read_is_listed_and_exists(macro_env):
    items = outputs.list_outputs(SLUG, VARIANT)
    by_key = {it["key"]: it for it in items}

    # m_regime_read 必须可见且文件存在
    assert "m_regime_read" in by_key, f"m_regime_read 未列出: {sorted(by_key)}"
    assert by_key["m_regime_read"]["file_exists"] is True

    # sanity: 00_primer 也在
    assert "00_primer" in by_key
    assert by_key["00_primer"]["file_exists"] is True

    # sidecar transmission_map 必须不列入
    assert "transmission_map" not in by_key
