# 宏观输入层 — 解析器演进 + policy 立场模型 + 面板打磨 设计

> 上游 spec（脊梁）：[2026-06-08-macro-judgment-cockpit-and-provenance-design.md](2026-06-08-macro-judgment-cockpit-and-provenance-design.md)
> 实现计划：（待 writing-plans 产出）

**日期**：2026-06-08
**状态**：设计已与用户逐节确认，待落计划。

## 目标

让宏观输入→判断回路的数据层更**全**（fetcher 能吃 csv，不只 json）、更**可核**（policy 立场有序、可溯源）、更**可读**（中文 / 表格 / 变更一眼看清）。

本 spec 覆盖 **A（面板打磨）+ B（schema/引擎演进）**。**C（内容填料：逐条写 recipe、判源评权威、填 policy 立场、补术语表）是依赖本 spec schema 就位的后续工作，另走一轮 spec，不在此。**

## 承重原则（延续上游 spec）

输入→判断回路必须**可控、可溯、可验证**：

- **不静默**：任何校验缺失（缺必填键、非法枚举、悬空引用）即抛错，绝不悄悄跳过或假装成功。
- **不 trust-me**：判断结论可溯到输入、输入可溯到出处。policy 立场必须附 evidence。
- **零-LLM 派生**：diff / 汇总 / 渲染全部由脚本零-LLM 派生；判断永远人在对话里触发。
- **诚实盲区**：抓不到的标"未抓"，没稳定源的标 `no_stable_source`，绝不编造。

---

## 范围决策（已与用户确认）

| 决策点 | 选定 |
|---|---|
| 本轮 spec 范围 | A（面板打磨）+ B（schema 演进）合一份；C（填料）后续另走 |
| fetcher 解析器 | json + csv 两个解析器 + `kind` 判别/注册表脚手架；html 留接口、后续按需加 |
| policy 立场模型 | 命名有序轴（stance_scale）+ 必附 evidence |
| 变更汇总表 | 输入页顶、只列变化项、与下方全表互补 |

---

## B-1 · fetcher：recipe 类型化 + 解析器注册表

### 现状

`prism/scripts/llmweb_fetch.py` 的 `fetch_by_recipe` 只支持 JSON（`json_path` / `date_path`）。真实源异构（json API / csv 下载 / html 页），JSON-only 会漏掉很多源。

### 目标形态

把解析升级成**按 `kind` 判别的声明式解析器注册表**。解析仍是**声明式**（选择器写在 recipe 里），**不是每条输入一段命令式脚本**——保住可统一校验、零-LLM、可诚实跳过。

recipe 结构：

```yaml
fetch_recipe:
  kind: csv                # json | csv（缺省 json，向后兼容现有写法）
  url: https://…
  parse:
    # kind=json: json_path: [...]   date_path: [...]      （现有逻辑原样保留）
    # kind=csv:  value_column: "Value"  date_column: "DATE"  row: latest   # latest | first | <int>
```

### 设计

- `llmweb_fetch.py` 建解析器注册表 `_PARSERS = {"json": _parse_json, "csv": _parse_csv}`。
- `fetch_by_recipe(recipe, *, client=None)`：
  - 读 `kind`（缺省 `"json"`）。
  - 取响应：`json` → `resp.json()`；`csv` → `resp.text`。
  - 派发给对应解析器，统一签名 `parser(payload, parse_cfg) -> (value: float|None, as_of: str|None)`。
- `_parse_json(payload, cfg)`：保留现有 `_dig` 取 `json_path` / `date_path` 逻辑。
- `_parse_csv(text, cfg)`：用标准库 `csv.DictReader` 解析；按 `value_column` 表头取列、按 `row`（`latest`=末行 / `first`=首行 / 整数=索引）选行；`date_column` 同理取日期；值转 `float`，失败返回 `(None, as_of)`。
- `run_llmweb_fetch` 的抓取闸门不变：只抓 `availability=='scripted'` 且有 `fetch_recipe` 的，其余诚实计数跳过。

### 校验（macro_registry.validate_registry 内）

- `fetch_recipe.kind` 必须在注册表键内（json/csv），否则报错。
- 按 kind 检查 `parse` 必填键：json 需 `json_path`；csv 需 `value_column`。缺失即报错（**不静默**）。
- 无 `fetch_recipe` 的输入不触发上述校验（字段可空）。

