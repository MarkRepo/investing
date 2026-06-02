"""模型登记表 — 变体名（= 目录名 = 路径身份）的规范化与父变体兜底选择。

单一维护点：换模型重研时变体目录名应是模型 id（全 model-id 式）。历史目录命名
分裂（同一 Opus 4.8 既有 `claude-opus-4-8` 又有 `opus4.8`），靠本表的别名做
**运行时识别**——绝不重命名磁盘目录、绝不在 `_topic_path`/`_topic_dir` 里归一。

零副作用、零 LLM。拿不准的判断（多个异模型父该借哪个）由 resolve_parent_variant
返回 confident=False + candidates，交主 agent 在对话里问用户。

新增模型：在 REGISTRY 加一行；调兜底优先级改 rank（越大越优先）。
"""
from __future__ import annotations

# 规范名 → {aliases, rank}。rank 越大越优先作兜底（借异模型父时取最高）。
REGISTRY: dict[str, dict] = {
    "claude-opus-4-8": {"aliases": ["opus4.8", "opus-4.8"],     "rank": 100},
    "claude-opus-4-7": {"aliases": ["opus4.7", "opus-4.7"],     "rank": 90},
    "deepseek-v4-pro": {"aliases": ["deepseek-v4", "deepseek"], "rank": 70},
    "gpt-5-4":         {"aliases": ["gpt-5.4", "gpt5.4"],       "rank": 60},
    "qwen3-6-plus":    {"aliases": ["qwen3.6-plus", "qwen3.6"], "rank": 50},
    "gemini":          {"aliases": [],                          "rank": 40},
    "doubao2.0code":   {"aliases": ["doubao2.0", "doubao"],     "rank": 30},
}

# 别名 → 规范名（含规范名自身）。模块加载时一次性建立。
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canon, _meta in REGISTRY.items():
    _ALIAS_TO_CANONICAL[_canon] = _canon
    for _a in _meta.get("aliases") or []:
        _ALIAS_TO_CANONICAL[_a] = _canon


def canonical(name: str) -> str:
    """别名/规范名 → 规范名；未登记原样返回（不抛、不猜）。"""
    if not isinstance(name, str):
        return name
    return _ALIAS_TO_CANONICAL.get(name, name)


def is_known(name: str) -> bool:
    """是否登记在册（别名或规范名）。"""
    return isinstance(name, str) and name in _ALIAS_TO_CANONICAL


def rank(name: str) -> int | None:
    """规范名/别名的兜底优先级；未登记返 None。"""
    canon = canonical(name)
    meta = REGISTRY.get(canon)
    return meta["rank"] if meta else None


def same_model(a: str, b: str) -> bool:
    """两个变体名是否同一模型（桥接 `opus4.8` ≡ `claude-opus-4-8`）。

    未登记名只与字面相等者算同一（passthrough，不误并）。
    """
    if not isinstance(a, str) or not isinstance(b, str):
        return False
    return canonical(a) == canonical(b)


def resolve_parent_variant(child_variant: str, parent_variants: list[str]) -> dict:
    """为子变体在父 topic 的多个变体里挑一个复用源。

    返回 {chosen, confident, candidates, reason}：
      - chosen: 选中的父变体目录名（保持磁盘原样，不归一）；无可选时 None。
      - confident: True 表示可放心自动用；False 表示拿不准，主 agent 须问用户。
      - candidates: 供问用户时展示的候选列表（confident=False 时非空）。
      - reason: 选择理由（人读）。

    判定顺序（对应 plan 五分支）：
      1. 父无变体 → None / False。
      2. 有同模型变体 → 选它 / True（同名优先）。
      3. 仅一个变体 → 选它 / True（无可比，唯一即取）。
      4. 多个、无同模型、但全部登记 → rank 最高 / True（借异模型父，reason 注明）。
      5. 多个、无同模型、且含未登记 → None / False，列 candidates 交主 agent 问用户。
    """
    pvs = [v for v in (parent_variants or []) if isinstance(v, str) and v]
    if not pvs:
        return {"chosen": None, "confident": False, "candidates": [],
                "reason": "父 topic 无任何变体"}

    # 2. 同模型优先（桥接命名分裂）
    same = [v for v in pvs if same_model(v, child_variant)]
    if same:
        chosen = _pick_among_same(child_variant, same)
        return {"chosen": chosen, "confident": True, "candidates": [],
                "reason": f"同模型变体（{canonical(child_variant)}）"}

    # 3. 唯一
    if len(pvs) == 1:
        return {"chosen": pvs[0], "confident": True, "candidates": [],
                "reason": "父仅一个变体，唯一即取"}

    # 4/5. 多个异模型
    if all(is_known(v) for v in pvs):
        best = max(pvs, key=lambda v: (rank(v), v))
        return {"chosen": best, "confident": True, "candidates": list(pvs),
                "reason": f"无同模型父，按 rank 借最高优先级异模型父 {best!r}"}

    return {"chosen": None, "confident": False, "candidates": list(pvs),
            "reason": "多个异模型父且含未登记变体，拿不准——请主 agent 问用户显式指定"}


def _pick_among_same(child_variant: str, same: list[str]) -> str:
    """同模型多变体里挑一个：精确同名 > 规范名命中 > 字典序，保证确定性。"""
    if child_variant in same:
        return child_variant
    canon = canonical(child_variant)
    if canon in same:
        return canon
    return sorted(same)[0]
