# Workflow 10 — Arena → Peer Matrix 横向矩阵

**触发**: arena topic 完成 04-synthesizing（stage 为 04-synthesizing）
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

读取以下文件：
- `outputs/01_business_panorama.md`
- `outputs/02_cycle_positioning.md`
- `outputs/03_narrative_ecology.md`
- `outputs/04_implied_expectations.md`
- 所有 `findings_mat_*.md`

从以上内容中提取至少 **5 家候选公司**。

---

## Step 3：拉取财务 + 行情数据

对每家有 ticker 的公司，调用 wrapper（自动判断本地 DB 是否有数据，无则拉取）：

```bash
python -c "
from prism.scripts.financial_data import get_peer_comparison_data
from prism.scripts.market_data import get_quote

# 替换为 peer slug 列表
peers = ['cn-guobo-electronics', 'cn-shanghai-hanxun']
fin_data = get_peer_comparison_data('{slug}', '{variant}', peers)
for slug, d in fin_data.items():
    print(f'{slug}:', d)

# 行情数据（当前 PE）
q = get_quote('{slug}', '{variant}')
print(f'当前 PE(TTM): {q.get(\"pe_ttm\")}, PB: {q.get(\"pb\")}')
"
```

如果没有可用数据，注明"训练知识估算"或"数据缺失"。

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
