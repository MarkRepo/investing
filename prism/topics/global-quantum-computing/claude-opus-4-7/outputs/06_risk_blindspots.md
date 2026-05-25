---
slug: global-quantum-computing
output_key: 06_risk_blindspots
version: 1
generated: 2026-05-23T00:00:00+08:00
data_freshness: 2026-Q1
data_freshness_basis: findings_mat-2e82b4 + findings_external_psiquantum_microsoft (Nature editorial note 2024-2025) + findings_external_quantinuum_atom (RIKEN 客户集中度)
---

# 风险盲点：全球量子计算

> 生成于 2026-05-23，训练知识占比约 50%

## 市场已知风险（共识，已部分定价）

### 1. SPAC 估值过高
- **市场定价方式**：已部分定价（IONQ 2025-2026 跌幅最大达 -40%，但 2026 Q1 重新涨回）
- **是否充分定价**：**不足**——当前 trailing PS ~330× 仍是 2021 SPAC 顶 1.4×，市场只定价了"叙事修正"而非"叙事崩塌"
- **剩余下跌空间**：50-70%

### 2. 收入烧钱速度过快 → 融资稀释
- **市场定价方式**：部分定价（IonQ 烧钱率 $4-5M/quarter 已 baked-in 卖方 NTM 模型）
- **是否充分**：中等——市场假设融资窗口可永续打开，未定价"宏观利率上行 + 风险偏好下降 → 融资窗口关闭"组合
- **剩余下跌空间**：30-50%（若任意 1 家融资失败）

### 3. 量子优势 2027 不兑现（K1 失败）
- **市场定价方式**：部分定价——多空双方各执 50%
- **是否充分**：不足——v1 校准 K1 命中概率 15-25%，市场隐含定价 50%+
- **剩余下跌空间**：20-30%（K1 在 2026 Q4 IBM demo 后被证伪时）

### 4. 路线之争（技术路线不确定）
- **市场定价方式**：部分定价——多头买"赢家通吃"，空头看"路线分化"
- **是否充分**：中等
- **剩余下跌空间**：10-20%

---

## 潜在盲点风险（市场低估或忽视）

### 盲点 1：**Microsoft Majorana 学术诚信危机** ★★★★★（最严重）

- **风险描述**：Microsoft 2024 在 Nature 发表的 Majorana 1 拓扑量子比特读出论文，**Nature 编辑部 2024-2025 已附 editorial expression of concern，明文声明"the data presented do not represent evidence of Majorana zero modes (MZMs)"**（findings_external_psiquantum_microsoft）
- **为什么市场可能低估**：
  - editorial note 在 Nature 网站不显眼，主流财经媒体几乎未报道
  - MSFT 体量大（量子部分占总市值 <0.1%），不影响其股价
  - 普通投资者无法理解技术细节
  - 拓扑路线信徒（VC/某些卖方）有动机隐瞒
- **触发条件**：
  - Nature 正式 retraction（撤稿）— 概率 5-10%
  - 第二次独立学术质疑论文上 PRX/arXiv 高引 — 概率 30%
  - 媒体（Quanta Magazine/Wired）深度报道 — 概率 40%
- **影响量级**：**严重**——拓扑路线整体跌价；与拓扑/差异化叙事挂钩的 PsiQuantum 等独角兽估值降级；MSFT 量子板块研发预算可能被董事会重新审视
- **盲点深度**：**99% 的多头不知道这件事**

### 盲点 2：**Quantinuum IPO 客户集中度（RIKEN 90%→7%）** ★★★★★

- **风险描述**：Quantinuum FY2025 RIKEN 单一客户营收占比 **90%**，但 Q1 2026 降至 **7%**（findings_external_quantinuum_atom）。这意味着：
  1. FY2025 高营收增长很可能由 RIKEN 单笔大额订单驱动，**不可重复**
  2. Q1 2026 7% 占比是常态，则真实 ARR 远低于 IPO 路演叙述
  3. IPO target $20B / 估 FY2025 营收 $50M = 400× PS，已是顶部
