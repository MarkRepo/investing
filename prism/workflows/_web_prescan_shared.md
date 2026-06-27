# Shared Sub-workflow — LLM-driven Web-search Prescan

**被引用**：01-build-roadmap (Step 7) / 02-gather-materials (Step 0) / 06-daily-monitor (Step N) / 07-drilldown (Step M)
**定位**：通用 across 所有 topic type（company / industry / arena / concept），用 LLM 主动调 WebSearch + WebFetch 把"训练截止后的新事件"和"高频小数据"自动纳入 manifest，减少用户手工收集负担
**LLM 分工**：脚本零 LLM——覆盖槽枚举 / 域名分类 / 写 inbox / 入 manifest / 更新 todo 都由 Python；**query 措辞** / WebSearch 调用 / confidence 判断 / addresses 标注由主 agent 在对话里做（参 `memory/feedback_llm_workflow.md`）。注意：query 文本**不再由脚本模板生成**——查什么是领域判断（旧版对创新药套死"产能变化"即 PRISM_VALIDATION F3 病根），脚本只给"需要覆盖哪些 address"的清单

---

## Step A：拿覆盖清单 + 主 agent 逐槽写 query

脚本只枚举"哪些 address 需要被 web 覆盖"，**不代写 query 文本**：

```bash
python3 << 'EOF'
from prism.scripts.web_prescan import build_search_queries
slots = build_search_queries('{slug}', '{variant}', recency_days={recency_days})
print(f'共 {len(slots)} 个覆盖槽（每槽你写 ≥1 条 query，addresses 原样带回）：')
for s in slots:
    print(f'  [{s["kind"]}] addrs={s["addresses"]} hint={s["hint"]}')
EOF
```

返回的是**覆盖槽清单**，每槽含 `addresses`（绑定，原样带回）/ `kind` / `recency_days` / `hint`（原始素材）。**无 `query` 字段**——query 文本由你在对话里写。

主 agent 据 `hint` + 领域知识，为每个槽写实际 query（一槽可写多条），措辞要点：
- **`scope`**：用 `hint["short_name"]` + `hint["search_terms"]`（写 topic 时的精炼词）拼 5-15 词搜索友好串；勿把长 `hint["question"]` 整句塞进去
- **`company-event`**：`hint["name"]` + `hint["ticker"]` + 你按该公司情形选的事件轴（最新公告 / 业绩预告 / 监管处罚 / 高管变动 / ……按行业自定）
- **`industry-event`**：`hint["base_terms"]` + 你按**该行业**选的事件轴。创新药→医保谈判 / 临床读出 / BD 交易 / 审评进度；锂电芯片→产能 / 开工率 / 价格；金融→政策 / 利率 / 牌照……**不要套用别行业的轴**（这是 F3 的根：旧版对所有行业写死"产能变化"）
- **`concept-update`**：`hint["concept"]` + 最新进展 / 动态
- **`l4-hunting`**：优先用 `hint["search_keywords"]`（roadmap 已写好的精炼词）；缺则从 `hint["question"]` 提炼名词短语。一条 query 对一个 K#（`addresses` 已绑）

> 完备性：清单已覆盖 scope + 每个 concept + 每条 L4 hunting（逐 K# 对齐）。**逐槽都要写 query 并执行**，漏槽 = 漏覆盖。后续 Step B/C 里的"query"均指你在此写的串；`expected_queries=N` 传你实际执行的 query 条数。

`recency_days` 调用方传：
- 01-prescan：90（建库时一次性回看 90 天）
- 02-step0：30（增量扫近 1 个月）
- 06-daily-monitor：7（deep tier）/ 14（watch tier）
- 07-drilldown：180（专项往回查更长时段）

---

## Step B：执行检索（**adapter-first**——每条 query 执行一次）

