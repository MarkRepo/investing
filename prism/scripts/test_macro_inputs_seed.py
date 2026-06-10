"""无遗漏闸：macro_inputs.yaml 必须覆盖 spec §3 表的每一行，且通过机制 validator。

源真相 = spec 文件的 §3 表。本测试解析 spec §3 各表的"输入"列（首列），断言每个
输入名都在登记表里出现（去 ** 与空白后比对）。这把"框架完整性"钉死在外部文档上，
直接兑现用户"输入不能有遗漏"的硬要求。
"""
import re
from pathlib import Path

import pytest

from prism.scripts import macro_registry as mr

SLUG = "global-macro-rates-liquidity"
VARIANT = "opus4.8"
_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC = _ROOT / "docs/superpowers/specs/2026-06-07-macro-dynamic-monitoring-and-maturation-design.md"


def _clean(cell: str) -> str:
    return cell.replace("**", "").strip()


def _spec_input_names() -> list[str]:
    """抽 §3 各表首列输入名。§3 起于 '## 3.'，止于 '## 4.'。"""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("## 3. ")
    end = text.index("## 4. ")
    block = text[start:end]
    names: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c for c in line.split("|")]
        # 去掉首尾空串
        cells = cells[1:-1] if len(cells) >= 2 else cells
        if not cells:
            continue
        first = _clean(cells[0])
        # 跳过表头与分隔行
        if first in ("输入", "") or set(first) <= set("-: "):
            continue
        names.append(first)
    return names


def test_spec_block_parsing_sane():
    names = _spec_input_names()
    # §3 表约 114 行；低于 110 说明解析漏了块或 spec 被改瘦
    assert len(names) >= 110, f"只解析到 {len(names)} 个输入名，疑似漏块"
    assert "非农就业 NFP" in names
    assert "结售汇 + 外汇占款 + 代客涉外收付" in names


def test_registry_covers_every_spec_input():
    reg_names = {i["name"] for i in mr.read_registry(SLUG, VARIANT)["inputs"]}
    missing = [n for n in _spec_input_names() if n not in reg_names]
    assert missing == [], f"登记表遗漏 {len(missing)} 个 spec 输入：{missing}"


def test_seed_registry_passes_validator():
    errors = mr.validate_registry(SLUG, VARIANT)
    assert errors == [], f"登记表机制纪律不过：{errors}"


def test_alert_series_only_on_autofed_inputs():
    """越带报警只挂在能自动取数的输入上。MOVE/基差/DR007/CNH-CNY 因无可脚本化的
    免费结构化源(avail=llm)关带,降级为到期人工看——否则 observed.value 永不更新、
    报警永不触发(死带)。本测试同时作为'不许再有死带'的不变量。"""
    inputs = mr.read_registry(SLUG, VARIANT)["inputs"]
    alert = {i["name"] for i in inputs if i.get("alert_series")}
    assert alert == {"HY OAS", "USDJPY / 日元 carry"}, f"越带集合变了: {alert}"
    # 不变量：凡开越带，必须自动抓得到（fred-api 或 已写 recipe 的 scripted），不得是死带
    for i in inputs:
        if i.get("alert_series"):
            auto = i.get("fetch_method") == "fred-api" or (
                i.get("availability") == "scripted" and i.get("fetch_recipe"))
            assert auto, f"死带：{i['name']} 开了 alert_series 却不自动抓数"
