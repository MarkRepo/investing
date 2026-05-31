# Arena → Peer Matrix 规范（财务横比 / 矩阵 / 分流 / sidecar / stub）

> **工具规范，非独立产出步骤。** arena 的公司选拔已折进 `_arena_funnel.md` 决策链环④（peer 财务横比矩阵）+ 环⑥（三档分流 + 落 sidecar + 建 company stub），叙事写进 `a_arena_case`。本文件只作 `_arena_funnel.md` **逐字引用**的工具规范：环①/②/④引 **Step 3**（financial_data 拉数口径）+ **Step 4**（矩阵维度）、环⑥引 **Step 6.5**（sidecar schema）+ **Step 7/7b**（company stub 创建 / 继承 thesis_v0）。查规范，不照搬结构。
>
> **不再产出**独立 markdown（旧 `10_peer_matrix.md`）；sidecar `10_peer_matrix.yaml` 是 dashboard 竞技场层唯一契约。Tier 排序以 `_synthesis_brief.md` 的 K# 校准为锚（funnel Step 1 已读 brief + thesis）；brief 不存在时在评分备注写"无 brief 校准，纯 findings 推断"。

---

## Step 3：拉取财务 + 行情数据

**默认走 ticker 模式**（不需要 stub company topic 已建）。每家候选公司只要在 findings 里有股票代码（A 股 / 港股 / 美股），都能直接拉数据：

```bash
python -c "
from prism.scripts.financial_data import get_peer_comparison_data_by_tickers

# 列出所有候选 peer：A 股用 SSE/SZSE/BSE，美股用 NASDAQ/NYSE，港股用 HKEX
peers = [
    {'key': '利元亨', 'ticker': '688499', 'market': 'SSE'},
    {'key': '海目星', 'ticker': '688559', 'market': 'SSE'},
    {'key': '联赢激光', 'ticker': '688518', 'market': 'SSE'},
    {'key': '先导智能', 'ticker': '300450', 'market': 'SZSE'},
]
data = get_peer_comparison_data_by_tickers(peers)
for k, d in data.items():
    print(f'{k}:', d)
"
```

返回 `{key: {ticker, revenue, gross_margin, roic_3y_avg, debt_to_equity}}`，自动 freshness 检查 + akshare/yfinance 拉取。

如果某家 peer 没有 ticker（如卫蓝/清陶等一级市场公司），用训练知识估算 + 注明"非上市，估算"。

**已注册成 stub company topic 的 peer**（如父级 industry 选拔后建好的 stub），可走 slug 模式：

```bash
python -c "
from prism.scripts.financial_data import get_peer_comparison_data
data = get_peer_comparison_data('{slug}', '{variant}', ['cn-leadex-300450', 'cn-yuanli-heng-688499'])
for k, d in data.items():
    print(k, d)
"
```

行情（当前 PE/PB/PS/市值）走 market_data ticker 级 API（**已实现，F13**）：

```bash
python3 -c "
from prism.scripts.market_data import get_valuation_context_by_tickers
print(get_valuation_context_by_tickers([
    {'ticker': '600276', 'market': 'SSE', 'name': '恒瑞'},
    {'ticker': '01801', 'market': 'HKEX', 'name': '信达'},   # 港股经 yfinance 路由，HKD 计价
]))
"
```

> peer 只有 ticker（还没注册 company topic）也能拿倍数——`get_quote_by_ticker(ticker, market)` 单家 / `get_valuation_context_by_tickers([...])` 批量。底层与 get_quote 同链路（US/HKEX→yfinance、CN→akshare）；**港股盲区已闭**（HKD 计价）。取不到的会显式标 *(取不到)*，不要当成"没源"——核 ticker/market 或用研报 PE 表补，并在对话里 log。

