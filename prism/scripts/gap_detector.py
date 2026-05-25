"""Knowledge gap detector — zero LLM calls.

Reports (does NOT decide) which K# need more evidence, which web-search
materials are stale, and which claims have only training-knowledge basis.

LLM 自己看 report 决定继续搜还是停。
"""
from __future__ import annotations

from pathlib import Path

from prism.scripts import topic as topic_io
from prism.scripts.manifest import list_expired_web_search, read_manifest

PRISM_ROOT = Path(__file__).resolve().parent.parent


def _addr_key(addr: str) -> str:
    return addr.split("@", 1)[0] if isinstance(addr, str) else ""


def detect_gaps(
    slug: str,
    variant: str,
    min_evidence: int = 2,
) -> dict:
    """Detect knowledge gaps in a topic's research.

    Returns:
        {
            'topic': {slug, variant, thesis_version},
            'uncovered_ks':       [K#, ...],     # 0 evidence
            'thin_evidence':      [K#, ...],     # < min_evidence
            'evidence_count':     {K#: int},
            'expired_web_materials': [...],      # web-search > 90d
            'training_only_claims': [...],       # placeholder, requires baseline
        }
    """
    try:
        topic = topic_io.read_topic(slug, variant)
    except FileNotFoundError:
        return {"error": f"topic not found: {slug}/{variant}"}

    thesis_block = topic.get("thesis") or {}
    cur_v = thesis_block.get("current_version")

    ks: list[str] = []
    if cur_v is not None:
        try:
            from prism.scripts.outputs import extract_killer_questions
            ks = list(extract_killer_questions(slug, variant, cur_v))
        except Exception:
            ks = []

    try:
        manifest = read_manifest(slug, variant)
    except FileNotFoundError:
        manifest = {"materials": []}

    evidence_count: dict[str, int] = {k: 0 for k in ks}
    for m in manifest.get("materials") or []:
        addrs = m.get("addresses") or []
        seen_keys = {_addr_key(a) for a in addrs}
        for k in seen_keys:
            if k in evidence_count:
                evidence_count[k] += 1

    uncovered = [k for k in ks if evidence_count[k] == 0]
    thin = [k for k in ks if 0 < evidence_count[k] < min_evidence]

    expired = list_expired_web_search(slug, variant) if manifest.get("materials") else []

    training_only: list[str] = []

    return {
        "topic": {
            "slug": slug,
            "variant": variant,
            "thesis_version": cur_v,
        },
        "uncovered_ks": uncovered,
        "thin_evidence": thin,
        "evidence_count": evidence_count,
        "expired_web_materials": [
            {"id": m["id"], "filename": m["filename"],
             "expire_at": (m.get("search_meta") or {}).get("expire_at")}
            for m in expired
        ],
        "training_only_claims": training_only,
    }


def format_summary(report: dict) -> str:
    """Human-readable summary for 主 agent 在对话里展示给用户。"""
    if "error" in report:
        return f"⚠ {report['error']}"
    lines = []
    t = report["topic"]
    lines.append(
        f"📊 Gap report: {t['slug']}/{t['variant']} "
        f"(thesis_v{t['thesis_version']})"
    )
    if report["uncovered_ks"]:
        lines.append(
            f"  ❌ 0 evidence: {', '.join(report['uncovered_ks'])}"
        )
    if report["thin_evidence"]:
        ec = report["evidence_count"]
        thin_str = ", ".join(f"{k}({ec[k]})" for k in report["thin_evidence"])
        lines.append(f"  ⚠ thin: {thin_str}")
    if report["expired_web_materials"]:
        lines.append(
            f"  ⏰ expired web-search: {len(report['expired_web_materials'])} 条 (>90d)"
        )
    if not (report["uncovered_ks"] or report["thin_evidence"]
            or report["expired_web_materials"]):
        lines.append("  ✅ no gaps detected")
    return "\n".join(lines)
