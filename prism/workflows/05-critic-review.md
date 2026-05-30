# Workflow 05 — 批评者评审 (Critic Review)

**触发**：用户说「评审 {slug}」或「steelman 反方」  
**定位**：强制用反方逻辑质疑自己的研究结论  
**前置**：产出 04（隐含预期）和 06（风险盲点）必须已生成

> **Web 搜索路径**：见 [[_web_search_routing]]（必读）。本步默认走 adapter；
> 仅事实校验类临时单查走 WebSearch tool。
>
> Step 6.5 request-more 兜底命令：
> ```bash
> python -m prism.scripts.web_search search "<反方关键词>" \
>     --intent news --days 60 \
>     --output sidecar --slug <slug> --variant <variant> \
>     --triggered-by 05-critic --addresses <K#>
> ```

---

## Step 0.0：prescan 状态门禁（**修 ISSUE-001 — 第一道门**）

```bash
python3 << 'EOF'
from prism.scripts.topic import get_current_prescan_status, read_topic
# H5 修订：读 helper（取 history[current_version]），不读 thesis.prescan_status 顶层
# （顶层已废弃 — 会被后续轮次 prescan 污染当前版本写时状态）
info = get_current_prescan_status('{slug}', '{variant}')
status = info["status"]
reason = info["failure_reason"]
print(f'prescan_status: {status} (thesis v{info["version"]} 写时)')
print(f'prescan_failure_reason: {reason}')

# 可选：扫后续轮次 prescan_log，了解 thesis 写定后 web 资料是否再 drift
t = read_topic('{slug}', '{variant}')
plog = t.get('prescan_log') or []
if plog:
    latest = plog[-1]
    print(f'最近一次 prescan_log: {latest["triggered_by"]} {latest["round_at"][:10]} → {latest["status"]}')
EOF
```

- **`status == 'failed'`** → **BLOCK 04-synthesize**。critic 不允许给 approve / request-more 之外的任何 verdict 前必须先要求用户二选一：
  1. **手工 prescan 补漏**：另设备搜索 baseline 第五节优先 query 并粘贴结果入库，重跑 `check_prescan_health` 直到 `partial` 或 `full`
  2. **接受 failed prescan 继续推进**：用户显式确认"接受训练知识赌注"，critic 在 Step 2 反方论据中**自动加重"thesis 论断脆弱"加权**，Step 3 评分对所有"time_sensitivity=快变"的 fact 强制降级 uncertain，verdict 最高只能 `request-more`，不许 `approve`
- **`status == 'partial'`** → critic 必须在 Step 2 列出 baseline 第六节"仍未校准"清单作为反方论据起点
- **`status == 'full'` 或 None（旧 topic）** → 正常推进

---

## Step 0：gap 体检（进 05 第二件事）

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

**按 topic 合成路径取文件**——三类 topic 都走决策链路径：company 产 `c_investment_case`（+`07_decision_kit.yaml`）、industry 产 `i_industry_case`（+`09_industry_to_arenas.yaml`）、arena 产 `a_arena_case`（+`10_peer_matrix.yaml`）；旧 topic 可能仍是 8 份分箱（04/06/07）：

```bash
# 决策链路径（存在哪个 *_case.md 即走哪条）
cat prism/topics/{slug}/{variant}/outputs/c_investment_case.md 2>/dev/null   # company
cat prism/topics/{slug}/{variant}/outputs/i_industry_case.md 2>/dev/null     # industry
cat prism/topics/{slug}/{variant}/outputs/a_arena_case.md 2>/dev/null        # arena
cat prism/topics/{slug}/{variant}/outputs/07_decision_kit.yaml 2>/dev/null
cat prism/topics/{slug}/{variant}/outputs/09_industry_to_arenas.yaml 2>/dev/null
cat prism/topics/{slug}/{variant}/outputs/10_peer_matrix.yaml 2>/dev/null
# 旧 8 份分箱路径（未重合成的老 topic）
cat prism/topics/{slug}/{variant}/outputs/04_implied_expectations.md 2>/dev/null
cat prism/topics/{slug}/{variant}/outputs/06_risk_blindspots.md 2>/dev/null
cat prism/topics/{slug}/{variant}/outputs/07_decision_kit.md 2>/dev/null
```

读到哪条就评哪条（`*_case` 的反方步直接对决策链 ①→⑥ 做 steelman——含 funnel 的环⑥ 选拔逻辑）；全为空 = 合成未完成，停止并提示先跑 04。

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
# triggered_by='05-critic' 时 register_web_search_batch 自动产 inline finding
# (修 B2)，summary['inline_finding_paths'] 直接可用 — 不需要等下一轮 03
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
from prism.scripts.topic import set_critic_verdict, append_user_todos, set_output_status, read_topic

slug = '{slug}'
variant = '{variant}'

verdict = '{approve|request-rewrite|request-more}'
summary = '{一句话总结评审结论，例如：thesis_v1 在 K3 论证较弱，建议补 Q1-Q2 同业对比}'
t = read_topic(slug, variant)
cur_v = (t.get('thesis') or {}).get('current_version')