需要的指标（**通用财务脊柱，best-effort；不可比的项按 arena 业务类型替换，不要硬填会误导的数字**）：
- 收入规模（亿元，最近财年） — 从 financial_data
- 3 年平均 ROIC — 从 financial_data
- 毛利率 — 从 financial_data
- 资产负债率 — 从 financial_data
- 当前 PE — 从 market_data
- 历史 PE 区间 — 从 market_data（52周高低 ÷ EPS）或训练知识估算

> ⚠️ 上面这套默认贴制造/实业。**当 arena 业务类型不同，主 agent 按领域换掉不适用项**（这是领域判断，不写死）：银行/保险→净息差·ROE·不良率·拨备覆盖·偿付能力；未盈利 biotech→现金 runway·管线阶段·peak sales 预估·授权回流（PE / 收入规模 / 毛利率 此时无意义，标 *(不适用)*）；平台/SaaS→GMV·take-rate·NDR·获客成本；资源/矿业→储量·品位·完全成本·产量。脊柱列（收入 / ROIC / 负债 / 估值倍数）凡可比就保留，不可比就换。

---

## Step 4：构建对比矩阵

至少 **5 家候选公司**（来源：findings + 决策链① 卡位判断）：

列分两段：**财务脊柱**（按上方 best-effort 取，不可比则换领域对应指标）+ **诊断轴**（`{诊断轴1/2}` 由主 agent 按 arena 选最有区分度的 1-2 个，**不套固定"技术路线/客户结构"**）：

| 公司 | Ticker | 业务结构 | 收入规模 | 3Y ROIC | 毛利率 | 资产负债率 | 当前 PE | 历史 PE 区间 | {诊断轴1} | {诊断轴2} | 管理层信号 | 综合 | 短名单 |
|------|--------|---------|---------|--------|--------|-----------|--------|------------|-----------|-----------|-----------|------|--------|
| {name} | {ticker} | {一句话} | {亿} | {%} | {%} | {%} | {x} | {x-y} | … | … | 看好/中性/警示 | 1-5 | ✓/✗/观察 |

> 诊断轴示例（**按 arena 选，不是全填**）：创新药→管线阶段·靶点差异化·BD 记录；锂电/芯片→技术路线·产能·良率；银行→资产质量·区域·零售占比；平台→品类·变现率·网络效应。财务脊柱列遇银行/未盈利 biotech 等按上方 ⚠️ 替换。

**评分逻辑说明**（≤5句话）：
- 权重组合方式
- hard filter（不达标直接淘汰）
- 软评分维度

---

## Step 4.5：填写 data_freshness

写进 sidecar（及 case frontmatter）：
- `data_freshness`: 用到的最晚数据所在期（季度/月份）
- `data_freshness_basis`: 该期来自哪份 finding

---

## Step 5：强制三档分流

**必须**将至少 1 家公司分到每一档：

1. **深研档**（短名单 ✓）：综合评分 ≥4，或有强催化剂
2. **观察档**：综合评分 2-3，或有不确定性
3. **淘汰档**：综合评分 ≤2，或有硬伤

对每一档：
- **深研档**：写出入选理由（业务卡位+估值+催化剂，3句话）+ 预期 thesis + 建议的 company slug
- **观察档**：写出暂不深研理由 + 触发深研条件
- **淘汰档**：写出淘汰主因 + 是否进入 quarantine

---

## Step 6.5：生成 sidecar YAML（machine-readable 快照）

写入文件：`prism/topics/{slug}/{variant}/outputs/10_peer_matrix.yaml`

从决策链④/⑥ 提取以下字段。**数字不加引号，缺失用 null，tier 只能是 shortlist / watch / eliminated。**

