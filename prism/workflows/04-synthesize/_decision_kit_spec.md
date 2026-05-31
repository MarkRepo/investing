# 决策套件 sidecar 规范 — `07_decision_kit.yaml`

> **工具规范，非独立产出步骤。** company 的决策叙事由 `_company_case.md` 的 6 环决策链写进 `c_investment_case`；本文件只定义随 case 落盘的 **machine-readable sidecar**（`07_decision_kit.yaml`，dashboard 直接消费）的字段 schema。由 `_company_case.md` Step 4 + `_shared.md` 调度模式**逐字引用**（查 schema，不照搬结构）。industry / arena 的同性质规范见 `_arena_select_spec.md` / `_peer_matrix_spec.md`。

**output_key**：`07_decision_kit`　|　**文件**：`prism/topics/{slug}/{variant}/outputs/07_decision_kit.yaml`（随 case 由主 agent 直接 Write；文件名固定，即使本规范文档已改名也不变）

---

## Step 2.5：填写 data_freshness

写进 sidecar（及 case frontmatter）：
- `data_freshness`: 用到的最晚数据所在期（季度/月份）
- `data_freshness_basis`: 该期来自哪份 finding

---

## Step 3.5：sidecar YAML schema（严格 · dashboard 直接消费 · 禁自创字段）

写入文件：`prism/topics/{slug}/{variant}/outputs/07_decision_kit.yaml`

从决策链 case（环②/④/⑤/⑥）提取以下字段，写成严格 YAML。**所有数字不加引号，缺失用 null，日期统一格式（年 "2026"、季度 "2026-Q2"、月份 "2026-08"、具体日 "2026-08-27"）。**

```yaml
slug: {slug}
variant: {variant}
topic_type: {type}           # company / arena / industry
display_name: {display_name}
ticker: {ticker}             # "SZSE_001270" 格式；非 company 留空 ""
generated: {ISO8601 timestamp}
data_freshness: {date}       # 同 frontmatter

# ── 仅 company type 填写以下字段 ─────────────────────────
buy_box:
  strong_buy_max: {number or null}      # 强力买入上限价格
  accumulate_min: {number or null}      # 可建仓下限
  accumulate_max: {number or null}      # 可建仓上限
  hold_min: {number or null}            # 观望下限
  hold_max: {number or null}            # 观望上限（超过视为 above_hold）
  current_price: {number}
  price_as_of: {date}
  current_zone: {strong_buy|accumulate|hold|above_hold|unknown}

position_framework:
  initial_max_pct: {number}             # 首仓上限 %
  full_max_pct: {number}                # 满仓上限 %
  add_ladder_prices: [{number}, ...]    # 加仓阶梯价格列表，升序
  max_cluster_pct: {number or null}     # 主题集中度约束 %

# 估值模型汇总（来自决策链②估值锚，每个模型独立）
valuation_models:
  - name: {snake_case_id}              # e.g. reverse_pe_dcf
    label: {显示名称}
    bull_fair_value: [{low}, {high}]   # null 表示无上界
    base_fair_value: [{low}, {high}]
    bear_fair_value: [{low or null}, {high or null}]
  # 追加更多模型...
# ── 所有 type 填写以下字段 ─────────────────────────────────

kill_criteria:
  - id: {snake_case_id}
    description: {一句话描述触发条件}
    status: pending                    # pending / triggered_bull / triggered_bear / expired
    check_at: {date}                   # 预计验证时间点

signposts:
  - date: {date}
    event: {事件描述}
    bull_signal: {多方信号}
    bear_signal: {空方信号}
    triggered: null                    # null=pending, "bull", "bear"

# 主题标签（用于跨 topic 相关性分组）
cluster_tags: [{tag1}, {tag2}]        # e.g. [ai-compute, china-defense]
```

**写入命令：**

```bash
python3 -c "
from pathlib import Path
import yaml

content = '''
{上面填好的 yaml 内容}
'''
path = Path('prism/topics/{slug}/{variant}/outputs/07_decision_kit.yaml')
path.write_text(content, encoding='utf-8')
print('sidecar 写入完成')
"
```
