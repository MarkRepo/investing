"""Tests for industries/ facts layer IO."""
import pytest

from app.io import industry


def test_list_sectors_empty(tmp_path):
    sectors = industry.list_sectors(base=tmp_path)
    assert len(sectors) == 5
    assert all(s["present"] == {"landscape": False, "players": False, "competence-map": False} for s in sectors)
    assert {s["sector"] for s in sectors} == {"consumer", "saas", "cyclical", "bank", "biotech"}


def test_read_missing_returns_defaults(tmp_path):
    result = industry.read("consumer", "landscape", base=tmp_path)
    assert result["exists"] is False
    assert "## 供需" in result["body"]
    assert result["frontmatter"] == {}


def test_write_then_read_round_trip(tmp_path):
    industry.write(
        "consumer",
        "landscape",
        {"source_type": "annual_report_xref"},
        "## 供需\n白酒高端集中度上升。\n",
        base=tmp_path,
    )
    result = industry.read("consumer", "landscape", base=tmp_path)
    assert result["exists"] is True
    assert result["frontmatter"]["sector"] == "consumer"
    assert result["frontmatter"]["source_type"] == "annual_report_xref"
    assert "last_updated" in result["frontmatter"]
    assert "白酒高端集中度上升" in result["body"]


def test_list_sectors_reflects_presence(tmp_path):
    industry.write("saas", "players", {}, "| ticker | market | name |\n", base=tmp_path)
    sectors = {s["sector"]: s["present"] for s in industry.list_sectors(base=tmp_path)}
    assert sectors["saas"]["players"] is True
    assert sectors["saas"]["landscape"] is False
    assert sectors["consumer"]["players"] is False


def test_invalid_sector_rejected(tmp_path):
    with pytest.raises(ValueError, match="unknown sector"):
        industry.read("unknown_sector", "landscape", base=tmp_path)
    with pytest.raises(ValueError, match="unknown sector"):
        industry.write("foo", "landscape", {}, "body", base=tmp_path)


def test_invalid_kind_rejected(tmp_path):
    with pytest.raises(ValueError, match="kind must be one of"):
        industry.read("consumer", "bogus", base=tmp_path)