> 🧭 **路径选择（对齐 `_web_search_routing.md` 总则「进文件 → adapter；进上下文 → tool」）**：prescan 结果**要进文件**（sidecar → register → inbox/manifest）**且高频**（一轮十几条 query），按 routing 文档分步表，prescan 场景**默认走 adapter**。理由是 `--output sidecar` 落盘 + `review-digest` 紧凑投影判 tier，避免每条 query 把结果整坨灌进上下文（16 query = 16 坨叙事，纯防爆上下文）。**WebSearch 工具降为 fallback**（adapter `ALL_PROVIDERS_EXHAUSTED` / 无 provider key 时）。
>
> 注：选 adapter 不是因为 WebSearch「没结构」——本 harness WebSearch 返回的 `Links:` 是结构化 `{title,url}`（URL 真实可用）；纯粹是「进文件 + 高频 → adapter」的场景判定。

**默认路径（adapter）**——对 Step A 每条 query：

```bash
python3 -m prism.scripts.web_search search "<query>" \
    --intent <news|semantic|exact|general> --output sidecar \
    --slug {slug} --variant {variant}
```

→ 主 agent 用 `review-digest` 看 index 投影判 tier（**勿 Read 整 json**，见 Step C/D）→ 手动调 `register_web_search_batch`（入库时 `addresses` 用该槽的 `slot["addresses"]` 或更精细事件锚）。adapter 返回结构化 `{title,url,snippet,score,domain_tier}`，直接对上 register 契约。

**Fallback 路径（WebSearch 工具）**——仅当 adapter 全 provider 耗尽 / 无 key：

- 主 agent 直接调 `WebSearch`，取返回的 `Links:` 数组（结构化 `{title,url}`）。**本 harness WebSearch 无 per-hit snippet，且正文是跨 hit 合成叙事——snippet 一律留空，禁止从叙事里抠摘要贴给某条 URL（会错配）**。下游 dedup/domain_tier 只看 URL、register 容忍空 snippet，留空无碍。
- 经 adapter postprocess 注入（走 dedup + 黑名单 + 落 sidecar）：

  ```bash
  echo '<json hits array>' | python3 -m prism.scripts.web_search postprocess \
      --source websearch_fallback --slug {slug} --variant {variant} \
      --triggered-by {step}-fallback --addresses K1
  ```
- **硬约束**：只引用工具实际返回的 URL，**禁止用训练知识补 URL / 编造引文**——参 plan 「风险与缓解」。

> 下方 **B.1（并发限流）/ B.2（长时不可用兜底）仅在走 fallback、即实际调用 WebSearch 工具时适用**；adapter 路径不受 WebSearch 并发静默限流约束（它有自己的 provider 配额/重试，见 `web_search status`）。**B.3 健康度检查路径无关，两条路径都跑。**

### B.1 并发限流（**走 WebSearch fallback 时必照做**）

Anthropic WebSearch 在短时窗内并发调用过多会**静默返空**（只返回标题行 + REMINDER，无任何 search result block，无错误）。主 agent 看到的现象与"该 query 真没结果"无法区分。

**硬约束**（single source of truth：`prism/scripts/web_prescan.py` 顶部常量）：

```python
WEB_SEARCH_BATCH_LIMIT = 5            # 单条消息最多 5 个 WebSearch 并行
WEB_SEARCH_BATCH_INTERVAL_S = 10      # 两批之间至少等 10s
WEB_SEARCH_SERIAL_RETRY_INTERVAL_S = 30  # 限流后串行重试每条间隔 30s
WEB_SEARCH_FAIL_THRESHOLD = 0.5       # 入库率 <50% → prescan_status='failed'
```

