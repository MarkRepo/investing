# Workflow 06 — 日常监控 (Daily Monitor · headless 巡检)

**触发**：web-server 每日 6:00 自动拉起 / web 端「立即巡检」按钮 / 用户说「监控 {slug}」
**执行者**：headless `claude -p`（由 `app/monitor_runtime.py` 拉起）或对话里的 Claude
**定位**：扫关注清单里到期的 event → 自动搜 → **轻判读** → 写 proposal 进 queue
**耗时**：目标 5-10 分钟

> **铁律（B 层分叉=只翻牌,thesis 另议）**：
> - **只翻牌，不写 thesis 草案**。kill 触发 / 重大 signpost 翻 bear → 标
>   `requires_thesis_review=True`，把重评留给用户在对话里发起交互式 05-critic-review。
> - **绝不 confirm**。proposal 一律 `awaiting_confirm`，确认永远是用户在 web 端点头。
> - 成本闸是 watchlist：本 workflow 只处理 `scan` 吐出的到期项，不全量扫 topic。

> **Web 搜索路径**：见 [[_web_search_routing]]。本步默认走 adapter；事实校验单查走 WebSearch tool。

---

## Step 1：拿到期清单（零 LLM，机械）

```bash
python3 -m prism.scripts.monitor scan 14
```

输出 JSON 分桶（已只含 watchlist 内的 topic）：

| 桶 | 含义 | 本步动作 |
|---|---|---|
| `due_signposts` | 到期/逾期且未翻牌的 signpost | → Step 2 判读 |
| `due_kills` | 到期且 status=pending 的 kill | → Step 2 判读 |
| `price_breach` | 现价跌入买入框 | **跳过**——已由 web 进程零 LLM 直接 propose |
| `recurring_review` | industry/arena 周期重扫 | → Step 3 |
| `unparseable` | 日期写错的 event（永不触发）| **贴对话上报**，建议人工修 sidecar 日期 |
| `price_unavailable` | 停牌/缺数/币种错配 | 记一笔，不误报 |
| `skipped_no_sidecar` | 关注了但还没 sidecar | 记一笔 |

`due_signposts`/`due_kills` 都为空且 `recurring_review` 为空 → 无事可做，结束。

---

## Step 2：逐条自动搜 + 轻判读（company signpost/kill）

对每个 `due_signposts` / `due_kills` 项：

**2a. 写 query 自动搜**（query 由你写，脚本不写）。重点查：
- signpost：该 `event` 是否已兑现？围绕 `bull_signal` / `bear_signal` 的最新事实
- kill：`description` 描述的证伪条件是否触发（带数据找数据）

```python
from prism.scripts.web_search import WebSearchAdapter
hits = WebSearchAdapter().search("<你写的 query>", intent="news", days=14)
```

> **证据注册已下沉到 confirm（修 — 巡检不白做）**：你**不必**在这里手动调
> `register_web_search_batch`。把判读所依据的 hits 原样塞进下面 proposal 的
> `evidence` 字段即可；用户在 web 端**确认该翻牌时**，`monitor.confirm_flip` 会自动
> 把这批 hits 注册进 web_search 库（`triggered_by='06-daily-monitor'`，addressed 到该
> signpost/kill 的语义锚点，URL 去重幂等）。这样 05 重评的 `gap_detector` 数得到这批新
> 证据、独立反方拿得到——证据不再只躺在 living_feed 散文里。**evidence 必须是从搜索结果
> 原样拷的真实 hits（title/url/snippet），不能凭记忆构造 URL**（占位 URL 会在注册时被拒）。

**2b. 轻判读**——只判三件事，不重写 thesis：
```
□ 事件兑现了吗？      未兑现/没新信息 → 不 propose（留到下次扫）
□ 偏多还是偏空兑现？   signpost → proposed_value = "bull" | "bear"
□ 触发 kill 了吗？     kill → proposed_value = "triggered_bull" | "triggered_bear" | "cleared"
```
弱证据（只命中 low-tier/other 源）→ 仍可 propose，但 `rationale` 注明「弱证据需复核」，
web 端会标黄。

**2c. 写 proposal**（含预写好的 living_feed 文案）：
```python
from prism.scripts import monitor
monitor.propose_flips([
  {
    "slug": slug, "variant": variant,
    "kind": "signpost",                 # 或 "kill"
    "locator": "<scan 给的 locator>",    # signpost=hash / kill=id（原样回填）
    "proposed_value": "bull",           # signpost: bull/bear；kill: triggered_bull/triggered_bear/cleared
    "expected_current": None,           # signpost 未翻牌时为 None；kill 为 "pending"（照 scan 的 current_*）
    "evidence": [                       # 必带，至少 1 条：判读所依据的真实搜索 hit（confirm 时注册进证据库）
      {"title": "<原样拷>", "url": "https://...", "snippet": "<原样拷>"},
    ],
    "evidence_urls": ["https://..."],   # 可选：仅供 web 端快速展示的裸链接（evidence 缺失时回退用它合成 hit）
    "living_feed_entry": (              # 你现在就写好，confirm 时机械落盘（零 LLM）
      "## {YYYY-MM-DD} {事件简述}\n"
      "**来源**：{资料}\n**关键信息**：{带数据}\n"
      "**对已有判断的影响**：支持/否定了 {假设}\n**当前判断更新**：{维持/小调}"
    ),
    "rationale": "一句话：为什么这么翻",
    "requires_thesis_review": False,    # kill 触发 / signpost 翻 bear 且动摇核心论点 → True
  },
])
```

**`requires_thesis_review` 规则**：
- kill 翻成 `triggered_bull`/`triggered_bear` → **必 True**
- signpost 翻 `bear` 且否定核心假设 → True
- 其余 → False
> True 不会自动跑 04/05——只在 web「建议重评 thesis」里点名，等用户在对话里发起。

---

## Step 3：industry / arena 周期重扫（recurring_review）

09/10 的 `upgrade_triggers` / `monitor_metrics` 无具体日期，按「距上次巡检」周期扫。
对每个 `recurring_review` 项：自动搜该 arena 的升级触发器关键词。若触发器命中，写一条
signpost/kill 等价的 proposal（locator 用触发器文本的 hash 或 metric 名）；判读完无论有无
命中，都记一次复查时间：
```python
from prism.scripts.topic import set_monitoring_reviewed
set_monitoring_reviewed(slug, variant)
```

---

## Step 4：收尾

- 把 `unparseable` / `price_unavailable` / `skipped_no_sidecar` 三桶**贴对话**（headless 模式写进 stdout），让用户知道哪些没扫到、为什么。
- **不**调 dashboard build——web 端读 queue 实时渲染；下次 04/05/thesis 升版会自动重建 dashboard。
- **不** confirm 任何 proposal。结束。

---

## 附录：monitoring_tier 三档（watchlist 之外的展示分层）

| Tier | 含义 | 触发频率 |
|------|------|----------|
| `deep` | 持仓 / 候选标的 | 每日 + 重大事件 |
| `watch` | 值得关注但暂不投 | 每周 |
| `dormant` | 历史归档 | 不主动 |

> 实际成本闸是 **watchlist**（用户在 web 勾选）：tier 只影响展示与建议,真正决定"扫不扫"
> 的是这个 event 在不在关注清单。`set_monitoring_tier` 已联动 `monitoring.enabled`。
