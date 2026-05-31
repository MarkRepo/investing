# Prism 全链路验证 — cn-innovative-drug / opus4.8（从零）

运行日期：2026-05-30
目的：dogfood 全链路（00→05），记录流程设计缺陷 + 事实漂移 + 死内容 + 可优化项。

---

## 发现的问题（按严重度）

### 🔴 F1 — create_topic 仍 stamp 旧 8 维 outputs_state（code · 迁移残留）
- **现象**：新建 industry 变体 `opus4.8`，`outputs_state` keys = `01_business_panorama … 08_living_feed + 09_industry_to_arenas`（旧并列维度 schema）。
- **应为**：决策链流程 industry 实际产 `00_primer` + `i_industry_case` + `09_industry_to_arenas` sidecar。
- **影响**：8 个死 slot 永远 pending；04 真正写的产出（00_primer/i_industry_case）无 state slot（除非 set_output_status 时动态建）。dashboard/收敛判定可能被死 slot 干扰。
- **定位**：`prism/scripts/topic.py` create_topic 的默认 `outputs_state`（按 type 的 OUTPUT_KEYS 未随迁移更新）。
- **定位精确**：`topic.py:14 _BASE_OUTPUT_KEYS` + `_outputs_for_type`(L84-90) 返回旧 8 维；而 L1255 已有新 map（`industry→i_industry_case`）供合成路径用 → 两套 key 源不同步，create_topic(L302) 用了旧的。
- **状态**：待用户决定是否修。

### 🔴 F2 — Step 5.0a backfill 在 'scope' 约定下是死步骤（doc↔code 漂移）
- **现象**：80 份 prescan 材料 addresses 全是 `scope`（4.5a register 示例 + adapter `--addresses scope` 默认）。`backfill_addresses_by_mapping({fact-NN:[K#]})` → `updated_count=0`（无 fact-NN 可重映）。
- **doc 前提错**：Step 5.0a 称"prescan 材料 addresses 标的是 fact-NN，写完 thesis 必须立即 fact→K# 映射，否则 gap_detector 误报 K# 全 0"。但 4.5a 实际用 scope，backfill 永远空转；且 scope 本就不计入 K# 覆盖（三态表 scope=✗），不会"误报"。
- **影响**：5.0a "必须" 步骤实为 no-op；新手照做会困惑。K# 覆盖实际来自 02/03 真材料，与此步无关。
- **修法二选一**：(a) 4.5a 把 prescan 命中按 fact-NN 标 addresses（则 backfill 有意义）；(b) 删/降级 5.0a 为"仅当 prescan 用 fact-NN 标注时适用"。
- **状态**：待用户定夺。

### 🟡 F3 — build_search_queries 产出关键词汤 + 套用不适配后缀
- **现象**：industry 模板 query = `中国创新药 ADC 出海 BD 创新药 国谈 医保 双抗 GLP-1 自免`（"创新药"重复、9 个离散词堆叠）；industry-event 套 `行业政策/技术突破/产能变化/龙头新闻` 四后缀，其中 **"产能变化"对创新药无意义**（电池/芯片模板词）。
- **影响**：4.5b 模板 query 质量远低于手写 baseline §五 优先 query；对写得好的 baseline，4.5b 边际价值低、且需主 agent 手动改写才可用。
- **可优化**：按 topic.type 分模板（pharma 不该有"产能变化"）；或对长 search_terms 拼接做去重 + 限长；或当 baseline §五 足够时允许跳过 4.5b。

### 🟡 F4 — 白名单对中国医药权威源覆盖差，H2 救回近乎每条必做（复发税）
- **现象**：本轮 ~55 命中里仅 ~4 个在 WHITELIST；其余全是权威源却默认 0.4 将被丢弃——公司 IR（hengrui/akesobio/kelun-biotech）、政府（nhsa.gov.cn / ybj.*.gov.cn）、交易所（hkexnews.hk）、头部财媒（news.cn/caixin/yicai/thepaper/stcn/sina finance/cnstock/eeo/21jingji）、医药数据（pharmcube/zhihuiya/pharnexcloud）、券商 PDF（pdf.dfcfw.com / eastmoney）。
- **影响**：CN-pharma 主题 H2 手动救回从"偶发"变"每条必做"，是稳定的人力税；与 memory `feedback_prescan_domain_tier` 同源但更严重（覆盖率而非个例）。
- **可优化**：把确定性权威 host 批量补进 WHITELIST：`*.gov.cn`（医保/药监）、`hkexnews.hk`、`pdf.dfcfw.com`/`*.eastmoney.com`（券商研报 CDN）、`news.cn`/`thepaper.cn`/`caixin.com`/`yicai.com`/`stcn.com`/`cnstock.com`、`pharmcube.com`/`bydrug.pharmcube.com`/`zhihuiya.com`/`pharnexcloud.com`、主流公司 IR 根域。

