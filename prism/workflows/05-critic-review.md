	# Workflow 05 — 批评者评审 (Critic Review)

**触发**：用户说「评审 {slug}」或「steelman 反方」  
**定位**：用**独立反方**（干净上下文 subagent，押与作者相反方向、只看成稿结论不看作者推理）对抗式质疑研究结论——自我批评共享盲点等于没批评（修 #1）  
**前置**：决策链成稿 case 必须已生成（company `c_investment_case` / industry `i_industry_case` / arena `a_arena_case`，含其环③隐含预期 + 环④/⑤风险与证伪）

> **Web 搜索路径**：见 [[_web_search_routing]]（必读）。本步默认走 adapter；
> 仅事实校验类临时单查走 WebSearch tool。
>
> Step 6.5 request-more 兜底命令：
> ```bash
> python3 -m prism.scripts.web_search search "<反方关键词>" \
>     --intent news --days 60 \
>     --output sidecar --slug <slug> --variant <variant> \
>     --triggered-by 05-critic --addresses <K#>
> ```

---

## Step 0.0：prescan 状态门禁

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

- **`status == 'failed'`** → **封顶 verdict（最高只能 `request-more`，不许 `approve`）**。注意 05 在 04 之后跑、并不能回头拦 04；这道闸是卡在 critic 自己头上——出裁决前必须先要求用户二选一：
  1. **手工 prescan 补漏**：另设备搜索 baseline 第五节优先 query 并粘贴结果入库，重跑 `check_prescan_health` 直到 `partial` 或 `full`
  2. **接受 failed prescan 继续推进**：用户显式确认"接受训练知识赌注"，**Step 2 传给独立反方的输入包中显式注入"以下时敏论断未经 web 校准、按脆弱处理、加重攻击"指令**，Step 3 评分对所有"time_sensitivity=快变"的 fact 强制降级 uncertain，verdict 最高只能 `request-more`，不许 `approve`
- **`status == 'partial'`** → **Step 2 输入包必须含 baseline 第六节"仍未校准"清单作为反方攻击起点**
- **`status == 'full'` 或 None（旧 topic）** → 正常推进

---

## Step 0：gap 体检（进 05 第二件事）

```bash
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
print(format_summary(detect_gaps('{slug}', '{variant}')))
"
```

主 agent 直接读上面 Bash 输出的 report 做决策——**不必再整份贴/复述到对话**（Bash 输出里已有一份，actionable 项在 web）。**若本会话刚从 04 终态报告直连推进、其后无状态变更，直接沿用其双轴 gap、不必重跑本块；新会话/隔轮回来则照常重跑本块（从磁盘重算，绝不跳过）。** 看四项：
- `uncovered_ks` 非空 → 该 K# 当前 0 条材料覆盖
- `thin_evidence` 非空 → 该 K# 证据 < 2 条
- `single_source` 非空 → 该 K# 条数够但**来源单一**（全同一 source_type / 域名）。这是**注意力路由器、不是裁决**：去**读那几条内容**判是否真独立（多家券商转引同一份原始报告≈单源），别因条数达标就放行
- `expired_web_materials` 非空 → web-search 材料 > 90 天（critic 阶段视为 stale，可能需刷新）

gap report 是 critic 的**起手量化输入**——别只凭主观感觉判论证强弱。任一非空都应该作为 Step 2 反方论据的种子（"K# 论证薄弱因为 0 条材料 / 2 条但都来自同一份资料"），最终影响 Step 7 verdict（如 thin_evidence ≥3 个 K# → 不应给 approve）。

> **承重充分性（常驻 mandate · 质性，不是数条数）**：对每条**承重结论**——thesis 命门 K# + 各环 **hard 输入**（`input_contract` 标 hard 的项，如 arena 的 `arena-mirror`/company 的 `consensus`·`historical-mirror`·`mgmt-capital-alloc`）——必须独立判一句"证据是否足以支撑该结论"，靠**读内容**判**直接性 / 相互独立性 / 时效**对该命门的契合度。gap 的 `single_source`/`thin` 只是定量指针（可能假绿也可能假红：单条原始公告就够、五条二手转引仍不够），最终充分与否**由你读完内容质性下**。这一判断在 Step 5/7 落进 case 头横幅（见下）。

