# Dispatch 合并规则（annual / quarterly / sell-side 共用）

**场景**：预处理切出多个 `name` 相同的 section（典型：`_section_fallback` 把研报正文多个子章节归入同一通道；或 A 股年报多个附录段同被归类）。默认"每个 section 派一个 subagent"在这种场景下并发浪费 + 视野窄，应合并派单。

## 合并决策树

对每个 `action: extract` 的 section 集合，按 `name` 分组后逐组处理：

```
if count == 1:
    独立派（无合并空间）

elif name == "investment_thesis" and count >= 2:
    # 方案 C：研报 thesis 类专属——默认按一级章节号分组（不再全合并）
    # 原因：研报 thesis 细分子节各自主题不同，全合并成一个大 prompt 会
    # 稀释 claim 抽取的 atomic 质量，并让 arena checklist 填答失去按
    # heading 主题路由的机会。所以即便合并总 chars ≤ 50K，也默认按章节号分派。
    按一级章节号分组 → 每组 ≤ 50K 内合并派 1 个 subagent，组间并发
    subagent_results key = {name}__lvl{一级号} / {name}__misc

elif count >= 2 and total_chars <= 50000:
    # 方案 A：全合并
    派 1 个 subagent，prompt 里 section_text 用下列格式拼接：
    
        ### {heading_raw_1}
        {text_1}
        
        ### {heading_raw_2}
        {text_2}
        
        ...

elif count >= 2 and total_chars > 50000:
    # 方案 B：按一级章节号分组再合并
    对每个 section，从 heading_raw 开头抽"一级章节号"：
      - "1.1 股权结构..."   → 一级号 "1"
      - "1.2 营收..."       → 一级号 "1"
      - "2.1 行业..."       → 一级号 "2"
      - "投资要点"           → 无号 → 独立成组
      - "4 投资建议"         → 一级号 "4"
    
    对每个子组：
      if sub_total <= 50000:
          子组内合并派 1 个 subagent
      else:
          子组内每个 section 独立派（这一组无法再降级）
```

**一级章节号提取正则**（`heading_raw` 开头）：`^\s*(\d+)(?:\.\d+)?\s+`。group(1) 为一级号；未匹配的 heading（如"投资要点"）单独成一组。

## 阈值 50,000 chars 的取舍

- ≤ 50K：单次 LLM 调用健康处理，输出质量稳定
- 50K-100K：还能跑但 Explore subagent 容易做多余 tool-use 兜圈子
- > 100K：有实测卡死先例（HIMS 10-Q Risk Factors 203K → 600s 超时）

50K 是保守线。如果实际出现"按一级章节分组后仍 >50K 需要降级"的场景足够多，再调高或引入 routing-level 的 `merge_threshold` 字段覆盖。

## name 冲突处理

合并多个同名 section 成一份派单后，在 `subagent_results` 字典里**不能**用 `name` 原样作 key（冲突）。用后缀区分：

- 方案 A（全合并）→ key = `{name}` （唯一，无冲突）
- 方案 B（按一级号分组）→ key = `{name}__lvl{一级号}` / `{name}__misc`（例：`investment_thesis__lvl1` / `investment_thesis__lvl2` / `investment_thesis__misc`）
- 降级到独立派 → key = `{name}__{order}`（order 来自预处理 section.order）

注意：这些后缀只影响 `subagent_results` dict 的 key，**aggregate 的输出里 claims 没有 section 字段**，最终 claims.jsonl 完全不受影响。

## 触发 oversize_action 的交互

`section-routing.yaml` 的 `max_chars` / `oversize_action: skip` 在**合并决策之前**生效——任何单个 section 超 `max_chars` 直接按 oversize_action 处理（skip 记 flag），不进入合并流程。合并决策只对"通过 oversize 检查的剩余 section"做。

## Worked examples

### 本轮太湖远大（方案 C：investment_thesis 默认按章节号分派）

```
name                     count   total_chars
investment_thesis        10      32,418      → 按一级章节号分组
  1.1/1.2/1.3           18,000  → thesis__lvl1 合并派 1
  2.1/2.2/2.3/2.4       15,000  → thesis__lvl2 合并派 1
  3.1/3.2/3.3           8,000   → thesis__lvl3 合并派 1
  "投资要点"             3,000   → thesis__misc 合并派 1（无一级号）
valuation                1       870         → 独立派 1
risk_section             1       3,661       → 独立派 1
                                              ────
                                              共 5-6 个并发（而非原规则的 3 个）
```

**为什么**：
- claim 抽取上——10 个 thesis 子节压成 1 prompt 会稀释 atomic 质量；按章节号分派后每个子 subagent 处理单一主题，claim 数量和聚焦度都更好
- arena checklist 填答上——每个子 subagent 的 heading 主题清晰，主 agent 可按 heading → tag 语义路由 checklist item 到对应子 subagent，避免 thesis 一个 subagent 拿全量 item

### 假设情况：某深度研报 thesis 合计 70K（一样走方案 C）

```
投资要点              10,000   → 无号，单独成组（10K ≤ 50K）         → 合并 1
1.1/1.2/1.3           18,000   → 一级号 "1"（18K ≤ 50K）             → 合并 1
2.1/2.2/2.3/2.4       35,000   → 一级号 "2"（35K ≤ 50K）             → 合并 1
3.1/3.2               7,000    → 一级号 "3"（7K ≤ 50K）              → 合并 1
                                                                     ────
                                                                     4 个并发（而非 10 个独立派）
```

### 极端：某行业研报 thesis 合计 200K

```
1.1/1.2/1.3           60,000   → 一级号 "1"（60K > 50K）→ 退回独立派  → 3 个
2.1/2.2               45,000   → 一级号 "2"（45K ≤ 50K）              → 合并 1
3.1/3.2/3.3/3.4       95,000   → 一级号 "3"（95K > 50K）→ 退回独立派  → 4 个
                                                                     ────
                                                                     8 个并发
```

（这种情况通常意味着 routing 该给这个 section 加 `max_chars` + `oversize_action: skip` 从源头拦掉）
