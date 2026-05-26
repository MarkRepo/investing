# 产出 01 — 商业全景 (Business Panorama)

> **调度提示**：本文件是 04-synthesize 的**内容规范**，不直接 dispatch。实际由 `_shared.md` 描述的单 subagent 顺序生成 01-08 时按本文件填内容。如需单独重生成本份产出，参考 `_shared.md` § Dispatch Prompt 模板调整范围即可。

**定位**：给完全不了解这个行业的人，用 1 份文档解释「这个生意是怎么运转的」  
**训练知识比例**：约 60%（结合资料补充最新数据）  
**产出文件**：`prism/topics/{slug}/{variant}/outputs/01_business_panorama.md`

---

## Step 0：前置检查

参见 `_shared.md` 前置检查，执行完再继续。

---

## Step 1：聚焦商业模式维度（按索引补读，不要无脑 Read 全部 findings）

本节 addresses 维度：`[scope, K3, K5]`（业务范围、护城河、增长驱动）。

⚠️ **不要 `ls` 或重读全部 findings_*.md**——`_shared.md` Step 1 已一次性加载。写本份前：

1. Read `outputs/_findings_index.md`（~3K token，廉价）
2. 按 addresses=`[scope, K3, K5]` 从索引筛出相关 mat_id
3. **自检**：能清晰回忆这些 mat_id 内容 → 直接写；模糊 → 单 Read 那几份补回（不要全读 22 份）

---

## Step 2：撰写商业全景

按以下结构写 markdown（每节 3-8 句话或要点）：

### 2.1 行业定义与边界
- 这个行业做什么，提供什么产品/服务
- 边界在哪里（哪些算这个行业，哪些不算）
- 关键词/标准分类（SIC/GICS/SW）

### 2.2 市场规模与结构
- 当前市场规模（总量 + 增速），数据年份
- 国内/海外分布（如相关）
- CR3/CR5 集中度（如有数据）

### 2.3 价值链解析
用简图（文本版）展示上中下游：
```
原材料供应商 → [核心环节：XXX] → 品牌商/系统集成商 → 终端用户
```
每个环节说明：谁在做、毛利率水平、竞争格局

### 2.4 商业模式类型
- 主要商业模式（To B / To C / 平台 / 订阅等）
- 收入结构（产品 vs 服务，一次性 vs 经常性）
- 盈利驱动因子（量 × 价 × 成本）

### 2.5 需求端分析
- 核心客户群体
- 购买决策驱动因素
- 需求增长的核心驱动（人口/政策/技术/消费升级）

### 2.6 供给端分析
- 主要参与者类型（国央企/民企/外资）
- 进入壁垒（技术/资本/资质/品牌/规模）
- 产能/供给增速

### 2.7 竞争格局
- 格局类型（高度集中 / 分散 / 两极化）
- 核心竞争要素（不超过 3 个）
- 行业龙头与其优势来源

### 2.8 行业发展阶段
- 当前所处阶段（导入期/成长期/成熟期/衰退期）
- 判断依据（增速/格局/技术成熟度）

---

## Step 2.5：填写 data_freshness

在 frontmatter 写入：
- `data_freshness`: 用到的最晚数据所在期（季度/月份）
- `data_freshness_basis`: 该期来自哪份 finding

---

## Step 3：写入文件

写入 `prism/topics/{slug}/{variant}/outputs/01_business_panorama.md`：

```markdown
---
slug: {slug}
output_key: 01_business_panorama
version: {N}
generated: {timestamp}
---

# 商业全景：{display_name}

> 生成于 {date}，训练知识占比约 60%，资料更新截至 {latest_data_date}

## 行业定义与边界
{content}

## 市场规模与结构
{content}

## 价值链解析
{content}

## 商业模式
{content}

## 需求端分析
{content}

## 供给端分析
{content}

## 竞争格局
{content}

## 发展阶段
{content}

## 信息来源
- 训练知识（约 60%）
- {mat_id}: {filename}（数据更新）
```

---

## Step 4：更新状态

```bash
python -c "
from prism.scripts.topic import set_output_status, read_topic
t = read_topic('{slug}', '{variant}')
current_v = t['outputs_state']['01_business_panorama']['version']
set_output_status('{slug}', '01_business_panorama', 'fresh', '{variant}', version=current_v+1)
print('状态已更新')
"
```

---

## Step 5：汇报

```
✅ 商业全景已生成 → v{N}

Web 查看：http://localhost:8000/prism/{slug}/{variant}/output/01_business_panorama

关键数据点：
- 市场规模：{X}
- 增速：{Y}
- 集中度：CR3={Z}

下一步：说「生成产出 {slug} 周期定位」继续
```