### html（本期不实现）

`kind: html` 留作未来扩展点：注册表加一个 parser 即可。html 抓取脆（选择器易碎），且很多源属 `no_stable_source`，应继续走 `availability` 诚实闸门——能加 parser ≠ 都该脚本化。

---

## B-2 · policy：命名有序立场轴 + 必附 evidence

### 现状

policy 输入（货政报告 / 点阵图 / 官员讲话等，登记表 21 条）没有数值读数，现在一律显示"未抓"。它们的"读数"本质是**定性立场**，且不同维度不在同一根轴上（鹰/鸽 不能表达财政扩张/收缩）。

### 目标形态

policy 输入声明它在哪根**有序轴**（`stance_scale`）上，读数 `observed.stance` 是轴上一档，并**强制附 `evidence` 出处**。

### 种子轴（4 根，档位有序，diff 据此算方向）

| stance_scale | 档位（有序，低→高） | 适配输入 |
|---|---|---|
| `hawk_dove` | 鸽 / 偏鸽 / 中性 / 偏鹰 / 鹰 | 货政报告、FOMC 措辞、官员讲话 |
| `ease_tighten` | 宽松 / 偏松 / 中性 / 偏紧 / 收紧 | 中国货币政策定调、监管 |
| `expand_contract` | 扩张 / 中性 / 收缩 | 财政 / 发债指引 |
| `path_shift` | 上移 / 不变 / 下移 | 点阵图 / SEP 路径 |

轴定义集中存为 `macro_registry.py` 常量（轴名 → 有序档位元组），供校验与 diff 方向计算共用。

### 数据形状

```yaml
# input 级：声明用哪根轴
stance_scale: hawk_dove
# 读数（policy 输入的 observed 用 stance 取代 value）
observed:
  stance: 偏鹰              # 必须是 stance_scale 的合法档
  as_of: '2026-05-...'
  evidence: "5月声明删去'保持耐心'，主席Q&A 三提通胀上行风险"   # 设了 stance 即必填
```

### 校验（macro_registry.validate_registry 内）

- `stance_scale`（若设）必须是已注册轴名，否则报错。
- 若 `observed.stance` 设了：
  - 该输入必须声明了 `stance_scale`；
  - `stance` 必须是该轴的合法档位；
  - `evidence` 必须非空——否则报错（**不 trust-me**）。

### diff（eval_snapshot.diff_since_last 内）

policy 输入走立场比对而非数值比对：

- `changed = live_stance != snapshot_stance`。
- **方向** `direction`：按档位在轴中的索引差符号 → `"更鹰"/"更鸽"`（或 更松/更紧、扩张/收缩、上移/下移，按轴取词），无变化为 `None`。
- 不计算数值 `delta`，不显示"越带"（policy 无报警带）。
- diff 行新增 `stance`(现值) / `snapshot_stance`(上次) / `direction` 字段；数值输入这些为 `None`，policy 输入数值字段为 `None`——两类各取所需，互不干扰。

### 信息完整性

policy 立场只是**可核的触发器**：立场变化触发重判，真正重判在对话里对着源做。结论的完整推理仍沉淀在 `causal` 句；`evidence` 让"凭什么是这一档"可查。所以压成一档不丢信息——丰度在 causal，可核性在 evidence。

---

## A · 面板打磨

均为展示层改动（数据仍存代码 / 不改 schema），用现成的 `diff_since_last` 数据。

### A-1 承重报警序列：卡片 → 表格

`macro_inputs.html` 把 `.alert-board` 的卡片改为表格，列：

`输入 / 报警带 / 上次值 / 现值 / Δ / 越带 / 支撑结论`

数据源不变（`inputs | selectattr('alert_series')` + `diff.get(name)`）。

### A-2 变更汇总表（输入页顶）

`macro_inputs.html` 页顶新增一个表，**只列 `diff` 中 `changed` 为真的输入**：

`输入 / 上次→现值 / Δ（或立场方向）/ 越带 / 影响哪些结论`

