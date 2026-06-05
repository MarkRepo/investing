"""Trace → per-topic 诊断页 markdown（仿 dashboard.py）。纯被动 · 零 LLM。

render_diagnostic_page(slug, variant) 调 observability.run_probes 出 Trace，
按贯穿 + 逐 stage 分组渲染，复核旗（flag）单列汇总。供 web 详情页「诊断」标签
（/prism/{slug}/{variant}/trace）直接调用。spec: observability.md §6。
"""
from prism.scripts.observability import run_probes

_BADGE = {"pass": "🟢", "fail": "🔴", "flag": "🟠", "na": "⚪"}


def render_diagnostic_page(slug: str, variant: str) -> str:
    trace = run_probes(slug, variant)
    probes = trace["probes"]
    s = trace["summary"]
    L = [f"# 诊断 · {slug} / {variant}", ""]
    # 体检条
    L.append(f"**体检条**：🔴 {s['fail']} 　🟠 {s['flag']} 　🟢 {s['pass']} 　⚪ {s['na']}")
    L.append("")

    def section(title, rows):
        L.append(f"## {title}")
        L.append("| | 探针 | 检查 | detail | 动作 |")
        L.append("|--|--|--|--|--|")
        for p in rows:
            L.append(f"| {_BADGE[p['status']]} | {p['probe_id']} | {p['label']} "
                     f"| {p['detail']} | {p['action']} |")
        L.append("")

    cc = [p for p in probes if p["stage"] == "cross-cutting"]
    section("贯穿（cross-cutting）", cc)

    stages = ["00", "01", "02", "03", "04", "05", "06"]
    for st in stages:
        rows = [p for p in probes if p["stage"].startswith(st)]
        if rows:
            section(f"Stage {st}", rows)

    flags = [p for p in probes if p["status"] == "flag"]
    L.append("## 复核旗汇总（待人复核）")
    if flags:
        for p in flags:
            L.append(f"- 🟠 **{p['probe_id']}** {p['label']} — {p['detail']}")
    else:
        L.append("- 无")
    return "\n".join(L) + "\n"
