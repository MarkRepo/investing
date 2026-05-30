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

行情（当前 PE/PB）走 market_data ticker API：

```bash
python -c "
from prism.scripts.market_data import get_quote_by_ticker  # 见下方注释
# 该 API 不存在则跳过 live PE，用研报里的 PE 表代替
"
```

> 注：如果 `market_data.get_quote_by_ticker` 还没实现（截至当前），仍只能走 slug 模式或从研报数据 fallback。后续在批次 3 中补。

需要的指标：
- 收入规模（亿元，最近财年） — 从 financial_data
- 3 年平均 ROIC — 从 financial_data
- 毛利率 — 从 financial_data
- 资产负债率 — 从 financial_data
- 当前 PE — 从 market_data
- 历史 PE 区间 — 从 market_data（52周高低 ÷ EPS）或训练知识估算

---

## Step 4：构建对比矩阵

至少 **5 家候选公司**（来源：findings + 决策链① 卡位判断）：

| 公司 | Ticker | 业务结构 | 收入规模 | 3Y ROIC | 毛利率 | 资产负债率 | 当前 PE | 历史 PE 区间 | 技术路线 | 客户结构 | 管理层信号 | 综合 | 短名单 |
|------|--------|---------|---------|--------|--------|-----------|--------|------------|---------|---------|-----------|------|--------|
| {name} | {ticker} | {一句话} | {亿} | {%} | {%} | {%} | {x} | {x-y} | {主线} | {B/C/政府} | 看好/中性/警示 | 1-5 | ✓/✗/观察 |

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
)
"
```

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