**执行模式**：
1. **第一轮**：N 条 query 按 5 个一批并行，批间隔 10s。每批后 register，看 stderr 是否出现 `⚠️ [upstream_empty]` 或 `⚠️ [all_low_band]` 告警
2. **读 register 返回的 `failure_mode`**（'upstream_empty' / 'all_low_band' / 'none'）—— 比单看 `silent_failure: bool` 精准：
   - `'upstream_empty'`：hits=0，疑似 WebSearch 上游静默限流 → 等 30s 串行重试本 query；≥3 条 upstream_empty 转 Step B.2 兜底
   - `'all_low_band'`：hits>0 全 drop low band → **不是限流，是 H2 救回未启动**。调 `extract_url_features(dropped_urls)` + LLM 判 tier + 救回列表带 `domain_tier='llm-judged-official'` 再调一次 register（Step C/D）
   - `'none'`：至少 1 条入库，正常
3. **`silent_failure: bool`** 字段保留向后兼容（= upstream_empty or all_low_band），但**新代码用 `failure_mode` 字符串分流**

### B.2 兜底协议（WebSearch 长时不可用时）

按优先级降级：
1. **WebFetch 已知权威 URL**（手工列 5-10 个最相关一手源 — IR PDF / 学术综述 / Wikipedia 当事条目 / 政府公告页）
2. **跳过 prescan，标 `prescan_status='failed'`**：
   - **若本轮在写 thesis 之前（仅 workflow 00 Step 5.0）**：调 `set_thesis(prescan_status='failed', force_failed=True, prescan_failure_reason='WebSearch 长时不可用，已尝试串行重试 + WebFetch 兜底均无果')`——这是 thesis 写时状态，绑 history[N]
   - **若本轮在 thesis 写定之后（workflow 01 Step 8 / 02 Step 0 / 06 Step 1b 等）**：**不要调 set_thesis**——会污染 thesis 写时 prescan 状态。改调 `set_prescan_log(slug, variant, status='failed', triggered_by='01-prescan', failure_reason='...')` 写到独立 `topic.prescan_log` 数组

### B.3 健康度检查（写 thesis 之前必跑）

```python
from prism.scripts.web_prescan import check_prescan_health
h = check_prescan_health('{slug}', '{variant}', expected_queries=N, triggered_by_prefix='00-prescan')
# {'status': 'full'/'partial'/'failed', 'queries_run': N, 'queries_with_hits': M,
#  'queries_skipped_covered': S, 'hit_rate': float, 'failure_reason': str|None}
# "命中"= 该 slot 已校准：入库 high/mid，或主动跳过且标了已覆盖（见 Step D §跳过留痕）。
```

**根据调用情境分流（H5 修订）**：

- **写 thesis 前的 prescan**（仅 workflow 00 Step 5.0）：把 `h['status']` + `h['failure_reason']` 传给 `set_thesis(prescan_status=h['status'], prescan_failure_reason=h['failure_reason'], force_failed=(h['status']=='failed'))`——这一轮的 prescan 状态是该 thesis 版本论据来源的凭证，绑 history[N]
- **thesis 写定之后的 prescan**（workflow 01 Step 8 / 02 Step 0 / 06 Step 1b 等）：**不调 set_thesis**，改调：

  ```python
  from prism.scripts.topic import set_prescan_log
  set_prescan_log(slug, variant,
      status=h['status'], triggered_by='01-prescan',
      hit_rate=h.get('hit_rate'),
      queries_run=h.get('queries_run'),
      queries_with_hits=h.get('queries_with_hits'),
      failure_reason=h.get('failure_reason'),
  )
  ```

  写到独立 `topic.prescan_log` 数组——不污染 thesis 写时状态，但下游（05-critic）可查最近一次 prescan 是否 drift。

> 历史教训：H5 前所有 prescan 调用方都按 set_thesis 一条路写，结果 workflow 01 Step 8 末尾 prescan 失败会把 thesis_v0 写时 prescan='full' 覆盖成 'failed'，下游 05-critic 误 BLOCK 04-synthesize。修法：thesis.prescan_status 顶层删除，绑 history；后续轮次走独立 log。

---

## Step C：主 agent 对每条结果判断 confidence + addresses