- **为什么市场可能低估**：S-1 中可能在脚注披露，但路演 deck 强调"客户分散"和"多元化趋势"；散户与多数机构不会下钻
- **触发条件**：IPO 后 6 个月 lock-up 解禁（2026 Q4 IPO → 2027 Q2 解禁）+ 第一个完整 fiscal year 财报披露真实 ARR
- **影响量级**：**严重**——Quantinuum 估值 -50~-70%；带动 sector 整体重新审视客户集中度披露
- **关联第二个 D-Wave QCaaS 故事**：D-Wave 2021 SPAC 招股书允诺 2024 QCaaS $400M，实际 $5.5M，相差 70×；Quantinuum 可能复刻

### 盲点 3：**Bluefors 母公司 PE 退出 → 卖铲人叙事估值崩塌** ★★★

- **风险描述**：Bluefors 母公司 Bregal Sagemount 持有 5 年（2020 收购），按 PE 周期 2025-2026 应触发退出；Bluefors EV/EBIT 已估 25-30×，PE 退出（IPO 或并购）若估值不及预期，整个"卖铲人 +40% 订单"叙事会被重新定价
- **为什么市场可能低估**：Bluefors 私营，无公开数据；K3 卖铲人叙事的 OXIG/Janis 等公开标的不会主动披露 Bluefors 估值压力
- **触发条件**：2026-2027 任意时点 Bluefors PE 退出公告
- **影响量级**：中等——OXIG 等"卖铲人"标的可能 -20~-40%
- **盲点深度**：50%

### 盲点 4：**Oxford Instruments NanoScience 已剥离 → "OXIG 卖铲人"叙事错配** ★★★★

- **风险描述**：OXIG 2024 财年已剥离 NanoScience 业务（含稀释制冷机产线），**当前"OXIG 量子卖铲人"叙事 fundamentally 错配**；剥离后接手方需 2 年消化（NIH/Quantinuum 等买家），期间 OXIG 营收结构与量子完全脱钩
- **为什么市场低估**：OXIG 涨势中市场仍按"量子卖铲人"叙事估值；剥离公告未被广泛传播；LSE 流动性低，价格发现延迟
- **触发条件**：FY2026 财报（2026 年中）首次完整披露剥离后业务结构；OR 卖方下调"量子敞口"评级
- **影响量级**：中等——OXIG 可能 -25~-35%
- **盲点深度**：30%

### 盲点 5：**PsiQuantum Brisbane 12 月延期 + GlobalFoundries 良率信号** ★★

- **风险描述**：PsiQuantum Brisbane 系统从原 2027 推迟至 2028 H1（findings_external_psiquantum_microsoft），同时 GlobalFoundries 量子光子芯片良率数据未公开 → 硅光路线可能比叙述慢 12-18 月
- **为什么市场低估**：PsiQuantum 私营 $7B 估值未受影响；GlobalFoundries 不公布量子项目数据
- **触发条件**：PsiQuantum 下轮融资估值停滞或下降；OR 第二次官方推迟公告
- **影响量级**：轻微-中等——影响光量子路线整体可信度

### 盲点 6：**ITAR / 美中科技脱钩 → IonQ/Quantinuum 海外订单丢失** ★★★

- **风险描述**：2024 美国 DoC 加严量子出口管制；2026 H2 大选后若进一步收紧，IonQ 60% 政府订单 + Quantinuum 国际客户（含日本 RIKEN、欧洲科研）可能被限制
- **为什么市场低估**：地缘政策不确定性常被市场低估；卖方模型一般 baseline 假设政策不变
- **触发条件**：2026-2027 任何 ITAR 收紧公告
- **影响量级**：中等-严重

### 盲点 7：**IBM/Google 自研稀释制冷机 → 卖铲人需求内部化** ★★

- **风险描述**：IBM 已公开提及自研稀释制冷机能力；Google 收购了一家低温公司（具体名 待 verify）；2027 后大客户内部化可能减少 Bluefors/OXIG 30-40% 订单
- **为什么市场低估**：增量信息少，外部不易察觉
- **触发条件**：IBM 或 Google 公开自研产品；OR Bluefors 母公司财报中 top 客户结构变化

