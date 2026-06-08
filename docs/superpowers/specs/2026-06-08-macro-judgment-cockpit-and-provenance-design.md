# 宏观层「判断驾驶舱 + 评估溯源」设计 (α+β 统一)

> 日期：2026-06-08 · slug `global-macro-rates-liquidity` · variant `opus4.8` · type=macro
> 实现计划：docs/superpowers/plans/2026-06-08-macro-judgment-cockpit-and-provenance.md

## 目标

把宏观层的「输入 → 判断」回路在 web 上做到**可控、可溯、可验证**，回应用户长期主张
（「不要静默 / 不是 trust-me / 因果须可核」）。一句话：让用户在输入源表上就能看清
**当前结论基于哪些输入、自上次评估这些输入变了什么、为什么得出该结论、是否该重估**，
并能选择监控哪些输入、一键组装重估简报。

## 背景与现状（已核实）

- 登记表 `macro_inputs.yaml`：**116 条输入**，仅 **8 条有 `observed.value`**（FRED 自动抓），
  83 条 `llm-web`、30 条 `fred-api`、3 条 `manual`。
- `observed` 现有字段：`{value, prev_value, z, as_of, next_due, last_proposed_value, checked_at, streak}`。
  **`prev_value` 是「上一次观测」，不是「上一次评估」。**
- `monitoring: {enabled: bool}` **已存在**于 schema，且 `scan_macro_inputs` 已尊重它
  （`enabled is False → 跳过`）——「让用户选哪些监控」只差 UI。
- **全系统无任何「评估快照」**：没有地方记录「上次写 regime_read 时各输入是什么值 / 哪些结论靠哪些输入」。
- 「评估」是一次 **LLM 行为**（在对话里重写 regime_read），非自动引擎；
  `monitor` 永不自动改 regime_read（spec 既定：判断永远人在 web 端触发）。
- regime_read 在 web 上是 `{{ html_body | safe }}` 整块渲染（决定了溯源不能安全地内嵌进散文）。

## 架构总览

**脊梁是一个新产物——评估快照 `outputs/regime_eval_log.yaml`。** 其余全部从它派生：
diff、「结论←输入」链、参与标记、重估简报。

```
                ┌─ 评估时(LLM 在对话里写) ─┐
 regime_read ──▶│  regime_eval_log.yaml    │◀── 第一份由阶段1补写
 (散文,人读)    │  (input_snapshot +       │
                │   conclusions[].based_on)│
                └────────────┬─────────────┘
                             │ 零-LLM 派生
        ┌────────────────────┼─────────────────────┐
        ▼                    ▼                      ▼
   diff(现值 vs 快照)   based_on 反查           重估简报
   = 变了什么           = 结论靠哪些输入        = 变化×受影响结论+到期/越带
        │                    │                      │
        ▼                    ▼                      ▼
   输入表 变化列(S3)    评估溯源 tab(S6)        发起重估(S5)→盖戳→对话重判→写回新快照
```

## 数据模型

### 新产物：`outputs/regime_eval_log.yaml`

```yaml
slug: global-macro-rates-liquidity
variant: opus4.8
updated: "2026-06-08T..."         # 任何写入刷新
reeval_pending: null              # 或 {stamped_at, brief: {...}}（S5 盖戳；append_evaluation 时清空）
evaluations:                      # 追加式，末条为最新
  - version: 1
    evaluated_at: "2026-06-08T..."
    note: "首份快照（阶段1由现有 regime_read 逆向补写）"
    input_snapshot:               # 评估那一刻每个被查输入的值；未抓的诚实记 null
      - {name: "美国政策利率", value: 3.625, as_of: "2026-06-07", used: true}
      - {name: "核心 PCE",    value: 2.8,   as_of: "2026-05-31", used: true}
      - {name: "某未抓输入",   value: null,  as_of: null,         used: false}
      - ...                        # 116 条全列，used=false/value=null 即「登记但未参与/未抓」
    conclusions:                  # 按结论挂输入（结构化链）
      - id: rates_us
        label: "美国利率体制"
        state: "高位筑顶 / 防二次通胀"
        based_on:
          - {input: "美国政策利率", role: load_bearing}
          - {input: "核心 PCE",    role: confirming}
        causal: "核心 PCE 黏 → 联储不敢转鸽 → 政策利率维持高位 → 利率体制偏紧"
      - {id: liquidity_us, label: "美国流动性体制", state: ..., based_on: [...], causal: ...}
      - {id: fx_cny,       label: "人民币汇率体制", state: ..., based_on: [...], causal: ...}
      - {id: quadrant,     label: "象限",          state: "滞胀", based_on: [...], causal: ...}
      - {id: fragility,    label: "脆弱度",        state: "high", based_on: [...], causal: ...}
```

**不变量（诚实/可验证，硬约束）：**
- `input_snapshot` **必须列全登记表所有输入**；未参与记 `used: false`，未抓记 `value: null`。
  禁止"只列被用到的"造成"看起来全覆盖"的假象。
