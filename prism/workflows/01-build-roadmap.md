# Workflow 01 — 制定研究路线图

**触发**：stage=01-roadmap-pending 或用户说「制定路线图」  
**前置**：topic.yaml 已存在  
**产出**：`prism/topics/{slug}/{variant}/roadmap.yaml`

---

## Step 1：读取 topic

```bash
python3 -c "
import json
from prism.scripts.topic import read_topic
print(json.dumps(read_topic('{slug}', '{variant}'), ensure_ascii=False, indent=2))
"
```

确认研究问题、类型、地理范围、深度。

---

## Step 1.5：检查父 topic 可复用资料

如果此 topic 有 `parent_topic`，列出父 topic 已收集的 materials 并标记哪些可复用：

```bash
python3 -c "
from prism.scripts.topic import read_topic, list_parent_materials
from prism.scripts.manifest import read_manifest
import json

topic = read_topic('{slug}', '{variant}')
parent = topic.get('parent_topic')
if parent:
    print(f'父 topic: {parent}')
    # 列出父 topic materials 目录
    materials = list_parent_materials('{slug}', '{variant}')
    print(f'父 topic materials ({len(materials)} 份):')
    for m in materials:
        print(f'  {m}')
    
    # 读取父 topic 的 manifest 获取 notes
    # 尝试所有 variant
    from prism.scripts.topic import list_variants
    variants = list_variants(parent)
    if variants:
        try:
            manifest = read_manifest(parent, variants[0])
            print()
            print('Manifest 详情:')
            for mat in manifest.get('materials', []):
                print(f'  [{mat[\"id\"]}] {mat[\"filename\"]}')
                print(f'    类型: {mat[\"source_type\"]}')
                print(f'    备注: {mat.get(\"notes\", \"\")}')
        except Exception as e:
            print(f'(无法读取 manifest: {e})')
else:
    print('无 parent_topic，跳过')
"
```

**根据输出判断**：哪些父 topic 资料对此 arena/company 研究有直接价值？在 Step 3 中将这些可复用资料标注为 `✓ 已收集（来自父 topic）`，并在 roadmap 的 `why` 字段中注明"复用父 topic materials/{filename}"。

> **复用排除边界**：复用**排除 prescan 校准层**（父 manifest 里 `addresses==['scope']` 或 `triggered_by` 为 `*-prescan*` 的 web-search 料——价/量/事件快照，时效性强）；带 `K#` addresses 的**耐久文档**（财报/研报/drilldown/findings 源 + web-search 挖到的实质文档，仍受 90 天 `expired_web_materials` 闸门约束，过期由 03 点名刷新）照复用。**新 topic 自跑 prescan**（Step 8），不复用父级 scope 校准料。

**关键：用脚本登记 parent_materials 字段**（让 workflow 04 自动复用，不用 dispatch prompt 手填路径）：

**先预览父变体兜底**（父 topic 可能有多个模型变体，确认会引到哪个）：

```bash
python3 -c "
from prism.scripts.topic import list_variants
from prism.scripts.model_registry import resolve_parent_variant
res = resolve_parent_variant('{variant}', list_variants('{父slug}'))
print(res)
# confident=True → 直接用 res['chosen']；confident=False → 列 candidates 问用户该用哪个变体，再显式传 parent_variant
"
```

```bash
python3 -c "
from prism.scripts.topic import set_parent_materials
items = [
    {'parent_slug': '{父slug}', 'parent_variant': '{父variant}', 'mat_id': 'mat-XXXXXX', 'addresses': ['K1','K2'], 'note': '...'},
    # 只列对本 topic thesis 有价值的父级 mat_id（不要全部塞）
    # parent_variant 省略时脚本按 model_registry 兜底：同模型/唯一/全登记自动选，
    #   多个异模型且含未登记则 raise（按上一步预览结果问用户后显式传）
]
set_parent_materials('{slug}', '{variant}', items)
print(f'已登记 {len(items)} 项父级复用')
"
```

mat_id 从父 topic `manifest.yaml` 拿（`prism/topics/{父slug}/{父variant}/manifest.yaml`），filename 不重要，链接通过 mat_id。变体名以 `model_registry` 规范名为准（opus 4.8 为短名 `opus4.8`，其余全 model-id 式）；父历史目录若是旧写法（如 `claude-opus-4-8`），读时会经 `model_registry.same_model` 自动桥接。

---

