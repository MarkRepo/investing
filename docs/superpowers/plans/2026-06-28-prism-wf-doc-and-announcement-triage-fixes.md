# Prism Workflow — 文档修复 + 公告标题分诊重设计 Implementation Plan (v2 · verbatim)

> **For agentic workers (Sonnet):** 逐任务执行。每个 Edit 的 `old_string` 均从当前文件 **verbatim 抄录**；执行前先 `Read` 目标文件确认该串仍存在（其它任务可能已改动行号，用唯一串匹配，不要靠行号）。脚本改动**先跑 gitnexus `impact`**。每个任务末尾有验证命令，必须跑且看到预期输出才算完成。

**已确认的 4 个决策（baked in，无需再问）：**
1. `fetch()/fetch_many()` 的 `with_announcements` 默认 **翻成 `False`**——report fetch 永不自动拉公告。
2. `list_announcements_cn` **沿用现有 5 类目**（yjygjxz/zf/kzz/fxts/tbclts）。
3. list 清单交 LLM 前 **仅剪纯冗余件**（摘要/英文/更正/修订），治理件保留。
4. Task C（snippet 兜底）**仅改文档**。

**Goal:** 修 cn-adc 这轮暴露的 6 个缺陷。核心 A：公告从"report fetch 隐式触发→关键词黑名单→下载即入库"改为"显式 list→LLM 标题分诊→按选 download"，根除 67 份治理噪音灌进抽取队列。

**Branch:** **不开新分支**，直接在当前分支 `docs/wf00-fixes` 上改。

**Tech Stack:** Python 3（`./.venv/bin/python`）+ Markdown。

## Global Constraints

- **脚本改动走 gitnexus**：编辑 `fetch_report_prism.py` / `gap_detector.py` 任一函数前 `impact({target, direction:"upstream"})`，HIGH/CRITICAL 先报告再改。全部改完 `detect_changes({scope:"compare", base_ref:"main"})`。
- **Edit verbatim**：先 Read 再 Edit，唯一串匹配。
- **测试**：A/F 改完跑 `./.venv/bin/python -m pytest scripts/test_fetch_report_prism.py prism/scripts/test_gap_detector.py -q`。
- **不改语义边界**：A 改的是"抓哪些公告"（行为改进），不动 auto-fetch 三态 / empty 硬闸门 / todo 闭环 / thesis-decomposition-baseline 三轴语义。

---

## 根因（cn-adc 实测，已验证）

cn-adc manifest 148 份料里 **67 份 `source_type=quarterly-report` 实为公告**（文件名多 `_announce_kzz_`）。三因叠加：
1. **隐式触发**：`fetch()`（line 945）与 `fetch_many()`（line 1075）默认 `with_announcements=True`；每次抓年报/季报，CN 分支（line 1057-1063 / 1092-1096）自动调 `fetch_announcements_cn` 拉近 1 年公告。
2. **`kzz`(可转债) 类目对可转债发行人 = 全量公告消防栓**——返回该公司全部公告（临床/回购/董事会/辞职/议事规则…），类别白名单形同虚设。
3. **`_TITLE_NOISE_RE` 故意高精度窄覆盖** + **标签 bug**：`_register_in_prism`（line 289-293）无 `announcement` 分支，`report_type="announcement"`（line 677）塌缩成 `quarterly-report`，撞 03 §2.2 "目标 15-20 条" 预期。

---

## Task A：公告 list→LLM 分诊→download（核心 · 脚本 4 处 + 文档 3 处）

### A1 — `fetch_report_prism.py`：拆冗余预剪正则 + 给 `_list_reports` 加 `noise_re` 参数

- [ ] `impact({target:"_list_reports", direction:"upstream"})`，报告调用方。
- [ ] **Edit 1**（在 `_TITLE_NOISE_RE` 定义块后新增 `_DUP_NOISE_RE`）：

old_string:
```python
    r"限制性股票|股票激励计划|激励对象|持续督导|内部控制|公司章程|H股公告|月报表"
)

_ANNOUNCEMENT_WINDOW_DAYS = 365
```
new_string:
```python
    r"限制性股票|股票激励计划|激励对象|持续督导|内部控制|公司章程|H股公告|月报表"
)

# 仅"纯冗余重复件"——同一公告的摘要/英文/更正/修订版。list_announcements_cn 用它做最小
# 预剪（LLM 看了也是丢），治理/程序性件全部保留交 LLM 标题分诊判断（不再用关键词杀治理件）。
_DUP_NOISE_RE = r"摘要|英文版|英文|更正|修订"

_ANNOUNCEMENT_WINDOW_DAYS = 365
```