---

## Step 0.1：daily-monitor 破位喂入（**这次 05 为什么被发起的种子**）

很多时候发起 05 正是因为 **06-daily-monitor 确认了一条重大翻牌**（kill 触发 / signpost 翻
bear），详情页挂着「⚠️ 有未消化的重大变更，待重评 thesis」横幅。这条破位 + 它当时搜到的证据
就是本轮 critic 的**起手攻击种子**——不读它等于无视触发重评的那件事。

```python
from prism.scripts.topic import get_pending_thesis_review
from prism.scripts import monitor

marker = get_pending_thesis_review('{slug}', '{variant}')
if marker:
    print('破位锚点:', marker.get('reason'))
    print('locator :', marker.get('locator'), '| 确认于', marker.get('since'))
    # 找到那条已确认 proposal，取它注册进证据库的 mat_ids + 锚点
    for p in monitor.load_queue():
        if p.get('proposal_id') == marker.get('proposal_id'):
            print('已注册证据 mat_ids:', p.get('registered_mat_ids'))
            print('证据锚点 addresses:', p.get('evidence_anchor'))
            print('living_feed 文案:', (p.get('living_feed_entry') or '')[:400])
            if p.get('evidence_register_error'):
                print('⚠️ 证据注册失败:', p['evidence_register_error'], '— 该批证据未入库，需在 Step 2 现搜补')
            break
```

- `marker` 非空 → **Step 2 独立反方输入包必须显式注入这条破位**："daily-monitor 已确认
  {reason}，按该 bear/kill 已兑现为前提攻击 thesis，证据见 mat_ids / 锚点 `{evidence_anchor}`"。
- 那批证据已 `triggered_by='06-daily-monitor'` 注册进 web_search 库并 addressed 到该
  signpost/kill，**Step 0 的 `gap_detector` 已经数得到**（不再是 living_feed 里的散文）。
  顺手 grep manifest 里 `triggered_by: 06-daily-monitor` 的材料读其 finding。
- `evidence_register_error` 非空（极少：缺 manifest / 占位 URL）→ 该批证据没入库，Step 2 现搜补回。
- `marker` 为空 → 本轮 05 不是被 daily-monitor 触发（常规评审），跳过本步。

> 跑完 04（重合成）或本次 05（`set_critic_verdict`）后，`get_pending_thesis_review` 会因
> `thesis.last_updated` / `critic.at` 晚于破位 `since` 自动返回 None，详情页横幅随之消失——
> 即"这条破位已被消化"的机械依据，无需手动清。

---

## Step 1：读取核心产出

**按 topic 合成路径取文件**——三类 topic 都走决策链路径：company 产 `c_investment_case`（+`07_decision_kit.yaml`）、industry 产 `i_industry_case`（+`industry_to_arenas.yaml`）、arena 产 `a_arena_case`（+`peer_matrix.yaml`）：

```bash
# 决策链路径（存在哪个 *_case.md 即走哪条）
cat prism/topics/{slug}/{variant}/outputs/c_investment_case.md 2>/dev/null   # company
cat prism/topics/{slug}/{variant}/outputs/i_industry_case.md 2>/dev/null     # industry
cat prism/topics/{slug}/{variant}/outputs/a_arena_case.md 2>/dev/null        # arena
cat prism/topics/{slug}/{variant}/outputs/07_decision_kit.yaml 2>/dev/null
cat prism/topics/{slug}/{variant}/outputs/industry_to_arenas.yaml 2>/dev/null
cat prism/topics/{slug}/{variant}/outputs/peer_matrix.yaml 2>/dev/null
```

读到哪条就评哪条（`*_case` 的反方步直接对决策链 ①→⑥ 做 steelman——含 funnel 的环⑥ 选拔逻辑）；全为空 = 合成未完成，停止并提示先跑 04。

---

## Step 2：独立反方评审（dispatch 干净上下文 subagent · 修 #1）