## Step 1.7：读取 thesis（**强制：路线图必须 thesis-driven**）

在制定路线图前先把 thesis_v0（如有）读进来：

```bash
python3 -c "
from prism.scripts.topic import read_topic
from prism.scripts.outputs import extract_killer_questions, extract_research_questions
t = read_topic('{slug}', '{variant}')
cur = (t.get('thesis') or {}).get('current_version')
if cur is None:
    print('⚠ 无 thesis — 应先回 workflow 00 Step 5.0 写 thesis_v0')
else:
    print(f'当前 thesis: v{cur}')
    print('Killer Questions:', extract_killer_questions('{slug}', '{variant}', cur))
    print('Research Questions:', extract_research_questions('{slug}', '{variant}', cur))
"
```

**如果没有 thesis**：先回 workflow 00 Step 5.0 写 thesis_v0，再回来跑 Step 2。

---

## Step 2：制定学习轨道（L3 争议 + L4 狩猎 · S2 简化）

> **S2 · L1/L2 坍缩**：旧版 L1 定向（是什么）+ L2 历史（怎么来的）本质是**背景理解层**，与 thesis 无强对齐——这些现在由 00_primer 全权承担（primer-first）。roadmap 不再单列 L1/L2 问题树，**坍缩成一行 primer scope 备注**（"primer 该覆盖：行业边界/参与者/市场规模/发展阶段/周期"），把篇幅集中到真正驱动收料的两层：
> - **L3 争议层 → 喂决策链环④**（多空分歧、共识可能错在哪）
> - **L4 狩猎层 → 喂 K#**（找错误定价，逐条对齐 thesis Killer Question）

**硬要求**：
- **L4 狩猎层必须逐条对齐 thesis 的 Killer Question**（K1, K2, ...），每条 L4 question 写 `addresses: [Kn]` 字段
- L3 争议层应反映 thesis 的"最大反方观点"——把反方逻辑展开为 3-5 个可调研的争议点
- **L1/L2 不再列问题树**：在 roadmap 顶部写一行 `primer_scope:` 备注即可（背景深度交给 00_primer，§1.2 primer↔case 分工）

基于训练知识 + thesis_v0 + decomposition_v0 命门，为这个研究主题制定两层问题：

**L3 争议层**（4-5 个问题）：搞清楚「分歧在哪」
- 多空双方的核心分歧是什么？
- 市场共识是什么，哪里可能是错的？
- 最容易被忽视的风险是什么？

**L4 狩猎层**（3-5 个问题）：找错误定价
- **每条必须对应一个 thesis Killer Question（K1/K2/...），addresses: [Kn]**
- **每条必须写 `search_keywords: [...]` 字段**（H4 修订）—— 2-3 个 web-search 关键词组（每个 ≤8 字、无问号），脚本会拿这些拼成 prescan query（无此字段则该 L4 跳过，Step 8 prescan 缺这一条 query）
- 如果市场错了，错在哪里？
- 哪个时间节点能验证或证伪？
- 什么样的新信息会改变当前判断？

L4 写完后做 self-check：thesis 的 N 个 K# 是否每个都有对应的 L4 question？没覆盖的要么补 L4，要么回 thesis 标注"本次不验证此 K"。

**示例（修 H4 后必须 search_keywords）**：

```yaml
l4_hunting:
  - question: AbbVie RC148 全球 III 期 2026Q3-Q4 能否宣布 IND/CTA 注册？市场目前隐含的概率多少？
    addresses: [K1]
    search_keywords: [RC148 III 期, AbbVie 注册, PD-1 VEGF 双抗]
    source_hint: AbbVie 2026 R&D Day + ClinicalTrials.gov 全量监控
```

注意 search_keywords 替代 question 喂给 WebSearch：question 长句问号往往返空（H4 缺陷），关键词组短促直接命中。**不要拿 question 直接当 query**。

---

## Step 3：制定资料优先级（A 合同地板 + B 命门靶点 双轴驱动）

