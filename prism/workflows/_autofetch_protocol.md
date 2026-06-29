# 自动获取协议（auto-fetch 规约 · R2 有效尝试判定）

> 被 `00-research-topic.md`(Step 6.5)、`01-build-roadmap.md`(Step 5.6)、`02-gather-materials.md`(Step 5.7)、`03-extract-findings.md`(Step 2.4/2.4b)、`05-critic-review.md`(Step 6.5)共享引用。
>
> **一句话**：每个产 todo 的点，浮给用户前必须先**有效尝试**一次自动抓；留不留 user-todo、是否要重试，由**尝试的真实结果**决定，不由 tier/info_tier 标签事前 gate。
>
> ⚠️ **venv 硬约定**：凡命令 import 第三方包——`fetch_report_prism`/`annual_report_extractor`/`financial_data`/`market_data`/`mineru_api`（依赖 requests/pymupdf/akshare/yfinance）——一律用 `./.venv/bin/python`（含 `python3 -c "…"` 里 import 这些模块的块）。裸 `python3` 仅用于纯 CRUD（`prism.scripts.topic`/`manifest`/`outputs`/`findings`/`gap_detector`）。裸跑 fetcher/extractor 会 `ModuleNotFoundError: No module named 'requests'/'pymupdf'/'akshare'`。

---

## 总规约：产即收（最高优先级）

> **谁产 todo，谁当场收。** 任一阶段写下 todo，**立刻**在同一阶段跑 auto-fetch（R1/R2/R3）盖 `fetch_status`：抓到→`done`、确认公开无源→留 `pending` 交用户（empty 硬闸门）、工具失败→重试。
>
> - **下游阶段只消费已入库的料，绝不替上游补抓。** 00 产的 todo 在 **00 Step 6.5** 当场抓（todo 产在 thesis 之后、赌注已锁，eager-fetch 不破 bet-first）；01/03/05/07 产的 todo 在本阶段当场收。01 只补抓自己 Step 2/3 新增的 todo + 按 R3 重试上游遗留的 `error`，不重抓已 `fetched`/`empty` 的。
> - **prescan（事实校准）永不碰 todo 闭环。** prescan 只入库校准事实（标 `addresses=['scope']`）+ funnel + 写 log，**不产生、不闭环任何 todo**。
> - **闭环只走文档身份**（见下「闭环键」），脚本侧**没有**任何 K# 自动撮合（旧 `auto_resolve_todos` / `suggest_*coverage*` 已彻底删除）。

---

## 三条规约

- **R1 全覆盖**：所有 tier（含 tier3）、所有 info_tier（含 hard）的缺口都要尝试。info_tier 只决定**努力顺序/强度**（hard 先上 exa advanced + 权威 URL WebFetch；public 可单跑 adapter），**不再作为跳过门槛**。
- **R2 有效尝试**：一次有效尝试 = 搜索真的跑了、且公开**确实**没有 → 才可降级。工具/网络/限流故障**不算尝试**，必须重试，**不得据此降级**。
- **R3 消费前兜底**：见各 workflow 的逐环/合成前钩子——消费某 todo 的材料前确认它已被有效尝试。

---

## 每次尝试后必做：盖 `fetch_status`

```python
from prism.scripts.topic import mark_todo_fetch
mark_todo_fetch(slug, variant, '<task 子串>', '<fetched|empty|error>', note='<一句话依据>')
```

| 盖什么 | 何时 | 后续 |
|--------|------|------|
| `fetched` | 抓到**这条 todo 要的那份文档**并入库（manifest 已登记） | 完结：按文档身份显式盖（见下「闭环键」） |
| `empty` | **有效尝试**确认公开无源 | 触发 empty 硬闸门 → 用户决策 `waived`/`will_collect`，**不静默写缺口** |
| `error` | 工具/网络/限流失败 | **必须重试**；永不降级为 user-todo；R3 会在下个 checkpoint 再试 |

> 三态 `fetched`/`empty`/`error` **全部必须显式盖**——脚本不再按 K# 自动盖戳（旧 `auto_resolve_todos` 已废）。漏盖 `fetched` → R3 会以为没抓过、反复重抓。

### 闭环键 = task/文档身份，**不是 K#**（必读）