### 🟢 F5 — prescan 读 raw 判 tier 缺紧凑视图，主 agent 上下文易被巨型 snippet 淹没
- **现象**：adapter 写的 raw json 含超长 snippet（券商 PDF 单条 ~3000 token）。Step C 要主 agent"读 raw 判 tier"，直接 Read 多个 raw 会爆上下文。本轮靠自写紧凑打印器（host+WL+title+snippet[:110]）规避。
- **可优化**：adapter/web_prescan 提供 `--review-digest` 子命令，输出每命中 host/whitelist/features/title/snippet 头，供主 agent 低成本判 tier（非 WL 才需看）。

### 🔴 F7 — A股 cninfo `fetch(report_type='annual')` 过度抓取，灌爆 manifest
- **现象**：对 3 个 A 股 ticker（恒瑞 600276/荣昌 688331/百利天恒 688506）各调一次 `fetch(report_type='annual')`，结果共下载 **99 份临时公告 PDF**（manifest 87→186），全部登记为 `source_type=quarterly-report`、`addresses=None`、`added_at=None`。
- **噪声占绝大多数**：公司章程、董事/高管薪酬管理制度、独立董事述职报告、限制性股票激励归属公告、律所意见书、H股公告月报表、董事会决议……真正有价值的（2026Q1 季报、业绩快报/预告、恒瑞-BMS 许可协议公告、百利天恒 iza-bren 临床公告）被淹没。
- **对比**：HK HKEXnews fetch（信达/百济/康方/科伦博泰）干净——每 ticker 恰好 1 份年报。问题只在 A 股 cninfo 路径。
- **下游伤害**：① 03-extract `list_unprocessed` 会拿到 99 份噪声 PDF 试图抽 findings（巨大浪费）；② addresses=None 绕过了 manifest 别处的 addresses 三态强制；③ added_at=None 时效字段缺失。
- **定位方向**：`scripts/fetch_report_prism.py` A 股/cninfo 分支——`annual` 似乎拉了整个 `category_kzz`(临时公告) 流而非仅年报。应：annual 只取年报本体（+ 可选最新季报），不扫临时公告全集；若要支持公告监控应是独立 report_type 且默认关。
- **状态**：本轮为继续推进，03 只抽 7 份年报 + 少数高价值公告，**不抽 99 份治理噪声**（正是 F7 造成的浪费实证）。

### 🔴 F9 — auto_resolve_todos 用裸 K# 假性闭环，灌绿 hard/half_public 收料 todo
- **现象**：01-prescan 24 份 K# web 材料经 `register_web_search_batch` 内部 auto_resolve，把**全部 9 条 user_todos 标 done**——包括 info_tier=**hard** 的"五大赛道竞争格局+在研管线密度"和"历史行业镜鉴(industry-mirror)"，以及 half_public 的"下载头部药企年报"。
- **根因**：`addresses_match` 的"裸 K 接受任意 K*"向后兼容路径——任一 K5 web 命中同时闭环所有挂 K5 的 todo（赛道格局 / 历史镜鉴 / 港股估值用了同一批 mat-24d5b8…），K1 临床读出命中闭环了"BIOSECURE/地缘"todo。命中内容与 todo 真实诉求无关。
- **in-code guard 形同虚设**：只跳过 `source_hint` 含 "reverse-check" 的 todo；正常结构化 todo 全被扫。
- **影响**：用户的"待办深度收料清单"（专家访谈/镜鉴复盘/地缘分析这些 hard 料）被背景 web 预扫一键清空 → 用户以为没事可做，实则真·hard 料从未收集。**与我刚修的 gap_detector A 轴 hard 假绿同源**，只是发生在 todo 层。
- **跨层矛盾佐证**：ring 轴仍报 `industry-mirror` uncovered 🔴，而对应 todo 已 done——两层结论打架，证明 todo 层在说谎。
- **修法**：auto_resolve 对 info_tier∈{hard, half_public} 的 todo 要么不自动闭环、要么要求事件锚/同 source_type 匹配；裸 K# web 命中只能标 in_progress 或 partial，不能 done。
- **状态**：待用户定夺（与 F1 thin 阈值是同一类"单弱料假装满足"问题，建议合并修）。

