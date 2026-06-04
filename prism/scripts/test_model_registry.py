#!/usr/bin/env python3
"""model_registry 单测 — 纯函数，无需 sandbox。

覆盖：canonical（别名/规范名/passthrough）、is_known、rank、same_model 桥接、
resolve_parent_variant 全 5 分支。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from prism.scripts import model_registry as mr


# --- canonical / is_known / rank -------------------------------------------

def test_canonical_alias_to_canonical():
    assert mr.canonical("opus4.8") == "opus4.8"                    # 规范名自身（短名）
    assert mr.canonical("opus-4.8") == "opus4.8"                   # 别名 → 规范名
    assert mr.canonical("claude-opus-4-8") == "opus4.8"           # 旧 model-id 现为别名
    assert mr.canonical("opus4.7") == "claude-opus-4-7"           # 其余模型仍全 model-id 规范名


def test_canonical_passthrough_unknown():
    assert mr.canonical("totally-unknown") == "totally-unknown"   # 未登记原样返回


def test_is_known():
    assert mr.is_known("opus4.8") is True
    assert mr.is_known("claude-opus-4-8") is True
    assert mr.is_known("totally-unknown") is False


def test_rank():
    assert mr.rank("claude-opus-4-8") == 100
    assert mr.rank("opus4.8") == 100          # 别名同 rank
    assert mr.rank("totally-unknown") is None


# --- same_model 桥接 --------------------------------------------------------

def test_same_model_bridges_naming_split():
    assert mr.same_model("opus4.8", "claude-opus-4-8") is True
    assert mr.same_model("claude-opus-4-8", "opus-4.8") is True


def test_same_model_distinct():
    assert mr.same_model("claude-opus-4-8", "claude-opus-4-7") is False
    assert mr.same_model("gpt-5-4", "gemini") is False


def test_same_model_unknown_only_literal():
    assert mr.same_model("foo", "foo") is True       # 未登记仅字面相等算同
    assert mr.same_model("foo", "bar") is False


# --- resolve_parent_variant 五分支 -----------------------------------------

def test_resolve_branch1_empty():
    res = mr.resolve_parent_variant("claude-opus-4-8", [])
    assert res["chosen"] is None
    assert res["confident"] is False


def test_resolve_branch2_same_model():
    # 父有同模型变体（命名分裂）→ 选它、confident
    res = mr.resolve_parent_variant("claude-opus-4-8", ["opus4.8", "claude-opus-4-7"])
    assert res["chosen"] == "opus4.8"
    assert res["confident"] is True


def test_resolve_branch2_same_model_prefers_exact():
    res = mr.resolve_parent_variant("claude-opus-4-8", ["opus4.8", "claude-opus-4-8"])
    assert res["chosen"] == "claude-opus-4-8"   # 精确同名优先
    assert res["confident"] is True


def test_resolve_branch3_unique():
    # 仅一个变体、异模型 → 唯一即取、confident
    res = mr.resolve_parent_variant("gpt-5-4", ["claude-opus-4-8"])
    assert res["chosen"] == "claude-opus-4-8"
    assert res["confident"] is True


def test_resolve_branch4_multi_all_known_by_rank():
    # 多个、无同模型、全登记 → rank 最高、confident
    res = mr.resolve_parent_variant("gpt-5-4", ["claude-opus-4-7", "claude-opus-4-8"])
    assert res["chosen"] == "claude-opus-4-8"   # rank 100 > 90
    assert res["confident"] is True


def test_resolve_branch5_multi_with_unknown_asks_user():
    # 多个、无同模型、含未登记 → 拿不准、列候选
    res = mr.resolve_parent_variant("gpt-5-4", ["claude-opus-4-8", "foo-unknown"])
    assert res["chosen"] is None
    assert res["confident"] is False
    assert set(res["candidates"]) == {"claude-opus-4-8", "foo-unknown"}
