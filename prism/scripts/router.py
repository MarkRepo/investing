from __future__ import annotations

import re
from typing import Iterable

from prism.scripts.providers.base import Provider

_NEWS_RE = re.compile(
    r"\b(today|yesterday|last\s+(week|month|quarter|year)|"
    r"this\s+(week|month|quarter|year)|"
    r"20\d{2}\s*[Qq][1-4]|"
    r"FDA|EPA|SEC\s+filing|earnings|approval|launch|recall|"
    r"announce(d|ment)?|release|update|breaking)\b",
    re.IGNORECASE,
)
_SEMANTIC_RE = re.compile(
    r"\b(similar\s+to|like\s+\w+|papers?\s+(on|about)|"
    r"research\s+about|companies?\s+like|alternatives?\s+to)\b",
    re.IGNORECASE,
)
_EXACT_RE = re.compile(r"\bsite:\S+|\binurl:|\bintitle:|\b\d{6,}\b")
_VERTICAL_MAP = {
    "patent":  re.compile(r"\bpatent(s|ed)?\b", re.IGNORECASE),
    "scholar": re.compile(r"\bscholar(ly)?\b|\bjournal\b|\bdoi\b", re.IGNORECASE),
    "image":   re.compile(r"\bimage(s)?\b|\bphoto(s)?\b", re.IGNORECASE),
    "map":     re.compile(r"\bmap\b|\bnear\s+\w+\b", re.IGNORECASE),
}


def classify_intent(query: str) -> str:
    """heuristic: 'news' | 'semantic' | 'exact' | 'vertical:<kind>' | 'general'

    顺序：vertical > exact > news > semantic > general
    """
    for kind, pat in _VERTICAL_MAP.items():
        if pat.search(query):
            return f"vertical:{kind}"
    if _EXACT_RE.search(query):
        return "exact"
    if _NEWS_RE.search(query):
        return "news"
    if _SEMANTIC_RE.search(query):
        return "semantic"
    return "general"


_INTENT_WEIGHTS: dict[str, dict[str, float]] = {
    "news":              {"news": 3.0, "time_filter": 2.0, "general": 0.5},
    "semantic":          {"semantic": 3.0, "general": 0.5},
    "exact":             {"general": 2.0, "exact": 3.0},
    "vertical:patent":   {"patent": 5.0, "general": 0.5},
    "vertical:scholar":  {"scholar": 5.0, "semantic": 1.0, "general": 0.5},
    "vertical:image":    {"image": 5.0, "general": 0.5},
    "vertical:map":      {"map": 5.0, "general": 0.5},
    "general":           {"general": 1.5, "news": 1.0, "semantic": 1.0},
}


def rank_providers(
    providers: Iterable[Provider],
    *,
    intent: str,
) -> list[Provider]:
    """按 intent 给 provider 打分并排序，过滤不 healthy 的。"""
    weights = _INTENT_WEIGHTS.get(intent, _INTENT_WEIGHTS["general"])
    scored: list[tuple[float, Provider]] = []
    for p in providers:
        if not p.healthy():
            continue
        score = sum(w for cap, w in weights.items() if cap in p.capabilities)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]
