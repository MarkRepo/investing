"""Tests for new endgame helper functions in scripts.ingest_aggregate."""
from __future__ import annotations

import json
from pathlib import Path

from scripts import ingest_aggregate as agg


def test_write_figure_contexts_for_company(tmp_path):
    contexts = [
        {
            "page": 3,
            "kind": "figure",
            "caption": "图1：收入结构",
            "nearby_text": "公司披露收入结构。",
        }
    ]
    source_meta = {"source_id": "annual-1", "source_title": "2025 年报"}
    n = agg.write_figure_contexts_for_company(
        "SSE_603011", contexts, source_meta, base=tmp_path
    )
    assert n == 1
    out_file = tmp_path / "companies" / "SSE_603011" / "figure_contexts.jsonl"
    assert out_file.exists()
    rows = [json.loads(line) for line in out_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "annual-1"
    assert row["page"] == 3
    assert row["caption"] == "图1：收入结构"


def test_bootstrap_arena_from_candidate(tmp_path):
    candidate = {
        "tentative_slug": "cn-fusion-magnet-supply",
        "name": "中国聚变磁体供应竞争",
        "parent_industry_slug": "cn-nuclear-fusion",
        "battleground_focus": "围绕聚变装置磁体部件供应能力的竞争。",
    }
    agg.bootstrap_arena_from_candidate(candidate, base=tmp_path)
    definition_file = tmp_path / "arenas" / "cn-fusion-magnet-supply" / "definition.md"
    assert definition_file.exists()
    content = definition_file.read_text(encoding="utf-8")
    assert "中国聚变磁体供应竞争" in content