> 🚨 **H2 失血必读**（2026-05 荣昌生物实战教训）：
> 非 WHITELIST 域名默认 confidence=0.4 → low → **直接丢弃不入库**。
> 实战：P0 6 条 query 首发 40 hit 仅 4 个入库（80% 失血）；救回靠主 agent 显式标 `llm-judged-official` 第二轮补登。
>
> **三条硬规则**（必照做）：
> 1. **每次 register 后看 `drop_ratio`**：>0 就扫返回的 `dropped_hits` 列表；>=0.5 stderr 会自动附 url 提示
> 2. **看不准就调脚本拿事实**：`extract_url_features(urls)` 返回每个 url 的客观特征（in_whitelist / host / subdomain_tokens / tld_class / path_is_pdf / path_announce_tokens / known_low_signal_host），LLM 据此自己判断是否升 `llm-judged-official`
> 3. **救回模式**：救回列表带 `domain_tier='llm-judged-official'` 重新调一次 `register_web_search_batch(query=...同上..., hits=[救回的], ...)`，dedup 会自动避免重复
> 4. **域族收敛（F4）**：救回时带 `domain_tier='llm-judged-official'` 的 host，会被脚本按域族（`parent_topic||slug`）累计；同族跨 ≥2 个 topic 判为权威即自动晋升进 `prism/state/whitelist/overlays/{family}.json`，下次同族 topic 直接命中、不必再救。**这是脚本侧自动行为，主 agent 无需也不要 Read overlay/log 文件**（它们是 oracle 数据，非上下文材料）。
>
> 已知行业垂直/海外医药/券商研报源完整列表 → `python3 -c "from prism.scripts.web_prescan import WHITELIST_DOMAINS; print('\n'.join(sorted(WHITELIST_DOMAINS)))"`（不要把列表抄进文档/memory，避免 token 膨胀）

### 判 tier 的操作路径（digest 优先 — 不再 Read 整个 raw json）

`--output=sidecar` 把整批 hit（含可能很长的 snippet / `raw_content` 全文）写进 `_websearch_raw/{ts}_{qhash}.json`。**禁止直接 `Read` 这个 json 判 tier**——会把每条正文全灌进上下文（实测一轮 6-query prescan ≈70K+ token 纯为判 tier）。改走惰性升级阶梯：

1. **看 index**（零正文）：
   ```bash
   python3 -m prism.scripts.web_search review-digest --raw-path {raw_path}
   # 或省路径取该 topic 最新一次：--slug {slug}
   ```
   每条一行 `[idx] WL=Y/N host tld_class | title | snip=NNN raw=NNN/none [flags]`，flags 透传确定性特征（low_signal/pdf/announce/sub:ir…）+ provider 已设 domain_tier + published_at。**绝大多数 hit 在这一层就能判**：`WL=Y`→whitelist；`low_signal`→other 跳过；`sub:ir/investor` + `pdf` + `announce`→公司公告/IR，多半 `llm-judged-official`；host 是你训练知识里的行业垂直/券商/海外医药源→`llm-judged-official`。
2. **残差才展开 snippet**（整段，引擎给定）：`review-digest --raw-path {raw_path} --show {idx}`（可 `--show 0,3,4`）。
3. **snippet 仍判不出且该 hit 值得入库（够 high）才取全文**：`--show {idx} --full` 打 `raw_content` 整段；raw json 无 `raw_content`（未 `--need-extract`）才 `WebFetch` 抓一次。

> 每跳都是在「两个完整给定字段间选哪个加载」，脚本从不替你截选片段或判 tier。碰 snippet/全文的是残差的残差。

对每条 hit，主 agent 在对话里给出：

