"""Markdown I/O for V0 files and price-triggers.md."""
from pathlib import Path
from typing import List, Dict, Any
import yaml


def _parse_frontmatter(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter between leading '---' fences. Empty dict if absent."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    raw = text[3:end].strip()
    return yaml.safe_load(raw) or {}


def list_active_v0s(base_path: Path) -> List[Dict[str, Any]]:
    """Scan companies/*/v0.md, return entries with status=active.

    Fields returned per entry: ticker, market, status, last_reviewed,
    entry_date, position_size_pct, v0_path.
    """
    companies_dir = Path(base_path) / "companies"
    if not companies_dir.exists():
        return []

    out: List[Dict[str, Any]] = []
    for v0 in sorted(companies_dir.glob("*/v0.md")):
        fm = _parse_frontmatter(v0.read_text(encoding="utf-8"))
        if fm.get("status") != "active":
            continue
        out.append({
            "ticker": fm.get("ticker"),
            "market": fm.get("market"),
            "status": fm.get("status"),
            "last_reviewed": fm.get("last_reviewed"),
            "entry_date": fm.get("entry_date"),
            "position_size_pct": fm.get("position_size_pct", 0),
            "v0_path": str(v0),
        })
    return out