### 🔴 F10 — 报告 ring 自动打标 type-blind，industry 主题 A 轴整体失灵
- **现象**：7 份年报被打 rings `['biz-moat-unit-econ','financial-arc','mgmt-capital-alloc']`——这是 **company 型 ring code**；但本 topic 是 **industry**，合同码是 `value-chain-profit-pool / industry-financial-arc / leader-valuation-anchor / migration-path-evidence / arena-scoring-inputs / industry-mirror`。
- **后果**：年报 rings 与 industry 轴**零交集** → `ring_coverage` 全 0，即便已有 7 份年报；A 轴对 industry 主题完全失灵（gap 永远报全 uncovered，thin 桶也永不触发，因为是 0 不是 1）。
- **定位**：`fetch_report_prism` / `add_material` 给 report 默认 rings 用了固定 company 集，未读 topic.type。应按 type 映射（industry 年报→`industry-financial-arc`+`value-chain-profit-pool`）。
- **缓解**：02 doc 说"03 抽取时按实际内容在 finding frontmatter 补 rings"——可在 finding 层手补 industry rings 兜底，但材料层默认标错仍误导 gap 直到 findings 落地。
- **关联**：因 F10，本轮无法自然触发我新加的 `thin_ring_inputs` 黄桶（industry 轴 hard 项 industry-mirror 一直是 0）；thin 逻辑单测已证，但 industry auto-fetch 路径喂不出"恰好 1 份"。

### 🟡 F7b — 03 队列被 99 份治理噪声污染（F7 的下游实证）
- `list_unprocessed` 返回 106 = 7 年报 + 99 quarterly-report（公司章程/独董述职/股权激励/律所意见…）。逐份抽 findings 是巨大浪费；本轮只抽年报 + 高价值公告，治理噪声跳过。

### 🔴 F12 — 03/02 文档输出路径用了不存在的 variant-scoped materials/，extractor 直接崩
- **现象**：`annual_report_extractor --out prism/topics/{slug}/{variant}/materials/..._extracted.md` → `FileNotFoundError`，因为 materials 在 **slug 级** `prism/topics/{slug}/materials/`，没有 `{slug}/{variant}/materials/` 这个目录。
- **波及**：03 Step 2.1 年报 extractor 路径、03/02 的 mineru `{stem}_vlm` 输出路径都写成 `{slug}/{variant}/materials/` → 真操作者第一份年报就崩（除非历史遗留建过该目录）。
- **修法**：文档统一改 slug 级 `{slug}/materials/`，或在写前 `mkdir -p`，或 extractor 自己建父目录。
- **状态**：本轮 re-run 时写到 slug 级正确路径绕过。

### 🔴 F13 — get_financial_context / get_peer_comparison_data 对 industry 主题无源（no ticker）
- **现象**：`get_financial_context('cn-innovative-drug','opus4.8')` → `*(财务数据不可用: no ticker)*`。函数 key 在 `scope.ticker`，industry 主题无 ticker。
- **后果**：industry funnel 环①【行业财务弧线】、环②【估值锚】明文要求"基于 Step 1 财务数据给代表主体 3 年弧线"，但 Step 1 财务自动拉对 industry 返回空 → 这两环的数字脊柱只能靠手读年报，自动路径缺位。与 F10（ring 轴失灵）叠加 → industry 主题的"数据最硬两环"全无自动支撑。
- **修法**：industry/arena 主题从 roadmap 的代表公司 ticker 列表（或 peer 配置）批量拉 peer 财务，喂 `get_peer_comparison_data`；不要只认 scope.ticker。
- **补充验证（2026-05-31，深挖 i_industry_case 环②时实测）**：即使绕开 scope.ticker、直接用 `get_peer_comparison_data_by_tickers` 拉头部，仍三重撞墙：
  1. **HKEX 整条 fetch 路径不支持**——`fetch_financials_us only supports US, got 'HKEX'` 直接 raise。而本行业龙头主要在港股（信达 01801、百济 06160、恒瑞 H 01276）→ 自动财务对"以港股为主的行业"系统性不可用（与 F7/F8 的 A 股/HK fetch 摩擦同根）。
  2. **A 股路径也回脏数据**——百济 A（688235）fetch 到的是 **2021 招股说明书(申报稿)** 的过时数据 + 一堆 `unmapped CN column`，不可用。
  3. **即便取到也只有 fundamentals（revenue/gross_margin/roic/debt_to_equity），无 PE/PS 估值倍数**——而环②"命门环"要的恰恰是倍数反推。~~倍数需市值，本工具不产。~~ **← 此条订正，见下。**