| 字段 | 如何判断 |
|---|---|
| `domain_tier` | 命中 `WHITELIST_DOMAINS`（index `WL=Y`） → `whitelist`；非白名单但内容可信（该公司官方 IR 页/微信公众号官方账号/已知财经平台/行业垂直媒体） → `llm-judged-official`；其余 → `other` |
| `confidence` | 不传 → 用 `confidence_for_tier(domain_tier)` 默认（whitelist=0.9 / llm-judged=0.7 / other=0.4）。若 snippet 内容明显高度对题，可上调；明显跑题可下调 |
| `addresses` | 该 hit 攻打的 K# 列表（与该 query 所属槽的 `slot["addresses"]` 一致或更精细）。**事件锚规则**：若 hit 内容明确绑定某个时间/事件（财报季、监管事件、产品发布），用 `K#@event-slug` 格式（如 `K1@2026Q2-earnings`、`K6@CSRC-2026-05-22`、`K7@Airstar-launch`），事件 slug 仅含 `[A-Za-z0-9_-]`。**裸 `K#`** 表示该 K# 的通用资料（财务结构、商业模式、长期数据），不绑事件。锚的作用：阻止 Q1 材料误覆盖 Q2 事件 todo——参 `memory/feedback_addresses_granularity.md` |
| `full_text` | **keep 档需要全文时**优先用 raw json 已有的 `raw_content`（`--show {idx} --full` 即取到），缺失才 `WebFetch`。判 tier 时已为某条拉过的全文按下方 §复用 透传 `register_web_search_batch(full_texts={url: 全文})`，**不重拉**；low/drop 档不抓全文 |

**§ full_text 复用（修重复抓取）**：为判 tier 而展开/抓取的 `raw_content` 或 WebFetch 全文，对最终 keep（high/mid）的 hit 保留，整批透传进 `register_web_search_batch(full_texts={url: 全文})` → 落 inbox md `## Full text` → 03-extract 直接复用，全程**一次抓取**。

**§ drop 即沉没（硬纪律）**：tier 判 drop 的 hit——① 不进 register（或仅作 `dropped_hits` 不救回）；② **即使你已为判 tier 读了它的 `raw_content` / WebFetch 了全文，也不得据此写任何 finding**。已付的抓取成本不构成入库理由；drop 就是内容丢弃。

**§ 整条 query 主动不入库时必须留痕（硬纪律 — 修 prescan-health 假阴性）**：当一条 prescan query 跑完、你判定**整条无需调 `register_web_search_batch`**（best hit 已在库、或全是低质垃圾），**不许静默跳过**——静默 = `web_search_log` 无痕 = `check_prescan_health` 把它误判成"没搜到"，拖低校准率甚至误触 `failed`。改调：

```python
from prism.scripts.web_prescan import log_search_skipped
log_search_skipped(slug, variant, query='<本条 query 原文>',
    triggered_by='00-prescan',  # 与本轮 register 一致
    n_results=<WebSearch 实际返回 hit 数>,
    reason='skipped-covered',   # 或 'skipped-duplicate' / 'skipped-lowtier'
)
```

`reason` 必须**如实分类**（直接决定该 slot 算不算校准命中）：

| reason | 用于 | 健康度 |
|---|---|---|
| `skipped-duplicate` / `skipped-covered` | top hit 已在库 / 已被本轮别的 query 覆盖——该 slot 本就校准过 | **算命中** |
| `skipped-lowtier` | 返回了 hit 但全非权威、无一够格入库 | **不算命中**（诚实未校准，critic 会列进"未校准清单"）|

> 🚨 **不要用 covered 刷假覆盖**：只有 top hit 确属已在库/已覆盖才标 covered；判不准就标 lowtier。用 covered 把低质 slot 刷成绿，等于 `feedback_addresses_granularity` / `project_variant_reuse_gotchas` 记过的"假覆盖"坑——会让 thesis 时敏论断少了本该有的反方校准。`n_results=0`（WebSearch 返空）**不要**用本函数，那是限流，走 §B.2 串行重试。

---

## Step D：register 每条 hit（自动三档分流）

> **`register_web_search_batch` 返回 dict 的计数 key 是 `n_high`/`n_mid`/`n_low`/`n_dropped_low`/`drop_ratio`/`dropped_hits`/`failure_mode`（不是 `high`/`mid`）**——读它判救回时勿用 `r['high']`（会 KeyError/None）。单条版 `register_web_search_result` 才返回 `{mat_id, band, confidence, domain, domain_tier, filename}`。

