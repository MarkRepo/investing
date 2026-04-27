"""Ingest QA — 抽取异常告警 + 认知缺口清单。

不打分。两件事：
1. ``warn``：跑规则集 → 输出告警列表。让用户知道本次 ingest 出了哪些可疑抽取。
2. ``gap``：扫 company + arena 现状 → 输出缺口 markdown。让用户知道下次应 ingest 什么。

用法::

    python -m scripts.ingest_qa warn --merged /tmp/taihu-merged.json \\
        --preprocess /tmp/ingest-taihu.sections.json \\
        --arena cn-power-cable-polymer-material

    python -m scripts.ingest_qa gap --company BSE_920118
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

# --- 规则：抽取异常告警 -----------------------------------------------------

_UNCERTAINTY_WORDS = [
    "未提及", "未披露", "未明确", "未透露", "未给出", "未说明",
    "未涉及", "未讨论", "未提到", "未详细",
]

_BEAR_KEYWORDS = [
    "下降", "下跌", "下滑", "放缓", "收窄", "萎缩", "承压", "恶化",
    "回落", "走低", "减少", "流失", "不及预期", "失速", "降温", "回调",
    "亏损", "净流出",
]

_BULL_KEYWORDS = [
    "增长", "提升", "扩张", "改善", "提速", "突破", "超预期", "加速",
    "强劲", "创新高", "修复", "回暖", "抬升", "扩大", "回升", "净流入",
]


_PUNCT_RE = re.compile(
    r"["
    r"\s　"                       # whitespace + 全角空格
    r"，。、；：！？,\.;:!?"            # 标点
    r"\"'"                            # ascii quotes
    r"“”‘’"       # “ ” ‘ ’
    r"（）()\[\]【】《》〈〉"           # brackets
    r"—\-–—…"          # dashes + …
    r"·•・¨"                           # middle dots
    r"]+"
)


def _normalize(s: str) -> str:
    """Strip whitespace and common CJK punctuation for loose matching."""
    return _PUNCT_RE.sub("", s or "")


def _contains_any(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if kw in text]


def _token_set(s: str) -> set[str]:
    """Crude token set: 2-char sliding window on CJK + ascii word split."""
    s = re.sub(r"[\s　，。、；：！？,\.;:!?\"'\"\"''（）()\[\]【】—\-]+", " ", s)
    tokens: set[str] = set()
    for chunk in s.split():
        if re.match(r"^[\x00-\x7f]+$", chunk):
            for w in re.split(r"\W+", chunk.lower()):
                if len(w) > 2:
                    tokens.add(w)
        else:
            # 2-char sliding window for CJK
            for i in range(len(chunk) - 1):
                tokens.add(chunk[i : i + 2])
    return tokens


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# Thresholds for preprocess completeness hint (Plan 5 T7).
# Below this the message is softened: preprocess text is probably lossy so
# every "not found" should be read with a grain of salt.
_PREPROCESS_SMALL_CHARS = 25_000


def check_evidence_fidelity(claims: list[dict], haystack: str) -> list[dict]:
    """Each claim.evidence[*].text should be substring of some section_text.

    Two layers of tolerance:
    1. Full quote substring match against normalized haystack.
    2. First 40 chars of normalized quote against haystack (OCR/wording noise).

    When the preprocess haystack is short (< _PREPROCESS_SMALL_CHARS), the
    warning detail notes the preprocess may be lossy — this happens with
    image-heavy or table-heavy PDFs where pdftotext drops content.
    """
    hay = _normalize(haystack)
    preprocess_short = len(hay) < _PREPROCESS_SMALL_CHARS
    warnings = []
    for i, c in enumerate(claims):
        for ev in c.get("evidence") or []:
            quote = ev.get("text") if isinstance(ev, dict) else str(ev)
            if not quote:
                continue
            needle = _normalize(quote)
            if not needle:
                continue
            if needle in hay:
                continue
            head = needle[: min(40, len(needle))]
            if head in hay:
                continue
            if preprocess_short:
                detail = (
                    f"evidence_quote 在 preprocess 文本（{len(hay)} 字，偏短，"
                    f"可能是 PDF→text 损失）里匹配不到（前 40 字：{quote[:40]!r}）"
                )
            else:
                detail = f"evidence_quote 在原文里找不到（前 40 字：{quote[:40]!r}）"
            warnings.append({
                "rule": "fidelity",
                "claim_id": c.get("id") or f"#{i}",
                "subject_tag": c.get("subject_tag"),
                "detail": detail,
            })
    return warnings


def check_answered_self_contradiction(answered: list[dict]) -> list[dict]:
    """level=specific 但 answer_text 自己说'未提及/未披露' → 矛盾."""
    warnings = []
    for a in answered:
        lvl = a.get("level")
        txt = a.get("answer_text") or ""
        hits = _contains_any(txt, _UNCERTAINTY_WORDS)
        if lvl == "specific" and hits:
            warnings.append({
                "rule": "self_contradict_specific",
                "q_id": a.get("q_id"),
                "detail": f"level=specific 但 answer_text 含 {hits!r}",
            })
        elif lvl in ("specific", "vague"):
            ev = a.get("evidence_quote") or ""
            if not ev.strip():
                warnings.append({
                    "rule": "empty_evidence",
                    "q_id": a.get("q_id"),
                    "detail": f"level={lvl} 但 evidence_quote 为空",
                })
    return warnings


def check_polarity_text_mismatch(claims: list[dict]) -> list[dict]:
    """polarity=bull 但 claim_text 只含负面词（反之亦然）→ 候选矛盾."""
    warnings = []
    for i, c in enumerate(claims):
        txt = c.get("claim_text") or ""
        pol = c.get("polarity")
        bear_hits = _contains_any(txt, _BEAR_KEYWORDS)
        bull_hits = _contains_any(txt, _BULL_KEYWORDS)
        if pol == "bull" and bear_hits and not bull_hits:
            warnings.append({
                "rule": "polarity_mismatch",
                "claim_id": c.get("id") or f"#{i}",
                "detail": f"polarity=bull 但 claim_text 只含负面词 {bear_hits!r}",
            })
        elif pol == "bear" and bull_hits and not bear_hits:
            warnings.append({
                "rule": "polarity_mismatch",
                "claim_id": c.get("id") or f"#{i}",
                "detail": f"polarity=bear 但 claim_text 只含正面词 {bull_hits!r}",
            })
    return warnings


def check_proposed_vs_existing(
    proposed: list[dict],
    existing_items: list[dict],
    threshold: float = 0.35,
) -> list[dict]:
    """proposed_question 和 existing question 的 token Jaccard 过高 → 重叠."""
    warnings = []
    existing_tokens = [
        (it["id"], _token_set(it["question"])) for it in existing_items or []
    ]
    for p in proposed or []:
        q = p.get("proposed_question") or ""
        qtok = _token_set(q)
        best_id, best_sim = None, 0.0
        for (qid, etok) in existing_tokens:
            sim = _jaccard(qtok, etok)
            if sim > best_sim:
                best_id, best_sim = qid, sim
        if best_sim >= threshold:
            warnings.append({
                "rule": "proposed_dup",
                "proposed": q[:60],
                "detail": f"与 existing item {best_id} jaccard={best_sim:.2f}（阈值 {threshold}）",
            })
    return warnings


def check_checklist_company_contamination(
    items: list[dict],
    participants: list[dict],
) -> list[dict]:
    """Checklist question 里包含 participant name → 公司名污染，跨公司对比失效."""
    warnings = []
    names = [p.get("name") for p in (participants or []) if p.get("name")]
    for it in items or []:
        q = it.get("question") or ""
        hits = [n for n in names if n and n in q]
        if hits:
            warnings.append({
                "rule": "checklist_company_contamination",
                "q_id": it.get("id"),
                "detail": f"question 含 participant 名字 {hits!r}，替换成 participant 后仍可问才合格",
            })
    return warnings


# --- 规则：缺口清单 ---------------------------------------------------------

ANNUAL_PATTERNS = [
    r"10-?K", r"20-?F", r"年度报告", r"年报",
]
QUARTERLY_PATTERNS = [
    r"10-?Q", r"季度报告", r"季报",
]
SEMI_PATTERNS = [r"半年度报告", r"半年报"]

RESEARCH_PATTERNS = [
    r"证券", r"Securities", r"证研", r"研报",
]


def _classify_source(filename: str) -> str:
    for p in ANNUAL_PATTERNS:
        if re.search(p, filename):
            return "annual"
    for p in QUARTERLY_PATTERNS:
        if re.search(p, filename):
            return "quarterly"
    for p in SEMI_PATTERNS:
        if re.search(p, filename):
            return "semi"
    if any(re.search(p, filename) for p in RESEARCH_PATTERNS):
        return "sell_side"
    return "unknown"


def _parse_source_id(source_id: str) -> dict:
    """研报-{institution}-{YYYY-MM-DD}-{sha8} | 年报-{YYYY}-{sha8} | ..."""
    parts = source_id.split("-")
    out = {"type": parts[0] if parts else "", "raw": source_id}
    # try to pull date YYYY-MM-DD
    m = re.search(r"(\d{4}-\d{2}-\d{2})", source_id)
    if m:
        out["date"] = m.group(1)
    elif parts and re.match(r"^\d{4}$", parts[-2] if len(parts) >= 2 else ""):
        out["date"] = parts[-2] + "-01-01"
    if out["type"] == "研报" and len(parts) >= 4:
        out["institution"] = parts[1]
    return out


def collect_company_gaps(ticker: str, market: str) -> dict:
    from app.io import claims as claims_io
    from app.io import company as company_io
    from app.io import arenas as arenas_io

    meta = company_io.read_meta(ticker, market)
    name = meta.get("name", f"{market}_{ticker}")
    sector = meta.get("industry_primary")
    arena_slugs = meta.get("arenas") or []

    # claims
    try:
        claims = claims_io.read_claims(ticker, market)
    except Exception:
        claims = []

    sources_dir = Path(f"companies/{market}_{ticker}/sources")
    source_files = sorted([p.name for p in sources_dir.glob("*")]) if sources_dir.exists() else []
    source_types: dict[str, list[str]] = {}
    for fn in source_files:
        source_types.setdefault(_classify_source(fn), []).append(fn)

    source_ids = sorted({c.get("source_id") for c in claims if c.get("source_id")})
    institutions = set()
    latest_date = None
    for sid in source_ids:
        meta_sid = _parse_source_id(sid)
        if meta_sid.get("institution"):
            institutions.add(meta_sid["institution"])
        d = meta_sid.get("date")
        if d:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").date()
                if latest_date is None or dt > latest_date:
                    latest_date = dt
            except ValueError:
                pass

    polarity_counts = {"bull": 0, "bear": 0, "neutral": 0}
    for c in claims:
        p = c.get("polarity")
        if p in polarity_counts:
            polarity_counts[p] += 1

    # tag coverage
    tags_covered: dict[str, int] = {}
    for c in claims:
        t = c.get("subject_tag")
        if t:
            tags_covered[t] = tags_covered.get(t, 0) + 1

    # arena breakdown
    arena_data = {}
    for slug in arena_slugs:
        info = arenas_io.read_arena(slug)
        if not info["exists"]:
            continue
        fm = info["definition_fm"]
        participants = fm.get("participants") or []
        items = info["checklist"].get("items") if info["checklist"] else []
        notes_text = info["notes_text"]

        # per-ticker coverage: parse competence-notes for "## {market}_{ticker}"
        ticker_sections = re.findall(r"##\s+(\w+)_(\w+)\s+·", notes_text)
        covered_tickers = {(m, t) for m, t in ticker_sections}

        # per-item level for this ticker
        this_ticker_header = f"## {market}_{ticker} ·"
        item_levels_for_this: dict[str, str] = {}
        if this_ticker_header in notes_text:
            start = notes_text.index(this_ticker_header)
            end = notes_text.find("\n## ", start + 1)
            block = notes_text[start : end if end != -1 else None]
            for m in re.finditer(r"###\s+(q_\w+)\s+·\s+level=(\w+)", block):
                item_levels_for_this[m.group(1)] = m.group(2)

        arena_data[slug] = {
            "name": fm.get("name", slug),
            "participants": participants,
            "covered_tickers": covered_tickers,
            "items": items,
            "this_ticker_levels": item_levels_for_this,
        }

    return {
        "ticker": ticker,
        "market": market,
        "name": name,
        "sector": sector,
        "claims_count": len(claims),
        "polarity_counts": polarity_counts,
        "tags_covered": tags_covered,
        "source_ids": source_ids,
        "institutions": sorted(institutions),
        "latest_source_date": latest_date.isoformat() if latest_date else None,
        "source_files_by_type": source_types,
        "arenas": arena_data,
    }


def _months_since(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    except ValueError:
        return None
    today = date.today()
    return (today.year - d.year) * 12 + (today.month - d.month)


def render_gap_markdown(gaps: dict) -> str:
    lines = []
    ticker = gaps["ticker"]
    market = gaps["market"]
    name = gaps["name"]
    sector = gaps.get("sector") or "未分类"

    lines.append(f"# {market}_{ticker} · {name} · 认知缺口")
    lines.append("")
    lines.append(f"*sector={sector} · claims={gaps['claims_count']} · sources={len(gaps['source_ids'])}*")
    lines.append("")

    # --- 一手披露 ---
    lines.append("## 一手披露")
    st = gaps["source_files_by_type"]
    has_annual = bool(st.get("annual"))
    has_quarterly = bool(st.get("quarterly") or st.get("semi"))
    if has_annual:
        for fn in st.get("annual", []):
            lines.append(f"- [x] 年报：{fn}")
    else:
        lines.append("- [ ] **缺年报 / 10-K / 20-F / 年度报告** —— 这是事实层（profile / financials）的必需源")
    if has_quarterly:
        for fn in (st.get("quarterly", []) + st.get("semi", [])):
            lines.append(f"- [x] 季报/半年报：{fn}")
    else:
        lines.append("- [ ] 缺季报 / 半年报 —— 用于更新近期动态")

    # recency
    months = _months_since(gaps["latest_source_date"])
    if months is not None:
        if months > 6:
            lines.append(f"- [ ] **最新 source 已 {months} 月前（{gaps['latest_source_date']}）**，建议 ingest 最新季报或公告")
        else:
            lines.append(f"- [x] 最新 source {months} 月前（{gaps['latest_source_date']}）")
    lines.append("")

    # --- 声道多样性 ---
    lines.append("## 声道多样性")
    inst = gaps["institutions"]
    if not inst:
        lines.append("- [ ] 未 ingest 任何卖方研报")
    elif len(inst) == 1:
        lines.append(f"- [ ] **只有 1 家机构的研报（{inst[0]}）** —— 建议 ingest 不同机构做对立视角（如中信/华泰/申万）")
    else:
        lines.append(f"- [x] 研报机构 {len(inst)} 家：{', '.join(inst)}")

    pc = gaps["polarity_counts"]
    if pc["bear"] == 0 and pc["bull"] > 0:
        lines.append(f"- [ ] **bear claim = 0** （bull={pc['bull']} / neutral={pc['neutral']}）—— 只见多不见空，建议 ingest 唱空研报或关注财报风险段")
    elif pc["bull"] == 0 and pc["bear"] > 0:
        lines.append(f"- [ ] **bull claim = 0** —— 只见空不见多")
    else:
        lines.append(f"- [x] polarity 平衡：bull={pc['bull']} bear={pc['bear']} neutral={pc['neutral']}")
    lines.append("")

    # --- tag 覆盖 ---
    lines.append("## Subject tag 覆盖")
    tags = gaps["tags_covered"]
    if tags:
        for t, n in sorted(tags.items(), key=lambda x: -x[1]):
            lines.append(f"- `{t}`: {n}")
        # 提示某些 tag 缺失
        critical_tags_by_sector = {
            "cyclical": ["cyclical_risk", "capex_cycle", "catalyst", "revenue_growth"],
            "consumer": ["pricing_power", "revenue_growth", "gross_margin", "channel_inventory"],
            "saas": ["revenue_growth", "operating_leverage", "concentration_risk"],
            "bank": ["margin_trend", "regulatory_risk"],
            "biotech": ["regulatory_risk", "catalyst", "concentration_risk"],
        }
        crit = critical_tags_by_sector.get(sector or "", [])
        missing = [t for t in crit if t not in tags]
        if missing:
            lines.append("")
            lines.append(f"- [ ] sector={sector} 下推荐但缺失的 tag：**{', '.join(missing)}**")
    else:
        lines.append("- （无）")
    lines.append("")

    # --- Arena ---
    if not gaps["arenas"]:
        lines.append("## Arena 横向")
        lines.append("- （本公司未归属任何 arena —— 考虑在下次 ingest 时 bootstrap arena）")
        lines.append("")
    for slug, a in gaps["arenas"].items():
        lines.append(f"## Arena · {a['name']} (`{slug}`)")
        lines.append("")
        lines.append("### 参与者覆盖")
        participants = a["participants"] or []
        covered = a["covered_tickers"]
        for p in participants:
            key = (p["market"], p["ticker"])
            checked = "x" if key in covered else " "
            name_ = p.get("name", "")
            lines.append(f"- [{checked}] {p['market']}_{p['ticker']} {name_} ({p.get('role','')})")
        if len(covered) < len(participants):
            miss = [
                f"{p['market']}_{p['ticker']} {p.get('name','')}"
                for p in participants
                if (p["market"], p["ticker"]) not in covered
            ]
            if miss:
                lines.append("")
                lines.append(f"- [ ] **arena 横向对比未铺开** —— 建议 ingest：{', '.join(miss)}")
        lines.append("")

        # 本公司的 checklist 填答
        levels = a["this_ticker_levels"]
        items = a["items"] or []
        lines.append(f"### {market}_{ticker} 在本 arena 的 checklist 填答")
        for it in items:
            qid = it["id"]
            lvl = levels.get(qid, "missing")
            icon = {
                "specific": "✓",
                "vague": "~",
                "unanswered": "✗",
                "missing": "?",
            }.get(lvl, "?")
            badge = f"`{lvl}`"
            lines.append(f"- {icon} `{qid}` — {it['question']} {badge}")
        # 硬伤 hint
        vague_or_missing = [
            it["id"] for it in items
            if levels.get(it["id"]) in (None, "vague", "unanswered", "missing")
        ]
        if vague_or_missing:
            lines.append("")
            lines.append(
                f"- [ ] 未达到 `specific` 的 item（{len(vague_or_missing)} 条）：建议 ingest 补强\n  "
                + ", ".join(f"`{q}`" for q in vague_or_missing)
            )
        lines.append("")

    return "\n".join(lines)


# --- CLI -------------------------------------------------------------------


def _target_from_rule(rule: str, w: dict, source_id: str | None) -> str:
    """Build a stable ``target`` string for a raw warning dict."""
    if rule in ("fidelity", "polarity_mismatch"):
        return f"claim:{w.get('claim_id', '?')}"
    if rule in ("self_contradict_specific", "empty_evidence"):
        return f"q_id:{w.get('q_id', '?')}"
    if rule == "proposed_dup":
        return f"proposed:{(w.get('proposed') or '')[:40]}"
    if rule == "checklist_company_contamination":
        return f"item:{w.get('q_id', '?')}"
    return w.get("claim_id") or w.get("q_id") or "?"


def _validate_scope(scope: str) -> str:
    """Accept MARKET_TICKER or industry:SLUG. Raises SystemExit on malformed."""
    from app.io import qa as qa_io
    try:
        qa_io._resolve_scope_dir(scope)
    except ValueError as e:
        raise SystemExit(f"--scope: {e}")
    return scope


def cmd_warn(args: argparse.Namespace) -> int:
    merged = json.loads(Path(args.merged).read_text(encoding="utf-8"))
    claims = merged.get("claims", []) or []
    findings = merged.get("competence_findings", {}) or {}
    answered = findings.get("answered", []) or []
    proposed = findings.get("proposed_additions", []) or []

    source_id = None
    for c in claims:
        if c.get("source_id"):
            source_id = c["source_id"]
            break

    # haystack for fidelity
    haystack_parts = []
    if args.preprocess:
        pre = json.loads(Path(args.preprocess).read_text(encoding="utf-8"))
        for s in pre.get("sections", []):
            if s.get("action") != "skip":
                haystack_parts.append(s.get("text") or "")
    haystack = "\n".join(haystack_parts)

    raw_warnings: list[dict] = []
    if haystack:
        raw_warnings += check_evidence_fidelity(claims, haystack)
    raw_warnings += check_answered_self_contradiction(answered)
    raw_warnings += check_polarity_text_mismatch(claims)

    # checklist-dependent checks
    if args.arena:
        from app.io import arenas as arenas_io
        arena = arenas_io.read_arena(args.arena)
        existing_items = (arena.get("checklist") or {}).get("items") or []
        participants = (arena.get("definition_fm") or {}).get("participants") or []
        raw_warnings += check_proposed_vs_existing(proposed, existing_items)
        raw_warnings += check_checklist_company_contamination(existing_items, participants)

    # render to stdout regardless
    if not raw_warnings:
        print("✓ 无告警（4 条抽取规则 + 2 条 arena 规则全过）")
        if args.write:
            return 0
        return 0

    by_rule: dict[str, list[dict]] = {}
    for w in raw_warnings:
        by_rule.setdefault(w["rule"], []).append(w)
    print(f"# 抽取告警 · {len(raw_warnings)} 条")
    print()
    for rule, ws in by_rule.items():
        print(f"## {rule} ({len(ws)})")
        for w in ws:
            ident = w.get("claim_id") or w.get("q_id") or w.get("proposed", "")[:40]
            print(f"- [{ident}] {w['detail']}")
        print()

    # optional: persist
    if args.write:
        if not args.scope:
            print("ERROR: --write 需要配合 --scope MARKET_TICKER 或 industry:SLUG", file=sys.stderr)
            return 2
        from app.io import qa as qa_io

        scope = _validate_scope(args.scope)
        normalized = [
            qa_io.make_warning(
                scope=scope,
                source_id=source_id,
                rule=w["rule"],
                target=_target_from_rule(w["rule"], w, source_id),
                detail=w["detail"],
            )
            for w in raw_warnings
        ]
        counts = qa_io.append_warnings(scope, normalized)
        dest_dir = "industries" if scope.startswith("industry:") else "companies"
        dest_name = scope[len("industry:"):] if scope.startswith("industry:") else scope
        print(
            f"✓ 落盘 {dest_dir}/{dest_name}/qa_warnings.jsonl"
            f"：added={counts['added']} skipped_dup={counts['skipped_dup']} reopened={counts['reopened']}"
        )
    return 1


def cmd_gap(args: argparse.Namespace) -> int:
    scope = _validate_scope(args.company)
    if scope.startswith("industry:"):
        raise SystemExit("gap 子命令目前仅支持公司 scope（MARKET_TICKER）")
    market, ticker = scope.split("_", 1)
    gaps = collect_company_gaps(ticker, market)
    md = render_gap_markdown(gaps)
    print(md)
    if args.write:
        from app.io import qa as qa_io

        path = qa_io.write_gap_markdown(scope, md)
        print(f"\n✓ 落盘 {path}", file=sys.stderr)
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    from app.io import qa as qa_io

    scope = _validate_scope(args.scope)
    ok = qa_io.update_status(scope, args.id, "resolved", note=args.note)
    print("✓ resolved" if ok else "✗ warning id 未找到", file=sys.stderr)
    return 0 if ok else 1


def cmd_dismiss(args: argparse.Namespace) -> int:
    from app.io import qa as qa_io

    scope = _validate_scope(args.scope)
    ok = qa_io.update_status(scope, args.id, "dismissed", note=args.note)
    print("✓ dismissed" if ok else "✗ warning id 未找到", file=sys.stderr)
    return 0 if ok else 1


def cmd_list(args: argparse.Namespace) -> int:
    from app.io import qa as qa_io

    scope = _validate_scope(args.scope)
    ws = qa_io.read_warnings(scope, status=args.status)
    if not ws:
        print(f"({scope}) 无 {args.status or 'all'} 状态的告警")
        return 0
    print(f"# {scope} · {args.status or 'all'} warnings ({len(ws)})\n")
    for w in ws:
        print(f"- [{w['id']}] ({w['rule']}) {w['target']}  status={w['status']}")
        print(f"  · {w['detail']}")
        if w.get("fix_hint"):
            print(f"  · fix: {w['fix_hint']}")
        print()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="ingest_qa")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_warn = sub.add_parser("warn", help="抽取异常告警")
    p_warn.add_argument("--merged", required=True, help="aggregate 后的 merged.json")
    p_warn.add_argument("--preprocess", help="preprocess 产出的 sections.json（跑 fidelity 校验）")
    p_warn.add_argument("--arena", help="checklist slug（跑 proposed_dup / company contamination）")
    p_warn.add_argument("--write", action="store_true", help="落盘到 {scope}/qa_warnings.jsonl（公司或行业）")
    p_warn.add_argument("--scope", help="MARKET_TICKER（BSE_920118）或 industry:SLUG（industry:cn-cmp-material），配合 --write 使用")
    p_warn.set_defaults(func=cmd_warn)

    p_gap = sub.add_parser("gap", help="认知缺口清单")
    p_gap.add_argument("--company", required=True, help="MARKET_TICKER 如 BSE_920118")
    p_gap.add_argument("--write", action="store_true", help="覆写到 companies/{key}/qa_gaps.md")
    p_gap.set_defaults(func=cmd_gap)

    p_resolve = sub.add_parser("resolve", help="标记 warning 为 resolved")
    p_resolve.add_argument("--scope", required=True)
    p_resolve.add_argument("--id", required=True, help="warning id（前 12 位 hash）")
    p_resolve.add_argument("--note", help="解决说明")
    p_resolve.set_defaults(func=cmd_resolve)

    p_dismiss = sub.add_parser("dismiss", help="标记 warning 为 dismissed（规则误报）")
    p_dismiss.add_argument("--scope", required=True)
    p_dismiss.add_argument("--id", required=True)
    p_dismiss.add_argument("--note", help="忽略原因")
    p_dismiss.set_defaults(func=cmd_dismiss)

    p_list = sub.add_parser("list", help="列出已落盘的 warnings")
    p_list.add_argument("--scope", required=True)
    p_list.add_argument("--status", choices=["open", "resolved", "dismissed"], help="过滤状态")
    p_list.set_defaults(func=cmd_list)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
