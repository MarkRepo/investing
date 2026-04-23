from pathlib import Path
import sys
import importlib.util

# Load our custom _io module explicitly (avoiding the built-in _io module)
bin_path = Path(__file__).resolve().parent.parent / "bin"
spec = importlib.util.spec_from_file_location("custom_io", bin_path / "_io.py")
_io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_io)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_list_active_v0s_returns_only_active():
    result = _io.list_active_v0s(FIXTURES)
    tickers = [v["ticker"] for v in result]
    assert tickers == ["TEST"]


def test_list_active_v0s_has_required_fields():
    result = _io.list_active_v0s(FIXTURES)
    entry = result[0]
    assert entry["ticker"] == "TEST"
    assert entry["market"] == "US"
    assert entry["status"] == "active"
    assert str(entry["last_reviewed"]) == "2026-04-22"
    assert entry["v0_path"].endswith("companies/US_TEST/v0.md")
