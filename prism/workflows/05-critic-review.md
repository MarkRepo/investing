# Workflow 05 — 批评者评审 (Critic Review)

**触发**：用户说「评审 {slug}」或「steelman 反方」  
**定位**：强制用反方逻辑质疑自己的研究结论  
**前置**：产出 04（隐含预期）和 06（风险盲点）必须已生成

---

## Step 0：gap 体检（进 05 第一件事）

```bash
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
print(format_summary(detect_gaps('{slug}', '{variant}')))
"
```

把 report 输出**完整贴到对话**。看三项：
- `uncovered_ks` 非空 → 该 K# 当前 0 条材料覆盖
- `thin_evidence` 非空 → 该 K# 证据 < 2 条
- `expired_web_materials` 非空 → web-search 材料 > 90 天（critic 阶段视为 stale，可能需刷新）

gap report 是 critic 的**起手量化输入**——别只凭主观感觉判论证强弱。任一非空都应该作为 Step 2 反方论据的种子（"K# 论证薄弱因为 0 条材料 / 2 条但都来自同一份资料"），最终影响 Step 7 verdict（如 thin_evidence ≥3 个 K# → 不应给 approve）。

---

## Step 1：读取核心产出

```bash
cat prism/topics/{slug}/outputs/04_implied_expectations.md
cat prism/topics/{slug}/outputs/06_risk_blindspots.md
cat prism/topics/{slug}/outputs/07_decision_kit.md 2>/dev/null
```

---

## Step 2：扮演反方（Steelman）

**指令：现在切换为持有相反观点的分析师。**

如果当前研究结论偏多，现在用空方最强逻辑反驳。
如果当前结论偏空，用多方最强逻辑反驳。

反驳格式：

### 对「核心假设 1」的质疑

多方假设：{原假设}  
反驳：{空方为什么认为这个假设不成立}  
支撑证据：{有什么数据或逻辑}  
强度评估：{强/中/弱} — 如果弱，说明为什么仍然值得考虑

### 对「核心假设 2」的质疑

{同格式}

### 对「核心假设 3」的质疑

{同格式}

---

## Step 3：给原研究评分

| 维度 | 评分(1-5) | 评语 |
|------|-----------|------|
| 逻辑严密性 | | |
| 证据充分性 | | |
| 考虑反面观点 | | |
| 隐含假设透明度 | | |
| 整体 | | |

---

## Step 4：给出修改建议

「如果我要加强这个研究，最重要的 3 件事是：」
1. {具体建议}
2. {具体建议}
3. {具体建议}

---

## Step 5：保存评审结果到 outputs

**保存评审结果**，写入 `prism/topics/{slug}/outputs/05-critic-review.md`：

```markdown
---
slug: {slug}
output_key: 05-critic-review
version: 1
generated: {timestamp}
---

# 批评者评审：{display_name}

> 生成于 {timestamp}，基于产出 04/06/07

{评审内容完整复制}
```

---

## Step 6：追加到信息流时间线

追加到 `prism/topics/{slug}/outputs/08_living_feed.md`：

```markdown
---

## {timestamp_short} 批评者评审完成

**来源**：Workflow 05-critic-review，钢人反方视角

**关键信息**：
- {评审摘要1}
- {评审摘要2}
- {评审摘要3}

**对已有判断的影响**：
- 支持了：{...}
- 新增了：{...}
- 调整了：{...}

**当前判断更新**：
{如有变化写变化，如无写「维持原判断」}
```

---

## Step 6.5：critic 缺口先 web-search 兜底（**新增**）

如果 Step 4 的修改建议指向"需要补 X 资料"或"K# 论证薄弱因为缺 Y 数据"，**先尝试 web-search 兜一轮**再决定 verdict——而不是直接 `request-more`。

判定流程：

```
critic 找到缺口
  ↓
该缺口能用 web-search 找到？
  ↓ Yes → 即兴 web-search 1-3 条 query → 入库 → 重新看 critic 缺口是否还成立
  ↓ No  → 直接 verdict = request-more（让用户上传一手资料）
```

「能用 web-search 找到」的典型场景：
- 公开数据：行业规模、监管文件、龙头公告、公开财报
- 半公开：卖方研报标题/摘要、新闻报道、产业协会数据

「web-search 不够」的典型场景：
- 一手专家访谈、付费墙后内容、未公开内部数据、产业链调研

执行：

```python
# 主 agent 在对话里调 WebSearch 拉一批 hit，再一行入库
from prism.scripts.web_prescan import register_web_search_batch
summary = register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='critic 缺口的精准查询',
    addresses=['{涉及的 K#}'],
    triggered_by='05-critic',
    hits=[...],
)
print(f"web-search 兜底：高/中/低 = {summary['n_high']}/{summary['n_mid']}/{summary['n_low']}")
```

入库后**重新读一次相关 finding / 产出**，看 critic 缺口是否被消除：
- 是 → verdict 改为 `approve` 或 `request-rewrite`（让 04 用新 mat 重写部分产出）
- 否 → verdict 仍为 `request-more`，但在 user_todos 里只列 web-search 拿不到的部分

**纪律**：
- Step 6.5 即兴 web-search 不超过 5 条 query × 5-10 hit/query = 不超过 50 hit/critic 轮
- 即兴 web-search 入库的 mat 在 verdict='request-rewrite' 时，set_output_status 把对应 output 标 stale
- **保溯源链**：判 critic 缺口"已被消除"时必须 cite 新入库的 mat_id
- URL/snippet 必须来自 WebSearch 工具实际返回，不得用训练记忆补 URL

