"""headless LLM 取数的落盘 CLI（带 promote 闸门）。零 LLM 本身——只是给 headless claude
一个干净、带闸门的写工具，定时监控与 web 手动两路共用。

用法：
  python -m prism.scripts.macro_record <slug> <variant> <name> \\
      --value <float> --as-of <date> --evidence "<引文/采用源>" \\
      [--scriptable --note "<缺什么 recipe>"]

内部：record_observation(value/as_of/evidence)；--scriptable 时调 flag_scriptable（promote 闸门
在 macro_registry：仅 availability=='llm' 且已落到 value 才升 scriptable_todo）。
--value 缺省则只记 evidence（如 event/policy 立场项无数值），--scriptable 自动失效（闸门拦下）。
"""
from __future__ import annotations

import argparse
import sys

from prism.scripts import macro_registry as reg


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(prog="macro_record", description="headless LLM 取数落盘（带 promote 闸门）")
    p.add_argument("slug")
    p.add_argument("variant")
    p.add_argument("name", help="输入名（登记表唯一键）")
    p.add_argument("--value", type=float, default=None, help="抓到的数值（缺省则只记 evidence）")
    p.add_argument("--as-of", dest="as_of", default=None, help="观测对应日期 YYYY-MM-DD")
    p.add_argument("--evidence", default=None, help="采用源/引文（尤其 search 模式必填）")
    p.add_argument("--acq-note", dest="acq_note", default=None,
                   help="本次取数/可否脚本化的判定留痕（无论是否 --scriptable 都写入 observed.acq_note）")
    p.add_argument("--scriptable", action="store_true",
                   help="判定该源可脚本化 → 试图 promote llm→scriptable_todo（闸门：须已落到 value）")
    p.add_argument("--note", default="", help="--scriptable 时写入的 note（缺什么 recipe）")
    args = p.parse_args(argv)

    reg.record_observation(
        args.slug, args.variant, args.name,
        value=args.value, as_of=args.as_of, evidence=args.evidence,
        acq_note=args.acq_note,
    )
    promoted = False
    if args.scriptable:
        promoted = reg.flag_scriptable(args.slug, args.variant, args.name, note=args.note)

    print(f"recorded {args.name!r}: value={args.value} as_of={args.as_of} "
          f"evidence={'有' if args.evidence else '无'} | promoted_to_scriptable_todo={promoted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
