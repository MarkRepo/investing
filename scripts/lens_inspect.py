"""CLI smoke test for investment lens fetcher.

Usage:
    .venv/bin/python -m scripts.lens_inspect --scope industry --ref cn-nuclear-fusion
    .venv/bin/python -m scripts.lens_inspect --scope arena --ref cn-fusion-divertor-material
    .venv/bin/python -m scripts.lens_inspect --scope company --ref SSE_600363
"""
from __future__ import annotations

import argparse

from app import config as cfg
from app.io.claim_registry import ClaimRegistry
from app.io.investment_lens import fetch_lens_material

SCOPE_DIMS = {
    "industry": cfg.INDUSTRY_INVESTMENT_VIEW_DIMS,
    "arena": cfg.ARENA_BATTLEFIELD_VIEW_DIMS,
    "company": cfg.COMPANY_MEMO_VIEW_DIMS,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect investment lens material for a scope/ref.")
    parser.add_argument("--scope", required=True, choices=["industry", "arena", "company"])
    parser.add_argument("--ref", required=True, help="slug or key (e.g. cn-nuclear-fusion, SSE_600363)")
    args = parser.parse_args()

    scope_type = args.scope
    scope_ref = args.ref
    dims = SCOPE_DIMS[scope_type]

    registry = ClaimRegistry(base=cfg.BASE_PATH / "data")

    print(f"\n=== Investment Lens: {scope_type}/{scope_ref} ===\n")

    for field in dims:
        mat = fetch_lens_material(
            scope_type,
            scope_ref,
            field,
            registry=registry,
            base=cfg.BASE_PATH,
        )
        print(f"[{scope_type}/{scope_ref}/{field}]")
        # Bundle excerpts
        n_be = len(mat.bundle_excerpts)
        first_be = ""
        if n_be > 0:
            txt = mat.bundle_excerpts[0].text
            first_be = f' (first: "{txt[:80]}{"..." if len(txt) > 80 else ""}")'
        print(f"  bundle_excerpts: {n_be}{first_be}")
        # Claims
        print(f"  claims: {len(mat.claims)}")
        # Narrative excerpts
        n_ne = len(mat.narrative_excerpts)
        ne_detail = ""
        if n_ne > 0:
            ne = mat.narrative_excerpts[0]
            ne_detail = f" ({ne.dimension}, {ne.headline_count} 段)"
        print(f"  narrative_excerpts: {n_ne}{ne_detail}")
        print()


if __name__ == "__main__":
    main()