### Step 6.5b：缺口涉及多子问题时升级为 sub-agent 深挖

如果 critic 缺口指向"K# 论证薄弱因为缺 3 个独立子问题的数据"——主 agent 应**dispatch sub-agent 并行深挖**而不是自己串行调 5×WebSearch：

执行方式（参 `prism/workflows/_subagent_deep_search.md`）：

```python
# 主 agent 同时 dispatch 多个 sub-agent（不同 K# / 不同子问题各一）
# 每个 sub-agent 独立跑 1-3 轮深挖
# 全部回来后批量 register_web_search_batch
```

**适用判定**：
- critic 列出 ≥3 个独立缺口子问题 → sub-agent
- critic 列出 1-2 个简单缺口 → 主 agent 即兴 web-search（Step 6.5 原路径）

**收回 verdict**：所有 sub-agent 入库后，重新读 critic 缺口判定是否被消除——逻辑同 Step 6.5。

---

## Step 7：定 verdict 并自动跳转 stage（**修 7**）

根据 Step 3 评分 + Step 4 建议，给出三选一 verdict：

| verdict | 何时选 | 后效 |
|---|---|---|
| `approve` | 评分 ≥4 / 反方反驳"中-弱" / 无重要遗漏 | stage → `done`，进入 06-daily-monitor |
| `request-rewrite` | 评分 ≥3 但部分 K# 论证薄弱 / 某 output（如 04 隐含预期）需重写 | stage → `04-synthesizing`，调 `set_output_status` 把目标 output 标 `stale` |
| `request-more` | 反方提出的关键证据当前 manifest 无覆盖 / 需要新一轮 web-search 或用户上传 | stage → `02-gather-materials`，调 `set_user_todos` 列出待补资料 |

```bash
python3 << 'EOF'
from prism.scripts.topic import set_critic_verdict, set_next_actions, set_user_todos, set_output_status, read_topic

slug = '{slug}'
variant = '{variant}'

# 写 verdict + 自动 set_stage
verdict = '{approve|request-rewrite|request-more}'
summary = '{一句话总结评审结论，例如：thesis_v1 在 K3 论证较弱，建议补 Q1-Q2 同业对比}'
t = read_topic(slug, variant)
cur_v = (t.get('thesis') or {}).get('current_version')
critic = set_critic_verdict(slug, variant, verdict, summary=summary, thesis_version=cur_v)
print(f'verdict={critic[\"verdict\"]} → stage={critic[\"next_stage\"]}')

# next_actions / user_todos 因 verdict 而异
if verdict == 'approve':
    set_next_actions(slug, [
        '研究主题已闭环，下一步「监控 {slug}」启动 daily/weekly monitor',
        f'thesis_v{cur_v} 已通过 critic-review',
    ], variant)
    set_user_todos(slug, [
        {'task': '说「监控 {slug}」启动 06-daily-monitor', 'priority': 'P0', 'info_tier': 'public'},
        {'task': '或说「记录决策 {slug}」固化最终投资决策', 'priority': 'P1', 'info_tier': 'public'},
    ], variant)

elif verdict == 'request-rewrite':
    # 把要重写的 output 标 stale，下次 04-synthesize 会判其为 stale 自动重写
    for ok in ['{output_key_to_rewrite}']:  # 主 agent 按评审结果填
        try:
            set_output_status(slug, ok, 'stale', variant)
        except Exception:
            pass
    set_next_actions(slug, [
        '说「合成 {slug}」重新跑 04，会按增量判定只重写 stale 的 output',
        f'critic 建议：{summary}',
    ], variant)

elif verdict == 'request-more':
    # 缺资料：让用户/web-search 来补，回 02-gather-materials
    set_user_todos(slug, [
        # 主 agent 按评审结论填具体待补项
        {'task': '补充：{具体资料 / web-search 关键词}', 'priority': 'P0', 'info_tier': 'half_public', 'addresses': ['K?']},
    ], variant)
    set_next_actions(slug, [
        '说「prism 推进 {slug}」回到 02-gather-materials，先跑 web-search prescan',
        f'critic 缺口：{summary}',
    ], variant)

# living feed bump（所有 verdict 都做）
try:
    current = t.get('outputs_state', {}).get('08_living_feed', {}).get('version', 1)
    set_output_status(slug, '08_living_feed', 'fresh', variant, version=current + 1)
except Exception:
    pass
EOF
```

**注意**：
- `set_critic_verdict` 会直接 `set_stage`，**不需要再手动 set_stage**
- `request-rewrite` 路径走"标 stale + 04 重跑"——配合修 1 的 list_affected_outputs，未变章节不会被无谓重写
- `request-more` 路径走 02-gather-materials，可直接顺手跑 _web_prescan_shared.md 查 critic 提的关键词
- **若 critic 触发新的 thesis_v{N+1}**（无论 verdict 类型），新版本必须采用 Scheme C 全快照约定（详见 `prism/workflows/04-synthesize/_shared.md` § "Scheme C 写作约定"）——禁止只写增量 delta、禁止"见 v{N} §X"引用

---

## Step 8：刷新仪表盘（最终一步，必跑）

```bash
python -m prism.scripts.dashboard
```

评审若调整了 thesis 强度 / kill criteria status / signpost triggered，dashboard 必须重建以反映新状态。失败允许重试一次；仍失败记入 user_todos 不阻塞主流程。