```bash
python3 << 'EOF'
from prism.scripts.web_prescan import register_web_search_result

# 主 agent 把 Step C 的判断填进来：
result = register_web_search_result(
    slug='{slug}',
    variant='{variant}',
    query='{query}',
    url='{url}',
    title='{title}',
    snippet='{snippet}',
    addresses={addresses_list},
    full_text='{full_text or None}',
    confidence={confidence_or_None},
    domain_tier='{domain_tier_or_None}',
)
print(result)
# {mat_id, band, confidence, domain, domain_tier, filename}
# band='low' 则不入 manifest（mat_id=None），仅 log
EOF
```

**分流规则**（脚本内置）：
- `band='high'`（≥0.8）→ 写 `prism/topics/{slug}/inbox/web-search/{date}_{slug-of-title}.md` + 调 `add_material(source_type='web-search')`
- `band='mid'`（≥0.5）→ 同 high 但 `notes` 追加 `待用户确认`
- `band='low'`（<0.5）→ 跳过，不写文件不入 manifest

**救回闭环**：

```python
# 1. 第一遍 register（主 agent 没把握的 hit 不传 domain_tier）
summary = register_web_search_batch(slug=..., query=..., hits=[...], ...)
# 自动 stderr 摘要：
#   register_web_search_batch[01-prescan]: 8 hits → 入库 high=1 mid=0,
#   dropped=7 (invalid=0 low=7) drop_ratio=0.88
#   → drop_ratio≥0.5: 扫 dropped_hits + 调 extract_url_features 后决定救回
#   → 被丢 url (前 10)：...

# 2. drop_ratio > 0 时拿事实
if summary['drop_ratio'] > 0:
    from prism.scripts.web_prescan import extract_url_features
    dropped_urls = [d['url'] for d in summary['dropped_hits']
                    if d['reason'] == 'low-band']
    features = extract_url_features(dropped_urls)
    # features[url] = {in_whitelist, host, subdomain_tokens, tld_class,
    #                  path_is_pdf, path_announce_tokens, path_news_tokens,
    #                  path_depth, known_low_signal_host}

# 3. 主 agent 看 features + title + snippet，LLM 判断每条该不该救
#    判断要点（参考非规则化）：
#      - features['known_low_signal_host'] == True → 跳过（明确低信噪）
#      - features['path_is_pdf'] + path_announce_tokens 非空 → 大概率公司公告/年报，标 official
#      - features['subdomain_tokens'] 含 'ir'/'investor' → 公司 IR 页（已被 whitelist heuristic 抓但 host pattern 不匹时兜底）
#      - host 是已知行业垂直媒体（LLM 训练知识）→ 标 official
#      - 其余靠 title/snippet 内容判断

# 4. 一行救回（dedup 自动）
summary2 = register_web_search_batch(
    slug=..., query=..., addresses=..., triggered_by=...,
    hits=[
        {**dropped[i], 'domain_tier': 'llm-judged-official'}
        for i in 主_agent_判该救的索引
    ],
)
# 救回的会按 mid 入库 (0.7 > 0.5)
```

### 关于 runtime whitelist（2026-05-28 已删）

历史上有一个 `promote_to_whitelist` 沉淀机制（per-repo `_runtime_whitelist.yaml`），
设想"救回 ≥2 次同一 host 后 promote 到全局白名单跨 topic 复用"。**已删除**——
违反 H2 设计原则（主观分类应由 LLM 判，脚本只做 deterministic 黑名单），且无人
持续维护，沉淀的白名单会过期。每轮 prescan **重新走 H2 救回闭环**：主 agent 看
`dropped_hits` + `extract_url_features` 临场判 tier，**不沉淀**。重复一点 LLM
推理远比维护一个慢慢腐烂的白名单可靠。