> **收料不再只盯 K#**。两条轴一起组织资料优先级：
> - **A 轴（输入合同地板 · type 必收）**：照 `_input_contract.md` 本 type 的类目，**逐项确认有 todo 在收**。尤其三项真·欠供必须显式排期（旧流程从不主动收，是产出质量天花板）：
>   - `mgmt-capital-alloc` 管理层 track record + 资本配置史（年报/proxy/治理）→ 喂环①
>   - `consensus` 卖方一致预期/目标价模型 → 喂环②（建 todo 时标 `info_tier: half_public`——**这只是努力顺序提示,不是预授权降级用户**。consensus 不走 financial_data API 自动拉,但**仍须按 R1 在 Step 5.6/5.8 自动抓**：卖方 PE-G/估值表深度、财经媒体一致预期汇总常有公开转载,exa 多能命中;只有有效尝试 `empty` 才归用户 todo。**禁止在 Step 3 就把它写成"用户去收"**）
>   - `historical-mirror` / `industry-mirror` / `arena-mirror` 历史失败镜鉴（由 Step 4 类比落成）→ 喂环⑤
>   - 结构化项（`financial-arc` / `valuation-anchor` / peer 财务）由 financial_data/market_data 在合成期自动拉，给 ticker 即可，不必单列收料 todo（gap ring 轴标 api_pending 非红）。
> - **B 轴（命门靶点）**：照 `decomposition_v0.md` 每环 B 靶点收料，**低置信度命门优先砸料**（对冲薄拆解风险）。

**硬要求**：
- **建 todo 前扫 manifest 查已有料覆盖**（纪律，复用 `read_manifest`）：00 Step 4.0 早期 ingest + 父复用已把家底登记。每新增一条 todo 前，主 agent `read_manifest('{slug}','{variant}')` **按文档身份**判——已有料就是这条要的文档 → 建成 `done` 填 `covered_by=[已有mat]` 或不建；没有才建 `pending`。按文档身份判，不是 K# 撞 K#。
- **复用 5.3 已写的 user_todos** 作为 tier1 基础——它们已带 priority/info_tier/addresses 字段
- 每份资料填写 `addresses: [Kn]` 字段，对应 thesis K#（Q# 已降级，不再用）
- A 合同必收类目 + B 命门靶点 → 新增 todo 时，**在 `notes`/`source_hint` 标明服务哪个 ring code**，便于 02 登记材料时打 `rings`
- 5.3 P0 → 默认进 tier1；P1 → tier2；P2 → tier3
- 如果 5.3 没覆盖但路线图需要的，新增到对应 tier，**也必须写 addresses**

根据研究深度，列出三档资料：

**Tier 1（必读）**：对研究结论影响最大、最难被替代的 3-5 份
**Tier 2（补充）**：有助于验证但非必须的 3-5 份
**Tier 3（可选）**：深度研究时可参考的

每份资料说明：标题方向、类型（研报/年报/政策/数据）、从哪里找、为什么重要、**addresses（对应哪些 K#/L 问题）、info_tier**。

**对 `annual-report` 类型，必须填写 `ticker` 字段**以支持自动下载：
- A 股：`SSE_600519` / `SZSE_300750`
- 美股：`NVDA` / `AAPL`（直接写 ticker）
- 港股：`HKEX_02228`（走 HKEXnews，零 key，annual/semi/prospectus；`HK_` 旧前缀仍兼容）
- 英股：`LSE_OXIG`（走 FCA NSM，零 key，annual/semi）
- 韩股：`006400` 或 `KRX_006400`（走 DART，零 key）
- 日股決算短信（first-look）：`5019` 或 `TSE_5019`（走 TDnet，零 key，覆盖近 30 天）
- 日股有価証券報告書（年报正本）：`EDINET_E00040`（走 EDINET v2，需 `EDINET_API_KEY` env）
- 不可自动下载的（非上市/退市）：留空

---

## Step 4：识别历史类比（→ 落成 historical-mirror 收料 todo · O3 接线）

列出 2-3 个值得研究的历史类比案例，格式：
- 案例名称（国家+行业+时间段）
- 类比逻辑（哪里像）
- 类比局限（哪里不像）

> **O3 接线 · 类比不再是孤儿，直接喂决策链环⑤**：历史类比正是决策链环⑤【历史失败镜鉴】（输入合同 `historical-mirror` / 行业 `industry-mirror` / arena `arena-mirror`，见 `_input_contract.md`）的输入。**每个值得研究的类比必须落成一条收料 todo**——目标是拿到"相似剧本怎么崩 / 利润为何没兑现"的实证材料（行业研报 / 复盘文章 / web-search）。这是 plan 认定的**三项真·欠供之一**（旧流程从不主动收），不可省。
>
> 收料阶段（02）登记该材料时打 `rings=["historical-mirror"]`（或对应 type 的 mirror code）；只能训练知识粗述、收不到实证的，明写"镜鉴待补"进 `user_todos`，不冒充实证。
>
> ```python
> # 把类比落成收料 todo（示例，code 按 topic.type 选 historical/industry/arena-mirror）
> from prism.scripts.topic import set_user_todos
> set_user_todos('{slug}', ['收 historical-mirror 实证：{类比案例} 的崩盘/未兑现复盘（行业研报或复盘文章）'], '{variant}')
> ```

