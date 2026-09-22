"""surf · 把卡片里的个股注册进 companies/，使其能跳 /prices 与 /financials。

**最小化动作**：只写 `companies/{MARKET}_{TICKER}/meta.md` 一个文件。
`company_io.list_companies()` 只要求目录名含下划线，`read_meta()` 只读 meta.md 的
frontmatter —— 不需要 v0.md / valuation.md / competence-check.md 那套价值研究脚手架
（`company_io.create_company()` 会铺全套模板，对趋势股是多余的，故不用它）。

frontmatter 打 `source: surf` 标记，与 prism 自己的 company 主题区分开。
已能解析的标的（prism 已有同名 topic）**跳过，不覆盖** —— companies/ 优先级高于
prism topic，覆盖会改掉 prism 列表里的显示名。

零 LLM 调用。用法：
    .venv/bin/python surf/scripts/register_companies.py [--dry-run]
"""
from __future__ import annotations

import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
from scan_stock import SURF  # noqa: E402

CARDS = os.path.join(SURF, "cards")
ROOT = os.path.abspath(os.path.join(SURF, ".."))
COMPANIES = os.path.join(ROOT, "companies")


def _market(code: str, market: str) -> str:
    """surf 的 market 字段 → companies/ 与 /prices 用的交易所代码。"""
    if market == "US":
        return "US"
    if market == "HK":
        return "HKEX"
    if code[:2] in ("60", "68") or code[:1] == "9":
        return "SSE"
    if code[:1] in ("0", "3"):
        return "SZSE"
    return "BSE"


def card_stocks() -> list[dict]:
    out, seen = [], set()
    for slug in sorted(os.listdir(CARDS)):
        path = os.path.join(CARDS, slug, "card.md")
        if not os.path.exists(path):
            continue
        raw = open(path, encoding="utf-8").read()
        if not raw.startswith("---"):
            continue
        for s in (yaml.safe_load(raw.split("---", 2)[1]) or {}).get("stocks") or []:
            code = str(s.get("code", ""))
            if not code or code in seen:
                continue
            seen.add(code)
            mk = _market(code, s.get("market", "CN"))
            out.append({"code": code, "name": s.get("name", code), "market": mk,
                        "key": f"{mk}_{code}", "card": slug})
    return out


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    from app.io import company as company_io

    existing = {c["key"] for c in company_io.list_companies()}
    stocks = card_stocks()
    made, skipped = [], []

    for s in stocks:
        if s["key"] in existing:
            skipped.append(f"{s['name']}({s['key']}) — prism 已覆盖，不覆写")
            continue
        d = os.path.join(COMPANIES, s["key"])
        meta = os.path.join(d, "meta.md")
        if os.path.exists(meta):
            skipped.append(f"{s['name']}({s['key']}) — 已注册")
            continue
        if not dry:
            os.makedirs(d, exist_ok=True)
            with open(meta, "w", encoding="utf-8") as f:
                yaml.safe_dump({"name": s["name"], "ticker": s["code"],
                                "market": s["market"], "source": "surf",
                                "surf_card": s["card"]},
                               f, allow_unicode=True, sort_keys=False)
                # frontmatter 需要首尾分隔线，safe_dump 不带
            body = open(meta, encoding="utf-8").read()
            open(meta, "w", encoding="utf-8").write(
                f"---\n{body}---\n\n> 由 surf 趋势系统注册（卡片 `{s['card']}`），"
                f"**不是 prism 研究标的**。\n> 建这个文件只为打通 /prices 与 /financials 跳转；"
                f"若要做基本面研究，请在 prism 正式开主题。\n")
        made.append(f"{s['name']}({s['key']})")

    print(f"{'[dry-run] ' if dry else ''}新注册 {len(made)} 个：", file=sys.stderr)
    for m in made:
        print(f"  + {m}", file=sys.stderr)
    print(f"跳过 {len(skipped)} 个：", file=sys.stderr)
    for m in skipped:
        print(f"  · {m}", file=sys.stderr)
