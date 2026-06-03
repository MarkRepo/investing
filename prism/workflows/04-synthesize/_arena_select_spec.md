# Industry → Arenas 选拔规范（arena 评分 / 分流 / sidecar / stub）

> **工具规范，非独立产出步骤。** industry 的 arena 选拔已折进 `_industry_funnel.md` 决策链环④（6 维评分）+ 环⑥（三档分流 + 落 sidecar + 建 arena stub），叙事写进 `i_industry_case`。本文件只作 `_industry_funnel.md` **逐字引用**的工具规范：环④引 **Step 3**（6 维评分口径）、环⑥引 **Step 6.5**（sidecar schema）+ **Step 6/6b**（arena stub 创建 / 继承 thesis_v0）。查规范，不照搬结构。
>
> **不再产出**独立 markdown（旧 `industry_to_arenas.md`）；sidecar `industry_to_arenas.yaml` 是 dashboard 行业层唯一契约。

---

## Step 3：对每个 arena 进行 6 维度评分

至少识别 **5 个细分 arena**（来源：findings + 决策链①③ 的价值链/迁移路径判断），每个沿 6 维评分：

| 维度 | 说明 | 评分标准 (1-5) |
|------|------|----------------|
| 利润池规模 | 当前及 5 年期 arena 总利润（亿元，区间） | 1: <10亿, 5: >1000亿 |
| 增速预期 | 3 年 CAGR | 1: <5%, 5: >30% |
| 竞争结构 | CR3 / 是否有自然垄断 / 是否同质化 | 1: 完全竞争, 5: 自然垄断 |
| 估值水位 | 当前 PE/PS 相对该 arena 历史 + 全球 peer | 1: 历史高位, 5: 历史低位 |
| 周期位置 | 早期成长 / 中段加速 / 晚期分化 / 成熟饱和 | 1: 衰退/饱和, 5: 早期成长 |
| 综合评分 | 以上维度加权平均 | 1-5 |

每个数字注明来源（findings mat_id 或"训练知识假设"）。

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

写进 sidecar（及 case frontmatter）：
- `data_freshness`: 用到的最晚数据所在期（季度/月份）
- `data_freshness_basis`: 该期来自哪份 finding

---

## Step 6：为深挖档创建 stub arena topic

对每个深挖档 arena：

```bash
python3 -c "
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
    short_name='{arena_short_name}',          # 简称（dashboard 显示用）
    search_terms=['{词1}', '{词2}', '{词3}'],  # 见下 ⚠️：arena question 普遍 >25 字，必填
)
"
```

> ⚠️ **必传 `search_terms`（否则 create_topic 直接 raise）**：当 `question` >25 字时 create_topic 强制要求 `search_terms`（避免脚本自行从长问题里乱拆关键词）。arena 问题几乎都 >25 字 → **本步漏传必崩**。规则：`list[str]`，每项 ≤15 字，至少 1 个非空项。从 arena 主题手挑 3-5 个检索词（如 `['ADC', '出海 BD', '双抗']`），别整句塞进去。

### Step 6b：为 stub 写入继承自父 thesis 的 thesis_v0.md

create_topic 完成后，**立即**为 stub 写 thesis_v0.md，省去用户后续推进时再走 00-research-topic 的麻烦。

1. 读父 topic 当前 thesis：

```bash
python3 -c "
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
python3 -c "
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

写入文件：`prism/topics/{slug}/{variant}/outputs/industry_to_arenas.yaml`

从决策链④/⑥ 提取以下字段。**数字不加引号，缺失用 null，tier 只能是 deep / watch / eliminated。**

> ⚠️ **机器↔叙事一致性（硬规约 · dashboard 直接消费 composite 与 tier）**：
> 1. **`scores.composite` 排序必须与 case ④综合评级同向**。同档内若出现倒挂，**必须在 case 里显式写一句解释为什么倒挂**——否则 dashboard 按 composite 排序展示出来的顺序会与 case 叙事方向相反。
> 2. **`tier` 枚举 ↔ case 中文档名的映射必须在 case 里显式写明一行**（深挖=deep / 观察=watch / 淘汰=eliminated）。sidecar 存英文枚举、case 用中文档名，二者口径不显式锁定时 dashboard 关联会对不上。

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
python3 -c "
from pathlib import Path
import yaml

content = '''
{上面填好的 yaml 内容}
'''
path = Path('prism/topics/{slug}/{variant}/outputs/industry_to_arenas.yaml')
path.write_text(content, encoding='utf-8')
print('09 sidecar 写入完成')
"
```