---

## Step 5：写入 roadmap.yaml

复制 `prism/templates/roadmap.yaml.tmpl`，填入上面分析内容，写入：
`prism/topics/{slug}/{variant}/roadmap.yaml`

---

## Step 5.5：尝试自动下载可获取的资料

> **ticker 规则**：LLM 在 Step 3 写 roadmap 时，对 `annual-report` 类型材料必须填写 `ticker` 字段。
> - A 股：`SSE_600519` / `SZSE_300750`（自动走 cninfo）
> - 美股：`QS` / `NVDA` / `AAPL`（自动走 SEC EDGAR；自动下 10-K + 10-Q）
> - 港股：`HKEX_02228`（自动走 HKEXnews，零 key；annual=年报 / semi=中期 / prospectus=招股章程；`HK_` 旧前缀仍兼容）
> - 英股：`LSE_OXIG`（自动走 FCA NSM，零 key；annual=Final/Preliminary Results / semi=Half-year Report；UK 不强制季报）
> - 韩股：`006400` 或 `KRX_006400`（自动走 DART，年报/半年报/季报均可）
> - 日股決算短信：`5019` 或 `TSE_5019`（自动走 TDnet 適時開示，零 key，30 天窗口；report_type=annual→決算短信，semi→中間決算短信，quarterly→四半期決算短信）
> - 日股有価証券報告書：`EDINET_E00040`（自动走 EDINET v2 API，需 env `EDINET_API_KEY`；EdinetCode 不是 ticker，5019/E00040 是出光興産）
> - 不可自动下载的（非上市/退市）：留空

**统一入口**：`scripts.fetch_report_prism.fetch(ticker, slug=, variant=)` 根据 ticker 格式自动路由到 cninfo / SEC / HKEXnews / FCA NSM / DART / TDnet / EDINET，并登记 manifest + 更新 todo status。

**多年批量**（A 股 / cninfo only — 用于 thesis 需要多年纵向对照的场景）：

```python
from scripts.fetch_report_prism import fetch_many
fetch_many('SSE_688499', years=[2020, 2021, 2022, 2023, 2024], slug=slug, variant=variant)
# 或 CLI: python3 -m scripts.fetch_report_prism SSE_688499 --years 2020-2024 --slug ...
```

**文件命名规范**（E7）：年报 / 10-K 落盘后均以 `{report_year}_{ticker}_...` 开头，便于按 report_year 排序、grep 同公司多年材料。旧文件保留原名不动；只对新下载生效。

```bash
python3 << 'EOF'
import re, yaml
from pathlib import Path
from scripts.fetch_report_prism import fetch

slug = '{slug}'
variant = '{variant}'
roadmap = yaml.safe_load(Path(f'prism/topics/{slug}/{variant}/roadmap.yaml').read_text())

# material type → fetch() report_type
TYPE_MAP = {
    'annual-report':     'annual',
    'quarterly-report':  'quarterly',
    'semi-annual-report':'semi',
    'semi-report':       'semi',
    'prospectus':        'prospectus',
}

def guess_year(title: str) -> int | None:
    # 优先抓 "2026年..." / "2024 年报"；否则取最大 4 位年
    m = re.search(r'(20\d{{2}})\s*年', title)
    if m:
        return int(m.group(1))
    years = [int(y) for y in re.findall(r'20\d{{2}}', title) if 2015 <= int(y) <= 2030]
    return max(years) if years else None

def guess_quarter(title: str) -> int | None:
    # 显式指定 Q1/Q3 时 fetch quarter 参数；不写则 fan-out 取最新
    if re.search(r'(Q1|一季|1Q)', title, re.IGNORECASE):
        return 1
    if re.search(r'(Q3|三季|3Q)', title, re.IGNORECASE):
        return 3
    return None

downloaded, failed = [], []
for tier in ['tier1', 'tier2', 'tier3']:
    for mat in roadmap.get('material_priority', {}).get(tier, []) or []:
        rtype = TYPE_MAP.get(mat.get('type'))
        if not rtype:
            continue
        tk = (mat.get('ticker') or '').strip()
        title = mat.get('title', '')
        if not tk:
            failed.append(f'{{title[:50]}} (无 ticker)')
            continue
        year = guess_year(title)  # None → fetch() 用 today.year - 1
        kwargs = {{}}
        if rtype == 'quarterly':
            q = guess_quarter(title)
            if q:
                kwargs['quarter'] = q  # 显式 Q1/Q3；否则 fan-out 取最新
        try:
            result = fetch(tk, report_type=rtype, year=year, slug=slug, variant=variant, **kwargs)
            downloaded.append(f'[{{rtype}}/{{year or "default"}}] {{title[:50]}} → {{result}}')
        except Exception as e:
            failed.append(f'[{{rtype}}/{{year or "default"}}] {{title[:50]}} ✗ ({{e}})')

print(f'=== DOWNLOADED ({{len(downloaded)}}) ===')
for x in downloaded: print(f'  {{x}}')
print(f'\\n=== FAILED ({{len(failed)}}) ===')
for x in failed: print(f'  {{x}}')
EOF
```