---

## triggered_by 字段约定（Role α/β/γ 分流根据）

每次 `register_web_search_batch(triggered_by=...)` 传入的字符串会写入 mat 的
`search_meta.triggered_by`，下游按它决定 mat 进哪一档处理：

| triggered_by | Role | 下游处理（默认）|
|---|---|---|
| `00-prescan-baseline` / `00-prescan` / `01-prescan` | **α 背景校准** | **跳过** 03/04（baseline §六 + roadmap 已消化一次）|
| `02-step0` | **β 研究材料** | 与卖方研报/年报并列，正常进 03 → 04 |
| `03-extract` / `04-synth` / `05-critic` | **γ 即兴补料** | `register_web_search_batch` 自动产 inline finding + mark_processed（不再悬挂）|
| `06-daily-monitor` / `07-drilldown` | 监控/深挖 | 按场景另行处理 |

实现细节：`list_unprocessed` 与 `list_affected_outputs` 都默认
`exclude_triggered_by=('00-prescan-baseline','00-prescan','01-prescan')`，
保持两层一致。如确需对 Role α 强抽 finding，显式传 `exclude_triggered_by=()`。

---

## Step E：prescan 不碰 todo

> **prescan 只入库校准事实（标 `addresses=['scope']`）+ funnel + 写 log，不产生、不闭环任何 todo。** prescan（事实校准）与 todo（收某份具体文档）是两条不相干的管子——曾经的「列共享 K# 候选」（`suggest_todo_coverage_candidates` / 旧 `auto_resolve_todos`）已彻底删除。
>
> todo 闭环键是 **task/文档身份，不是 K#**（见 [`_autofetch_protocol.md`](_autofetch_protocol.md) 「产即收」+「闭环键」节 + memory `feedback_todo_closure_key`）。要收的文档由**产 todo 的阶段**当场 fetch、主 agent 按文档身份 `mark_todo_fetch` + `update_user_todo_status` 闭环——与本 prescan 无关。

---

## Step F：append 搜索日志 + 汇报

```bash
python3 << 'EOF'
from prism.scripts.web_prescan import append_search_log
# 整轮汇总后追加一条
append_search_log(
    slug='{slug}', variant='{variant}',
    query='{Step A 全部查询的汇总描述，例如 "01-prescan 全量"}',
    n_results=<本轮 hit 总数>,
    n_high=<band=high 数>, n_mid=<band=mid 数>, n_low=<band=low 数>,
    triggered_by='{01-prescan|02-step0|06-daily-monitor|07-drilldown}',
)
EOF
```

汇报模板：

```
✅ web-search 本轮完成（triggered_by={...}）
  查询数：N 条
  命中：H/M/L 三档 = X/Y/Z
  入库：X+Y 份（high 自动 / mid 待审）
  （prescan 只校准事实，不产生/不闭环 todo）
```

---

## stale / expired 维护（仅 06-daily-monitor 调）

```bash
python3 << 'EOF'
from prism.scripts.manifest import list_stale_web_search, list_expired_web_search
stale = list_stale_web_search('{slug}', '{variant}')   # >30 天
exp   = list_expired_web_search('{slug}', '{variant}') # >90 天
print(f'stale={len(stale)}, expired={len(exp)}')
# expired 条目：主 agent 用同样的 query 重跑 Step B-F，新 mat_id 会通过 dedup(filename) 合并 search_meta
EOF
```

UI 中 `stale_at < now` 显示黄色 chip；`expire_at < now` 显示红色 chip 提示待重扫。

---

## 关键纪律

