# Workflow 09 — Industry → Arenas 选拔

**触发**: industry topic 完成 04-synthesizing（stage 为 04-synthesizing）
**定位**: 从行业研究中识别细分 arena，按 6 维度评分并强制分流
**产出文件**: `prism/topics/{slug}/outputs/09_industry_to_arenas.md`

---

## Step 1：前置检查

```bash
python -c "
from prism.scripts.topic import read_topic
data = read_topic('{slug}', '{variant}')
assert data['type'] == 'industry', '仅 industry topic 可运行此 workflow'
assert data['stage'] in ('04-synthesizing', '09-arena-shortlist'), '请先完成 01-08 合成'
print('前置检查通过')
"
```

---

## Step 2：读取已有产出并提取 arena 信号

读取以下文件：
- `outputs/01_business_panorama.md`
- `outputs/02_cycle_positioning.md`
- `outputs/03_narrative_ecology.md`
- `outputs/04_implied_expectations.md`
- `outputs/06_risk_blindspots.md`
- `outputs/07_decision_kit.md`
- 所有 `findings_mat_*.md`

从以上内容中提取至少 **5 个细分 arena**。

---

## Step 3：对每个 arena 进行 6 维度评分

| 维度 | 说明 | 评分标准 (1-5) |
|------|------|----------------|
| 利润池规模 | 当前及 5 年期 arena 总利润（亿元，区间） | 1: <10亿, 5: >1000亿 |
| 增速预期 | 3 年 CAGR | 1: <5%, 5: >30% |
| 竞争结构 | CR3 / 是否有自然垄断 / 是否同质化 | 1: 完全竞争, 5: 自然垄断 |
| 估值水位 | 当前 PE/PS 相对该 arena 历史 + 全球 peer | 1: 历史高位, 5: 历史低位 |
| 周期位置 | 早期成长 / 中段加速 / 晚期分化 / 成熟饱和 | 1: 衰退/饱和, 5: 早期成长 |
| 综合评分 | 以上维度加权平均 | 1-5 |

---

## Step 4：强制三档分流

**必须**将至少 1 个 arena 分到每一档：

1. **深挖档**：综合评分 ≥ 4，或有强催化剂
2. **观察档**：综合评分 2-3，或有不确定性
3. **淘汰档**：综合评分 ≤ 2，或有硬伤

对每一档：
- **深挖档**：写出入选理由（≤100字）+ 预期关键洞见 + 预填 L4 狩猎问题（2-3 个）+ 建议的 arena slug
- **观察档**：写出暂不深挖理由 + 升档触发条件 + 监控指标 1-2 个
- **淘汰档**：写出淘汰理由（≤50字）+ 复活条件（如有）

---

## Step 4.5：填写 data_freshness

在 frontmatter 写入：
- `data_freshness`: 用到的最晚数据所在期（季度/月份）
- `data_freshness_basis`: 该期来自哪份 finding

---

## Step 5：写入产出文件

使用模板 `prism/templates/industry_to_arenas.md.tmpl`，写入 `outputs/09_industry_to_arenas.md`。

**强制要求**：
- 至少 5 个 arena
- 每档至少 1 个
- 每个数字注明来源（"来自 01_panorama p3" 或 "训练知识假设"）

---

## Step 6：询问用户是否创建 stub arena topic

对每个深挖档 arena：

```bash
python -c "
from prism.scripts.topic import create_topic, read_topic
parent = read_topic('{slug}', '{variant}')
geo = parent.get('scope', {}).get('geo', 'cn')  # 从父 topic 继承 geo
create_topic(
    slug='{geo}-{arena_slug}',
    display_name='{arena_display_name}',
    topic_type='arena',
    question='{arena_question}',
    geo=geo,
    depth='deep',
    variant='{variant}',
    parent_topic='{slug}',
)
"
```

---

## Step 7：更新 state 并追加到 living feed

```bash
python -c "
from prism.scripts.topic import set_output_status, set_stage, set_next_actions
set_output_status('{slug}', '09_industry_to_arenas', 'fresh', '{variant}', version=1)
set_stage('{slug}', '09-arena-shortlist', '{variant}')  # 或 'done'
set_next_actions('{slug}', ['为深挖档创建 arena topic', '或进入日常监控'], '{variant}')
"
```

将 "09-industry-to-arenas 完成" 摘要追加到 `08_living_feed.md`。