**注意**：
- `quarterly-report` 现在会被下载。`fetch()` 对 cninfo 季报：title 含 `Q1/一季` → 强制 Q1；含 `Q3/三季` → 强制 Q3；都没写 → fan-out 查 Q1+Q3 取最新披露（修 Q1 缺陷后行为）
- cninfo 一季报 `category_yjdbg_szsh` 与三季报 `category_sjdbg_szsh` 是独立 category，不能用同一 query 查全；fan-out 是修复方法
- 如果 roadmap 列了 2026Q1 + 2026Q3 同年两份季报，必须在 title 里明确写"2026 Q1" / "2026 Q3"让 `guess_quarter` 区分
- 半年报 `semi-annual-report` 同理走 `category_bndbg_szsh`

---

## Step 5.6：深度抓取公开分析材料（**先尝试自动获取，抓不到才变 user_todos**）

> **为什么必须做**：Step 5.5 只处理了 `annual-report` / `quarterly-report` 等有 ticker 的结构化文件。但 roadmap 里还有很多 `sell-side-note` / `industry-research` / `policy` / `data` 类型的材料，**实际上在公开渠道有全文或摘要可搜到**（卖方报告转载、行业研究机构公开报告、监管裁决原文、独立研究博客）。
>
> 如果跳过本步直接把这些写成 user_todos，等于把**本可以自动完成的工作甩给用户**。
>
> **产即收衔接**：本步抓 **01 自己 Step 2/3 新增**的 todo（L4 狩猎 / A合同必收类目）——00 产的 todo 已在 **00 Step 6.5** 当场抓过（产即收：谁产谁收），这里**只对 00 遗留的 `error` 按 R3 重试**，不重抓已 `fetched`/`empty` 的。闭环按**文档身份**盖戳（`mark_todo_fetch` + `update_user_todo_status`），**不靠 K# 撮合**。
>
> **硬规则（auto-fetch 规约 R1/R2，判定与盖戳见 [`_autofetch_protocol.md`](_autofetch_protocol.md)）**：
> - 作用域 = **tier1 + tier2 + tier3 全部、所有 info_tier**（仅排除 Step 5.5 已处理的 `annual-report`/`quarterly-report`）。`info_tier` 只决定**努力顺序/强度**（hard 先上 exa advanced + 权威 URL WebFetch），**不再作为跳过门槛**。
> - 每条尝试后**必须 `mark_todo_fetch`**：抓到 `fetched`、有效尝试确认公开无源 `empty`、工具/网络失败 `error`。
> - 只有 `fetch_status='empty'`（**有效尝试**过）才保留为 user_todo；`error` **必须重试**，绝不降级；`fetched` 在 Step 6 标 `done`。

### 执行方法

对 roadmap `material_priority` **tier1 + tier2 + tier3** 中每条**非 `annual-report`**（Step 5.5 已处理）的材料——**不分 info_tier**——按以下阶梯尝试（hard 类同样跑，多半 `empty` 但要由真实结果证明）：

#### 阶梯 1：exa 高级搜索（最适合找分析报告全文）

