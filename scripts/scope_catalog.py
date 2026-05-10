"""Output all registered scopes as a JSON catalog for bundle extraction."""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent


def main() -> None:
    # Industries
    industries_dir = BASE / "industries"
    industries = sorted(
        p.name for p in industries_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ) if industries_dir.is_dir() else []

    # Arenas
    arenas_dir = BASE / "arenas"
    arenas = sorted(
        p.name for p in arenas_dir.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ) if arenas_dir.is_dir() else []

    # Companies — from app.io.company (covers all registered companies)
    try:
        from app.io import company as company_io
        companies = sorted(c["key"] for c in company_io.list_companies() if c.get("key"))
    except Exception:
        companies = []

    catalog = {
        "industries": industries,
        "arenas": arenas,
        "companies": companies,
    }

    json.dump(catalog, sys.stdout, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
