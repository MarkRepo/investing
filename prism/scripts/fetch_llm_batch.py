"""承重漏判主动取数（LLM 通道，同步 CLI）。

对登记表里 importance==load_bearing 且 availability==llm 且 observed.value 为空 的输入，
逐条拉起 headless `claude -p` 做 web 检索取数 + 判可否脚本化，回写 registry。复用既有机制、零重造：
  - 提示词：monitor_runtime._build_macro_llm_prompt（已含「绝不编造、判 scriptable+note」）
  - 拉起：claude_runner.run_headless（同步；继承 env 以启用 web-search）
  - 末尾 JSON 解析：macro_jobs._parse_json_payload
  - 回写：macro_registry.record_observation（含 value=null 诚实留空）+ flag_scriptable（promote 闸门）

与 web 端单条 ⟳ 行为一致，只是批量、同步、可在终端直接看逐条结果与成本。取不到的诚实留空，不污染。

用法：
  python -m prism.scripts.fetch_llm_batch [slug] [variant] [--dry-run] [--limit N] [--only 名1 名2 ...]
"""
from __future__ import annotations

import argparse
import json
import sys

from app import macro_jobs
from app.monitor_runtime import _build_macro_llm_prompt
from prism.scripts import claude_runner
from prism.scripts import macro_registry as reg


def select_targets(slug: str, variant: str) -> list[dict]:
    """承重漏判无数据项：load_bearing + llm + observed.value 为空。"""
    data = reg.read_registry(slug, variant)
    out = []
    for e in data["inputs"]:
        if e.get("importance") != "load_bearing":
            continue
        if e.get("availability") != "llm":
            continue
        if (e.get("observed") or {}).get("value") is not None:
            continue
        out.append(e)
    return out


def _extract_text_and_cost(proc) -> tuple[str, float | None]:
    """run_headless(--output-format json) 的 stdout 是 result 信封；取其 result 文本 + cost。
    解析不出信封则把整段 stdout 当文本、cost=None（仍可喂 _parse_json_payload 兜底）。"""
    raw = proc.stdout or ""
    try:
        env = json.loads(raw)
        if isinstance(env, dict) and "result" in env:
            return env.get("result") or "", env.get("total_cost_usd")
    except json.JSONDecodeError:
        pass
    return raw, None


def fetch_one(slug: str, variant: str, entry: dict, *, model: str) -> dict:
    """对单条 entry 拉起 LLM 取数并回写。返回本条结果摘要（供打印）。"""
    name = entry["name"]
    prompt = _build_macro_llm_prompt(slug, variant, [entry])
    proc = claude_runner.run_headless(
        prompt,
        extra_args=["--model", model, "--output-format", "json",
                    "--disallowedTools", ",".join(macro_jobs.DISALLOWED_TOOLS)],
    )
    if proc.returncode != 0:
        return {"name": name, "status": "failed",
                "error": (proc.stderr or "")[:200] or f"rc={proc.returncode}"}
    text, cost = _extract_text_and_cost(proc)
    items = macro_jobs._parse_json_payload(text)
    if items is None:
        return {"name": name, "status": "no_json", "cost": cost}

    # 选定本条对应的 item：prompt 只问一条 → 单 item 直接采用（容忍 LLM 简写名）；
    # 多 item 才按名精确匹配（少见，如 LPR 1Y/5Y 拆两条时回退）。
    dicts = [it for it in items if isinstance(it, dict)]
    if len(dicts) == 1:
        item = dicts[0]
    else:
        item = next((it for it in dicts if it.get("name") == name), None)

    result = {"name": name, "status": "ok", "cost": cost,
              "value": None, "as_of": None, "scriptable": False}
    if not dicts:
        result["status"] = "empty"  # LLM 返空数组/无对象 = 诚实没查到，不落值
        return result
    if item is None:
        result["status"] = "name_mismatch"  # 多 item 且无一名字对得上 → 诚实不落
        return result
    value = item.get("value")
    as_of = item.get("as_of")
    try:
        reg.record_observation(slug, variant, name, value=value, as_of=as_of,
                               evidence=item.get("evidence"), acq_note=item.get("acq_note"))
    except Exception as e:
        return {"name": name, "status": "write_error", "error": str(e), "cost": cost}
    result["value"], result["as_of"] = value, as_of
    if item.get("scriptable") and value is not None:
        try:
            promoted = reg.flag_scriptable(slug, variant, name, note=item.get("note") or "")
            result["scriptable"] = bool(promoted)
        except Exception:
            pass
    return result


def run(slug: str, variant: str, *, dry_run: bool = False,
        limit: int | None = None, only: set[str] | None = None) -> list[dict]:
    targets = select_targets(slug, variant)
    if only is not None:
        targets = [e for e in targets if e["name"] in only]
    if limit is not None:
        targets = targets[:limit]

    print(f"承重漏判无数据项（load_bearing + llm + 无值）：{len(targets)} 条")
    for e in targets:
        print(f"  · {e['name']}")
    if dry_run:
        print("（--dry-run：不实拉）")
        return []
    if not targets:
        return []

    model = macro_jobs.MACRO_FETCH_MODEL
    print(f"\n用模型 {model} 逐条拉取（headless web 检索，有 token 成本）…\n")
    results = []
    total_cost = 0.0
    for i, e in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {e['name']} …", flush=True)
        r = fetch_one(slug, variant, e, model=model)
        results.append(r)
        if r.get("cost"):
            total_cost += r["cost"]
        val = r.get("value")
        tag = "✓值" if val is not None else "○空"
        scr = " ↑scriptable" if r.get("scriptable") else ""
        cost = f" ${r['cost']:.4f}" if r.get("cost") else ""
        print(f"     {r['status']} {tag}={val!r} as_of={r.get('as_of')!r}{scr}{cost}")
    got = sum(1 for r in results if r.get("value") is not None)
    print(f"\n汇总：{len(results)} 条拉取，{got} 条落值，"
          f"{sum(1 for r in results if r.get('scriptable'))} 条升 scriptable_todo，"
          f"总成本 ${total_cost:.4f}")
    return results


def main(argv=None):
    p = argparse.ArgumentParser(description="承重漏判 LLM 主动取数")
    p.add_argument("slug", nargs="?", default="global-macro-rates-liquidity")
    p.add_argument("variant", nargs="?", default="opus4.8")
    p.add_argument("--dry-run", action="store_true", help="只列目标，不实拉")
    p.add_argument("--limit", type=int, default=None, help="最多拉前 N 条（控本）")
    p.add_argument("--only", nargs="*", default=None, help="仅拉这些输入名")
    a = p.parse_args(argv if argv is not None else sys.argv[1:])
    run(a.slug, a.variant, dry_run=a.dry_run, limit=a.limit,
        only=set(a.only) if a.only else None)


if __name__ == "__main__":
    main()