用 `mcp__exa__web_search_advanced_exa` 工具，按材料类型选 query：
- **卖方报告**（sell-side-note）：搜 `"{公司名} {ticker} deep research analyst report {年份}"` + 中文 `"中金 高盛 {公司名} 深度研报 {年份}"`，设 `enableHighlights=true`、`highlightsMaxCharacters=2000`、`textMaxCharacters=5000`
- **行业研究**（industry-research）：搜 `"{行业/主题} market share data report {年份}"`，同上参数
- **政策/监管**（policy）：搜 `"{公司名} {regulation} enforcement {年份}"`，同上参数
- **数据**（data）：搜 `"{公司名} statistics financial data {年份}"`，同上参数

每个材料跑 1 次 exa search（`numResults: 5`），**5 个一批并发**（不同材料可并行）。

#### 阶梯 2：adapter semantic 搜索（补充 exa 未覆盖的）

对阶梯 1 未找到满意结果的材料，用 adapter 补搜：
```bash
python3 -m prism.scripts.web_search search "<材料标题关键词>" \
    --intent semantic --days 365 --max-results 5 --output sidecar \
    --slug {slug} --variant {variant} \
    --triggered-by 01-deep-fetch --addresses K1,K2
```
注意 `--intent semantic`（不是 `news`）——目的是找分析性内容，不是最新新闻。`--days 365` 因为研报/报告时效性比新闻长。

#### 阶梯 3：WebFetch 抓取已知 URL

对阶梯 1/2 搜到的高质量 URL（domain_tier 判为 `llm-judged-official` 的），用 `mcp__exa__web_fetch_exa` 批量抓取全文（`maxCharacters: 5000`，可一次传多个 URL）。

#### 落盘与入库

找到的内容写到 `prism/topics/{slug}/inbox/{descriptive_name}.md`（资料只在 topic 层，无全局 inbox），格式：
```markdown
# {材料标题}

Source: {来源}
Date: {日期}

{全文或摘要内容}
```

然后调 `add_material` 入库，并 `mark_todo_fetch` 盖结果：
```python
from prism.scripts.manifest import add_material
from prism.scripts.topic import mark_todo_fetch
# 抓到：
mid = add_material('{slug}', '{filename}', '{source_type}', '{variant}',
    notes='{材料描述}', addresses={addresses}, rings={rings}, confidence=0.8)
mark_todo_fetch('{slug}', '{variant}', '<对应 todo task 子串>', 'fetched', note='exa→{来源}')
# 有效尝试但公开无源：
mark_todo_fetch('{slug}', '{variant}', '<task 子串>', 'empty', note='exa+semantic 0 命中')
# 工具/网络/限流失败（必须重试，不要降级）：
mark_todo_fetch('{slug}', '{variant}', '<task 子串>', 'error', note='providers exhausted')
```

### 判定结果汇总

跑完后输出一张表，明确标注每条材料的 `fetch_status`：

```
| 材料 | info_tier | 获取方式 | fetch_status |
|------|-----------|----------|--------------|
| Goldman Sachs PDD Report | half_public | exa search → BigGo 转载 | fetched（mat-xxx） |
| QuestMobile 份额报告 | half_public | exa search → BXTData 全文 | fetched（mat-xxx） |
| Temu 半托管单位经济 | hard | exa+semantic 均无果 | empty（待用户决策） |
| 某付费库数据 | hard | providers exhausted | error（下轮重试） |
```

### 纪律

- **不要跳过本步**。如果 exa/adapter/WebFetch 能搜到，就没理由让用户手动找
- **hard 也要尝试一次**（专家访谈/产业链调研/付费数据库多半 `empty`，但 empty 要由真实结果证明，不由标签预判——付费卖方深度常有公开转载，别先入为主跳过）
- **`error` 必须重试，永不降级**（工具/网络/限流不是"公开没有"；判定见 [`_autofetch_protocol.md`](_autofetch_protocol.md) 表 A/B）
- **exa search 的 `numResults` 不要超过 5**（控制成本）
- **搜不到不丢人**——但要 `mark_todo_fetch('empty')` 诚实记录"搜了没搜到"，而不是没搜就放弃
- 本步与 prescan 的分工：prescan 校准**事实**（数字/事件），本步获取**分析材料**（报告/数据/裁决）

---

## Step 5.7：自动校验 roadmap → thesis 闭环（**未通过不得进 Step 6**）