---

## Kill Criteria（致命信号 — 触发即应退出原有 thesis）

1. **2026 Q4 IBM Nighthawk advantage demo 失败或被独立学术验证证伪** → 整个通用优势叙事 A 终结，sector 应 -50% 以上 → 同时也证伪 super-bull / bull 情景的对冲（IBM 多头需要退出）

2. **IonQ 或 Rigetti lock-up 解禁后 30 天内内部人减持 ≥ 30% holdings** → 第三波 SPAC 崩盘启动信号，应立即追加 put spread 仓位至最大；该信号在 2026-07/09 解禁日历后 1 个月内会明确

3. **第二家美股四傻进入退市威胁（reverse split / 股价 < $1 / Nasdaq compliance notice）** → sector 整体可能进入 -70~-90% 区间；同期所有 ETF/ARK 类基金被迫减仓引发 cascade

4. **Nature 正式 retraction Microsoft Majorana 论文** → 拓扑路线整体崩塌；MSFT 量子部门重大重组；机会成本应转向 PsiQuantum 短

5. **Quantinuum IPO 定价 < $12B 或被推迟 ≥ 6 个月** → 私募市场对 "$20B+ 量子龙头"叙事祛魅，会传导到所有美股标的

6. **IBM 或 Google 量子部门高管离职 ≥ 2 人（C-level 或 fellow level）** → 内部对路线失去信心的强信号

---

## 监控清单（下次复盘重点看）

| 风险 | 监控指标 | 阈值 | 频率 |
|---|---|---|---|
| SPAC 估值修正 | IONQ/RGTI/QBTS/QUBT 加权 PS | 跌至 50× 以下表示叙事完成第一次纠正 | 每周 |
| 收入塌方扩散 | 4 家季度营收 YoY 增速 | 任意 2 家连续 2 季度 < 0% → 加仓空仓 | 每季 |
| Lock-up 解禁动作 | IonQ/Rigetti 13F + Form 4 | 内部人卖出 / 大宗交易 > 5% holdings | 解禁日历前后每周 |
| IBM 2026 advantage demo | IBM 官方公告 + Nature/Science 论文 + Aaronson 博客评价 | 是否独立可验证 + 是否商业 ROI | 2026 Q3-Q4 每月 |
| Quantinuum IPO 估值 | 路演定价 vs $20B target | < $15B → bear，> $25B → bull | IPO 期间每周 |
| Microsoft Majorana 论文状态 | Nature 网站 + arXiv 评议 | editorial note 升级到 retraction | 每月 |
| Bluefors PE 退出动作 | PitchBook / Crunchbase / 行业访谈 | 任何 IPO/并购公告 | 每月 |
| ITAR / 出口管制 | DoC 量子相关公告 + 国会听证 | 任何 quantum-specific 收紧 | 每月 |
| 中国国产替代进展 | 国盾量子月度公告 + 本源量子签约 | 国盾营收季度 +30% 以上 | 每季 |
| 政府订单延续性 | DARPA/DoE 量子合同公告 + NQI 拨款 | 年化拨款 > 2025 水平 | 每季 |

## 信息来源

- 训练知识（约 50%）—— PE 退出周期、ITAR 历史先例、SPAC lock-up 行为规律、Nature editorial process
- findings_external_psiquantum_microsoft：**Nature editorial note 否认 Majorana 证据**、PsiQuantum Brisbane 12 月延期
- findings_external_quantinuum_atom：**RIKEN 客户集中度 90%→7%**
- findings_external_ibm：IBM 路线图 + Krishna 2026 承诺（用作 kill criteria 锚点）
- findings_external_google：Google 自承 Stage 3 未达（kill criteria 验证）
- findings_mat-2e82b4：D-Wave Q1 -81%（收入塌方信号已现）
- findings_mat-fa4949：IonQ 烧钱速度 + Risk Factors 明文 "may never occur"
- findings_mat-d83292/-71e318：Rigetti/QUBT 政府订单依赖度
