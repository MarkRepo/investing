# Workflow 00 实战评审 — 荣昌生物 (cn-rongchang-bio-688331)

**日期**：2026-05-26
**变体**：claude-opus-4-7
**触发**：用户「prism 开始研究 荣昌生物」
**结论**：workflow 00 整体可走通，但**有 5 个明确缺陷 + 3 个可优化点**应在下一轮 workflow 重构中处理。

---

## 一、明确缺陷（必须修）

### H1: `create_topic(type='company')` 不强制 ticker 参数

**现象**：workflow 00 Step 1 文档明确说"如果是 company 类型，必须确认 ticker"，但 `prism.scripts.topic.create_topic` 的 ticker 是 `Optional[str] = None`，不传也能建 topic（我本次第一遍就忘传，事后手动 patch yaml 补 SSE_688331 + secondary HKEX_09995）。

**修法**：在 `create_topic` 内加 `if topic_type == 'company' and not ticker: raise ValueError(...)`；同时 workflow 00 Step 4 模板应该把 ticker 字段明确列出（当前模板代码块不含 ticker= 参数行）。

**影响**：后续 `build_search_queries` 的 company-event 系列依赖 ticker；漏传后这部分 query 直接没法生成。

---

### H2: `register_web_search_result` 对非 whitelist 源默认 confidence=0.4 直接 funnel low，导致大量优质来源被丢弃

**现象**：本次 P0 6 条 query 第一轮入库时，**每条 query 6-7 个 hit 平均只有 1 个高质 入库**，其余 5-6 个全部被判 low band 丢弃。原因是 `WHITELIST_DOMAINS` 是固定列表，**新浪财经 (`sina.com.cn` 不在 whitelist)、医药魔方 bydrug.pharmcube.com、ApexOnco、FierceBiotech、智慧芽 zhihuiya.com、远瞻慧库 baogaobox、东方财富 emcreative.eastmoney.com 等行业核心源都不在 whitelist**，自动落入 `other` 档（confidence=0.4 → band=low → 不入库）。

我事后用第二轮调用，**主 agent 显式给每条 hit 标 `domain_tier='llm-judged-official'`**，把这些源全部抢救入库（21 条 mid 入库）——但这是补救，**没有主 agent 警觉的话，第一轮真的会丢失 ~80% 优质素材**。

**修法（短期）**：在 `_web_prescan_shared.md` Step C 表格里加一条**显眼警告**：

> ⚠️ 主 agent 必须**主动对每条非 whitelist hit 判断**——如果是行业垂直媒体、券商研报平台、官方公告托管站等权威源，**必须显式传 `domain_tier='llm-judged-official'`**，否则会自动落 other(0.4) → low → 丢弃。

**修法（中期）**：扩充 `WHITELIST_DOMAINS`，按行业类别新增：
- 医药行业：`pharmcube.com`, `bydrug.pharmcube.com`, `phirda.com`, `pharnexcloud.com`, `zhihuiya.com`, `synapse.zhihuiya.com`, `fxbaogao.com`, `baogaobox.com`, `spdbi.com` 等
- 海外医药：`fiercebiotech.com`, `endpts.com`, `oncologypipeline.com`, `fiercepharma.com`, `biopharmadive.com` 等
- 中国财经补充：`sina.com.cn`（不仅 finance 子域）, `pharnexcloud.com`
- 自媒体公众号转载：`m.mp.oeeee.com` (南方都市报), `m.sohu.com`

**修法（长期）**：让 `register_web_search_batch` 接收一个"自动判 official 关键词列表"——如 url 含 `gov.cn / hkex / cninfo / official` 或 title 含"公告/年报/季报"自动升 official。

**影响**：当前 prescan 对**医药/科技/生物**类 topic 严重偏向只接受财经 mainstream 源，丢失行业 vertical 报道。

---

### H3: `build_search_queries` 的 scope query 直接拼接 `display_name + question` → query 字符串近 100 字，WebSearch 不友好

**现象**：本次默认模板 prescan 生成的 scope query 是：
```
荣昌生物 (RemeGen, SSE 688331) 荣昌生物作为中国领先的ADC+自免双管线创新药企业，全维度覆盖：商业化兑现节奏、海外授权回流、研发管线突破、竞争格局、财务/估值，最终给出是否值得长期持有的投资判断
```
**总长 ~80 字**，远超 WebSearch 的最佳 query 长度（5-15 词最佳）。我跳过这条直接用拆分关键词（"最新公告 2026"/"监管处罚"等）。

**修法**：`build_search_queries` 应该把长 question 字段截取关键名词短语作为 query 而非全句拼接；或者引入 LLM tool（不调 API，让主 agent 提示）把 question 改写成 search-friendly 形式。

**影响**：当前 scope query 通常返回的是低相关、宽泛的"公司简介"页面，没有信息价值。

---

### M1: `topic.yaml` 没有 `secondary_ticker` 字段标准化，AH 双重上市公司无处放第二代码

**现象**：荣昌生物 A 股 SSE_688331 + H 股 HKEX_09995，我把 secondary_ticker 塞进 scope dict，但这是**手动 patch**——topic schema 没有此字段约定，后续 workflow 想用第二 ticker 拉港股数据时不知道去哪取。

**修法**：在 `create_topic` 增加可选 `secondary_ticker` 参数，并写进 yaml schema；行情 / 财务 adapter（如 akshare）也需要兼容查 H 股代码。