```bash
python3 -c "
from prism.scripts.outputs import validate_roadmap_thesis_coverage
from prism.scripts.topic import read_topic
t = read_topic('{slug}', '{variant}')
cur = (t.get('thesis') or {}).get('current_version')
if cur is None:
    print('⚠ 无 thesis，跳过校验（强烈建议补 thesis）')
else:
    r = validate_roadmap_thesis_coverage('{slug}', '{variant}', cur)
    print(f'Thesis K#: {r[\"thesis_ks\"]}')
    print(f'L4 covered: {r[\"l4_covered\"]}')
    print(f'Material covered: {r[\"material_covered\"]}')
    if not r['ok']:
        print()
        if r['uncovered_in_l4']:
            print(f'❌ L4 未覆盖: {r[\"uncovered_in_l4\"]} — 补 L4 question 或在 thesis 中标注不验证')
        if r['uncovered_in_material']:
            print(f'❌ Material 未覆盖: {r[\"uncovered_in_material\"]} — 补 tier1/2/3 资料')
        raise SystemExit(1)
    print()
    print('✓ Coverage 通过')
"
```

如果非 0 退出，**回 Step 2/3 修 roadmap**，再回来跑 Step 5.7。

---

## Step 5.8：auto-fetch 全覆盖硬闸门（**未通过不得进 Step 6 / 不得 set_stage**）

> **为什么必须做**：Step 5.6 的「产即收 + R1 全覆盖」此前只是散文纪律（「不要跳过本步」），没有像 5.7 coverage 那样的机器卡口——主 agent 一旦漏抓某条 todo（尤其凭 `info_tier` 先入为主跳过 half_public/hard），stage 仍会静默推进到 02，下游不替它补抓（产即收的下游不补抓原则），缺口就永久蛰伏。本闸门把已有的 `pending_unfetched_todos`（R3 清单）接成 advance 前的硬断言，精确拦截「从未尝试就推进」。

```bash
python3 -c "
from prism.scripts.topic import pending_unfetched_todos
p = pending_unfetched_todos('{slug}', '{variant}')
unattempted = [t for t in p if t.get('fetch_status') == 'unattempted']
errored     = [t for t in p if t.get('fetch_status') == 'error']
if unattempted:
    print('❌ 产即收违规：以下 todo 从未尝试过抓取（fetch_status=unattempted）——')
    print('   info_tier 只决定努力顺序，不是跳过门槛（auto-fetch 规约 R1）。回 Step 5.6 逐条跑阶梯并 mark_todo_fetch：')
    for t in unattempted:
        print(f'   - [{t.get(\"info_tier\")}] {t[\"task\"][:60]}')
    raise SystemExit(1)
if errored:
    # error 是 transient（providers exhausted / 网络）：本轮可带过，交 02/03 的 R3 下轮重试；但要响铃可见，不静默
    print('⚠ 以下 todo 抓取失败（fetch_status=error），按退避梯重试；本轮带过将由 02/03 的 R3 续抓：')
    for t in errored:
        print(f'   - {t[\"task\"][:60]}')
print('✓ auto-fetch 全覆盖通过：无 unattempted（每条 todo 都已有效尝试过）')
"
```

如果非 0 退出（有 `unattempted`），**回 Step 5.6 把它们逐条抓完 / 盖 `empty` / 盖 `error`**，再回来跑 Step 5.8。**`unattempted` 清零是进 Step 6 的前置条件。**

---

## Step 6：增量更新 topic 状态（**禁止覆写 5.3 结构化 todos**）

⚠️ **重要**：5.3 阶段写的 todos 已带 `priority/info_tier/addresses` 字段；不能用 `set_user_todos(slug, list[str])` 全量覆写——会丢字段、破坏 K# coverage 闭环。

**正确做法**：
1. 对已下载的 material，**更新对应 todo 的 status 为 `done` 或 `in_progress`**（仅下载部分时 in_progress）
2. **append** roadmap 里新出现、但 5.3 没覆盖的 tier1/tier2 todos（带完整结构）
3. 不删除任何旧 todo

