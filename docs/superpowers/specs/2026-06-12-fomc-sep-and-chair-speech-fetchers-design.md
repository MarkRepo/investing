# 设计：FOMC 点阵图(SEP) 数值通道 + 美联储主席讲话 取文通道

日期：2026-06-12
主题 slug：`global-macro-rates-liquidity` / `opus4.8`

## 背景与目标

宏观层登记表（`macro_inputs.yaml`）里两条目前 `availability: llm` 的输入，其取数实际可脚本化、零 LLM：

1. **FOMC 点阵图(SEP)** — 数值型（`observed.value` = 近年中位联邦基金利率，现 = 3.4）。当前每轮靠 LLM 读 Fed 页判读，烧 token。Fed 的 SEP 投影表是静态 HTML，可脚本直拉。
2. **美联储官员讲话(主席)** — 立场型（`stance_scale: hawk_dove`，鹰鸽判读）。判读必须留给 LLM，但**原文下载**可脚本化（仿 FOMC 声明/纪要的取文通道），省去 LLM 每轮自己找页、并让新讲话自动发现。

目标：给 (1) 加**数值**脚本通道（`fetch_method: fomc_sep`），给 (2) 加**取文**脚本通道（`text_fetch: fed_speech`）。两者各仿一个已落地的同类 fetcher，自动继承定时巡检、去重门、Web 批量刷新。

非目标：不改 (1) 的单值口径（只落近年中位，不落全路径）；不把 (2) 的鹰鸽判读脚本化（仍 LLM）。

## 数据源已验证

- **SEP**：`fomccalendars.htm` 链接全部 `fomcprojtabl{YYYYMMDD}.htm`（实测 20 条，最新 `20260318`）。该表含一行 `<tr>`，剥标签后文本以 `Federal funds rate` 开头，其后第一个数字 = 近年中位（实测 `3.4 3.1 3.1 3.1` = 2026/2027/2028/长期），与登记表现有 evidence 完全吻合。
- **主席讲话**：主页 `speeches-testimony.htm` 为 JS 渲染（脚本取不到）。但 Fed 暴露静态 JSON feed `https://www.federalreserve.gov/json/ne-speeches.json`（utf-8-sig，1320 条），每条 `{d:日期, t:标题, s:讲话人, l:相对链接}`。过滤 `'Chair' in s and 'Vice Chair' not in s` 干净命中 `Chair Jerome H. Powell`（含 Chairman / Pro Tempore 历史变体），排除副主席（实测 290 条主席讲话）。feed 大致 newest-first，但脚本解析 `d` 取最大日期以防排序异常。

## A 部分 — SEP 点阵图数值通道

新文件 `prism/scripts/fomc_sep_fetch.py`，仿 `fedwatch_fetch.py`（数值通道，纯函数与 IO 分离）。

### 纯函数（可单测，零网络）

- `find_latest_projtabl(calendar_html: str) -> tuple[str, str] | tuple[None, None]`
  正则 `fomcprojtabl(\d{8})\.htm`，取最大日期 → `(绝对url, as_of='YYYY-MM-DD')`；无命中 → `(None, None)`。
- `parse_median_funds_rate(projtabl_html: str) -> float | None`
  扫 `<tr>`，剥标签后文本以 `Federal funds rate` 开头者，取其后第一个数字 token（`float`）。无命中/无数字 → `None`（诚实）。

### IO 入口

- `fetch_fomc_sep(slug, variant, *, client=None, input_name=None) -> dict`
  GET 日历页 → `find_latest_projtabl` → GET 投影表 → `parse_median_funds_rate` → 成功则 `reg.record_observation(value, as_of)`。返回 `{value, as_of, url, ok}`；任何一步取不到返回 `{"error": ...}`（真失败，调度器记 `record_fetch_error`）。
- `run_fomc_sep_fetch(slug, variant, *, only=None, client=None) -> dict`
  扫 `fetch_method=='fomc_sep'` 且 `availability=='scripted'` 的输入，逐条抓（一般仅 1 条）。失败记 `record_fetch_error` 计数、不连累其余。返回 `{"fetched", "skipped_todo", "failed"}`（仿 fedwatch summary）。
- `main(argv)`：无参时活体冒烟（拉真表打印中位）；带 slug 跑 `run_fomc_sep_fetch`。

### 登记表改动（`FOMC 点阵图(SEP)`）

- `availability: llm → scripted`
- 加 `fetch_method: fomc_sep`
- `cadence_type: event`、单值口径、`source_url`（日历页）不变
- 无需额外 config 块（无参）。

### 接线