> 📎 *为什么必须独立（自我批评共享盲点）→ 附录 A2（执行时可跳过）*

> **方向对称(别只做空)**：反方 = **押与作者相反方向的最强对手盘**。作者看多 → 反方是空头，用空方最强逻辑;作者看空 → 反方是多头，用多方最强逻辑;作者判分化/中性 → 反方攻"分化判断本身站不住"。下面 prompt 里的"对赌 / 验尸"措辞按 case 实际方向填，**不要默认看多**。

### 2.1 组装输入包（喂什么 / 瞒什么）

**喂给反方（成稿事实层）**：
- 当前成稿 case 全文（`c_investment_case` / `i_industry_case` / `a_arena_case`）
- 结构化财务/估值（`get_financial_context` + `get_valuation_context` / `_by_tickers` 的输出）
- Step 0 gap report 关键项（攻击种子：哪些 K# thin / single-source）
- prescan 状态：failed/partial 时按 Step 0.0 注入加权指令 + baseline 第六节"仍未校准"清单

**不喂给反方（作者的说服层——独立性的关键）**：
- 不喂 thesis 的推理理由 / decomposition 命门拆解的论证过程
- 不喂 findings 的解读叙事 / primer
- 让它只面对"结论 + 硬数据"，用自己的判断找致命伤，而非顺着作者框架点头

> case 正文里**作者自己写的**环⑤风险与证伪是**要喂**的（那是成稿的一部分，反方正好评"作者的自我证伪够不够狠"）；要瞒的是 case 之外的工作底稿（thesis 理由链 / findings 叙事）。

### 2.2 dispatch 独立反方（`subagent_type: general-purpose`，默认不传 model，**只读不写**）

> 📎 *可选换模型增强独立性 → 附录 A2.2（执行时可跳过）*

prompt 模板（按 topic 填空；**先判 case 方向，{对手方向}=空头/多头、{相反操作}=做空/做多 按实际填**）：

```
你被请来做一次独立的对手盘尽调。你**没有**参与这份研究，不知道作者的推理过程，只拿到最终结论和硬数据。

## 你的处境（对赌框定）
你是作者这个判断的**对手盘**：作者看多你就重仓做空、作者看空你就重仓做多——总之你用**自己的真金白银押了与作者相反的方向**（本例作者{看多/看空}，你{相反操作}）。作者若对，你巨亏。所以你的任务不是礼貌地提反方，是**找出最可能让你这笔对赌赚钱、让作者巨亏的那几个致命点**。

## 你拿到的材料
{粘贴成稿 case 全文（含其环⑤风险与证伪）}
{粘贴 get_financial_context / 估值数据}
{粘贴 gap report 关键项：哪些 K# 证据薄 / 单源}
{若 prescan failed/partial：注入"以下时敏论断未经 web 校准，按脆弱处理、加重攻击：{清单}"}

## 攻击方向
- 作者看多 → 用空方最强逻辑反驳；作者看空 → 用多方最强逻辑反驳；作者判分化/中性 → 攻"分化判断本身不成立（其实有明确赢家或全是输家）"。
- 只攻**承重假设**（命门 K#、定价锚、各环 hard 输入），不攻边角。
- 可用你自己的领域知识 + 上面的硬数据，但**不要默认作者框架成立**——质疑框架本身。
- 严格只用拿到的材料 + 你的常识/领域知识，不要脑补不存在的数据。

## 你要交付（纯 markdown，返回正文，**不要写文件**）
### 一、对承重假设的质疑（逐条）
对每条核心假设：
- 作者假设：{原结论里的假设}
- 反驳：{为什么可能不成立}
- 支撑：{什么数据 / 逻辑 / 历史先例}
- 强度：强 / 中 / 弱（弱也说明为何仍值得考虑）

### 二、预先验尸（pre-mortem）
假设一年后**作者这个判断被证伪、按它操作亏了 50%**。回头写**最可能的死因**（≤3 条，按概率排序）——具体到哪条承重假设先崩、由什么触发。

### 三、致命一击候选
若只能押一个让作者翻车的点，是哪个？为什么市场/作者会忽略它？

苛刻、直接、不留情面。1800 字内。
```

