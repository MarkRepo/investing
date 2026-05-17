# Workflow 03b — Company 质量红线检查

**触发**: company topic 完成 03-extracting（stage 为 03-extracting）
**定位**: 在进入 04 完整研究前，先检查质量红线，过滤明显不合格的公司
**产出文件**: `prism/topics/{slug}/outputs/00_quality_screen.md`
**归档文件**: `prism/quarantine/{slug}.md`（若 FAIL）

---

## Step 1：前置检查

```bash
python -c "
from prism.scripts.topic import read_topic
data = read_topic('{slug}', '{variant}')
assert data['type'] == 'company', '仅 company topic 可运行此 workflow'
assert data['stage'] in ('03-extracting', '00-quality-screen'), '请先完成 03-extracting'
print('前置检查通过')
"
```

---

## Step 2：拉取财务数据

```bash
python -c "
from prism.scripts.financial_data import get_quality_screen_data
data = get_quality_screen_data('{slug}', '{variant}')
if data.get('has_data'):
    print('财务数据已就绪')
    print(f'  最新报告期: {data[\"latest_period\"]}')
    print(f'  ROIC_3Y: {data[\"roic_3y\"]}')
    print(f'  FCF_3Y: {data[\"fcf_3y\"]}')
    print(f'  资产负债率: {data[\"debt_to_equity\"]}')
    print(f'  商誉占净资产: {data[\"goodwill_pct_equity\"]}')
    print(f'  OCF质量3Y: {data[\"ocf_quality_3y\"]}')
else:
    print('无财务数据: ' + data.get('error', 'unknown'))
"
```

需要的指标（从返回值中取）：
- 最近 3 年 ROIC（roic_3y）
- 最近 3 年自由现金流（fcf_3y）
- 资产负债率（debt_to_equity）
- 商誉占净资产比例（goodwill_pct_equity）
- 经营现金流/净利润 3年均值（ocf_quality_3y）

数据来源：优先本地 DB → 无数据/过期时自动从 akshare 拉取并存库。

如果没有可用数据，注明"数据缺失，用户判断"。

---

## Step 3：读取 findings 并检查治理/业务红线

读取所有 `findings_mat_*.md`，提取：
- 大股东质押率
- 审计意见
- 关联交易占比
- 是否有重大违规/立案调查
- 高管 3 年内大额减持
- 主业是否明确（CR1 > 50% 或多元化合理）
- 客户集中度（CR5 < 80%）
- 是否有商业模式过气信号

---

## Step 4：填写质量红线 checklist

使用模板 `prism/templates/quality_screen.md.tmpl`，填写：

### 自动数据红线
| 红线 | 阈值 | 当前值 | 状态 |
|------|------|--------|------|
| ROIC vs WACC | ROIC > WACC（最近3年） | {%} vs {%} | ✓/✗ |
| 自由现金流 | 最近3年≥2年为正 | {亿} | ✓/✗ |
| 资产负债率 | 行业内非outlier（<行业90分位） | {%} | ✓/✗ |
| 商誉占净资产 | <30% | {%} | ✓/✗ |
| 经营现金流/净利润 | 3年均值>0.7 | {x} | ✓/✗ |

### 治理红线
| 红线 | 状态 | 备注 |
|------|------|------|
| 大股东质押率 < 50% | ✓/✗ | |
| 审计意见标准无保留 | ✓/✗ | |
| 关联交易占比 < 20% | ✓/✗ | |
| 无重大违规/立案调查 | ✓/✗ | |
| 高管3年内大额减持 | ✓/✗ | |

### 业务红线
| 红线 | 状态 | 备注 |
|------|------|------|
| 主业明确（CR1 > 50%）或多元化合理 | ✓/✗ | |
| 客户集中度可接受（CR5 < 80%） | ✓/✗ | |
| 无明显商业模式过气信号 | ✓/✗ | |

---

## Step 5：综合判定

- **PASS**: 所有红线通过 / 不通过项 ≤1 且非致命 → 进入 04 完整研究
- **FAIL**: 致命红线任一触发（财务造假/重大违规/ROIC长期<WACC）→ quarantine
- **NEEDS-REVIEW**: 1-2项红线不通过但非致命 → 用户决定是否豁免

AskUserQuestion:
- 对 NEEDS-REVIEW 的项，是否豁免？
- 对 FAIL 的公司，是否确认 quarantine？

---

## Step 6：写入产出文件

写入 `outputs/00_quality_screen.md`，包含 frontmatter 字段 `verdict: pass/fail/needs-review`。

---

## Step 7：更新 state

**如果 PASS**:
```bash
python -c "
from prism.scripts.topic import set_output_status, set_stage, set_next_actions
set_output_status('{slug}', '00_quality_screen', 'fresh', '{variant}', version=1)
set_stage('{slug}', '00-quality-screen', '{variant}')
set_next_actions('{slug}', ['进入 04-synthesize：隐含预期与定价'], '{variant}')
"
```

**如果 FAIL**:
```bash
mkdir -p prism/quarantine
# 归档到 prism/quarantine/{slug}.md
python -c "
from prism.scripts.topic import set_output_status, set_stage, set_next_actions
set_output_status('{slug}', '00_quality_screen', 'failed', '{variant}', version=1)
set_stage('{slug}', 'quarantined', '{variant}')
set_next_actions('{slug}', ['已 quarantine，不再继续研究'], '{variant}')
"
```

将 "03b-quality-screen 完成" 摘要追加到 `08_living_feed.md`。