- **⚠️ 订正（2026-05-31 二次复核，触发：用户质疑"PE/PS 为什么不从 finance 模块拿，不是有现成脚本吗"）**：上面第 3 条与"无倍数源"的判断**是错的**，根因是我**只翻了 `financial_data.py`（基本面管），整个漏看了 `prism/scripts/market_data.py`**——后者就是专产倍数的模块：`get_valuation_context(slug,variant)` / `get_quote()` → PE(TTM)/PE(静)/PB/PS/市值/52周，走 `akshare_adapter.fetch_snapshot`（行情 + eastmoney 估值历史，与 fundamentals 管完全不同的另一条干净管）。实测当场拿到：
  - 恒瑞 600276/SSE → PE(TTM) **41.0** / PE静 43.2 / PB 5.2 / PS 10.2 / 市值 **¥3331亿**（date 2026-05-29）✓
  - 百济 688235/SSE → PE(TTM) **118.9** / PS 9.2 / 市值 ¥3760亿 ✓（**第 2 条"A 股回 2021 招股书脏数据"也是误判——那是 fundamentals 管的毛病；行情管这条干净，倍数实时可取**）
  - 信达 01801/HKEX → 仍 raise `unsupported market 'HKEX'` ✗（**只有这条是真盲区，且仅伤纯港股标的**）
- **根因收窄（替代旧"财务源缺位"叙事）**：环②脊柱当初塌，**不是"系统没有倍数源"**，而是三件事叠加：① **行业 funnel 链路没接 `market_data`**——该模块 company-scoped（要 `scope.ticker`），`_industry_funnel.md` 环② / Step 1.2 没有"龙头名 → `fetch_snapshot(ticker, market)`"这个钩子，脚本在但行业链路从不调它；② 我把 fundamentals 管的故障误当成"全系统无倍数源"（认知错，非系统缺陷）；③ akshare 适配器 HKEX 真盲区（次要，仅纯港股 peer）。
- **直接后果链（→ 环② 脊柱塌）**：本轮 i_industry_case **环②（契约明定"数字最硬的一环，否则整链失去脊柱"）退化为纯定性伪式**、环⑤镜鉴缺实证——是 **F9（镜鉴 todo 假闭环料没收）+ 上述根因①②（链路没接现成倍数源 + 我漏看）的产物**，且 **`_industry_funnel.md` Step 1.2 财务拉取在验证中被整体跳过**。系统经 05-critic `request-more` 正确捕获了这个脊柱缺口（对比 primer F17 是悄悄放过）。
- **已补证（2026-05-31）**：环② 已改用**本地 `market_data` 实测倍数**（恒瑞 PE 41.0/PS 10.2/市值¥3331亿、百济 PE 118.9 双龙头硬锚）重写，**取代上一稿的 web 现采估值**——本地数更准更新、可注册。证明脊柱本可承重，缺的只是链路去调那个已存在的脚本。
- **修法（订正版）**：① **给 industry/arena 路径接 `market_data`**——环② / Step 1.2 增"代表龙头 ticker → `fetch_snapshot` 拿 PE/PS/市值"钩子（脚本现成，只缺 wiring，是最便宜的修）；② akshare 适配器补 HKEX 行情/估值源（对齐 memory 的 sina 路径），消纯港股盲区；③ Step 1.2 在 industry 路径设硬 checkpoint，拉不到要 log 而非静默跳过。**（注：原"无倍数源、需 web 现采"那条修法作废。）**

### 🔴 F15 — gap_detector ring 轴只数材料层 rings，无视 finding 层 rings（与 B 轴不对称）
- **现象**：写了 3 份 finding 带正确 industry rings（industry-financial-arc/value-chain-profit-pool/leader-valuation-anchor），gap A 轴仍报这些 uncovered。
- **根因**：`_detect_ring_inputs`（gap_detector.py:84-157）coverage 只 `for r in m.get('rings')` 数 **manifest 材料层**；而 B 轴（K#）取 material∪findings∪reuse 并集（:216-231 的 bug 修复）。两轴不对称。
- **后果**：02-doc 明示的补救"03 在 finding frontmatter 补 rings"对 A 轴**完全无效**——finding rings 对 gap 不可见。叠加 F10（材料层被标 company rings）→ industry A 轴经任何文档路径都补不绿。
- **修法**：`_detect_ring_inputs` 比照 B 轴，把 finding 层（含 reuse）的 rings 并入 coverage 计数。**与我已修的 F1 thin 阈值同模块，可一并修。**
- **状态**：待用户定夺（建议与 F1/F9 合并为一次 gap_detector 一致性修订）。

