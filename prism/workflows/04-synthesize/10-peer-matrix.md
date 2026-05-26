# Workflow 10 — Arena → Peer Matrix 横向矩阵

**触发**: arena topic 完成 01-08 产出后自动触发（由 `_shared.md` 收尾逻辑判断 topic_type=arena）；也可手动说「生成产出 10」
**定位**: 识别 arena 内候选公司，拉取财务数据，输出对比矩阵
**产出文件**: `prism/topics/{slug}/outputs/10_peer_matrix.md`

---

## Step 1：前置检查

```bash
python -c "
from prism.scripts.topic import read_topic
data = read_topic('{slug}', '{variant}')
assert data['type'] == 'arena', '仅 arena topic 可运行此 workflow'
assert data['stage'] in ('04-synthesizing', '10-peer-matrix'), '请先完成 01-08 合成'
print('前置检查通过')
"
```

---

## Step 2：读取已有产出并提取候选公司

**必读**（决定 Tier 排序的依据，不可跳）：
- `outputs/_synthesis_brief.md` — K# 校准结论（v0→v1 thesis 强度调整、各 K# 翻盘/支持的 mat_id 清单）。**Tier 排序必须以 brief 的 K# 校准为锚**：被 K# 翻盘的公司不能进 shortlist；K# 强支持的公司应优先进 shortlist。如果 brief 不存在（资料 <10 跳过 brief 生成），在 Step 4 评分备注里写"无 brief 校准，纯 findings 推断"

参考：
- `outputs/01_business_panorama.md`
- `outputs/02_cycle_positioning.md`
- `outputs/03_narrative_ecology.md`
- `outputs/04_implied_expectations.md`
- 所有 `findings_mat_*.md`

从以上内容中提取至少 **5 家候选公司**。

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

| 公司 | Ticker | 业务结构 | 收入规模 | 3Y ROIC | 毛利率 | 资产负债率 | 当前 PE | 历史 PE 区间 | 技术路线 | 客户结构 | 管理层信号 | 综合 | 短名单 |
|------|--------|---------|---------|--------|--------|-----------|--------|------------|---------|---------|-----------|------|--------|
| {name} | {ticker} | {一句话} | {亿} | {%} | {%} | {%} | {x} | {x-y} | {主线} | {B/C/政府} | 看好/中性/警示 | 1-5 | ✓/✗/观察 |

**评分逻辑说明**（≤5句话）：
- 权重组合方式
- hard filter（不达标直接淘汰）
- 软评分维度

---

## Step 4.5：填写 data_freshness

在 frontmatter 写入：
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

## Step 6：写入产出文件

使用模板 `prism/templates/peer_matrix.md.tmpl`，写入 `outputs/10_peer_matrix.md`。

---

## Step 6.5：生成 sidecar YAML（machine-readable 快照）

写入文件：`prism/topics/{slug}/{variant}/outputs/10_peer_matrix.yaml`

从刚才写的 markdown 中提取以下字段。**数字不加引号，缺失用 null，tier 只能是 shortlist / watch / eliminated。**

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

## Step 7：询问用户是否创建 stub company topic

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

也读 `prism/topics/{slug}/{variant}/outputs/thesis_v{cur_v}.md` 全文 + 该公司在 10_peer_matrix.md 中的"入选理由 / 预期 thesis"段落作为 narrowing 输入。

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

---

## Step 8：更新 state 并追加到 living feed

```bash
python -c "
from prism.scripts.topic import set_output_status, set_stage, set_next_actions
set_output_status('{slug}', '10_peer_matrix', 'fresh', '{variant}', version=1)
set_stage('{slug}', '10-peer-matrix', '{variant}')  # 或 'done'
set_next_actions('{slug}', ['为深研档创建 company topic', '或进入日常监控'], '{variant}')
"
```

将 "10-peer-matrix 完成" 摘要追加到 `08_living_feed.md`。

---

## Step 9：仪表盘自动刷新（修 S5）

`set_output_referenced_mats('10_peer_matrix', ...)` 已自动 fire-and-forget 触发 dashboard 异步重建，**无需手跑** `python -m prism.scripts.dashboard`。后台失败留痕在 `prism/logs/dashboard_auto.log`。