- [ ] **Edit 2**（`_list_reports` 加参数 + 用之）：

old_string:
```python
def _list_reports(code: str, org_id: str, column: str, category: str) -> list[dict]:
    data = (
        f"stock={code}%2C{org_id}&category={category}"
        f"&pageNum=1&pageSize=50&tabName=fulltext&column={column}"
    )
    def _do():
        r = requests.post(_CNINFO_QUERY, headers=_HEADERS, data=data, timeout=15)
        r.raise_for_status()
        return r.json().get("announcements") or []
    announcements = _with_retry(_do, label=f"cninfo list {code}")
    # 丢摘要/英文/更正/修订 + 治理·中介程序性噪声（_TITLE_NOISE_RE）；未命中一律留，
    # 保住临床/BD/业绩预告/季报等催化剂（修 F7）。年报本体标题不含黑名单词，无误伤。
    return [
        a for a in announcements
        if not re.search(_TITLE_NOISE_RE, a.get("announcementTitle", ""))
    ]
```
new_string:
```python
def _list_reports(code: str, org_id: str, column: str, category: str,
                  noise_re: str = _TITLE_NOISE_RE) -> list[dict]:
    data = (
        f"stock={code}%2C{org_id}&category={category}"
        f"&pageNum=1&pageSize=50&tabName=fulltext&column={column}"
    )
    def _do():
        r = requests.post(_CNINFO_QUERY, headers=_HEADERS, data=data, timeout=15)
        r.raise_for_status()
        return r.json().get("announcements") or []
    announcements = _with_retry(_do, label=f"cninfo list {code}")
    # 默认丢治理·中介程序性噪声（_TITLE_NOISE_RE，报告抓取路径用，年报本体不含黑名单词无误伤）；
    # list_announcements_cn 传 _DUP_NOISE_RE 只丢纯冗余件，把治理件留给 LLM 标题分诊。未命中一律留。
    return [
        a for a in announcements
        if not re.search(noise_re, a.get("announcementTitle", ""))
    ]
```

### A2 — 修 `_register_in_prism` 标签 bug：加 `announcement` source_type

- [ ] `impact({target:"_register_in_prism", direction:"upstream"})`。
- [ ] **Edit 3**：

old_string:
```python
    source_type = (
        "prospectus" if report_type == "prospectus"
        else "annual-report" if report_type == "annual"
        else "quarterly-report"
    )
```
new_string:
```python
    source_type = (
        "prospectus" if report_type == "prospectus"
        else "annual-report" if report_type == "annual"
        else "announcement" if report_type == "announcement"
        else "quarterly-report"
    )
```
> `default_report_rings("announcement", topic_type)` 已有合理回退（company→`["financial-arc"]`，arena→`["peer-comparison-financials"]`，见 `prism/scripts/input_contract.py:238`），不改。

### A3 — 新增 `list_announcements_cn`（list-only）+ `download_announcements_cn`（按选下载）

- [ ] `impact({target:"fetch_announcements_cn", direction:"upstream"})`（新函数紧邻它放）。
- [ ] **Edit 4**：在 `fetch_announcements_cn` 定义**之前**（即 `_download_announcement` 函数结束、`def fetch_announcements_cn(` 之前）插入两个新函数。