### 2.3 主 agent 收稿（subagent 只返回 markdown，主 agent 落盘）

按 [[feedback_subagent_write_hallucination]] 铁律：**反方 subagent 不写文件**，只把三段 markdown 返回 final message。主 agent 接收后作为 Step 3 评分、Step 5 保存、Step 7 verdict 的输入。其中：
- "致命一击候选" + 预先验尸高概率死因 → 直接喂 Step 7：**若致命一击成立且 case 无应答 → 不得 `approve`**
- 反方若是换模型跑的，在 Step 5 保存时标注模型，便于事后校准

---

## Step 3：给原研究评分

**主 agent 据 Step 2 独立反方返回的报告打分**（不是自评）——"考虑反面观点"维度直接看 case 环⑤是否已应答反方的致命一击 / 预先验尸死因；反方点到而 case 无应答的，该维度 ≤3 并点名。

| 维度 | 评分(1-5) | 评语 |
|------|-----------|------|
| 逻辑严密性 | | |
| 证据充分性 | | |
| 考虑反面观点 | | |
| 隐含假设透明度 | | |
| 整体 | | |

> **「证据充分性」按承重 mandate 打**（见 Step 0）：不是数总条数，而是逐条承重结论（命门 K# + hard 输入）读内容判够不够。任一承重结论"单线承重 / 二手转引充数 / 过期"→ 该维度 ≤3，且必须在评语里点名是哪条、缺什么。

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

> 生成于 {timestamp}，基于成稿 case（独立反方 subagent{若换模型注明 model}）

## 独立反方报告（subagent 原样返回）
{Step 2 反方返回的三段 markdown 完整复制：承重假设质疑 / 预先验尸 / 致命一击}

## 评分与裁决（主 agent）
{Step 3 评分表 + Step 4 修改建议完整复制}
```

---

## Step 5.5：把承重充分性裁决落到 case 头一行（堵"骨架完整被误读为可执行"）

> 📎 *为什么裁决必须进产出本身 → 附录 A5.5（执行时可跳过）*

用 Edit 在**当前 `*_case.md` 的 frontmatter 之后、正文首个引用块之前**插入（已存在则**覆盖**该行，幂等）一行横幅：

```markdown
> 🧪 **承重充分性（05-critic · {date}）**：{够 / 单线承重 / 不足} — {一句话点名最弱的承重项及缺什么，如"命门3路线无关仅 1 条二手券商料、单线承重"}。verdict={approve / request-more / request-rewrite}。
```

- 三档取值锚：所有承重结论证据直接·独立·够新 → **够**；某承重结论靠单源/二手转引充数（含 gap `single_source` 命中且读内容确认不独立）→ **单线承重**；某承重结论缺料或证伪不成立 → **不足**。
- 与 Step 7 verdict 同向：**不足** 不得配 `approve`；**单线承重** 最高 `request-more`。
- 这是给读者/dashboard 的诚实标签，不替代评审正文，只把最关键一句顶到 case 头。

---

## Step 6：追加到信息流时间线

追加到 `prism/topics/{slug}/outputs/08_living_feed.md`：

```markdown
---

## {timestamp_short} 批评者评审完成

**来源**：Workflow 05-critic-review，独立反方 subagent（干净上下文对抗式、押相反方向）视角

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
# triggered_by='05-critic' 时 register_web_search_batch 自动产 inline finding
# summary['inline_finding_paths'] 直接可用 — 不需要等下一轮 03
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
| `request-rewrite` | 评分 ≥3 但部分 K# 论证薄弱 / 某 output（如 04 隐含预期）需重写（承重项为「单线承重」时**降级为 `request-more`**，见 Step 5.5/Step 0 横幅口径） | stage → `04-synthesizing`，调 `set_output_status` 把目标 output 标 `stale` |
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
rewrite_keys = []  # 按 type 用 ['c_investment_case'] / ['i_industry_case'] / ['a_arena_case']