1. **零幻觉**：URL/snippet 必须来自 WebSearch 工具实际返回；编造视为污染 manifest，需立即删除（手动 edit yaml）
2. **band='low' 不写文件**：避免 inbox 膨胀；低质量结果仅靠 `web_search_log.yaml` 留痕
3. **addresses 必填且语义分三态**（全局统一约定，02/03/04/05/07 都按此处理）：

   | 写法 | 语义 | 参与 K# 覆盖？ | 进 todo 覆盖**候选**？ | 何时用 |
   |---|---|---|---|---|
   | `[]` | **禁用**——不参与任何覆盖，等同未填 | ✗ | ✗ | 不允许；老条目遇到时按 `['background']` 升级 |
   | `['background']` | 背景资料、无具体 K# 攻打 | ✗ | ✗ | 02 登记的行业全景/历史背景；prescan scope query |
   | `['scope']` | 与本 topic 范围相关但无具体 K# 攻打 | ✗ | ✗ | 07 drilldown 在 thesis 形成前的探索；00 prescan baseline 优先 query |
   | `['K1', 'K6', ...]` | 攻打具体 K#（旧 topic 残留 Q# 仍兼容**读**，新 topic 不再产 Q#） | ✓ | ✓（仅出候选，不闭环） | 02/04/05/07 一般情况；roadmap 计划目标 |
   | `['K1@2026Q2-earnings', ...]` | 攻打 K# 的具体事件锚 | ✓ | ✓（事件锚命中，仍仅候选） | 财报季/监管事件/产品发布等高时效场景 |

   **三态判定流程**：(1) 资料有具体 K# 锚点 → 用 `['K#', ...]`（旧 topic 残留 Q# 仍可读，新 topic 不再产）；(2) 无 K# 但属于本 topic 知识背景 → `['background']`；(3) 与本 topic scope 相关但无 K# 且非背景 → `['scope']`。**禁止 `[]`**。

   > 注：材料的 `addresses` 标「这份料喂哪个命门」（内容覆盖 K#），与「某条 todo 是否收齐」是两回事——共享 K# 只让该 todo 进**候选**，闭环必须按 task/文档身份显式判（见 `_autofetch_protocol.md` 闭环键节）。

4. **不改 thesis**：web-search 走 manifest → 03-extract → 04-synthesize → critic-review 同条路径，禁止跳过 findings 直接改 thesis_v{N}.md

---

## 即兴 web-search 上限对照（按知识跨度递增）

整轮 prescan（01 Step 7 / 02 Step 0 / 06 Step 1b）走完整流程；**即兴 web-search** 是 03/04/05/07 等下游 workflow 在处理过程中临时调一次 WebSearch + 立即 `register_web_search_batch` 入库的简化路径，上限按 scope 设置：

| 触发位置 | scope | 上限（单位异） | 整轮累计 |
|---|---|---|---|
| 03 (per 单份资料处理) | 训练知识冲突点验证 | ≤3 query | ~30 query (10 份资料) |
| 04 (per 决策环合成) | 合成时数据缺失 | ≤5 query/环 | ~35 query (case 6 环 + primer；sidecar 机械免搜) |
| 05 (per critic 轮) | 反方论据缺口兜底 | ≤5 query × 5-10 hit | ≤50 hit/轮（一次性） |
| 07 (per drilldown) | 专项深挖 | 按需，无硬上限 | drilldown 本就是 deep dive |

**单位说明**：03/04 计 query 数（避免对话被 hit 列表淹没），05 计 hit 总数（critic 反方需要密度，按 hit 算更直接）。**04 的计量单位是「决策环」不是「产出文件」**——单份 case 是 6 环决策链（≈ 旧 8 份维度的内容量），产出文件数（case+sidecar+primer，大小悬殊）已不是有意义的内容单位；按环算 ≤5/环、累计 ≈35，内容守恒。三处都是 per-N scope，不能跨 workflow 相加比较——例如"05 ≤50 hit 比 04 ≤5 query 宽松"是错觉，按整轮累计实际同量级。

**升级到 sub-agent 的判定**：超 scope 上限 → 跳出即兴路径，按 `_subagent_deep_search.md` dispatch sub-agent 并行深挖（参 03 Step 2.4b / 05 Step 6.5b）。