old_string:
```python
def fetch_announcements_cn(
    market_ticker: str,
    slug: str | None = None,
```
new_string:
```python
def list_announcements_cn(
    market_ticker: str,
    days: int = _ANNOUNCEMENT_WINDOW_DAYS,
) -> list[dict]:
    """List recent A-share announcements (titles only — NO download, NO manifest register).

    供 workflow "列表→LLM 标题分诊→按选下载" 用：主 agent 读返回的标题清单，按 thesis/K#
    判定哪些值得拉，再调 download_announcements_cn(selected=...)。判断留在对话里（prism
    原则：Python 只做 CRUD/IO，不做投研判断）。

    只做最小预剪（_DUP_NOISE_RE：摘要/英文/更正/修订纯冗余件）；治理/程序性件全部保留交 LLM。
    跨类目按 adjunctUrl 去重（同一公告常同时落 kzz 全量流 + yjygjxz）。date 倒序返回。
    每项: {announcement_id, title, date, category_key, adjunct_url, announcement_time,
           org_id, code, column, company_name, ticker}
    """
    from datetime import datetime, timezone
    _, ticker = _parse_market_ticker(market_ticker)
    info = _company_info(ticker)
    code, org_id = info["code"], info["orgId"]
    company_name = info.get("zwjc", ticker)
    column = _column(code)

    seen: set[str] = set()
    out: list[dict] = []
    for key, category in _ANNOUNCEMENT_CATEGORIES.items():
        try:
            anns = _list_reports(code, org_id, column, category, noise_re=_DUP_NOISE_RE)
        except Exception as e:
            log.warning("Announcement category %s list failed: %s", key, e)
            continue
        for a in anns:
            if not _within_window(a, days):
                continue
            url = a.get("adjunctUrl") or ""
            if not url or url in seen:
                continue
            seen.add(url)
            ts = a.get("announcementTime")
            dt = (datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                  if ts else "")
            out.append({
                "announcement_id": a.get("announcementId"),
                "title": a.get("announcementTitle", ""),
                "date": dt,
                "category_key": key,
                "adjunct_url": url,
                "announcement_time": ts,
                "org_id": org_id,
                "code": code,
                "column": column,
                "company_name": company_name,
                "ticker": ticker,
            })
    out.sort(key=lambda x: x.get("announcement_time") or 0, reverse=True)
    return out


def download_announcements_cn(
    market_ticker: str,
    slug: str,
    variant: str | None,
    selected: list[dict],
) -> list[Path]:
    """Download + register the LLM-selected subset from list_announcements_cn.

    selected = list_announcements_cn 返回项的子集（需含 adjunct_url/announcement_time/
    title/category_key/ticker/company_name）。每条 download + _register_in_prism(
    report_type="announcement") → source_type='announcement'。fetch_status 由主 agent 按
    todo 文档身份盖（见 _autofetch_protocol.md），本函数不碰 todo 闭环。
    """
    dest_dir = _materials_dir(slug) if slug else _INBOX_AUTO
    dest_dir.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for sel in selected:
        ann = {
            "adjunctUrl": sel["adjunct_url"],
            "announcementTime": sel.get("announcement_time"),
            "announcementTitle": sel.get("title", ""),
        }
        try:
            p = _download_announcement(
                ann, dest_dir,
                sel.get("company_name", ""), sel.get("ticker", ""),
                sel.get("category_key", "sel"),
            )
            saved.append(p)
            if slug:
                _register_in_prism(slug, p, "announcement", sel.get("company_name", ""), variant)
        except Exception as e:
            log.warning("Announcement download failed (%s): %s", sel.get("title", "?")[:30], e)
    return saved


def fetch_announcements_cn(
    market_ticker: str,
    slug: str | None = None,
```

### A4 — 翻 `fetch()` 与 `fetch_many()` 的 `with_announcements` 默认为 False

- [ ] `impact({target:"fetch", direction:"upstream"})` + `impact({target:"fetch_many", direction:"upstream"})`。检查有无调用方依赖"自动带公告"（预期无——公告改走显式 list+download）。HIGH/CRITICAL 先报告。
- [ ] **Edit 5**（`fetch`，return type `-> Path:` 唯一区分于 fetch_many）：

old_string:
```python
    quarter: int | None = None,
    with_announcements: bool = True,
) -> Path:
    """Download a financial report. Returns the local file path.
```
new_string:
```python
    quarter: int | None = None,
    with_announcements: bool = False,   # 公告改走显式 list_announcements_cn→LLM分诊→download_announcements_cn；
                                        # report fetch 不再隐式拉全年公告（根除治理噪音灌入抽取队列）
) -> Path:
    """Download a financial report. Returns the local file path.
```

- [ ] **Edit 6**（`fetch_many`，return type `-> list[Path]:`）：

old_string:
```python
    quarter: int | None = None,
    with_announcements: bool = True,
) -> list[Path]:
```
new_string:
```python
    quarter: int | None = None,
    with_announcements: bool = False,   # 同 fetch：公告改走显式 list→分诊→download
) -> list[Path]:
```
> 不删 `fetch()`/`fetch_many()` 里的 CN/US 公告分支与 `fetch_announcements_cn`——保留为显式 `with_announcements=True` 的逃生口（向后兼容）；只是默认不再触发。