- 有首份快照才显示；无快照不显示。
- 有快照但无变化项 → 显示"自上次评估无变化"。
- 与下方 116 行全表互补：汇总表回答"变了啥"，全表回答"全貌"。
- 路由 `prism_macro_inputs` 已传 `diff`，无需新数据；模板内 `diff.values() | selectattr('changed')` 过滤。

### A-3 中文显示（展示层映射，数据存代码不变）

模板内建映射字典，渲染时转中文：

| 字段 | 代码 → 中文 |
|---|---|
| targets | rates→利率, liquidity→流动性, fx→汇率 |
| importance | load_bearing→承重, confirming→确认, background→背景 |
| cadence_type | event→事件, policy→政策, series→序列（+ 悬停释义） |
| mechanism | CD/CF/CO/CR → 悬停释义（值不变，仅 tooltip） |

cadence 悬停释义文案：事件=不定期事件（如 FOMC 会议、数据发布日）；政策=政策发布（如 LPR、货政报告）；序列=可连续抓取的常规时间序列。

mechanism 悬停释义文案（取自上游 spec §表）：CD=因果驱动；CF=资金流渠道（因果子类）；CO=同步读数；CR=仅相关。

### A-4 eval-trace 加「评估逻辑」标签

`eval_trace.html` 在每条结论的 `causal` 段前加一行浅色小标签「评估逻辑」，明确"这段是判断逻辑、下表是它依赖的输入"。

---

## 数据流 / 改动文件

| 文件 | 改动 |
|---|---|
| `prism/scripts/llmweb_fetch.py` | 解析器注册表 `_PARSERS`、`_parse_json`/`_parse_csv`、`fetch_by_recipe` 按 kind 派发 |
| `prism/scripts/macro_registry.py` | 轴常量（4 根有序轴）、recipe kind/parse 键校验、stance_scale/stance/evidence 校验 |
| `prism/scripts/eval_snapshot.py` | `diff_since_last` 支持 policy 立场比对 + 方向（新增 stance/snapshot_stance/direction 字段） |
| `app/templates/prism/macro_inputs.html` | 报警表格化、变更汇总表、中文映射、cadence/mechanism 悬停 |
| `app/templates/prism/eval_trace.html` | 「评估逻辑」标签 |
| `app/routes/prism.py` | 如需，向模板传中文映射常量（也可纯模板内建） |

## 测试策略（TDD：每项先红后绿）

| 测试 | 文件 |
|---|---|
| csv 解析器：按列/行取值与日期 | `prism/scripts/test_llmweb_fetch.py` |
| kind 派发：json/csv 正确路由；未知 kind 报错 | `prism/scripts/test_llmweb_fetch.py` |
| recipe 校验：缺 kind 必填 parse 键报错 | `prism/scripts/test_macro_registry_fields.py` |
| stance_scale 非法 / stance 越档 / 缺 evidence 报错 | `prism/scripts/test_macro_registry_fields.py` |
| policy diff：立场变化方向（更鹰/更松）正确 | `prism/scripts/test_eval_snapshot.py` |
| 报警表格渲染 | `tests/test_macro_inputs_web.py` |
| 变更汇总表渲染（有变化 / 无变化 / 无快照三态） | `tests/test_macro_inputs_web.py` |
| 中文映射渲染（targets/importance/cadence） | `tests/test_macro_inputs_web.py` |
| eval-trace「评估逻辑」标签渲染 | `tests/test_macro_inputs_web.py` |

## 错误处理

- 解析失败（HTTP 错 / JSON 解析错 / csv 列缺失 / 值非数值）→ `fetch_by_recipe` 返回 `(None, as_of)`，`run_llmweb_fetch` 计入 `failed`，不写观测、不抛断流程。
- 校验失败（registry 非法）→ `validate_registry` 收集错误列表，调用方决定抛错；不静默放过。
- 展示层缺数据（无快照 / 无 diff）→ 优雅降级显示"未抓"/"无变化"，不报错。

## 不做（YAGNI / 留待后续）

- html 解析器（留 kind 扩展点）。
- 逐条填 recipe / 判源 / 填 policy 立场 / 补术语表（C，另走一轮）。
- policy 立场的数值化打分（用户已否，有序档位足够）。
- 报警带应用到 policy（policy 无带，只报方向）。
