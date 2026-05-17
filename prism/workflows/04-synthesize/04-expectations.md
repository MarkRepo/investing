# 产出 04 — 隐含预期与观点光谱 (Implied Expectations & View Spectrum)

**定位**：反推市场当前价格隐含了什么预期，然后构建从极度乐观到极度悲观的完整观点谱系
**训练知识比例**：约 50%（估值框架来自训练，当前数据来自资料）
**产出文件**：`prism/topics/{slug}/{variant}/outputs/04_implied_expectations.md`
**重要性**：这是 8 份产出中对投资决策最直接有用的一份

---

## Step 0：前置检查（见 _shared.md）

至少需要：当前股价/估值数据、行业/公司盈利预测数据（来自资料）

---

## Step 1：按 topic.type 分支处理

```bash
python -c "
from prism.scripts.topic import read_topic
data = read_topic('{slug}', '{variant}')
print(data['type'])
"
```

根据 type 进入对应的分支：

---

## 「Industry 分支」（type == industry）

### Step I1：提取行业估值数据
从 findings 中提取：
- 行业整体 PE/PB/PS 当前值与历史区间
- 行业整体盈利预测（营收增速、净利润增速）
- 全球可比行业估值对比

### Step I2：反推行业隐含预期
**核心问题：「当前行业估值假设了什么必须为真？」**

步骤：
1. 以当前行业 PE，反推市场隐含的 3 年 CAGR
2. 对比历史增速区间，判断隐含增速是偏高/中性/偏低
3. 隐含的利润率假设
4. 隐含的终值估值假设

输出格式：
```
当前行业整体 PE = {X}x（历史均值 {Y}x，±1σ: {Ylow}-{Yhigh}x）
隐含 3 年行业净利润 CAGR = {Z}%（历史均值 {H}%）
市场似乎在假设：{一句话描述隐含假设}
这个假设属于：悲观 / 中性 / 乐观 / 极度乐观
```

### Step I3：行业观点光谱（5级）
同基础版，聚焦行业级，不写公司。

---

## 「Arena 分支」（type == arena）

### Step A1：提取 arena 估值数据
从 findings 中提取：
- arena 整体 PE/PB/PS 当前值与历史区间
- arena 利润池规模预测
- 龙头公司隐含估值与市占率

### Step A2：反推 arena 隐含预期
**核心问题：「当前 arena 估值假设了什么必须为真？」**

步骤：
1. 反推隐含的 arena 利润池 3 年 CAGR
2. 反推隐含的龙头公司市占率
3. **必须做**：利润池迁移分析（价值从哪段往哪段迁？）
4. 对比历史增速，判断隐含增速

### Step A3：arena 观点光谱（5级）
同基础版，聚焦 arena 级。

---

## 「Company 分支」（type == company，重点强化）

### Step C1：提取公司估值数据

先自动获取行情数据：

```bash
python -c "
from prism.scripts.market_data import get_valuation_context
print(get_valuation_context('{slug}', '{variant}'))
"
```

再从 findings 中补充：
- 卖方一致预期的未来 3 年净利润 CAGR
- 历史估值区间（从资料中获取）
- 同业公司估值对比（从 findings + 10-peer-matrix 获取）

### Step C2：反推隐含预期（必须有具体数字）
**核心问题：「当前价格假设了什么必须为真？」**

**最简反推公式**（直接写在产出中）：
```
当前价格 P = 未来3年净利润 CAGR g × 终值PE × 折现率 r
```

步骤：
1. **必须**：反推 DCF 表（基础情景）
   - 输入：P、当前营收、当前净利率、折现率假设 r
   - 反推：未来 3-5 年 CAGR g、终值假设、隐含 IRR
2. **必须**：同业反推对比（取 peer matrix 中 3-5 家）
   - 同样反推方法应用到同业
   - 对比本标的隐含假设相对同业是 cheap/fair/expensive
3. **必须**：5 级光谱 + 每档对应一个反推数学结果

**输出格式示例**：
```
当前价格 = {P}元，当前 PE = {X}x
反推 DCF（基础情景）：
  - 假设 3 年 CAGR = {g}%
  - 终值 PE = {terminal_PE}x
  - 折现率 = {r}%
  - 隐含 IRR = {irr}%
隐含净利率 = {M}%（当前 {N}%）
市场似乎在假设：{一句话描述隐含假设}

同业对比：
  - {peer1}: 隐含 CAGR {g1}%, PE {pe1}x
  - {peer2}: 隐含 CAGR {g2}%, PE {pe2}x
  - {peer3}: 隐含 CAGR {g3}%, PE {pe3}x
本标的相对同业：cheap / fair / expensive
```

### Step C3：构建观点光谱（5级，每档必须有数学）

**Super-bull（超级乐观）**
- 核心逻辑：
- 关键假设（3个）：
- 支持证据：
- 概率估计：X%
- **如果正确，潜在回报：+Y%**
- **对应反推：假设 {g_superbull}% CAGR + 终值 PE {pe_superbull}x

**Bull（乐观）**
- 核心逻辑：
- 关键假设：
- 支持证据：
- 概率估计：
- **潜在回报：+Y%**
- **对应反推：{g_bull}% + {pe_bull}x

**Base（中性/基准）**
- 核心逻辑：
- 关键假设：
- 支持证据：
- 概率估计：
- **潜在回报：**
- **对应反推：{g_base}% + {pe_base}x**

**Bear（悲观）**
- 核心逻辑：
- 关键假设：
- 支持证据（或：为什么这个情景可能发生）：
- 概率估计：
- **如果发生，潜在下跌：-Y%**
- **对应反推：{g_bear}% + {pe_bear}x**

**Super-bear（超级悲观）**
- 核心逻辑：
- 关键假设：
- 为什么市场低估这个风险：
- 概率估计：
- **尾部风险幅度：-Y%**
- **对应反推：{g_superbear}% + {pe_superbear}x**

---

## 「共用 Step」（所有 type）

### Step 4：识别关键分歧点

**「多空双方最核心的一个分歧是什么？」**

- 分歧焦点（一句话）：
- 多方认为：...，因为...
- 空方认为：...，因为...
- 解决这个分歧需要什么信息/等待什么时间节点？
- 我自己当前的判断（如果资料足够支撑）：

### Step 4.5：填写 data_freshness

在 frontmatter 写入：
- `data_freshness`: 用到的最晚数据所在期（季度/月份）
- `data_freshness_basis`: 该期来自哪份 finding

### Step 5：写入文件 + 更新状态

output_key = `04_implied_expectations`

### Step 6：汇报

```
✅ 隐含预期与观点光谱已生成 → v{N}

当前市场隐含假设：{一句话}
这个假设属于：{悲观/中性/乐观}
核心多空分歧：{一句话}
我的初步判断（供参考）：{一句话，标明信心度}
{% if type == 'company' %}
隐含 IRR（基础情景）：{irr}%
同业对比：本标的相对 {cheap/fair/expensive}
{% endif %}
```