### A5 — 测试（`scripts/test_fetch_report_prism.py`）

- [ ] 先 Read `scripts/test_fetch_report_prism.py` 头部，沿用其现有 monkeypatch 风格（按既有 fixture 命名）。新增：
  - `test_list_announcements_dedup_and_prefilter`：monkeypatch `_company_info`（返回 `{"code":"688506","orgId":"x","zwjc":"百利天恒"}`）+ `_list_reports`（按 category 返回含重复 adjunctUrl、含"业绩快报"催化件、含"董事会议事规则"治理件、含"…摘要"冗余件的假数据）。断言：① 返回按 url 去重；② "议事规则"治理件**保留**（在结果里）；③ "摘要"冗余件**被剪**（不在结果里，因 `noise_re=_DUP_NOISE_RE`）；④ 每项含 `title/date/category_key/adjunct_url`。
  - `test_download_announcements_selected_only`：monkeypatch `_download_announcement`（返回假 Path）+ `_register_in_prism`（记录 report_type 入 list）。传 2 条 selected，断言只下载这 2 条、且 `_register_in_prism` 收到的 `report_type == "announcement"`。
  - `test_register_announcement_source_type`：monkeypatch `prism.scripts.manifest.add_material`（捕获 `source_type`）+ `read_manifest`/`create_manifest`/`list_variants`/`read_topic`。调 `_register_in_prism(slug, Path("x_announce_kzz_y.PDF"), "announcement", "co", "opus4.8")`，断言捕获的 `source_type == "announcement"`（回归 mislabel bug）。
- [ ] `./.venv/bin/python -m pytest scripts/test_fetch_report_prism.py -q` 全绿。

### A6 — workflow 文档：插入 list→分诊→download 三步法 + 03 公告抽取强度

- [ ] **00-research-topic.md**：在 6.5a（line 541-568）代码块**之后**、`### 6.5b：分析材料` **之前**插入新子节。

old_string:
```python
update_user_todo_status(slug, variant, '茅五泸三家 2025 年报', 'done', covered_by=covered_ids)
```

### 6.5b：分析材料（卖方研报/行业数据/政策/科普）→ exa→semantic→WebFetch 阶梯
```
new_string:
```python
update_user_todo_status(slug, variant, '茅五泸三家 2025 年报', 'done', covered_by=covered_ids)
```

### 6.5a-ann：A 股临时公告 → list → LLM 标题分诊 → 按选下载（**不要一把梭全拉**）

> `fetch()` 默认 `with_announcements=False`，**不再隐式拉全年公告**（旧默认会把可转债发行人的
> `kzz` 全量公告流——临床/回购/董事会/辞职/议事规则——全灌进抽取队列）。公告改走显式三步，
> 由 LLM 看标题决定拉哪些（关键词黑名单杀不准催化剂、也漏不掉治理噪音）。**本段用 `./.venv/bin/python`。**

```python
from scripts.fetch_report_prism import list_announcements_cn, download_announcements_cn

# 1) 列表（只拿标题，不下载）——对每个目标 ticker
anns = list_announcements_cn('SSE_688506', days=180)
for i, a in enumerate(anns):
    print(i, a['date'], a['category_key'], a['title'])
```

2) **主 agent 读标题清单，按 thesis/K# 判定 selected**（判断留对话里，不写进脚本）：
   - **拉**：临床读出/适应症获批/BLA·NDA 受理/BD·License/重大合作/业绩预告·快报/与命门直接相关的自愿披露；
   - **丢**：议事规则/信息披露·薪酬管理制度/辞职·换届/股东会通知·会议资料/利润分配·权益分派/回购进展/募投变更/独董提名等程序治理件。
   - 清单 >50 条时按日期窗口 + 标题**批量**判定，不逐条纠结。

```python
# 3) 只下载选中的（download + register，source_type='announcement'）
selected = [anns[i] for i in (0, 3, 7)]   # ← 主 agent 判定的下标
got = download_announcements_cn('SSE_688506', slug, variant, selected)
# 盖 fetch_status / 闭环 todo 照 _autofetch_protocol.md（按 task 子串/文档身份，不用 K# 求交）
```

### 6.5b：分析材料（卖方研报/行业数据/政策/科普）→ exa→semantic→WebFetch 阶梯
```

