# Workflow 09 — Industry → Arenas 选拔

**触发**: industry topic 完成 01-08 产出后自动触发（由 `_shared.md` 收尾逻辑判断 topic_type=industry）；也可手动说「生成产出 09」
**定位**: 从行业研究中识别细分 arena，按 6 维度评分并强制分流
**产出文件**: `prism/topics/{slug}/{variant}/outputs/09_industry_to_arenas.md`

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
- **深挖档**：写出入选理由（≤100字）+ 预期关键洞见 + 预填 L4 狩猎问题（2-3 个）+ 建议的 arena slug + **必填 upgrade_triggers / monitor_metrics**（深挖期间也需要监控触发器；可写"已在 stub topic L1-L4 跟踪，无父级独立触发"但不能留空 list）
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

### Step 6b：为 stub 写入继承自父 thesis 的 thesis_v0.md

create_topic 完成后，**立即**为 stub 写 thesis_v0.md，省去用户后续推进时再走 00-research-topic 的麻烦。

1. 读父 topic 当前 thesis：

```bash
python -c "
from prism.scripts.outputs import extract_killer_questions
from prism.scripts.topic import read_topic
parent = read_topic('{slug}', '{variant}')
cur_v = (parent.get('thesis') or {}).get('current_version', 0)
ks = extract_killer_questions('{slug}', '{variant}', cur_v)
print('父级 K# 数量:', len(ks))
for k in ks: print(' -', k[:80])
"
```

也读 `prism/topics/{slug}/{variant}/outputs/thesis_v{cur_v}.md` 全文用作 narrowing 参考。

2. 在对话里**收窄到 arena 视角**：从父 K# 中挑出与该 arena 直接相关的 2-4 条，重写措辞使其聚焦本 arena（公司/路线/客户）；如父 K# 不足，补 1-2 条 arena 专属的待验证假设。

3. 按 thesis_v0 四段式（① 核心 thesis + 强度评分 / ② 支持理由 / ③ 反方观点 / ④ K1-K5；**不单列 V# 验证项**，与 workflow 00 Step 5.0 一致）写入 stub 的 `prism/topics/{geo}-{arena_slug}/{variant}/outputs/thesis_v0.md`。**核心 thesis ≤120 字**，强度先按父级强度 -1 起估（继承可信度低于亲自验证）。每条 K# 末尾标注「(继承自父 K#)」或「(新增)」。

4. 落入 stub 的 topic.yaml：

```bash
python -c "
from prism.scripts.topic import set_thesis
set_thesis(
    slug='{geo}-{arena_slug}',
    variant='{variant}',
    version=0,
    summary='{≤120字 arena 视角 thesis}',
    stage_set_at='00-init-from-parent',
)
"
```

> 跳过条件：父 thesis 完全不可拆分到 arena 维度（极少见）。此时 stub 仍创建，但不写 thesis_v0，由用户日后手动走 00-research-topic。

---

## Step 6.5：生成 sidecar YAML（machine-readable 快照）

写入文件：`prism/topics/{slug}/{variant}/outputs/09_industry_to_arenas.yaml`

从刚才写的 markdown 中提取以下字段。**数字不加引号，缺失用 null，tier 只能是 deep / watch / eliminated。**

```yaml
slug: {slug}
variant: {variant}
topic_type: industry
display_name: {display_name}
generated: {ISO8601 timestamp}
data_freshness: {date}

arenas:
  - name: {arena 中文名}
    suggested_slug: {e.g. global-advanced-packaging}   # 建议的 arena slug
    topic_created: false        # 是否已创建 arena topic（默认 false，创建后改为 true）
    topic_slug: null            # 实际创建的 topic slug（创建后填入）
    scores:
      profit_pool: {1-5}
      growth: {1-5}
      competition: {1-5}
      valuation: {1-5}
      cycle: {1-5}
      composite: {float}        # 综合加权分
    tier: deep                  # deep / watch / eliminated
    tier_reason: {入选/暂不/淘汰理由，一句话}
    upgrade_triggers: []        # deep/watch 档必填非空；deep 可写 ["已在 stub topic L1-L4 跟踪"]
    monitor_metrics: []         # deep/watch 档必填非空；同上
    revive_condition: null      # eliminated 档：复活条件
  # 追加更多 arena...

cluster_tags: [{tag1}, {tag2}]  # 继承自行业，e.g. [ai-compute, china-defense]
```

```bash
python -c "
from pathlib import Path
import yaml

content = '''
{上面填好的 yaml 内容}
'''
path = Path('prism/topics/{slug}/{variant}/outputs/09_industry_to_arenas.yaml')
path.write_text(content, encoding='utf-8')
print('09 sidecar 写入完成')
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

---

## Step 8：仪表盘自动刷新（修 S5）

`set_output_referenced_mats('09_industry_to_arenas', ...)` 已自动 fire-and-forget 触发 dashboard 异步重建，**无需手跑** `python -m prism.scripts.dashboard`。后台失败留痕在 `prism/logs/dashboard_auto.log`。