### 🟡 F14 — material_count.unprocessed 含 Role α web 料，03 Step 4 advance gate 永不触发
- **现象**：marked 106 processed 后 material_count 仍 `unprocessed=102`，全是 web-search（Role α）。`list_unprocessed` 排除 Role α 但 `material_count` 不排除。
- **后果**：03 Step 4 / Step 5 的 `if counts['unprocessed']==0: set_stage('04')` 对任何跑过 prescan 的 topic **永不成立** → 永远不自动升 04、报告永远显示"还有 N 份未处理"。
- **修法**：material_count 增 `exclude_triggered_by` 选项或单独给"可处理未处理数"，与 list_unprocessed 口径统一。

### 🟡 F11 — 旧 8 份叙事在多处未清（doc 清理不全，上次提交 #1(doc) 范围外）
- **03-extract-findings.md**：Step 4 next_actions "按顺序生成所有 8 份产出" + "生成第一份产出 商业全景"；Step 5 AskUserQuestion "重新生成 01-08 产出"。
- **05-critic-review.md**：① 头部前置"产出 04（隐含预期）和 06（风险盲点）必须已生成"（决策链 topic 无独立 04/06）；② Step 7 living_feed bump 仍 `set_output_status('08_living_feed')`（死键，会凭空造旧 slot）；③ Step 7 表格"某 output（如 04 隐含预期）需重写"。
- 上次提交 #1(doc) 只覆盖 _shared/05-critic L346 计数/_web_prescan；03 + 05 头部/Step7 + 可能的 06/07-drilldown 仍指向死的 8 份流程。建议补一轮全局清扫。

### 🟡 F17 — primer 无 depth gate / critic 非机械强制 → 可静默发 outline 还标 deep
- **现象**：本轮 from-zero 跑出的 `00_primer` v1 = 67 行 / 4.9KB 的提纲（~1800 字），却 frontmatter 自标 `depth: deep`。它**跳过了 `00-primer.md` 的多个深度产出步骤**：Step 3 独立 critic（文档原文"核心质控，**不可省**"）、写作硬规约的"争议必现 5-7 条"+"自检清单结尾"、Step 2.5 配套 `_prism_reading_guide.md`。对照参照级 ssb-electrolyte primer（709 行 / 21KB、过 critic、含争议节+自检节）深度差一个量级。
- **根因（两层）**：① 执行层——本轮为跑通 00→05 机制，primer 走了最小可行写法、省了慢的 critic 子代理；② **设计层（真缺陷）**——`set_output_status('00_primer','fresh')` 对内容长度 / critic 是否跑过 / 争议节·自检节是否存在**一律不校验**，`depth: deep` 是纯自报。所以一次赶进度的运行可以**静默发一份 outline 还标着 deep**，没有任何机械闸门拦得住。critic"不可省"目前只是文档约定。
- **同类性**：与 F1 / F9 / F15 同源——"自报满足 vs 实际欠供，无 gate 兜底"。且 primer 是所有下游 case 的理解地基，浅 primer 静默通过最隐蔽、危害最深。
- **已补证（产能在、缺的是闸门）**：2026-05-31 按 00-primer 全流程补跑 → 12 条目标 → 起点 outline → 全长撰写 → dispatch critic（一轮收敛，仅术语漏网类）→ v2 = 316 行 / 27KB，与参照级同档。证明瓶颈不在写作能力，在流程没强制走 critic。
- **修法**：critic"不可省"落成**机械 flag**（如 `set_critic_passed('00_primer')`，未置位则 dashboard 标"未过 critic"/`fresh` 降级为 `draft`）；`set_output_status` 对 00_primer 加软门禁：depth=deep 时长度下限告警 + 争议节/自检节存在性检查。

---

## 全链路验证结果（mechanism 维度，均 PASS）

