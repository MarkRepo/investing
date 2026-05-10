#!/usr/bin/env python3
"""Build Company Dashboard — multi-source opinion aggregation for a single company.

Usage:
    .venv/bin/python -m scripts.build_company_dashboard --ticker SSE_688122
    .venv/bin/python -m scripts.build_company_dashboard --ticker SSE_688122 --out companies/SSE_688122/dashboard.md

Reads all claims for the given ticker from claims/companies.jsonl, cross-references
with bundle_registry.jsonl for source metadata, and produces a dashboard.md with
opinion matrix, timeline, consensus/divergence, and verification questions.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.io.claim_registry import ClaimRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_institution(source_id: str) -> str:
    """Extract institution name from source_id patterns."""
    # Patterns: 行研-{institution}-{date}-{sha8}, 年报-{year}-{sha8}, etc.
    parts = source_id.split("-")
    if len(parts) >= 2 and parts[0] in ("行研", "券商点评", "研报"):
        return parts[1]
    return parts[0] if parts else ""


def _short_date(iso_date: str) -> str:
    if not iso_date:
        return ""
    return iso_date[:10]


def _load_bundle_sources(base: Path) -> dict[str, dict]:
    """Load bundle_registry.jsonl → {source_id: {institution, publish_date, ...}}."""
    path = base / "data" / "bundle_registry.jsonl"
    if not path.exists():
        return {}
    sources: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        entry = json.loads(line)
        sid = entry.get("source_id", "")
        if sid:
            sources[sid] = entry
    return sources


def build_dashboard(ticker: str, market: str, base: Path) -> dict:
    """Collect all data needed for the dashboard."""
    registry = ClaimRegistry(base)
    scope_ref = f"{market}_{ticker}"
    claims = registry.claims_for_scope("company", scope_ref)
    sources = _load_bundle_sources(base)

    # Read company meta
    meta_path = base / "companies" / scope_ref / "meta.md"
    company_name = scope_ref
    if meta_path.exists():
        content = meta_path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line.startswith("name:"):
                company_name = line.split(":", 1)[1].strip()
                break

    # Group claims by dimension_hint
    by_dimension: dict[str, list[dict]] = {}
    for c in claims:
        dim = c.get("dimension_hint", "unknown")
        by_dimension.setdefault(dim, []).append(c)

    # Build timeline from claims
    timeline: list[dict] = []
    seen_sources: set[str] = set()
    for c in sorted(claims, key=lambda x: x.get("as_of", "")):
        for ev in c.get("supporting_evidence", []):
            sid = ev.get("source_id", "")
            if sid and sid not in seen_sources:
                seen_sources.add(sid)
                src = sources.get(sid, {})
                timeline.append({
                    "date": c.get("as_of", ""),
                    "source_id": sid,
                    "institution": _parse_institution(sid),
                    "direction": ev.get("direction", "neutral"),
                })

    # Detect consensus/divergence
    # Consensus: claims where at least 2 sources agree (same dimension + direction)
    # Divergence: opposing directions on same dimension
    direction_by_dim: dict[str, dict[str, list[str]]] = {}
    for c in claims:
        dim = c.get("dimension_hint", "unknown")
        direction = "neutral"
        for ev in c.get("supporting_evidence", []):
            if ev.get("direction") in ("supports", "refutes"):
                direction = ev["direction"]
        direction_by_dim.setdefault(dim, {}).setdefault(direction, []).append(c["claim_text"])

    consensus: list[str] = []
    divergence: list[dict] = []
    for dim, dirs in direction_by_dim.items():
        if "supports" in dirs and "refutes" in dirs:
            divergence.append({
                "dimension": dim,
                "supports": dirs["supports"],
                "refutes": dirs["refutes"],
            })
        elif len(dirs.get("supports", [])) >= 2:
            consensus.append(f"{dim}: {dirs['supports'][0][:80]}...")

    # Collect verification questions from related bundles
    verification_questions: list[dict] = []
    touched_bundles: set[str] = set()
    for c in claims:
        for ev in c.get("supporting_evidence", []):
            sid = ev.get("source_id", "")
            if sid and sid not in touched_bundles:
                touched_bundles.add(sid)
                src = sources.get(sid, {})
                bundle_path_str = src.get("bundle_path", "")
                if bundle_path_str:
                    bundle_path = base / bundle_path_str
                    if bundle_path.exists():
                        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
                        for cc in bundle.get("company_candidates", []) or []:
                            if cc.get("ticker") == ticker and cc.get("market") == market:
                                for q in cc.get("verification_questions", []):
                                    verification_questions.append({
                                        "source_id": sid,
                                        "question": q,
                                    })

    return {
        "ticker": ticker,
        "market": market,
        "company_name": company_name,
        "scope_ref": scope_ref,
        "source_count": len(seen_sources),
        "claim_count": len(claims),
        "last_rebuilt": _now(),
        "claims": claims,
        "by_dimension": by_dimension,
        "timeline": sorted(timeline, key=lambda x: x["date"]),
        "consensus": consensus,
        "divergence": divergence,
        "verification_questions": verification_questions,
        "sources": sources,
    }


def _dimension_label(dim: str) -> str:
    labels = {
        "market_size": "市场规模",
        "lifecycle": "生命周期",
        "value_chain": "产业链",
        "competition": "竞争格局",
        "drivers": "驱动因素",
        "technology": "技术路线",
        "regulation": "政策监管",
        "benchmark": "对标",
        "risks": "风险",
        "valuation": "估值",
        "financial_profile": "财务画像",
        "catalysts": "催化剂",
    }
    return labels.get(dim, dim)


def render_dashboard(data: dict) -> str:
    lines: list[str] = []

    lines.append("---")
    lines.append(f"ticker: {data['ticker']}")
    lines.append(f"market: {data['market']}")
    lines.append(f"company: {data['company_name']}")
    lines.append(f"last_rebuilt: {_short_date(data['last_rebuilt'])}")
    lines.append(f"source_count: {data['source_count']}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {data['company_name']}（{data['market']} {data['ticker']}） — 多源观点面板")
    lines.append("")

    # Opinion matrix
    lines.append("## 观点矩阵（按维度分组）")
    lines.append("")
    for dim in sorted(data["by_dimension"]):
        dim_claims = data["by_dimension"][dim]
        lines.append(f"### {_dimension_label(dim)}")
        lines.append("")
        lines.append("| source | as_of | claim | direction | confidence |")
        lines.append("|---|---|---|---|---|")
        for c in dim_claims:
            for ev in c.get("supporting_evidence", []):
                sid = ev.get("source_id", "")
                institution = _parse_institution(sid)
                date = _short_date(c.get("as_of", ""))
                text = c["claim_text"][:80]
                direction = ev.get("direction", "neutral")
                conf = c.get("confidence", "medium")
                lines.append(f"| {institution}-{date} | {date} | {text} | {direction} | {conf} |")
        lines.append("")
    lines.append("")

    # Timeline
    lines.append("## 时间线")
    lines.append("")
    for entry in data["timeline"]:
        date = entry["date"][:10]
        inst = entry["institution"]
        direction = entry["direction"]
        lines.append(f"- {date} : {inst}（{direction}）")
    lines.append("")

    # Consensus and Divergence
    lines.append("## 共识与分歧")
    lines.append("")

    if data["consensus"]:
        lines.append("### 共识")
        for item in data["consensus"]:
            lines.append(f"- {item}")
        lines.append("")
    else:
        lines.append("### 共识")
        if data["source_count"] <= 1:
            lines.append("- 单一来源，未形成交叉验证。")
        else:
            lines.append("- 当前未检测到多源一致的 claim。")
        lines.append("")

    if data["divergence"]:
        lines.append("### 分歧")
        for div in data["divergence"]:
            lines.append(f"- **{_dimension_label(div['dimension'])}**：")
            for s in div["supports"]:
                lines.append(f"  - 看多：{s[:100]}")
            for r in div["refutes"]:
                lines.append(f"  - 看空：{r[:100]}")
        lines.append("")
    else:
        lines.append("### 分歧")
        lines.append("- 当前未检测到明确的方向分歧。")
        lines.append("")

    # Verification questions
    lines.append("## 尚待验证")
    lines.append("")
    if data["verification_questions"]:
        for vq in data["verification_questions"]:
            lines.append(f"- [{vq['source_id']}] {vq['question']}")
    else:
        lines.append("- （无）")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Dashboard generated at {_short_date(data['last_rebuilt'])} from {data['claim_count']} claims across {data['source_count']} sources.*")
    lines.append("")

    return "\n".join(lines)


def cmd_build(args: argparse.Namespace) -> int:
    base = Path(args.base)
    market = args.market
    ticker = args.ticker
    scope_ref = f"{market}_{ticker}"

    # Verify company exists
    company_dir = base / "companies" / scope_ref
    if not company_dir.exists():
        print(f"Error: company {scope_ref} does not exist under companies/", file=sys.stderr)
        return 1

    data = build_dashboard(ticker, market, base)
    md = render_dashboard(data)

    out = Path(args.out) if args.out else company_dir / "dashboard.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md, encoding="utf-8")
    print(f"Dashboard written to {out}")
    print(f"  Claims: {data['claim_count']} across {data['source_count']} sources")
    print(f"  Consensus items: {len(data['consensus'])}")
    print(f"  Divergence items: {len(data['divergence'])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build_company_dashboard")
    parser.add_argument("--ticker", required=True, help="Company ticker (e.g. 688122)")
    parser.add_argument("--market", default="SSE", help="Market: SSE, SZSE, BSE, HK, US")
    parser.add_argument("--base", default=".", help="Project root")
    parser.add_argument("--out", help="Output path (default: companies/{MARKET_TICKER}/dashboard.md)")
    args = parser.parse_args(argv)
    return cmd_build(args)


if __name__ == "__main__":
    raise SystemExit(main())
