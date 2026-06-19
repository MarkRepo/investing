# Workflow 07 — 深度钻探 (Drill-down)

**触发**：用户说「深挖 {slug} 的 {具体问题}」  
**定位**：对某个具体问题进行专项深度研究，产出专题笔记  
**产出文件**：`prism/topics/{slug}/outputs/drilldown_{timestamp}_{topic_keyword}.md`

---

## Step 1：明确钻探问题 + 深度分级

用户的问题可能是：
- 「深挖 {slug} 的竞争格局」
- 「分析 {slug} 里 {公司名} 的护城河」
- 「中国 vs 海外 {slug} 的格局差异」
- 「{slug} 在利率上行环境的历史表现」

如果问题不够具体，AskUserQuestion 细化。

### 深度分级（quick vs load-bearing）

**分级依据**：本次深挖是日常问答（quick）还是攻 capped 命门 / thin_evidence 薄弱 K# / 可能动摇 thesis（load-bearing）？
- **quick**：用户好奇、不承载 thesis 承重、纯背景探索
- **load-bearing**：深挖问题来自 `suggested_drilldowns`（`source=capped_decomposition` / `critic_weak_k`）/ 攻击 capped 命门 / 补 thin_evidence K# / 结论可能动摇现有 thesis

**判定时机**：用户说「深挖 X」时主 agent 主动判断，若来自 `suggested_drilldowns` 则默认 load-bearing；若是用户自发则默认 quick 但问一句"这个结论会影响 thesis 吗？"

**写入 frontmatter**（Step 4 笔记顶部）：
```yaml
weight: quick   # 或 load-bearing
```

load-bearing 专属：
- Step 3 → 4 之间插单轮自检（见下方 Step 3.5）
- Step 4.6 升级为强制回答"命门解没解决"（见下方）
- Step 4.7 必须闭环 `resolve_suggested_drilldown`

---

## Step 2：评估信息来源

```bash
python3 -c "
from prism.scripts.manifest import read_manifest
import json
data = read_manifest('{slug}')
for m in data['materials']:
    print(m['id'], '|', m['filename'], '|', 'processed' if m['processed'] else 'UNPROCESSED')
"
```

判断：现有资料是否足够回答这个问题，还是需要补充资料。

---

## Step 2b：专项 web-search（**新增**）

若 Step 2 判断"现有 material 不足"——例如 drilldown 需要 "HKEX 2026-09 月 ADV"、"某公司 2026 Q1 经营数据" 这类**高频小数据 / 训练截止后事件**——先跑 `_web_prescan_shared.md`（`recency_days=180`，往回查更长）做专项查询：

- 主 agent 把钻探问题拆成 1-3 条精准 query 喂给 Step B（drilldown 的 query 一律手写，可不跑 `build_search_queries` 覆盖槽枚举——专项深挖问题比通用 scope 槽更聚焦）
- 把 hit 的 addresses 按全局三态约定（参 `_web_prescan_shared.md` 关键纪律 3）填：攻打具体 K# 时填 `['K#']`/`['K#@event']`；thesis 未形成或纯探索性深挖填 `['scope']`；**禁止 `[]`**
- `triggered_by='07-drilldown'`

入库后再回到 Step 3 做深度分析——保溯源链：drilldown 的引文必须来自 manifest 中的 material（含 web-search 入库的），不准直接引 WebSearch 原文。

---

## Step 3：深度分析

使用训练知识 + 已有 findings，对问题进行深度分析：

- 结构：问题分解 → 每个子问题的分析 → 综合结论
- 要求：比 case 各环（环①-⑥）更深、更具体
- 字数：不限，以回答清楚问题为准

### Step 3.5：load-bearing 单轮自检（仅 weight=load-bearing 跑 · quick 跳过）

> load-bearing 深挖质量不稳的根因——缺独立校验、全靠 Step 4.6 软自评。本步加轻闸门。

**方式二选一**（主 agent 自行判断复杂度）：
1. **简单场景**（单条 K# / 问题聚焦）：主 agent 自己跑一次性自查清单
2. **复杂场景**（多条 K# / 结论可能动摇 thesis）：dispatch 独立 subagent（`subagent_type: general-purpose`，**只读不写**，照 `feedback_subagent_write_hallucination`），单轮反方，只查：
   - **单线承重**：结论是否只依赖单一源/单一类型源？
   - **证据够不够**：核心论断有硬数据支撑还是靠推理链？
   - **是否过度外推**：从有限证据推到了过宽的结论？

自查清单（无论方式）：
- 本 deep drilldown 的关键结论每条都有**至少 1 条 manifest 材料**支撑吗？
- 有没有结论纯粹靠训练知识或推理链、无实证锚？
- 如果有数字（规模/增速/份额），来源是实收料还是估算？

**发现致命弱项不要静默跳过**——在笔记里标「⚠️ 证据薄：...」并降级结论置信度。

---

## Step 4：写入专题笔记

```bash
# 文件名格式：drilldown_YYYYMMDD_keyword.md
```

格式：
```markdown
---
slug: {slug}
type: drilldown
question: {具体问题}
generated: {timestamp}
addresses: [K#, K#@event...]   # 本钻探攻打的 thesis K#，决定下方覆盖回流
---

# 深度钻探：{问题}

{分析内容}

## 结论
{一段话}

## 后续行动
{需要验证的 1-3 件事}
```

---

## Step 4.5：把 drilldown 注册回 manifest（**新增**）