| 阶段 | 结果 | 关键验证点 |
|---|---|---|
| 00-research | ✅ | 变体创建/baseline/adapter prescan(80 web,0 失血)/thesis_v0/decomposition_v0/ring 轴 active |
| 01-roadmap | ✅ | L3/L4+search_keywords/coverage 校验过/K# prescan(+24 web)/auto-download 7 年报 0 失败 |
| 02-gather | ✅ | Step0 跳过/mineru 0/双轴 gap（B 轴 K# 全覆盖；A 轴见 F10/F15）|
| 03-extract | ✅(代表性) | extractor 验证(F12 路径修)/3 findings+industry rings/索引重建/mark_processed |
| 04-synth | ✅ | primer+i_industry_case 6 环+09 sidecar(schema 通过)+2 arena stub+输出键自动注册+dashboard build exit 0(+2 行)|
| 05-critic | ✅ | type-aware 读 i_industry_case/prescan 门禁/gap 起手/verdict=request-more 跳 02 |

**数据校准价值**：训练 baseline 方向全对，prescan 锐化出 2025 BD $1356 亿(2.6×)、恒瑞-GSK $125 亿、信达-武田 $114 亿、百济全年盈利 ¥382 亿、丙类目录 9 月落地等精确事实；无重大推翻。

## 优先级建议（修复排序）

**P0（影响正确性，建议合并一次 gap_detector + 收料一致性修订）**
- **F10 + F15**：ring 自动打标读 topic.type（industry 用 industry-* code）+ gap ring 轴并入 finding 层 rings（比照 B 轴）。否则 industry A 轴永久失灵、thin 桶喂不出。
- **F9**：auto_resolve_todos 对 hard/half_public todo 不许裸 K# web 命中闭环（与我已修的 F1 thin 同源——"单弱料假装满足"）。
- **F7**：A 股 cninfo `fetch(annual)` 停止扫全量临时公告（99 份噪声）；annual 只取年报本体。

**P1（影响可用性/体验）**
- **F1**：create_topic 按 type stamp 决策链 outputs_state（删 8 死 slot）。
- **F13（已订正）**：倍数源**本就存在**（`market_data.get_valuation_context`，A 股实测可取 PE/PS/市值）——真缺口是 **industry/arena 链路没接它**（环②/Step 1.2 加"龙头 ticker→`fetch_snapshot`"钩子，最便宜）+ akshare 补 HKEX 消纯港股盲区 + Step 1.2 拉不到要 log 不静默跳。与 F9 同为环②/⑤塌陷的根因。
- **F12**：03/02 文档输出路径改 slug 级 materials/（或写前 mkdir）。
- **F14**：material_count.unprocessed 排除 Role α（与 list_unprocessed 口径统一）。
- **F2 + F16 + F11**：删/修死步骤（5.0a backfill）、补 arena stub create_topic 的 search_terms、全局清旧 8 份叙事。
- **F17**：把 primer critic"不可省"落成机械 flag + set_output_status 对 00_primer 加 depth/结构软门禁（与 F1/F9/F15 同属"无 gate 兜底"，可一并设计）。

**P2（低风险优化）**
- F3 模板 query 分 type（pharma 去"产能变化"）；F4 白名单补 CN 医药权威源；F5 prescan review-digest 子命令；F6/F8 python3 与 ticker 前缀统一。

### 🔴 F16 — _arena_select_spec.md Step 6 arena stub 创建漏 search_terms，create_topic 直接 raise
- **现象**：Step 6 模板 `create_topic(topic_type='arena', parent_topic=...)` 不含 `search_terms`；但 create_topic（H3 v2）对 question>25 字且无 search_terms 直接 raise。深挖 arena 问题普遍 >25 字 → funnel 说"逐字执行"Step 6 必崩。
- **影响**：04 环⑥ 建 arena stub 是 industry 漏斗的终点动作，文档照抄即失败；本轮手动补 search_terms 才建成。
- **修法**：Step 6 模板加 `search_terms`（+ 可选 short_name）字段与示例，或 create_topic 对 arena/industry 放宽（仅 company 强制）。

### 🟢 F8 — Step 5.5 与 create_topic 的 HK ticker 格式不统一
- 01 Step 5.5 文档用 `HK_02228`；00/create_topic 文档用 `HKEX_09995`。本轮 `HK_06160` 等可用（fetch 能解析），但两套前缀并存易混。建议统一。

### 🟢 F6 — 文档 `python` vs `python3` 不一致
- 多个 workflow 用 `python -c`/`python -m`，但环境只有 `python3`（`python` 不存在）。新机照抄即 127。统一成 `python3` 或在 skill 头注明。

---
