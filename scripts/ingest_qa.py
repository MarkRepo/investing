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


def check_figure_context_coverage(
    industry_facts: list[dict],
    figure_contexts: list[dict],
    ratio_threshold: float = 0.30,
) -> list[dict]:
    """Plan 5 T10: warn when digest produces too few numeric observations
    relative to figure_contexts with digit-bearing captions.

    The industry-digest prompt demands ≥80% of figure captions be scanned
    ("要么产 observation，要么影响 narrative"). We can't directly measure
    "scanned"; the useful proxy is the ratio of atomic numeric facts to
    figures whose caption contains a digit (TAM / CAGR / share-rate figures
    almost always have digits). A ratio < 0.30 likely means the subagent
    skipped most figures.

    No warning if there are zero digit-bearing captions — the rule only fires
    when there's measurable figure data to compare against.
    """
    numeric_captions = [
        f for f in figure_contexts or []
        if any(c.isdigit() for c in (f.get("caption") or ""))
    ]
    if not numeric_captions:
        return []
    numeric_facts = [
        f for f in industry_facts or []
        if f.get("value_numeric") is not None
    ]
    ratio = len(numeric_facts) / len(numeric_captions)
    if ratio >= ratio_threshold:
        return []
    return [{
        "rule": "figure_coverage_low",
        "detail": (
            f"图表数据回收率偏低：{len(numeric_captions)} 个带数字 caption，"
            f"仅 {len(numeric_facts)} 条 atomic 数值 observation "
            f"(ratio={ratio:.2f} < {ratio_threshold})。"
            "subagent 可能漏读 figure_contexts——检查 industry-digest 输出"
            "是否覆盖主要图表。"
        ),
    }]


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


# --- 规则：review bundle QA ---------------------------------------------------


def _qa_warning(
    rule: str,
    severity: str,
    target: str,
    detail: str,
    fix_hint: str | None = None,
) -> dict:
    warning = {
        "rule": rule,
        "severity": severity,
        "target": target,
        "detail": detail,
    }
    if fix_hint:
        warning["fix_hint"] = fix_hint
    return warning