**目的**：drilldown 笔记原本只活在 `outputs/` 是孤岛，不进 manifest / 不参与三层覆盖。本步把它当作 source_type='drilldown' 的 material 入库——drilldown 本身已是结构化结论，直接 `mark_processed`，**不再走 03-extract 重抽**。

```bash
python3 << 'EOF'
from prism.scripts.manifest import add_material, mark_processed
from pathlib import Path

slug = '{slug}'
variant = '{variant}'
addresses = [{addresses_list}]  # 与笔记 frontmatter 一致
drilldown_path = Path('prism/topics/{slug}/{variant}/outputs/drilldown_{ts}_{kw}.md')

mat_id = add_material(
    slug=slug, variant=variant,
    filename=drilldown_path.name,
    source_type='drilldown',
    notes='07-drilldown 专题：{问题}',
    source_path=drilldown_path,   # 会拷贝到 materials/ 做副本（可被 03b/04 引用）
    addresses=addresses,
)
mark_processed(slug, mat_id, variant)  # drilldown 自己就是 finding，跳过 03-extract
print(f'drilldown 入库 mat_id={mat_id}, addresses={addresses}')
EOF
```

> **drilldown 入库后，若它承接了某条 pending todo 要的那份文档**，主 agent 按 **task 身份**（不是 K#）显式闭环：
> `update_user_todo_status(slug, variant, '<task子串>', 'done', covered_by=[mat_id])`；只是碰巧同 K# 的旁证则不动。
> 没有任何「列共享 K# 候选」的脚本（已删）——撮合是主 agent 读 todo + 读料的判读。
> 闭环键是 task/文档身份不是 K#（见 `_autofetch_protocol.md` 「产即收」+「闭环键」节 + memory `feedback_todo_closure_key`）。

drilldown 默认不触发 04 重写：

`list_affected_outputs` 默认在 `ignore_source_types=('drilldown',)` 模式下跑——drilldown 入库**不会**自动让相关 output 判 stale。这是为了让 drilldown 保持"高频深挖"的低成本，避免每次问一次就拖 ~5 份 output 重写（~25-50K token、15-25 min）。

### Step 4.6：drilldown 是否动摇 thesis？主 agent 显式决策（**强制**）

**load-bearing 场景升级为强制**：必须显式回答「我 `addresses` 的那条 capped 命门 / 薄弱 K#，这次解没解决」，据此走三类处理；quick 维持现状（默认走第一类）。

| 类型 | 表现 | 处理 |
|---|---|---|
| 补佐证 | 验证了现有 K# 论证 / 补了量化细节 | **不动 output**，drilldown 仅作引用源（默认） |
| 边缘修正 | 某条 fact 修正了精度但不改方向 | **不动 output**，在 living feed 标注新引文 |
| 动摇论证 | 推翻了某 K# 的前提 / 发现 thesis 漏洞 | **显式标 stale**：`set_output_status(slug, output_key, 'stale', variant)` 让 04 走 critic-stale 路径重写 |

第三类的脚本调用：

```python
from prism.scripts.topic import set_output_status
# 例：drilldown 发现 K3 论证依赖的产能数据被推翻
# 决策链成稿 case 整份标 stale（company c_investment_case / industry i_industry_case / arena a_arena_case）
stale_keys = ['i_industry_case']  # 主 agent 按 topic.type 与受影响范围列
for output_key in stale_keys:
    set_output_status('{slug}', output_key, 'stale', '{variant}')
print(f'drilldown 动摇 thesis：{len(stale_keys)} 份 output 标 stale，下次 04 会走 critic-stale 重写')
```

**判断纪律**：
- 默认走"补佐证"（第一类）——drilldown 大多数是日常问答，不应触发重写
- 若 drilldown 摘要里含"推翻 / 纠正 / 矛盾 / 改变方向"等强信号词 → 升级到第三类
- 升级第三类时**必须在 living feed 写明哪条 K# 被动摇、为什么标 stale**，方便后续 04 重写时主 agent 读到
- **load-bearing 场景**：必须显式输出一句话——「本次深挖的目标（capped 命门 X / thin K# Y）：已收敛 / 部分收敛（缺口 Z）/ 未收敛」→ 写入笔记 § 结论的第一句

### Step 4.7：闭环 —— resolve suggested_drilldown（仅 weight=load-bearing 且来自 suggested_drilldowns 时跑）

**目的**：如果这条 drilldown 是被 `suggested_drilldowns` 触发的（web 用户看到「🔍 建议深挖」块点的），做完后必须把建议标 done——否则建议永远挂 web。

```bash
python3 -c "
from prism.scripts.topic import resolve_suggested_drilldown

# question_substr 匹配 suggested_drilldown 的 question 字段（子串匹配）
resolve_suggested_drilldown(
    '{slug}', '{variant}',
    '{question_substr}',          # 与触发建议的 question 子串匹配
    status='done',
    drilldown_file='drilldown_{ts}_{kw}.md',
)
print('suggested_drilldown → done ✓')
"
```

**纪律**：
- Step 4.6 判「命门已解」→ `status='done'`
- 判「部分收敛 / 未收敛」→ 仍标 `done`（本次深挖尝试了），在 `rationale` 里显式留 why 未解（不影响 resolve，只影响下次 05 是否再触发 thin_evidence/capped → 自动转建议时是否需要新一条）
- quick 深挖如果不来自 suggested_drilldowns → 跳过本步

---

## Step 5：更新 living feed（追加本次钻探摘要）