# set_critic_verdict 内部已写默认 next_actions + 把 rewrite_keys 标 stale
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
- `set_critic_verdict` 会自动 `set_stage` + 写默认 next_actions + 标 rewrite_keys 为 stale，**不再手动 set_stage / set_next_actions / set_output_status**
- `request-rewrite` 路径走"标 stale + 04 重跑"——配合 list_affected_outputs 读 status 字段（reason='critic-stale'），只重写 critic 点名的 output
- `request-more` 路径回 02-gather-materials；主 agent 需 append 具体待补 todo（含 addresses，回 02 后才能挂到对应 K# 进 gap_detector B 轴覆盖；收口仍按文档身份显式 `update_user_todo_status`）
- **若 critic 触发新的 thesis_v{N+1}**（无论 verdict 类型），新版本必须采用 Scheme C 全快照约定（详见 `prism/workflows/04-synthesize/_shared.md` § "Scheme C 写作约定"）——禁止只写增量 delta、禁止"见 v{N} §X"引用

### Step 7a：thin_evidence / 单线承重 → suggested_drilldowns 回流（终局对齐 · 新增）

**写完 verdict 后，扫 Step 0 gap report + Step 5.5 承重结论**：

```bash
python3 -c "
from prism.scripts.topic import detect_drilldown_candidates
c = detect_drilldown_candidates('{slug}', '{variant}')
print(f'thin_evidence={c[\"thin_evidence\"]}, uncovered_ks={c[\"uncovered_ks\"]}')
"
```

**若 `thin_evidence` ≥1 或 Step 5.5 判「单线承重」**：LLM 把每条薄弱 K# / 承重不足项翻成建议，调 `set_suggested_drilldowns(mode='append')`（**不覆盖 04 的**）：

```bash
python3 -c "
from prism.scripts.topic import set_suggested_drilldowns
set_suggested_drilldowns('{slug}', '{variant}', [
    {'question': '深挖问题', 'rationale': 'K3 thin_evidence 仅1条二手料', 'source': 'critic_weak_k',
     'related': ['K3'], 'priority': 'P0'},
], mode='append')
"
```

> **并行挂建议**：`request-more / request-rewrite` 走主线时**可并行挂建议**——建议深挖不替代主线判定，只作为"这些薄弱项值得抽空 07 专项深挖"的结构化备忘。

---

## Step 7.5：request-rewrite 时本对话内续跑 04

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
> - i_industry_case (critic-stale)   ← 决策链成稿（company `c_investment_case` / arena `a_arena_case`）
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

## Step 8：仪表盘自动刷新

`set_critic_verdict` 内部已 fire-and-forget 触发 dashboard 异步重建，**无需再手跑** `python3 -m prism.scripts.dashboard`。后台失败留痕在 `prism/logs/dashboard_auto.log`。

---

## 附录 A — rationale / 反例 / 历史教训（执行时可跳过，调试 / 维护时查）

> 本附录收纳从各步主流程搬出的"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"。**主流程逐字未删、只是移出执行动线**；要看某步的来龙去脉，按对应小节查。

### 附录 A2 — 为什么必须独立（自我批评共享盲点）

**为什么必须独立**：同一模型在同一段对话里"换帽子"做 steelman，已被前面的论证说服，反驳会手软、会回避真正致命的点——自我批评共享你的盲点等于没批评。所以反方**必须**是干净上下文的独立 subagent，只面对成稿结论 + 硬事实，不看作者的推理链。（与 04 已独立的 chain-critic / primer critic 同构——它们查"链通不通 / 目标达没达"，本步做对抗式 steelman。）

### 附录 A2.2 — 可选换模型增强独立性

> 可选增强独立性：主 agent 是 opus 时可给反方传 `model=sonnet`/`haiku` 换个脑子进一步降共享盲点（按 [[feedback_subagent_model]]，默认不传；仅在想进一步独立时用）。

### 附录 A5.5 — 为什么裁决必须进产出本身

critic 的承重充分性裁决（Step 0 mandate + Step 3「证据充分性」）必须**进被消费的产出本身**——否则读者只看 case 骨架完整、误当"结论可执行"（独立 critic 抓到的弱点蒸发在评审文件里）。
