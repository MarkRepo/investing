#!/bin/zsh
# W-F 覆盖闸门：产物瘦身四项的回归护栏。
#   ZERO 检查 = 消费端/早写口必须归零（改前应 FAIL，证明闸门能捕捉 pre-state）
#   KEEP 检查 = 必保行为不能被误删（改前后都应 PASS）
# 用法：./prism/scripts/wf_coverage_check.sh            # 跑全部（items 1-4）
#       ./prism/scripts/wf_coverage_check.sh 13         # 只跑 items 1-3（commit 1 用）
cd "$(dirname "$0")/../.."
SCOPE="${1:-all}"
fail=0

# cnt <pattern> <path...> — 统计匹配行数（-r 递归，排除闸门脚本自身，无匹配返回 0 不报错）
cnt() { grep -rInE --exclude=wf_coverage_check.sh "$1" "${@:2}" 2>/dev/null | wc -l | tr -d ' '; }

zero() {  # zero <label> <count>   期望 0
  if [[ "$2" == "0" ]]; then echo "  ✅ ZERO  $1  (=0)"; else echo "  ❌ ZERO  $1  (=$2, 期望 0)"; fail=$((fail+1)); fi
}
keep() {  # keep <label> <count>   期望 >=1
  if [[ "$2" -ge 1 ]]; then echo "  ✅ KEEP  $1  (=$2)"; else echo "  ❌ KEEP  $1  (=$2, 期望 ≥1)"; fail=$((fail+1)); fi
}

if [[ "$SCOPE" != "4" ]]; then
  echo "── ITEMS 1-3 ──────────────────────────────────────────"
  # Item 1: _synthesis_brief 退休（workflow 无落盘指令、脚本/app 无消费端）
  zero "item1 workflow 无 _synthesis_brief 落盘"  "$(cnt '_synthesis_brief' prism/workflows)"
  zero "item1 scripts/app 无 synthesis_brief 消费" "$(cnt 'synthesis_brief' prism/scripts app)"
  keep "item1 v0→v1 强度校准指令仍在"             "$(cnt 'v0→v1 强度' prism/workflows/04-synthesize)"
  # Item 2: 08_living_feed 移出 _DECISION_CHAIN_OUTPUTS（topic.py 注册表/兜底/docstring 归零）
  zero "item2 注册表无 \"08_living_feed\""          "$(cnt '\"08_living_feed\"' prism/scripts/topic.py)"
  keep "item2 monitor append 仍在"                 "$(cnt '_append_living_feed' prism/scripts/monitor.py)"
  keep "item2 living_feed 展示 label 保留(outputs)" "$(cnt '08_living_feed' prism/scripts/outputs.py)"
  keep "item2 living_feed 展示 label 保留(routes)"  "$(cnt '08_living_feed' app/routes/prism.py)"
  # Item 3: 停 per-topic 复制 + web canonical 回落
  zero "item3 无 cp _reading_guide_canonical 复制步" "$(cnt 'cp .*_reading_guide_canonical' prism/workflows)"
  keep "item3 canonical 被 web IO 渲染"             "$(cnt '_reading_guide_canonical' prism/scripts/outputs.py)"
fi

if [[ "$SCOPE" != "13" ]]; then
  echo "── ITEM 4 (A6) ────────────────────────────────────────"
  # 早写口（delta 空即 set_decomposition(version=1) 内联调用）归零
  zero "item4 _shared.md 无 delta 空早写口"        "$(cnt 'set_decomposition\(version=1' prism/workflows/04-synthesize/_shared.md)"
  # 收尾/§4 单点落盘仍在（多行形式 set_decomposition( 换行 version=1）
  keep "item4 收尾单点 set_decomposition 仍在"      "$(cnt 'set_decomposition\(' prism/workflows/04-synthesize/_shared.md)"
fi

echo "───────────────────────────────────────────────────────"
[[ -f prism/workflows/_reading_guide_canonical.md ]] && echo "  ✅ canonical 源文件存在" || { echo "  ❌ canonical 源文件缺失"; fail=$((fail+1)); }
if (( fail > 0 )); then echo "❌ $fail 项未过"; exit 1; else echo "✅ 全绿"; exit 0; fi
