# Workflow 07 — 深度钻探 (Drill-down)

**触发**：用户说「深挖 {slug} 的 {具体问题}」  
**定位**：对某个具体问题进行专项深度研究，产出专题笔记  
**产出文件**：`prism/topics/{slug}/outputs/drilldown_{timestamp}_{topic_keyword}.md`

---

## Step 1：明确钻探问题

用户的问题可能是：
- 「深挖 {slug} 的竞争格局」
- 「分析 {slug} 里 {公司名} 的护城河」
- 「中国 vs 海外 {slug} 的格局差异」
- 「{slug} 在利率上行环境的历史表现」

如果问题不够具体，AskUserQuestion 细化。

---

## Step 2：评估信息来源

```bash
python -c "
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

- 主 agent 把钻探问题拆成 1-3 条精准 query 喂给 Step B（**覆盖** `build_search_queries` 默认生成的通用 query）
- 把 hit 的 addresses 按全局三态约定（参 `_web_prescan_shared.md` 关键纪律 3）填：攻打具体 K# 时填 `['K#']`/`['K#@event']`；thesis 未形成或纯探索性深挖填 `['scope']`；**禁止 `[]`**
- `triggered_by='07-drilldown'`

入库后再回到 Step 3 做深度分析——保溯源链：drilldown 的引文必须来自 manifest 中的 material（含 web-search 入库的），不准直接引 WebSearch 原文。

---

## Step 3：深度分析

使用训练知识 + 已有 findings，对问题进行深度分析：

- 结构：问题分解 → 每个子问题的分析 → 综合结论
- 要求：比产出 01-08 更深、更具体
- 字数：不限，以回答清楚问题为准

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

**目的**：drilldown 笔记原本只活在 `outputs/` 是孤岛，不进 manifest / 不参与三层覆盖 / 不触发 auto_resolve_todos。本步把它当作 source_type='drilldown' 的 material 入库——drilldown 本身已是结构化结论，直接 `mark_processed`，**不再走 03-extract 重抽**。

```bash
python3 << 'EOF'
from prism.scripts.manifest import add_material, mark_processed
from prism.scripts.web_prescan import auto_resolve_todos
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

# 触发 todo 覆盖回流：drilldown 攻的 K# 若有 active todo，会被自动 done
resolved = auto_resolve_todos(slug, variant, [mat_id])
for r in resolved:
    print(f'  ✓ {r["task"][:60]} ← {r["mat_ids"]}')
print(f'drilldown 入库 mat_id={mat_id}, addresses={addresses}, 自动 resolve {len(resolved)} 条 todo')
EOF
```

**修 M6 — drilldown 默认不触发 04 重写**：

`list_affected_outputs` 默认在 `ignore_source_types=('drilldown',)` 模式下跑——drilldown 入库**不会**自动让相关 output 判 stale。这是为了让 drilldown 保持"高频深挖"的低成本，避免每次问一次就拖 ~5 份 output 重写（~25-50K token、15-25 min）。

`auto_resolve_todos` 不受影响——drilldown 写 addresses=['K3'] 仍会自动 done 对应 K3 todo（两条路径独立）。

### Step 4.6：drilldown 是否动摇 thesis？主 agent 显式决策（**新增**）

drilldown 跑完后，主 agent 自评本次结论与现有 thesis 的关系，分三类处理：

| 类型 | 表现 | 处理 |
|---|---|---|
| 补佐证 | 验证了现有 K# 论证 / 补了量化细节 | **不动 output**，drilldown 仅作引用源（默认） |
| 边缘修正 | 某条 fact 修正了精度但不改方向 | **不动 output**，在 living feed 标注新引文 |
| 动摇论证 | 推翻了某 K# 的前提 / 发现 thesis 漏洞 | **显式标 stale**：`set_output_status(slug, output_key, 'stale', variant)` 让 04 走 critic-stale 路径重写 |

第三类的脚本调用：

```python
from prism.scripts.topic import set_output_status
# 例：drilldown 发现 K3 论证依赖的产能数据被推翻
for output_key in ['04_implied_expectations', '06_risk_blindspots']:  # 主 agent 按受影响范围列
    set_output_status('{slug}', output_key, 'stale', '{variant}')
print(f'drilldown 动摇 thesis：{len(stale_keys)} 份 output 标 stale，下次 04 会走 critic-stale 重写')
```

**判断纪律**：
- 默认走"补佐证"（第一类）——drilldown 大多数是日常问答，不应触发重写
- 若 drilldown 摘要里含"推翻 / 纠正 / 矛盾 / 改变方向"等强信号词 → 升级到第三类
- 升级第三类时**必须在 living feed 写明哪条 K# 被动摇、为什么标 stale**，方便后续 04 重写时主 agent 读到

---

## Step 5：更新 living feed（追加本次钻探摘要）
