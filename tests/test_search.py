from pathlib import Path

import pytest

from app.io import search


@pytest.fixture
def env(tmp_path, monkeypatch):
    from app import config as cfg
    monkeypatch.setattr(cfg, "BASE_PATH", tmp_path)
    (tmp_path / "companies" / "US_HIMS").mkdir(parents=True)
    (tmp_path / "companies" / "US_HIMS" / "meta.md").write_text(
        "---\nticker: HIMS\nindustry_primary: consumer\n---\n\n# HIMS\n白酒\n"
    )
    (tmp_path / "watchlist").mkdir()
    (tmp_path / "watchlist" / "researching.md").write_text("| started | ticker | gap_focus | target_finish |\n|-|-|-|-|\n| 2026-04-23 | HIMS | 白酒 | 2026-05-15 |\n")
    (tmp_path / "journal" / "decisions").mkdir(parents=True)
    (tmp_path / "journal" / "decisions" / "x.md").write_text("---\nticker: X\n---\n\n决策内容：白酒")
    return tmp_path


def test_search_finds_matches_across_scope(env):
    out = search.search("白酒", scope="all")
    paths = {r["path"] for r in out}
    assert any("meta.md" in p for p in paths)
    assert any("researching.md" in p for p in paths)
    assert any("x.md" in p for p in paths)


def test_search_scoped_companies(env):
    out = search.search("白酒", scope="companies")
    assert all("companies" in r["path"] for r in out)


def test_search_empty_pattern(env):
    assert search.search("", scope="all") == []


def test_search_misses(env):
    assert search.search("no-such-string-12345", scope="all") == []