def check_review_bundle_shape(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    if not bundle.get("source_digest"):
        warnings.append(_qa_warning(
            "missing_source_digest",
            "error",
            "source_digest",
            "Missing source_digest.",
        ))
    if not bundle.get("insight_blocks"):
        warnings.append(_qa_warning(
            "missing_insight_blocks",
            "error",
            "insight_blocks",
            "Missing or empty insight_blocks.",
        ))
    if not bundle.get("synthesis"):
        warnings.append(_qa_warning(
            "missing_synthesis",
            "error",
            "synthesis",
            "Missing synthesis.",
        ))
    return warnings


_BLOCK_RELATION_VALUES = {"premise_for", "corroborates", "risk_to", "contradicts"}


def check_insight_blocks(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    block_ids = {
        block.get("id")
        for block in bundle.get("insight_blocks", []) or []
        if block.get("id")
    }
    for idx, block in enumerate(bundle.get("insight_blocks", []) or []):
        block_id = block.get("id") or f"#{idx}"
        target = f"insight_blocks.{block_id}"

        if not block.get("block_type"):
            warnings.append(_qa_warning(
                "block_missing_block_type",
                "error",
                f"{target}.block_type",
                "block_type is empty.",
            ))

        chain = block.get("reasoning_chain") or []
        if len(chain) < 2:
            warnings.append(_qa_warning(
                "block_shallow_reasoning_chain",
                "warning",
                f"{target}.reasoning_chain",
                f"reasoning_chain has {len(chain)} item(s); must have at least 2 "
                "(observation + investment implication).",
            ))

        for rel_idx, rel in enumerate(block.get("block_relations", []) or []):
            ref_id = rel.get("block_id")
            relation = rel.get("relation")
            rel_target = f"{target}.block_relations[{rel_idx}]"
            if ref_id and ref_id == block_id:
                warnings.append(_qa_warning(
                    "block_relations_unknown_block",
                    "error",
                    rel_target,
                    f"block_relations references itself ({ref_id!r}).",
                ))
            elif ref_id and ref_id not in block_ids:
                warnings.append(_qa_warning(
                    "block_relations_unknown_block",
                    "error",
                    rel_target,
                    f"block_relations references unknown block_id {ref_id!r}.",
                ))
            if relation and relation not in _BLOCK_RELATION_VALUES:
                warnings.append(_qa_warning(
                    "block_relations_invalid_relation",
                    "warning",
                    rel_target,
                    f"relation {relation!r} is not one of {sorted(_BLOCK_RELATION_VALUES)}.",
                ))
    return warnings


def _candidate_key(candidate: dict, fallback: str) -> str:
    market = candidate.get("market")
    ticker = candidate.get("ticker")
    if market and ticker:
        return f"{market}_{ticker}"
    return ticker or fallback


def check_fact_block_links(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    block_ids = {
        block.get("id")
        for block in bundle.get("insight_blocks", [])
        if block.get("id")
    }
    for idx, fact in enumerate(bundle.get("atomic_facts", []) or []):
        fact_id = fact.get("fact_id") or f"#{idx}"
        linked_block_id = fact.get("linked_block_id")
        if not linked_block_id:
            warnings.append(_qa_warning(
                "fact_missing_linked_block",
                "error",
                f"atomic_facts.{fact_id}",
                "atomic_fact.linked_block_id is missing.",
            ))
        elif linked_block_id not in block_ids:
            warnings.append(_qa_warning(
                "fact_unknown_linked_block",
                "error",
                f"atomic_facts.{fact_id}",
                f"linked_block_id {linked_block_id!r} does not exist in insight_blocks.",
            ))
        if not fact.get("evidence_quote"):
            warnings.append(_qa_warning(
                "fact_missing_evidence_quote",
                "error",
                f"atomic_facts.{fact_id}",
                "atomic_fact.evidence_quote is missing.",
            ))
    return warnings


def _preprocess_haystack(preprocess: dict) -> str:
    parts: list[str] = []
    for section in preprocess.get("sections", []) or []:
        if section.get("action") != "skip":
            parts.append(section.get("text") or "")
    return "\n".join(parts)


def check_fact_evidence_quotes(bundle: dict, preprocess: dict) -> list[dict]:
    haystack = _preprocess_haystack(preprocess)
    claims: list[dict] = []
    for idx, fact in enumerate(bundle.get("atomic_facts", []) or []):
        fact_id = fact.get("fact_id") or f"#{idx}"
        quote = fact.get("evidence_quote")
        if not quote:
            continue
        claims.append({
            "id": fact_id,
            "evidence": [{"text": quote}],
        })

    raw_warnings = check_evidence_fidelity(claims, haystack)
    warnings: list[dict] = []
    for warning in raw_warnings:
        fact_id = warning.get("claim_id") or "?"
        warnings.append(_qa_warning(
            "evidence_quote_not_found",
            "warning",
            f"atomic_facts.{fact_id}",
            warning["detail"],
        ))
    return warnings


_A_SHARE_TICKER_RE = re.compile(r"(?<!\d)(?:\d{6})\.(?:SH|SZ|BJ|SSE|SZSE|BSE)(?![A-Za-z0-9])", re.IGNORECASE)


def _known_fact_entities(bundle: dict, fact_text: str) -> list[str]:
    entities: list[str] = []
    for match in _A_SHARE_TICKER_RE.findall(fact_text or ""):
        ticker = match.split(".")[0]
        if ticker not in entities:
            entities.append(ticker)

    for candidate in bundle.get("company_candidates", []) or []:
        name = candidate.get("name")
        if name and name in fact_text and name not in entities:
            entities.append(name)
        ticker = candidate.get("ticker")
        if not ticker:
            continue
        ticker_base = str(ticker).split(".")[0]
        if ticker_base in (fact_text or "") and ticker_base not in entities:
            entities.append(ticker_base)
    return entities


def check_fact_quote_consistency(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    for idx, fact in enumerate(bundle.get("atomic_facts", []) or []):
        fact_id = fact.get("fact_id") or f"#{idx}"
        fact_text = fact.get("fact_text") or ""
        quote = fact.get("evidence_quote") or ""
        missing = [entity for entity in _known_fact_entities(bundle, fact_text) if entity not in quote]
        if missing:
            warnings.append(_qa_warning(
                "fact_text_entity_missing_from_quote",
                "warning",
                f"atomic_facts.{fact_id}",
                f"fact_text mentions entities not present in evidence_quote: {', '.join(missing)}.",
            ))
    return warnings

def _risky_pages(preprocess: dict) -> dict[int, dict]:
    pages = (preprocess.get("preprocess_metadata") or {}).get("extracted_pages") or []
    risky: dict[int, dict] = {}
    for page in pages:
        page_no = page.get("page")
        if page_no is None:
            continue
        if (
            page.get("text_quality") == "low"
            or page.get("image_heavy")
            or page.get("chart_heavy")
            or page.get("table_heavy")
        ):
            risky[int(page_no)] = page
    return risky


def _source_page_numbers(source_page_range: str) -> set[int]:
    pages: set[int] = set()
    text = source_page_range or ""
    for start, end in re.findall(r"(\d+)\s*[-–—~至到]\s*(\d+)", text):
        a = int(start)
        b = int(end)
        if a <= b:
            pages.update(range(a, b + 1))
        else:
            pages.update(range(b, a + 1))
    text_without_ranges = re.sub(r"\d+\s*[-–—~至到]\s*\d+", " ", text)
    pages.update(int(n) for n in re.findall(r"\d+", text_without_ranges))
    return pages


def check_preprocess_risk_confidence(bundle: dict, preprocess: dict) -> list[dict]:
    risky_pages = _risky_pages(preprocess)
    if not risky_pages:
        return []

    warnings: list[dict] = []
    for idx, fact in enumerate(bundle.get("atomic_facts", []) or []):
        fact_id = fact.get("fact_id") or f"#{idx}"
        source_page = fact.get("source_page")
        if fact.get("confidence") == "high" and source_page in risky_pages:
            warnings.append(_qa_warning(
                "high_confidence_fact_from_risky_page",
                "warning",
                f"atomic_facts.{fact_id}",
                f"High-confidence fact comes from risky preprocess page {source_page}.",
            ))

    block_pages: dict[str, set[int]] = {}
    for block in bundle.get("insight_blocks", []) or []:
        block_id = block.get("id")
        if not block_id:
            continue
        pages = _source_page_numbers(str(block.get("source_page_range") or ""))
        if pages:
            block_pages[block_id] = pages

    for idx, candidate in enumerate(bundle.get("company_candidates", []) or []):
        candidate_key = _candidate_key(candidate, f"#{idx}")
        candidate_pages: set[int] = set()
        for block_id in candidate.get("source_block_ids", []) or []:
            candidate_pages |= block_pages.get(block_id, set())
        if candidate.get("confidence") == "high" and candidate_pages & set(risky_pages):
            warnings.append(_qa_warning(
                "high_confidence_candidate_from_risky_page",
                "warning",
                f"company_candidates.{candidate_key}",
                f"High-confidence company candidate is sourced from risky preprocess pages {sorted(candidate_pages & set(risky_pages))}.",
            ))
    return warnings


def check_stage_gate_synthesis(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    cannot_conclude = (bundle.get("synthesis") or {}).get("cannot_conclude") or []
    for idx, gate in enumerate(bundle.get("stage_gates", []) or []):
        gate_id = gate.get("id") or f"#{idx}"
        if gate.get("crossed") is False and not cannot_conclude:
            warnings.append(_qa_warning(
                "stage_gate_missing_cannot_conclude",
                "error",
                f"stage_gates:{gate_id}",
                "Material uncrossed stage gate exists but synthesis.cannot_conclude is empty.",
            ))
    return warnings


def check_company_candidates(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    for idx, candidate in enumerate(bundle.get("company_candidates", []) or []):
        candidate_key = _candidate_key(candidate, f"#{idx}")
        target = f"company_candidates.{candidate_key}"
        if not candidate.get("exposure_type"):
            warnings.append(_qa_warning(
                "candidate_missing_exposure_type",
                "error",
                f"{target}.exposure_type",
                "Company candidate is missing exposure_type.",
            ))
        if not candidate.get("source_block_ids"):
            warnings.append(_qa_warning(
                "candidate_missing_source_blocks",
                "error",
                f"{target}.source_block_ids",
                "Company candidate is missing source_block_ids.",
            ))
        if not candidate.get("verification_questions"):
            warnings.append(_qa_warning(
                "candidate_missing_verification_questions",
                "error",
                f"{target}.verification_questions",
                "Company candidate is missing verification_questions.",
            ))
        if candidate.get("exposure_type") == "thematic_related" and candidate.get("confidence") == "high":
            warnings.append(_qa_warning(
                "thematic_related_high_confidence",
                "warning",
                target,
                "thematic_related company candidate cannot be high confidence.",
            ))
    return warnings


_STRONG_SYNTHESIS_WORDS = [
    "确定", "必然", "显著受益", "爆发", "高增长", "明确受益", "核心受益",
    "confirmed", "must", "will", "certain",
]


def check_synthesis_discipline(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    source_evidence = (bundle.get("source_digest") or {}).get("evidence_strength")
    synthesis = bundle.get("synthesis") or {}
    one_sentence = synthesis.get("one_sentence") or ""

    if source_evidence in ("low", "medium_low") and _contains_any(one_sentence, _STRONG_SYNTHESIS_WORDS):
        warnings.append(_qa_warning(
            "low_evidence_strong_synthesis",
            "warning",
            "synthesis.one_sentence",
            "Low evidence source produces strong one-sentence thesis.",
        ))

    overclaim_words = ["确定受益", "明确受益", "核心受益", "confirmed beneficiary"]
    for idx, candidate in enumerate(bundle.get("company_candidates", []) or []):
        name = candidate.get("name") or ""
        candidate_key = _candidate_key(candidate, f"#{idx}")
        if name and name in one_sentence and _contains_any(one_sentence, overclaim_words):
            warnings.append(_qa_warning(
                "candidate_overclaimed_in_synthesis",
                "warning",
                f"company_candidates.{candidate_key}",
                "Candidate company appears in synthesis.one_sentence as a confirmed beneficiary.",
            ))
    return warnings


_VALID_SCOPE_TYPES = {"industry", "arena", "company", "cross_cutting"}


def check_claim_candidates(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    candidates = bundle.get("claim_candidates") or []
    if not candidates:
        return warnings

    block_ids = {b.get("id") for b in (bundle.get("insight_blocks") or []) if b.get("id")}
    source_date = (bundle.get("source_digest") or {}).get("source_date")
    required_fields = (
        "candidate_id",
        "claim_text",
        "scope_type",
        "claim_type",
        "supporting_block_ids",
        "direction_on_source",
        "as_of",
    )

    for candidate in candidates:
        cid = candidate.get("candidate_id", "?")
        for field in required_fields:
            if not candidate.get(field):
                warnings.append(_qa_warning(
                    "claim_candidate_missing_field",
                    "error",
                    cid,
                    f"missing required field: {field}",
                ))

        scope = candidate.get("scope_type")
        if scope and scope not in _VALID_SCOPE_TYPES:
            warnings.append(_qa_warning(
                "claim_candidate_invalid_scope_type",
                "error",
                cid,
                f"scope_type={scope} not in {sorted(_VALID_SCOPE_TYPES)}",
            ))

        for block_id in candidate.get("supporting_block_ids") or []:
            if block_id not in block_ids:
                warnings.append(_qa_warning(
                    "claim_candidate_broken_link",
                    "error",
                    cid,
                    f"supporting_block_id={block_id} not in insight_blocks",
                ))

        as_of = candidate.get("as_of")
        if as_of and source_date and as_of != source_date:
            warnings.append(_qa_warning(
                "claim_candidate_as_of_mismatch",
                "warning",
                cid,
                f"as_of={as_of} != source_date={source_date}",
            ))

        text = (candidate.get("claim_text") or "").strip()
        if text and _looks_multi_sentence(text):
            warnings.append(_qa_warning(
                "claim_candidate_claim_text_not_atomic",
                "warning",
                cid,
                "claim_text 含多句迹象；应为单句命题",
            ))

    return warnings


def _looks_multi_sentence(text: str) -> bool:
    parts = re.split(r"[。！？；\n]+|(?<=[A-Za-z0-9])\.\s+(?=[A-Z0-9])", text)
    non_empty = [part for part in parts if part.strip()]
    return len(non_empty) > 1


def check_schema_fit_review(bundle: dict) -> list[dict]:
    warnings: list[dict] = []
    sfr = bundle.get("schema_fit_review")
    if sfr is None or sfr == {}:
        warnings.append(_qa_warning(
            "schema_fit_review_incomplete",
            "warning",
            "schema_fit_review",
            "schema_fit_review 未填写（Phase 1.5 起应至少给出 fits_current_schema 判断）",
        ))
        return warnings

    required = ("fits_current_schema", "missing_schema_fields", "extra_fields_needed", "notes")
    for key in required:
        if key not in sfr:
            warnings.append(_qa_warning(
                "schema_fit_review_incomplete",
                "warning",
                "schema_fit_review",
                f"missing key: {key}",
            ))

    if sfr.get("fits_current_schema") is False:
        missing = sfr.get("missing_schema_fields") or []
        extra = sfr.get("extra_fields_needed") or []
        if not missing and not extra:
            warnings.append(_qa_warning(
                "schema_fit_review_fits_false_without_details",
                "warning",
                "schema_fit_review",
                "fits_current_schema=false 但未给出 missing_schema_fields 或 extra_fields_needed",
            ))
    return warnings


def check_ingest_review_bundle(bundle: dict, preprocess: dict) -> list[dict]:
    warnings: list[dict] = []
    warnings += check_review_bundle_shape(bundle)
    warnings += check_insight_blocks(bundle)
    warnings += check_fact_block_links(bundle)
    warnings += check_fact_evidence_quotes(bundle, preprocess)
    warnings += check_fact_quote_consistency(bundle)
    warnings += check_preprocess_risk_confidence(bundle, preprocess)
    warnings += check_stage_gate_synthesis(bundle)
    warnings += check_company_candidates(bundle)
    warnings += check_claim_candidates(bundle)
    warnings += check_synthesis_discipline(bundle)
    warnings += check_schema_fit_review(bundle)
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
    figure_contexts = []
    if args.preprocess:
        pre = json.loads(Path(args.preprocess).read_text(encoding="utf-8"))
        for s in pre.get("sections", []):
            if s.get("action") != "skip":
                haystack_parts.append(s.get("text") or "")
        figure_contexts = pre.get("figure_contexts") or []
    haystack = "\n".join(haystack_parts)

    raw_warnings: list[dict] = []
    if haystack:
        raw_warnings += check_evidence_fidelity(claims, haystack)
    raw_warnings += check_answered_self_contradiction(answered)
    raw_warnings += check_polarity_text_mismatch(claims)
    # Plan 5 T10: figure_contexts coverage (industry workflow passes digest
    # industry key_facts via merged["industry_key_facts"]).
    industry_key_facts = merged.get("industry_key_facts") or []
    if figure_contexts and industry_key_facts:
        raw_warnings += check_figure_context_coverage(
            industry_key_facts, figure_contexts,
        )

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

def cmd_review_bundle(args: argparse.Namespace) -> int:
    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    preprocess = json.loads(Path(args.preprocess).read_text(encoding="utf-8"))
    warnings = check_ingest_review_bundle(bundle, preprocess)

    if not warnings:
        print("✓ review bundle QA passed")
        return 0

    by_rule: dict[str, list[dict]] = {}
    for warning in warnings:
        by_rule.setdefault(warning["rule"], []).append(warning)

    print(f"# Review bundle QA · {len(warnings)} warnings")
    print()
    for rule, items in by_rule.items():
        print(f"## {rule} ({len(items)})")
        for warning in items:
            severity = warning.get("severity", "warning")
            target = warning.get("target", "?")
            print(f"- [{severity}] {target}: {warning['detail']}")
        print()
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


def check_archive_writes_shape(data: dict) -> list[dict]:
    warnings: list[dict] = []
    for idx, write in enumerate(data.get("writes", []) or []):
        target = f"writes[{idx}]"
        if not write.get("fact_id"):
            warnings.append(_qa_warning("archive_missing_fact_id", "error", target, "fact_id is required."))
        final_targets = write.get("final_targets")
        if not final_targets:
            warnings.append(_qa_warning("archive_missing_final_targets", "error", target, "final_targets is required before apply."))
            continue
        for t_idx, final_target in enumerate(final_targets):
            t_ref = f"{target}.final_targets[{t_idx}]"
            action = final_target.get("action")
            if action not in {"new", "append"}:
                warnings.append(_qa_warning("archive_invalid_action", "error", t_ref, f"action {action!r} is not one of ['append', 'new']."))
            archive_path = final_target.get("archive_path", "")
            if not archive_path.startswith("archive/") or not archive_path.endswith(".jsonl"):
                warnings.append(_qa_warning("archive_invalid_path", "error", t_ref, f"archive_path {archive_path!r} must look like archive/.../*.jsonl."))
    return warnings


def cmd_archive_apply(args: argparse.Namespace) -> int:
    pending_path = Path(args.pending)
    base = Path(args.base)
    data = json.loads(pending_path.read_text(encoding="utf-8"))
    warnings = check_archive_writes_shape(data)
    errors = [w for w in warnings if w.get("severity") == "error"]
    if errors:
        for warning in errors:
            print(f"✗ {warning['rule']}: {warning['detail']}", file=sys.stderr)
        return 1
    for write in data.get("writes", []) or []:
        payload = write["fact_payload"]
        for final_target in write.get("final_targets", []) or []:
            target_path = base / final_target["archive_path"]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with target_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"✓ archive writes applied from {pending_path}")
    return 0


def cmd_evaluation_init(args: argparse.Namespace) -> int:
    from datetime import timezone

    bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    preprocess = json.loads(Path(args.preprocess).read_text(encoding="utf-8"))
    warnings = check_ingest_review_bundle(bundle, preprocess)
    source_id = (bundle.get("source_digest") or {}).get("source_id", "")

    evaluation = {
        "bundle_ref": source_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "evaluator": "",
        "eval_prompt_version": "phase1.5-v1",
        "method_layers_run": ["L1"],
        "dimension_ratings": {
            "coverage_fidelity": {"trend": None, "notes": ""},
            "reasoning_quality": {"trend": None, "notes": ""},
            "calibration": {"trend": None, "notes": ""},
            "narrative": {"trend": None, "notes": ""},
            "claim_extraction_quality": {"trend": None, "notes": ""},
        },
        "system_fit": {"notes": ""},
        "phase2_readiness": {"notes": ""},
        "defects": [
            {
                "id": f"d-{i + 1:03d}",
                "category": w.get("rule", "unknown"),
                "severity": w.get("severity", "warning"),
                "target_ref": w.get("target", ""),
                "description": w.get("detail", ""),
                "root_cause_hint": None,
                "suggested_fix": "",
            }
            for i, w in enumerate(warnings)
        ],
        "overall_notes": "",
    }
    Path(args.out).write_text(
        json.dumps(evaluation, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"✓ evaluation skeleton written to {args.out}")
    return 0


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


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ingest_qa")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_review = sub.add_parser("review-bundle", help="校验 ingest_review_bundle")
    p_review.add_argument("--bundle", required=True, help="ingest_review_bundle JSON")
    p_review.add_argument("--preprocess", required=True, help="preprocess JSON")
    p_review.set_defaults(func=cmd_review_bundle)

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

    p_archive = sub.add_parser("archive", help="archive pending write workflow")
    archive_sub = p_archive.add_subparsers(dest="archive_cmd", required=True)
    p_archive_apply = archive_sub.add_parser("apply", help="apply approved archive writes")
    p_archive_apply.add_argument("--pending", required=True)
    p_archive_apply.add_argument("--base", default=".")
    p_archive_apply.set_defaults(func=cmd_archive_apply)

    p_eval = sub.add_parser("evaluation", help="evaluation workflow")
    eval_sub = p_eval.add_subparsers(dest="eval_cmd", required=True)
    p_eval_init = eval_sub.add_parser("init", help="aggregate L1 warnings into evaluation skeleton")
    p_eval_init.add_argument("--bundle", required=True)
    p_eval_init.add_argument("--preprocess", required=True)
    p_eval_init.add_argument("--out", required=True)
    p_eval_init.set_defaults(func=cmd_evaluation_init)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