- [ ] **01-build-roadmap.md**：在多年批量块（line 316-320 的"注意"列表）后补一行指针。

old_string:
```
- 半年报 `semi-annual-report` 同理走 `category_bndbg_szsh`
```
new_string:
```
- 半年报 `semi-annual-report` 同理走 `category_bndbg_szsh`
- **A 股临时公告**：`fetch()`/`fetch_many()` 默认不再带公告（`with_announcements=False`）。公告走显式 `list_announcements_cn`→主 agent 标题分诊→`download_announcements_cn`，见 `00-research-topic.md` §6.5a-ann（关键词过滤杀不准，改 LLM 看标题）
```

- [ ] **03-extract-findings.md**：§2.2 §A 给 announcement 类降抽取强度。

old_string:
```
- 目标 15-20 条；超过需说明原因
```
new_string:
```
- 目标 15-20 条；超过需说明原因
- **例外（按 source_type 分流强度）**：`annual-report`/`sell-side-note`/`industry-research` 才按上面深度抽取；`source_type=announcement` 是 1-2 页催化件，**按事件抽 1-3 条 finding 即可**，不强求数据点数（残留少量漏网公告也不会被"15-20 条"误导去硬榨 1 页公告）
```

- [ ] **验证 A6**：`grep -n "6.5a-ann\|list_announcements_cn\|download_announcements_cn" prism/workflows/00-research-topic.md prism/workflows/01-build-roadmap.md` 命中；`grep -n "source_type=announcement" prism/workflows/03-extract-findings.md` 命中。

---

## Task B：venv/python 命令在文档里统一（纯文档）

- [ ] **Edit B1** — `03-extract-findings.md:254`：

old_string:
```
  || python3 -m scripts.annual_report_extractor \
```
new_string:
```
  || ./.venv/bin/python -m scripts.annual_report_extractor \
```

- [ ] **Edit B2** — `01-build-roadmap.md:246`：

old_string:
```
# 或 CLI: python3 -m scripts.fetch_report_prism SSE_688499 --years 2020-2024 --slug ...
```
new_string:
```
# 或 CLI: ./.venv/bin/python -m scripts.fetch_report_prism SSE_688499 --years 2020-2024 --slug ...
```

- [ ] **Edit B3** — `_subagent_fetch_material.md:37`：

old_string:
```
python3 -m scripts.fetch_report_prism SZSE_300073 --year 2024 --slug {slug}
```
new_string:
```
./.venv/bin/python -m scripts.fetch_report_prism SZSE_300073 --year 2024 --slug {slug}
```

- [ ] **Edit B4** — `_autofetch_protocol.md` 顶部加硬约定 callout。在第 6 行（`> **一句话**：…`）后插入：

old_string:
```
> **一句话**：每个产 todo 的点，浮给用户前必须先**有效尝试**一次自动抓；留不留 user-todo、是否要重试，由**尝试的真实结果**决定，不由 tier/info_tier 标签事前 gate。
```
new_string:
```
> **一句话**：每个产 todo 的点，浮给用户前必须先**有效尝试**一次自动抓；留不留 user-todo、是否要重试，由**尝试的真实结果**决定，不由 tier/info_tier 标签事前 gate。
>
> ⚠️ **venv 硬约定**：凡命令 import 第三方包——`fetch_report_prism`/`annual_report_extractor`/`financial_data`/`market_data`/`mineru_api`（依赖 requests/pymupdf/akshare/yfinance）——一律用 `./.venv/bin/python`（含 `python3 -c "…"` 里 import 这些模块的块）。裸 `python3` 仅用于纯 CRUD（`prism.scripts.topic`/`manifest`/`outputs`/`findings`/`gap_detector`）。裸跑 fetcher/extractor 会 `ModuleNotFoundError: No module named 'requests'/'pymupdf'/'akshare'`。
```

- [ ] **验证 B**：`grep -rn "python3 -m scripts.\(annual_report_extractor\|fetch_report_prism\)" prism/workflows/` 应 0 命中（除非 .venv 前缀）。

---

## Task C：deep-fetch web-search 只存 snippet 的兜底（纯文档）

- [ ] Read `01-build-roadmap.md` Step 5.6（line 322 起）找阶梯3（`mcp__exa__web_fetch_exa` 抓全文）那段，在其后补一条校验规则。先 `grep -n "web_fetch_exa\|阶梯3\|阶梯 3\|抓全文" prism/workflows/01-build-roadmap.md` 定位锚点，再 Edit 插入：