- `conclusions[].based_on[].input` 必须能在 `input_snapshot` 里找到（CRUD 校验，悬空引用报错）。
- `role ∈ {load_bearing, confirming, background}`。

### `macro_inputs.yaml` 每条 input 新增字段（β / pt2）

| 字段 | 取值 | 含义 |
|---|---|---|
| `source_url` | str（可空） | 具体源链接（取代/补充模糊的 `source`） |
| `authority` | `official` / `primary` / `secondary` / `aggregator` | 权威性（官方/一手/二手/聚合） |
| `availability` | `scripted` / `scriptable_todo` / `no_stable_source` | 可用性/可脚本化判定 |
| `fetch_recipe` | `{url, parse:{...}}`（可空） | llm-web fetcher 的抓取配方；`no_stable_source` 则为空 |

`monitoring.enabled` 沿用既有字段，不新增。

## 组件

### `prism/scripts/eval_snapshot.py`（新，零-LLM）

- `create_eval_log(slug, variant) -> Path`
- `read_eval_log(slug, variant) -> dict`（缺文件返回空骨架 `{evaluations: [], reeval_pending: None}`）
- `append_evaluation(slug, variant, evaluation: dict) -> int`：校验不变量 → 追加 → version 自增 → **清 `reeval_pending`**
- `latest_evaluation(slug, variant) -> dict | None`
- `diff_since_last(slug, variant) -> list[dict]`：对登记表每条输入，比对 `observed.value`(现) 与 latest
  `input_snapshot[name].value`(快照) → `[{name, snapshot_value, live_value, delta, changed, breached, used, conclusions:[id...]}]`。
  无快照时全部 `changed=None`（标「首次评估，无基准」）。数值算 delta+breached（复用 `macro_registry._reading_breaches`），
  非数值按字符串比 `changed`。
- `conclusions_for_input(evaluation, name) -> list[str]`：based_on 反查，返回 conclusion id 列表。
- `assemble_reeval_brief(slug, variant) -> dict`：组合 `diff_since_last` 的 `changed/breached` 项 +
  `monitor.scan_macro_inputs` 的到期/越带项 + 每项受影响结论（反查）+ **未抓输入清单（盲区提示）**。
  纯数据，供 S5 展示与对话重判消费。
- `stamp_reeval_pending(slug, variant, brief) -> None` / 读取经 `read_eval_log()['reeval_pending']`。

### `prism/scripts/llmweb_fetch.py`（新，零-LLM，β）

- 仿 `fred_fetch.run_fred_fetch`：遍历 `fetch_method=='llm-web'` 且 `availability=='scripted'` 且有 `fetch_recipe`
  的输入，按 recipe 抓取 → `macro_registry.record_observation`。
- `availability` 为 `scriptable_todo` / `no_stable_source` 的**跳过并计数**，绝不假装抓到。
- 返回 `{fetched, skipped_todo, skipped_no_source, failed}`。
- 判源 + 写 recipe + 评 authority/availability 是**逐条增量**的 LLM 工作（在对话里做），本脚本只跑已配好的。

### 路由（`app/routes/prism.py`）

- `GET /{slug}/{variant}/eval-trace`（macro 守卫）→ 渲染 `prism/eval_trace.html`：
  latest evaluation 的 conclusions[] + 每条的 based_on/causal + diff_since_last。
- `POST /{slug}/{variant}/macro-inputs/monitoring`（form: `name`, `enabled`）→ `macro_registry.upsert_input`
  写 `monitoring.enabled`，重定向回输入表。输入不存在 → 404。
- `POST /{slug}/{variant}/reeval` → `assemble_reeval_brief` + `stamp_reeval_pending`，重定向回输入表（带简报锚）。
- 三个新路由都必须声明在 `/{output_key}` 通配之前（同既有 macro-inputs / transmission-map）。

### 模板

- `app/templates/prism/macro_inputs.html`：加 S1 报警看板（页顶）、S2 监控 toggle（行内 form）、
  S3 变化列、S4 参与/溯源徽章、S5 发起重估按钮 + 简报区、S7 源/权威/可用性列。
- `app/templates/prism/eval_trace.html`（新）：S6 推理链视图。
- `app/templates/prism/_view_tabs.html`：macro 分支加「评估溯源」→ `eval-trace`。

## Web 表面（S1–S7）

| 编号 | 位置 | 内容 | 数据来源 |
|---|---|---|---|
| S1 报警序列专版 | 输入表页顶 | alert_series 卡片：名/报警带/现值/越带状态(绿红+streak)/支撑结论 | `alert_series`+`alert_band`+`observed`+based_on 反查 |
| S2 监控开关 | 输入表行内 | toggle 写 `monitoring.enabled` | POST → macro_registry |
| S3 变化列 | 输入表行内 | 上次评估值 \| 现值 \| Δ \| 是否越带；无数据显「未抓」 | `diff_since_last` |
| S4 参与/溯源标记 | 输入表行内 | 「是否参与上次评估」+「支撑哪些结论」chip；登记未参与者标灰 | snapshot `used` + based_on 反查 |
| S5 发起重估 | 输入表页 | 按钮 → 组装并展示重估简报 + 盖「待重判」戳 | `assemble_reeval_brief` + `stamp_reeval_pending` |
| S6 推理链 | 评估溯源 tab（独立） | 结论 ← 依赖输入(role) ← 因果句；并列现 vs 快照变化 | latest evaluation + diff |
| S7 源/权威/可用性 | 输入表抓取列展开 | 具体源链接 + authority 徽章 + availability 徽章 | 新 schema 字段 |