1. `prism/scripts/macro_registry.py`：`VALID_FETCH_METHOD += ("fomc_sep",)`。validator **不**加强制 config 块（无参通道，类比无专属块校验的简单通道）。
2. `app/monitor_runtime.py` `run_monitor_cycle`：在 cftc / fedwatch 块旁加一个 `fomc_sep` 派发块（遍历 macro 主题调 `run_fomc_sep_fetch`，失败吞掉不阻断周期），位置在 recipe 派生之前。
3. `app/routes/prism.py` 单条手动路由（约 967 行 `elif method == ...` 链）：加 `elif method == "fomc_sep": from prism.scripts import fomc_sep_fetch; summary = fomc_sep_fetch.run_fomc_sep_fetch(slug, variant, only={name})`。
4. `app/routes/prism.py` `fetch-script-all` 批量路由：import 加 `fomc_sep_fetch`，加 run 块（失败吞掉）、`fomc_sep_n` 计数、并入 JSON summary 与 `fetched` 合计。

## B 部分 — 主席讲话取文通道

新文件 `prism/scripts/fed_speech_fetch.py`，仿 `fomc_fetch.py` / `pbc_mpr_fetch.py`（取文通道，自带 HTML helper，不交叉 import）。**只下原文，鹰鸽立场仍 LLM 判读**，故 `availability` 保持 `llm`。

### 纯函数（可单测，零网络）

- `pick_latest_chair(entries: list[dict]) -> dict | None`
  过滤 `'Chair' in s and 'Vice Chair' not in s`，解析 `d`（`'M/D/YYYY h:mm:ss AM/PM'`）取最大日期。无命中 → `None`。
- `_strip_html` / `_extract_body`：本仓约定各取文 fetcher 自带一份（仿 pbc_mpr），讲话正文起始标记 + footer 截断。

### IO 入口

- `fetch_fed_speech(slug, variant, *, client=None, input_name=None) -> dict`
  GET `ne-speeches.json`（utf-8-sig）→ `pick_latest_chair` → GET 讲话页（`_FED_BASE + l`）→ 剥标签 → 写 `inbox/fed_speech_latest.md`（标题/讲话人/日期/url + 正文 + 脚注说明立场判读归 LLM）→ `reg.set_local_cache_path`。返回 `{title, speaker, date, url, cache_path, ok, fingerprint}`；feed/讲话页失败 → `{"error": ...}`。`fingerprint = 讲话相对链接`（内嵌日期，发布即定型）。
- `fetch_one(slug, variant, entry, *, client=None) -> dict`：取文调度器入口（`text_fetch=='fed_speech'` 路由到此），用 `entry['name']` 作目标输入名。
- `main(argv)`：CLI 直跑（默认主题）。

### 登记表改动（`美联储官员讲话(主席)`）

- 加 `text_fetch: fed_speech`
- `local_cache_path` 由 fetcher 写入
- `availability` 保持 `llm`（立场判读仍 LLM）。

### 接线

1. `prism/scripts/macro_registry.py`：`VALID_TEXT_FETCH += ("fed_speech",)`。
2. `prism/scripts/textfetch.py`：import `fed_speech_fetch`，`_FETCHERS["fed_speech"] = fed_speech_fetch.fetch_one`。
3. 无需改 `monitor_runtime` 或路由：定时循环已调 `run_textfetch`（遍历全部 `text_fetch` 项）、批量路由已调 `run_textfetch`、单条手动取文走 `textfetch.fetch_entry`（登记表驱动）——全自动纳入。

## 错误处理

- 两 fetcher 任一步取不到 → 返回 `{"error": ...}`；`run_*` 调 `reg.record_fetch_error` 留痕（哪条/何时/何因），不动旧 `value`/`local_cache_path`，不连累批次其余项。
- monitor / 批量路由对整通道异常一律 try/except 吞掉、记日志、不阻断周期。

## 测试

- `prism/scripts/test_fomc_sep_fetch.py`：
  - `find_latest_projtabl` 从内联日历 HTML 片段（多日期）取最大 → 正确 url/as_of。
  - `parse_median_funds_rate` 从内联投影表 `<tr>` 片段断言 = `3.4`；无 `Federal funds rate` 行 → `None`。
- `prism/scripts/test_fed_speech_fetch.py`：
  - `pick_latest_chair` 从内联 JSON（含 Chair / Vice Chair / Governor 混合 + 乱序日期）取最新主席条 → 正确条目；无主席条 → `None`。
  - `_extract_body` 从内联讲话 HTML 片段剥出正文（去 footer）。
- 均单测纯函数、零网络；遵循现有 `test_mofcom_fetch.py` / `test_pbc_mpr_fetch.py` 风格。

## 影响面（gitnexus 预检见 plan）

- 新增 2 文件 + 2 测试；改动 `macro_registry.py`（2 枚举元组追加，低风险）、`textfetch.py`（1 注册行）、`monitor_runtime.py`（1 派发块）、`app/routes/prism.py`（2 处路由追加）、`macro_inputs.yaml`（2 条目字段）。
- 现有 fetcher 行为不变；新通道隔离，validator 向后兼容（仅放宽枚举）。