```bash
python3 << 'EOF'
import yaml
from pathlib import Path
from prism.scripts.topic import (
    read_topic, set_stage, set_next_actions, set_user_todos, update_user_todo_status
)
from prism.scripts.manifest import register_inbox_materials

slug = '{slug}'
variant = '{variant}'
roadmap = yaml.safe_load(Path(f'prism/topics/{slug}/{variant}/roadmap.yaml').read_text())

# 0. 增量登记 topic 家底（用户中途放进 topics/{slug}/inbox/ 的料；幂等）
register_inbox_materials(slug, variant)

# 1. 收集已下载文件名（资料只在 topic 层：inbox + materials，无全局目录）
downloaded = set()
for d in [f'prism/topics/{slug}/inbox', f'prism/topics/{slug}/materials']:
    p = Path(d)
    if p.exists():
        downloaded.update(f.name for f in p.iterdir() if f.is_file())

# 2. 对每个 tier1 material 推断状态，更新匹配的 todo
def match_filename(ticker, keywords):
    '''检查 downloaded 里是否有匹配 ticker 或关键词的文件'''
    matches = []
    if ticker:
        tk = ticker.replace('SSE_', '').replace('SZSE_', '').replace('BSE_', '').upper()
        for f in downloaded:
            if tk in f.upper(): matches.append(f)
    for kw in keywords:
        for f in downloaded:
            if kw in f: matches.append(f)
    return matches

# LLM 在这里手动列出 (todo task 子串 → 资料完整性) 的判断
# 例：('宁德时代凝聚态', 'in_progress')  # 年报已到但访谈逐字稿还缺
# 例：('QuantumScape/Solid Power', 'done')  # 10-K + 10-Q 全到

todo_status_updates = [
    # ('todo task substring', 'done' | 'in_progress'),
    # 由 LLM 根据 manifest 判断填写
]
for sub, status in todo_status_updates:
    try:
        update_user_todo_status(slug, variant, sub, status)
        print(f'  ✓ {sub[:40]} → {status}')
    except ValueError as e:
        print(f'  ⚠ {e}')

# 3. Append 新结构化 todos（仅添加 5.3 没覆盖的、roadmap 新冒出来的资料任务）
data = read_topic(slug, variant)
existing_tasks = [t['task'] for t in data['user_todos']]
new_todos = list(data['user_todos'])
APPEND = [
    # 只 append 5.3 todos 完全没提到的新需求，例如：
    # {{'task': '查阅整车厂公告挖一级市场玩家披露', 'priority': 'P0',
    #  'info_tier': 'hard', 'addresses': ['K3','K4'], 'status': 'pending'}},
]
for t in APPEND:
    if not any(t['task'][:25] in et for et in existing_tasks):
        new_todos.append(t)

set_user_todos(slug, new_todos, variant)

set_stage(slug, '02-gather-materials', variant)
set_next_actions(slug, [
    f'已下载 N 份资料，登记 manifest（A股自动；美股需手工 add_material）',
    '运行 workflow 03-extract-findings 处理已收集资料',
    '剩余 P0 todo 补齐后再跑 workflow 03',
], variant)
EOF
```

**注意**：
- `update_user_todo_status` 按 task 字段子串匹配，确保子串唯一
- 旧的 list[str] 风格 todos 在 read 时会被 `_normalize_todo` 自动 upgrade 到 dict，但 priority/info_tier/addresses 会变成默认值——所以最好的实践是从 workflow 00 5.3 起就用结构化 schema

---

## Step 7：汇报

在对话输出：

```
✅ 研究路线图已生成 → prism/topics/{slug}/{variant}/roadmap.yaml

L4 狩猎问题（最重要）：
{list L4 questions}

Tier 1 必读资料：
{list tier 1 items}

你现在需要做的事：
1. 收集上述资料放入 prism/topics/{slug}/inbox/
2. 具体清单已同步到 Web 页面 "你需要做的事" 区域
3. 完成后说「prism 推进 {slug}」继续

Web 地址：http://localhost:8000/prism/{slug}/{variant}/
```

---

## Step 8：一次性 web-search prescan（**新增**）

roadmap 落地后立即跑 `_web_prescan_shared.md` 一次（`recency_days=90`），目的：
- 为每个 L3-debate 争议点 + L4 hunting question 主动拉近 90 天事件 / 数据
- 覆盖 `build_search_queries` 枚出的各槽：scope / company 主体 / industry 行业面 / 每个 concept / 每条 L4（逐 K# 对齐）
- thesis K# 一次性扫覆盖度

各槽的事件轴（**查什么**）由主 agent 按领域自定，**不套固定后缀**——旧版对所有行业写死"产能变化"、对 company 写死"最新公告/监管/业绩"即 PRISM_VALIDATION F3 病根；措辞规约见 `_web_prescan_shared.md` Step A。按 Step A-F 执行，`triggered_by='01-prescan'`。

完成后 user_todos 通常已自动消化掉大半 K# 级 todo——剩下的（如未公开内部数据、付费墙、专家访谈）才是真正需要用户手工去搞的清单。