**S6 为何独立 tab（非内嵌 regime_read）：** regime_read 是整块 `html_body` 渲染的散文，内嵌结构化链
需拼接生成 HTML（脆、破坏渲染逻辑），且与既有「活注解层」叠加打断阅读流；溯源是「给人核的台账」，
职能不同，独立 tab 更清晰，且能承载 diff/参与状态（散文放不下）。

## 关键数据流

1. **评估时写快照**（对话里，LLM）：重写 regime_read 后，调 `append_evaluation` 写 input_snapshot（116 条全列）
   + conclusions 链。清掉 `reeval_pending`。
2. **diff 计算**（零-LLM，请求时）：`diff_since_last` 比对现 `observed.value` vs 快照值。
3. **发起重估**（零-LLM，S5）：`assemble_reeval_brief` → 展示 + 盖戳。用户拿简报到对话发起重判 → 回到流程 1。
4. **监控开关**（零-LLM，S2）：toggle 写 `monitoring.enabled`，影响 `scan_macro_inputs` 是否纳入。
5. **数据抓取**（零-LLM）：`fred_fetch`（既有）+ `llmweb_fetch`（新，仅跑 scripted）刷新 `observed`。

## 落地阶段（一份 spec，四阶段，各自可独立交付/测试）

- **阶段 1 — 快照骨架**：`eval_snapshot.py`（CRUD+不变量校验+diff+简报组装）+ **补写当前 regime_read 的第一份快照**
  （读现有 regime_read + 116 输入逆向填，未抓记 null）。
- **阶段 2 — 展示面**：S1 / S3 / S4 / S6（含 eval-trace 路由+模板+tab），只读跑在阶段 1 数据上。
- **阶段 3 — 控制面**：S2 监控开关（POST）+ S5 发起重估（简报+盖戳）。
- **阶段 4 — β 数据落地**：schema 字段 + S7 列 + `llmweb_fetch.py` + 逐条判源工作流文档。

## 测试策略（TDD，逐步红→绿）

- `prism/scripts/test_eval_snapshot.py`（新）：append/校验不变量（悬空 based_on 报错、必须列全输入）、
  latest、diff（有/无快照、数值/非数值、越带）、简报组装（含未抓盲区清单）、reeval_pending 盖戳/清空、幂等。
- `prism/scripts/test_llmweb_fetch.py`（新）：仅抓 scripted、跳过 todo/no_source 并计数、recipe 解析（mock httpx，同 `test_fred_fetch`）。
- `tests/test_macro_inputs_web.py`（扩展）：S1 报警看板渲染、S2 toggle POST 改 enabled、S3 变化列（含「未抓」）、
  S4 参与/未参与徽章、S5 发起重估盖戳、S7 源/权威/可用性徽章；`eval-trace` 路由渲染 + macro 守卫 404 + tab 出现。
- `prism/scripts/test_macro_registry.py`（扩展）：新字段 upsert/校验（authority/availability 枚举）。
- 解释器 `.venv/bin/python`（3.14.4），`-p no:cacheprovider -q`。

## 错误处理 / 边界

- 缺 `regime_eval_log.yaml`：视为「无历史评估」——diff 全标「首次」，eval-trace 显示「未生成首份快照」而非 500。
- 登记表有、快照无的输入：S4 标「未参与上次评估」。
- 非数值输入：diff 用字符串比 `changed`，不算 delta/breach。
- 监控 toggle 命中不存在输入：404。
- `append_evaluation` 校验失败（悬空 based_on / 未列全输入）：抛错，不落盘（保持快照可信）。
- `llmweb_fetch` 单条抓取失败：计 `failed`，不中断其余（同 fred_fetch）。

## 显式取舍 / 暂不做（YAGNI）

- 不做「一键页面内跑 LLM 重判」——违背 web 零-LLM、判断在对话的既定边界。
- 不强求 83 条 llm-web 全脚本化——`no_stable_source` 是合法终态，诚实标注优于假抓。
- S6 不内嵌 regime_read——见上。
- 重估简报不自动发起对话——只组装+展示+盖戳，发起仍是人的动作。

## 受 GitNexus 纪律约束的实现期动作

实现阶段改 `macro_registry` / 路由等既有 symbol 前，按 CLAUDE.md：先 `gitnexus_impact(upstream)` 报爆炸半径、
HIGH/CRITICAL 先警告；提交前 `gitnexus_detect_changes`；重命名走 `gitnexus_rename`。
