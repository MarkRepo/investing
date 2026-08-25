#!/bin/zsh
# W-A 覆盖回归闸门：确认三份旧 case 路径里的"原子"在新文件集里一个不少。
# 用法：
#   ./prism/scripts/wa_coverage_check.sh --baseline          # 生成 /tmp/wa_baseline.txt
#   ./prism/scripts/wa_coverage_check.sh <新文件...>          # 校验覆盖
set -e
cd "$(dirname "$0")/../.."
OLD=(prism/workflows/04-synthesize/_company_case.md
     prism/workflows/04-synthesize/_industry_funnel.md
     prism/workflows/04-synthesize/_arena_funnel.md)
# 忽略清单：json.dumps 的 kwarg（非 prism 符号）+ 被替换掉的三个旧文件名自引用
IGNORE='ensure_ascii|_company_case\.md|_industry_funnel\.md|_arena_funnel\.md'

extract() {
  cat "$@" > /tmp/_wa_all.txt
  grep -ohE '\b(set|get|mark|list|read|write|register|validate|detect|build|format|ensure|resolve|append|update|create|next|primer|empty|pending|verify|extract|record|latest|find)_[a-z_]+' /tmp/_wa_all.txt \
    | sort -u | sed 's/^/SYM /'
  grep -ohE '`[_A-Za-z0-9./-]+\.(md|yaml|py)`|\[\[[_a-z0-9-]+\]\]' /tmp/_wa_all.txt \
    | tr -d '`' | sort -u | sed 's/^/REF /'
  grep -ohE '^(- )?【必带硬落地[^】]*】.{0,24}|^  ?[0-9]\. \*\*[^*]{4,30}\*\*|^- \*\*【[^】]+】\*\*.{0,20}' /tmp/_wa_all.txt \
    | sed -E 's/[[:space:]]+/ /g' | sort -u | sed 's/^/HARD /'
}

if [[ "$1" == "--baseline" ]]; then
  extract "${OLD[@]}" | grep -vE "$IGNORE" > /tmp/wa_baseline.txt
  echo "baseline: $(wc -l < /tmp/wa_baseline.txt) atoms → /tmp/wa_baseline.txt"
  exit 0
fi

[[ -f /tmp/wa_baseline.txt ]] || { echo "先跑 --baseline"; exit 2; }
cat "$@" > /tmp/_wa_new.txt
missing=0
while IFS= read -r line; do
  atom="${line#* }"
  grep -qF -- "$atom" /tmp/_wa_new.txt || { echo "MISSING  $line"; missing=$((missing+1)); }
done < /tmp/wa_baseline.txt
if (( missing > 0 )); then
  echo "❌ $missing / $(wc -l < /tmp/wa_baseline.txt) atoms 缺失"
  exit 1
fi
echo "✅ 全部 $(wc -l < /tmp/wa_baseline.txt) atoms 覆盖"