**影响**：港股 09995 估值/南向资金/外资行为对 thesis 很重要，无 secondary_ticker 后续 06-daily-monitor 无法自动拉 H 股数据。

---

### M2: workflow 00 Step 4.5a 主 agent 操作流程文档缺少"批量 query 并行 + 批量入库"提示

**现象**：Step 4.5a 文档建议**逐条 WebSearch + 逐条 register**，但实战中 baseline 第五节常有 10-15 条 query，**并行 WebSearch 6-7 条可显著节省时间**（本次我并行执行后总耗时减少 ~60%）。文档没有提示这点。

**修法**：在 Step 4.5a 文档加一段"性能提示"：
> 13 条 query 可分批 6+6+1 并行 WebSearch（在单条消息内调多个 WebSearch tool block），再批量 register_web_search_batch；总耗时显著优于串行。注意 batch 内 query 上下文要错开（避免 WebSearch 缓存命中错位）。

---

## 二、可优化点（建议改）

### S1: `register_web_search_batch` 的 `n_high/n_mid/n_low` 返回值统计**不区分"新入库"和"重复跳过"**

**现象**：本次 Q2 补登时显示 `high=0 mid=2 dup=1`——dup=1 那条原本是 high 入库的 xueqiu.com hit，重传时被去重跳过；但 mid 统计里 2 条是真新入库，不易直接看出"本轮实际净新增 mat 数"。

**修法**：返回值增加 `n_new_mid / n_new_high` 字段；或在打印时明确区分"新入"vs"刷新"。

---

### S2: thesis_v0 写作过程中主 agent **没有强制 cite 校准后的 mat_id**

**现象**：workflow 00 Step 5.0 说"thesis 财务数字必须引用 prescan 入库的 web-search 资料中数字"，但**校验机制是软的**——主 agent 写完不强制 grep mat_id；只在 K# coverage 上有自检。本次我在 thesis 各支持理由后用 `[refs: mat-xxx]` 形式但不是逐 fact 必 cite。

**修法**：增加 `verify_thesis_citations(slug, variant, version)` 脚本——扫 thesis_v{N}.md 中所有数字（用 regex 抽取财务数字、百分比、市值等）并要求紧邻 cite mat-xxxx 或 fact-NN；不达标 raise warning。

---

### S3: baseline 第六节回写格式 vs workflow 00 Step 4.5c 模板**字段命名不一致**

**现象**：Step 4.5c 文档示例用三个二级标题 `### 被推翻 / ### 被验证 / ### 仍未校准`，但 `_baseline_knowledge.md` 模版第六节示例也是同样三个但**缺少一个表格汇总**（我自己加的"关键事实方向反转汇总"表）和**缺少"训练完全遗漏的重大新事实"分类**（本次我用 `🟢 训练完全遗漏的重大新事实（增补）`）。

**修法**：在 `_baseline_knowledge.md` 模版第六节扩充为四档：
- 🔴 被推翻
- 🟡 被验证
- 🟢 训练完全遗漏的新事实（增补）
- ⚪ 仍未校准
- 表格：关键事实方向反转汇总（旧 vs 新 vs 影响）

四档比三档更能捕获 LLM 训练知识的全部偏差类型。

---

## 三、本轮工作量统计

| 阶段 | 耗时近似 | 入库量 |
|---|---|---|
| 4.3 baseline 写作 | ~3 min | 28 条 fact + 13 条 query |
| 4.5a 优先 query (13 条) | ~6 min (两轮：首发 + 补登) | ~46 份 mat (high 4 + mid 42) |
| 4.5b 默认 prescan (5 条) | ~3 min | ~26 份 mat (high 5 + mid 21) |
| 4.5c 校准回写 | ~3 min | 第六节 4 档 + 反转表 |
| 5.0 thesis_v0 | ~4 min | 5 段 + 5 K + Coverage 自检 |
| 6-7 登记 + todos | ~1 min | 8 条 user_todos |
| **合计** | **~20 min** | **~92 份 mat + 8 todos + thesis_v0** |

对比训练知识"独立工作"，prescan 把"过时认知"差不多反转了 7-8 条核心事实（包括完全不知道的 RC148/AbbVie BD），thesis_v0 方向感比训练知识独立写更准。

---

## 四、与历史评审的关联

- 验证 [feedback_thesis_after_prescan.md] 的判断："thesis_v0 之前必须先 web-prescan" — 本次若跳过 prescan，会把"现金紧张+研发亏损+RC48终止"作为 thesis 主线，完全错过 BD 回流 + 商业化兑现的真实拐点
- 验证 [feedback_gap_detector_checkpoints.md]：workflow 02-06 起步跑 gap_detector 是对的，本次 00 stage 暂未到此节点但 baseline 第六节已经在做类似事
- 与 [feedback_subagent_model.md] 一致：本轮 prescan 主 agent 直接做，未 dispatch sub-agent（数据规模 13+5 query 在主 agent 即兴范围内）

---

## 五、后续 workflow 01 应注意

- 直接基于 thesis_v0 的 K1-K5 构造 roadmap，不要重新发散
- L4 hunting questions 应聚焦：(a) RC148 全球管线对照 (b) RC18 IgAN 竞品 (c) BD 兑现条款 (d) NCT05911295 状态 (e) 关联采购 + 治理
- 01-prescan 应特别监控：AbbVie 2026Q2 earnings call / Pfizer disitamab 段落 / 控股股东减持窗口 / IgAN BLA 受理