插入内容（new_string 末尾追加，old_string 用阶梯3 段落现有结尾句 verbatim）：
```
> **snippet 兜底（修 cn-adc C）**：`sell-side-note`/`industry-research` 类落盘后若正文 < ~1500 字（疑似仅 title+snippet），**必须**对其权威 URL 再跑一次 `mcp__exa__web_fetch_exa`（`maxCharacters:5000`）抓正文；仍抓不到全文则 `add_material` 时显式标 `quality` 降级 + `notes='snippet-only, full text not fetched'`，**不得让 snippet 冒充深度材料进 03**（cn-adc 实测：浦银目标价等只存了标题行，定价锚踩在 snippet 上、时点不明）。
```
> ⚠️ 由于阶梯3 锚点未在本计划 verbatim 固定，执行者**先 Read 该段**取唯一结尾句作 old_string，再把上面这条作为追加。若 Step 5.6 已有等价表述则跳过（记录"已覆盖"）。

- [ ] **验证 C**：`grep -n "snippet-only\|snippet 兜底" prism/workflows/01-build-roadmap.md` 命中。

---

## Task D：修 `set_decomposition` 误导性 prose 简写（纯文档）

> 背景：完整代码块（`_shared.md:122-129`、`00:470-477`）**已正确**含 `summary`/`stage_set_at` 且注释列了枚举。坑在**散落的 prose 简写** `set_decomposition(version=1, convergence_status, changelog)`——漏 `summary`/`stage_set_at`（二者**无默认值、必填**，漏传 TypeError），且枚举仅 `open|converged|capped`（用 `converging` 会 ValueError）。把每处简写补全。

- [ ] **Edit D1** — `_shared.md:104`：

old_string:
```
直接 `set_decomposition(version=1, convergence_status='converged', changelog='厚料确认 v0 命门 + 入门目标，无变化')` 后正常写作。
```
new_string:
```
直接 `set_decomposition(version=1, summary=..., stage_set_at='04-synthesizing', convergence_status='converged', changelog='厚料确认 v0 命门 + 入门目标，无变化')` 后正常写作（`summary`/`stage_set_at` 必填；`convergence_status ∈ {open, converged, capped}`，无 'converging'）。
```

- [ ] **Edit D2** — `_arena_funnel.md:234`：

old_string:
```
**同时写 `decomposition_v1.md` + `set_decomposition(version=1, convergence_status, changelog)`**（见 `_shared.md` §B 轴有界 delta 重拆）。
```
new_string:
```
**同时写 `decomposition_v1.md` + `set_decomposition(version=1, summary, stage_set_at, convergence_status, changelog)`**（`summary`/`stage_set_at` 必填；`convergence_status ∈ {open, converged, capped}`；完整示例见 `_shared.md` §B 轴有界 delta 重拆）。
```

- [ ] **Edit D3** — `_industry_funnel.md:241` 与 **Edit D4** — `_company_case.md:309`：两处都含 verbatim 串 `set_decomposition(version=1, convergence_status, changelog)`，各自 Read 后用与 D2 相同的替换（把 `convergence_status, changelog)` 段补成 `summary, stage_set_at, convergence_status, changelog)` + 同款括注）。因两文件该串上下文不同，分别 Edit。

- [ ] **验证 D**：`grep -rn "set_decomposition(version=1, convergence_status, changelog)" prism/workflows/` 应 0 命中。

---

## Task E：peer_matrix score 量纲移进 arena_funnel（纯文档）

- [ ] **Edit E1** — `_arena_funnel.md:208`（schema 行）：

old_string:
```
companies[{name, ticker, score, tier(shortlist/watch/eliminated), topic_created, topic_slug, thesis_one_liner, upgrade_triggers, quarantine}] / cluster_tags`）。数字不加引号，缺失 null。
```
new_string:
```
companies[{name, ticker, score, tier(shortlist/watch/eliminated), topic_created, topic_slug, thesis_one_liner, upgrade_triggers, quarantine}] / cluster_tags`）。**`score` 用 1-5 制**（详见 `_peer_matrix_spec.md`；勿用 1-100），与 case ④综合评级同向。数字不加引号，缺失 null。
```

- [ ] **验证 E**：`grep -n "1-5 制" prism/workflows/04-synthesize/_arena_funnel.md` 命中。