> todo 是「去收**某份具体文档**」的任务。`addresses=[K#]` 只是「这份料喂哪个命门」的**相关性标签**（多对多、可空），**不是 todo 的身份**。
> 一篇挂 `K2` 的二手价 news 与一条挂 `K2` 的「年报全文」todo 共享 K2，**不代表年报到手**——多条不同 todo 常共享同一 K#（见 memory `feedback_todo_closure_key`）。
>
> 因此**禁止用 K# 交集闭环 todo**。闭环只走按 `task 子串`（文档身份）的显式调用：
> - 抓到它要的那份文档 → `mark_todo_fetch(slug, variant, '<task子串>', 'fetched', note=...)`
> - 确认覆盖、标完结 → `update_user_todo_status(slug, variant, '<task子串>', 'done', covered_by=[mat...])`
>
> 复用旧料同理：主 agent 读 todo + 读料，确认就是它要的那份 → `update_user_todo_status(..., 'done', covered_by=[旧mat])`。脚本**没有**任何「列共享 K# 候选」的函数（旧 `auto_resolve_todos` / `suggest_todo_coverage_candidates` 已删）——撮合是主 agent 按文档身份做的判读，不是脚本的 K# 求交。

---

## 判定表 A：web-search 阶梯（exa / adapter semantic / WebFetch）

阶梯：① `mcp__exa__web_search_advanced_exa`(找分析全文) → ② adapter `--intent semantic`(补 exa 未覆盖) → ③ `mcp__exa__web_fetch_exa`(抓权威 URL 全文)。判定按**最终信号**：

| 信号 | 含义 | 盖 | 动作 |
|------|------|----|----|
| `register_web_search_batch` 有 high/mid 入库（`failure_mode='none'`） | 抓到 | `fetched` | 入库后主 agent 按文档身份 `update_user_todo_status(..., 'done', covered_by=[mat])` 闭环 |
| responding-provider 返回 0 命中：CLI `EXIT_NO_HITS=20` 或 `failure_mode='upstream_empty'` 且 provider 确有响应 | **有效空** | `empty` | 触发硬闸门 |
| CLI `EXIT_ALL_EXHAUSTED=40` / `RuntimeError('all providers exhausted')` | 所有 key 在冷却/耗尽 | —（先别盖） | 按 keypool 退避梯 **[60,300,1800]** 重试；本轮无法等就先盖 `error`，交 R3 下轮再试 |
| CLI `EXIT_CONFIG=50` | 无可用 key（配置问题） | —（先别盖） | 修 key（见 `reference_mcp_env_location`）后重试；仍不行盖 `error` |
| `failure_mode='all_low_band'`（有命中但全被判低质丢弃） | **非有效空** | —（先别盖） | 先走 H2 救回（`extract_url_features` + LLM tier 判，必要时 `register_web_search_batch` 时显式 domain_tier override），再判 fetched/empty |

**关键**：`EXIT_NO_HITS`(真没有) ≠ `EXIT_ALL_EXHAUSTED`(key 没了)。前者是有效空可降级，后者是 transient 必重试——绝不能把 40/50 当成"公开没有"。

---

## 判定表 B：报告抓取（`fetch_report_prism`）

`scripts/fetch_report_prism.py` 已内置 `_with_retry`（ValueError 不重试、URLError/RequestException/429/5xx 重试 3 次退避 (2,8,30)s）。调用方按结果盖：

| 结果 | 含义 | 盖 |
|------|------|----|
| 返回 Path / 非空 list | 抓到入库 | `fetched`（resolve 路径会盖，可省） |
| 抛 `ValueError`（"No ... report found" / "CIK not found" / "Company not found"） | **有效空**：该标的/年度确无此报告 | `empty` |
| 重试耗尽后抛网络异常（URLError/RequestException/Timeout） | transient 失败 | `error` |

> 港股/英股/韩股/日股零 key，路由见 `fetch_report_prism._route`；ticker 格式见 01 Step 5.5。
> `info_tier: hard`（专家访谈/产业链调研/付费数据库）**同样要尝试一次**——多半 `empty`，但 empty 要由真实结果证明，不由标签预判。付费卖方深度常有公开转载（exa 能命中），别先入为主跳过。

---

## empty 硬闸门（reference）

`fetch_status='empty'` 不是终点。合成前与逐环 R3 调 `empty_undecided_todos(slug, variant)`，非空必须 `AskUserQuestion`（multiSelect）逐条让用户选：

- **跳过(waived)** → `set_todo_disposition(slug, variant, '<task子串>', 'waived', note='<理由>')` → 合成写"该项公开数据缺失"。
- **我来收(will_collect)** → `set_todo_disposition(..., 'will_collect', note=...)` → 合成写"待用户补料"显式缺口，保持可见 pending；用户补的料一登记后，由主 agent 按文档身份显式 `update_user_todo_status(..., 'done', covered_by=[新mat])` 收口（脚本不再自动翻转，见本文件「闭环键」）。

> AskUserQuestion 的 label/description **禁中文弯引号** `“”`（U+201C/U+201D 触发 InputValidationError），用 「」 或不加引号。

全部 empty 决策完成（`empty_undecided_todos` 空）前**不进决策链、不写任何缺口**——这是反静默核心。