# request-rewrite 时主 agent 列出要重写的 output keys；其他 verdict 留空
rewrite_keys = []  # 决策链路径用 ['c_investment_case'] / ['i_industry_case'] / ['a_arena_case']；旧分箱路径例：['04_implied_expectations','06_risk_blindspots']

# set_critic_verdict 内部已写默认 next_actions + 把 rewrite_keys 标 stale（修 S4）
critic = set_critic_verdict(
    slug, variant, verdict,
    summary=summary, thesis_version=cur_v,
    rewrite_keys=rewrite_keys,
)
print(f'verdict={critic["verdict"]} → stage={critic["next_stage"]}')

# 仅在 request-more 时追加具体待补 todo（主 agent 按评审结论填）
if verdict == 'request-more':
    append_user_todos(slug, [
        {'task': '补充：{具体资料 / web-search 关键词}',
         'priority': 'P0', 'info_tier': 'half_public', 'addresses': ['K?']},
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
- `set_critic_verdict` 会自动 `set_stage` + 写默认 next_actions + 标 rewrite_keys 为 stale，**不再手动 set_stage / set_next_actions / set_output_status**（修 S4 后）
- `request-rewrite` 路径走"标 stale + 04 重跑"——配合 list_affected_outputs 读 status 字段（reason='critic-stale'），只重写 critic 点名的 output
- `request-more` 路径回 02-gather-materials；主 agent 需 append 具体待补 todo（含 addresses，否则后续 auto_resolve 算不进）
- **若 critic 触发新的 thesis_v{N+1}**（无论 verdict 类型），新版本必须采用 Scheme C 全快照约定（详见 `prism/workflows/04-synthesize/_shared.md` § "Scheme C 写作约定"）——禁止只写增量 delta、禁止"见 v{N} §X"引用

---

## Step 7.5：request-rewrite 时本对话内续跑 04（**修 H1**）

**仅当 verdict='request-rewrite'**：写完 verdict 后**主 agent 不退场**，立即进入 04 重写循环。

### 7.5a：先报告范围 + 等用户 1 次 confirm

```bash
python3 -c "
from prism.scripts.outputs import list_affected_outputs
r = list_affected_outputs('{slug}', '{variant}')
stale = [(k, v['reason']) for k, v in r.items() if v['reason'] in ('stale', 'critic-stale')]
print(f'将重写 {len(stale)} 份产出：')
for k, reason in stale:
    print(f'  - {k} ({reason})')
"
```

主 agent 在对话里报告：
> 我要重写以下 N 份产出（critic 标 stale）：
> - 04_implied_expectations (critic-stale)
> - ...
>
> 输入：critic-review.md 反方论据 + 原 findings + 现有 thesis
> 预计 ~5-10K token/份、~3-5 min/份
>
> 继续吗？

**等用户回 yes/ok/继续/确认 才动**——回 no/等等/我看看 则保留 stale 状态，停在 04-synthesizing stage 让用户后续手动喊重跑。

### 7.5b：升 thesis 升级提示（stale ≥5 份）

如果 7.5a 算出来 stale ≥5 份，**不要直接确认**，主 agent 改口提示：

> critic 标 stale 的产出有 N≥5 份——这通常意味着 thesis 整体被翻案，**建议升 thesis_v{N+1} 全重写**而不是修补单份。
>
> 选项：
> A. 升 thesis_v{N+1}，按 _shared.md Scheme C 全快照重写全部 3 份决策链产出
> B. 仍按修补走，重写这 N 份（成本高且可能产出与 thesis 矛盾）
> C. 暂停，让我重看 critic 结论

用户决定后再走 7.5c（A 走 thesis 升版路径、B 走原 7.5c、C 保留 stale 退场）。

### 7.5c：用户 confirm 后续跑 04

收到 confirm → 主 agent 直接 re-enter `prism/workflows/04-synthesize/_shared.md`：
- list_affected_outputs 此时会算出 critic-stale，自动只跑被标的 output
- 读 `outputs/05-critic-review.md` 作为本轮重写的补充输入（反方论据 → 强化 K# 论证）
- 每份重写完调 `set_output_referenced_mats` 抹掉 stale 状态
- 全部完成后 stage 自然回 `04-post-synthesis`（04 _shared.md 末尾会做），后续可再跑 05 复评

**纪律**：
- 本对话内续跑 ≤4 份产出，超 4 份必走 7.5b 提示升 thesis
- 续跑过程中**不再 dispatch sub-agent**（参 [[feedback_subagent_bulk_synthesis]]），主 agent 直做
- 续跑失败的 output 走 04 `list_failed_outputs` 标准路径，不污染 critic verdict

---

## Step 8：仪表盘自动刷新（修 S5）

`set_critic_verdict` 内部已 fire-and-forget 触发 dashboard 异步重建，**无需再手跑** `python -m prism.scripts.dashboard`。后台失败留痕在 `prism/logs/dashboard_auto.log`。