---

## Task F：gap_detector 豁免 prescan 材料的 K# 假缺口（脚本）

> `prescan_untagged`（`gap_detector.py:300-309`）把"有 addresses 但无 K#"的料点名待补。Role α prescan 料（`search_meta.triggered_by ∈ {00-prescan-baseline,00-prescan,01-prescan}`）合法地只挂 `scope` 占位、且豁免抽取，却被永久点名（cn-adc 实测噪音）。复用 manifest 既有常量 `_DEFAULT_EXCLUDED_TRIGGERED_BY` 跳过它们。

- [ ] `impact({target:"detect_gaps", direction:"upstream"})`（或 `prescan_untagged` 所在的导出函数名，先 `grep -n "def " prism/scripts/gap_detector.py` 确认）。
- [ ] **Edit F1** — 导入常量。`gap_detector.py:16`：

old_string:
```
from prism.scripts.manifest import list_expired_web_search, read_manifest
```
new_string:
```
from prism.scripts.manifest import (
    _DEFAULT_EXCLUDED_TRIGGERED_BY,
    list_expired_web_search,
    read_manifest,
)
```

- [ ] **Edit F2** — 跳过 prescan 料。`gap_detector.py:300-309`：

old_string:
```python
    prescan_untagged: list[dict] = []
    if cur_v is not None:
        for m in manifest.get("materials") or []:
            addrs = m.get("addresses") or []
            if addrs and not any(_is_knum(a) for a in addrs):
                prescan_untagged.append({
                    "id": m.get("id"),
                    "filename": m.get("filename"),
                    "addresses": list(addrs),
                })
```
new_string:
```python
    prescan_untagged: list[dict] = []
    if cur_v is not None:
        for m in manifest.get("materials") or []:
            # Role α prescan 料（00/01 prescan 入库）合法只挂 scope 占位且豁免抽取——
            # 不点名待补 K#（否则每轮报永久假缺口，cn-adc 实测噪音）。
            tb = (m.get("search_meta") or {}).get("triggered_by", "unknown")
            if tb in _DEFAULT_EXCLUDED_TRIGGERED_BY:
                continue
            addrs = m.get("addresses") or []
            if addrs and not any(_is_knum(a) for a in addrs):
                prescan_untagged.append({
                    "id": m.get("id"),
                    "filename": m.get("filename"),
                    "addresses": list(addrs),
                })
```

- [ ] **测试 F** — `prism/scripts/test_gap_detector.py` 加用例：两份 `addresses=['scope']` 料，一份 `search_meta.triggered_by='00-prescan'`、一份 `='03-extract'`，thesis 已就位。断言 `prescan_untagged` 只含后者（prescan 料被豁免）。沿用该测试文件现有 fixture 构造 manifest/topic。
- [ ] `./.venv/bin/python -m pytest prism/scripts/test_gap_detector.py -q` 全绿。

---

## 收尾验证（全部任务后）

- [ ] `./.venv/bin/python -m pytest scripts/test_fetch_report_prism.py prism/scripts/test_gap_detector.py -q` 全绿。
- [ ] `detect_changes({scope:"compare", base_ref:"main"})` 确认改动只触及 `fetch_report_prism`（_list_reports/_register_in_prism/fetch/fetch_many/新增2函数）+ `gap_detector`（detect 函数）预期符号，无意外牵连。
- [ ] 各 `grep` 验证（见每任务末尾）全部命中/清零。
- [ ] **联网干跑**（可选，需网络）：`./.venv/bin/python -c "from scripts.fetch_report_prism import list_announcements_cn as L; a=L('SSE_688506', days=120); print(len(a)); [print(x['date'],x['category_key'],x['title'][:40]) for x in a[:15]]"` —— 人工核对：返回标题清单、治理件保留待 LLM 判、纯冗余件（摘要/英文）已预剪。

## Out of Scope

- 不重写 auto-fetch 三态 / empty 硬闸门 / todo 闭环语义。
- 不动 thesis/decomposition/baseline 三轴语义。
- 不为公告做脚本侧关键词白名单（本计划核心正是用 LLM 标题分诊取代关键词过滤）。
- 不改 `register_web_search_batch`（Task C 仅文档，已确认）。
- 不删 `fetch_announcements_cn` / 公告分支（保留为显式 opt-in 逃生口）。