```yaml
slug: {slug}
variant: {variant}
topic_type: arena
display_name: {display_name}
generated: {ISO8601 timestamp}
data_freshness: {date}

companies:
  - name: {公司名}
    ticker: {e.g. TSM or SZSE_001270}   # 空则 ""
    score: {float 1-5}
    tier: shortlist                      # shortlist / watch / eliminated
    topic_created: false                 # 是否已创建 company topic
    topic_slug: null                     # 实际创建的 topic slug
    thesis_one_liner: {一句话 thesis}    # shortlist 档必填，其他 null
    upgrade_triggers: []                 # watch 档：触发深研条件列表
    quarantine: false                    # eliminated 档：是否进入 quarantine
  # 追加更多公司...

cluster_tags: [{tag1}, {tag2}]
```

```bash
python -c "
from pathlib import Path
import yaml

content = '''
{上面填好的 yaml 内容}
'''
path = Path('prism/topics/{slug}/{variant}/outputs/10_peer_matrix.yaml')
path.write_text(content, encoding='utf-8')
print('10 sidecar 写入完成')
"
```

---

## Step 7：为深研档创建 stub company topic

对每个深研档公司：

```bash
python -c "
from prism.scripts.topic import create_topic, read_topic
parent = read_topic('{slug}', '{variant}')
geo = parent.get('scope', {}).get('geo', 'cn')  # 从父 topic 继承 geo
create_topic(
    slug='{geo}-{company_slug}',
    display_name='{company_display_name}',
    topic_type='company',
    question='{company_question}',
    geo=geo,
    depth='deep',
    variant='{variant}',
    parent_topic='{slug}',
    ticker='{ticker}',
    short_name='{company_short_name}',         # 简称（dashboard 显示用）
    search_terms=['{词1}', '{词2}', '{词3}'],  # 见下 ⚠️：company question >25 字时必填
)
"
```

> ⚠️ **必传 `search_terms`（否则 create_topic 直接 raise）**：`question` >25 字时 create_topic 强制要求 `search_terms`（`list[str]`，每项 ≤15 字，≥1 非空）。company stub 问题常 >25 字 → 漏传会崩。手挑 3-5 个检索词（公司名/核心产品/赛道），别整句塞。

### Step 7b：为 stub company 写入继承自父 thesis 的 thesis_v0.md

create_topic 完成后，立即为 stub 写 thesis_v0.md。

1. 读父 arena thesis：

```bash
python -c "
from prism.scripts.outputs import extract_killer_questions
from prism.scripts.topic import read_topic
parent = read_topic('{slug}', '{variant}')
cur_v = (parent.get('thesis') or {}).get('current_version', 0)
ks = extract_killer_questions('{slug}', '{variant}', cur_v)
print('父 arena K# 数量:', len(ks))
for k in ks: print(' -', k[:80])
"
```

也读 `prism/topics/{slug}/{variant}/outputs/thesis_v{cur_v}.md` 全文 + 该公司在决策链④矩阵中的"入选理由 / 预期 thesis"段落作为 narrowing 输入。

2. **收窄到公司视角**：从父 arena K# 中挑出与该公司直接相关的 2-4 条（重写为针对本公司的版本，例如「行业是否能跑出 OEM 模式」收窄为「{公司} 能否拿下 OEM 客户份额」）；补 1-2 条公司专属 K#（管理层兑现 / 单一大客户依赖 / 估值锚等）。

3. 按 thesis_v0 四段式（① 核心 thesis + 强度评分 / ② 支持理由 / ③ 反方观点 / ④ K1-K5；**不单列 V# 验证项**，与 workflow 00 Step 5.0 一致）写入 `prism/topics/{geo}-{company_slug}/{variant}/outputs/thesis_v0.md`。**核心 thesis ≤120 字**，强度按父 arena 强度 -1 起估。每条 K# 末尾标注「(继承自父 K#)」或「(新增)」。

4. 落入 stub topic.yaml：

```bash
python -c "
from prism.scripts.topic import set_thesis
set_thesis(
    slug='{geo}-{company_slug}',
    variant='{variant}',
    version=0,
    summary='{≤120字 company 视角 thesis}',
    stage_set_at='00-init-from-parent',
)
"
```
