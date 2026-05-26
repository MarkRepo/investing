---
slug: cn-rongchang-bio-688331
output_key: 08_living_feed
version: 1
generated: 2026-05-26T09:00:00+00:00
mat_ids_referenced:
  - mat-6601a1
  - mat-9ad4f3
  - mat-cf360d
addresses:
  - K1
  - K2
  - K3
  - K4
  - K5
---

# 08 — Living Feed（监控订阅）

> 用于 workflow 06 daily-monitor。每个 K# 列出"喂料源 + 频率 + 触发阈值 + 通知模板"。

## K1 — RC148 / AbbVie

### 订阅源

| 来源 | URL | 频率 | 关注内容 |
|---|---|---|---|
| 港交所公告（荣昌生物 09995） | hkexnews.hk → 09995 | 每周 | AbbVie 协议生效 / USD650M 上付到账 / 监管审批进度 |
| 巨潮（A 股 688331） | cninfo.com.cn → 688331 | 每周 | 同上中文版 |
| AbbVie IR + 季报 | abbvie.com/investors | 季度 | RC148 在 oncology pipeline 中的优先级；电话会议提及 |
| AbbVie 8-K（SEC EDGAR） | sec.gov/cgi-bin/browse-edgar | 月度 | 涉及 RC148 的关键事件披露 |
| FDA / EMA Drugs@FDA | accessdata.fda.gov | 月度 | RC148 IND/IDE 状态变更 |
| ClinicalTrials.gov | clinicaltrials.gov + 关键词 RC148 | 月度 | 1L sqNSCLC / 2L NSCLC III 期入组数据 |

### 触发阈值

- AbbVie 监管审批通过 → 重大利好（推动 USD650M 到账）
- AbbVie 在季报特别提及 RC148 优先级 → 加强信号
- ClinicalTrials.gov 新增 III 期 NCT 注册号 → 阶段进展

### 通知模板

`【K1 RC148/AbbVie】[来源] [日期] [事件] —— 影响：{加强/减弱} thesis；建议动作：{N/A | 见 07_decision_kit 加仓矩阵}`

---

## K2 — RC18 自免兑现

### 订阅源

| 来源 | URL | 频率 | 关注内容 |
|---|---|---|---|
| CDE 审评进度查询 | cde.org.cn → 受理号 | 每月 | RC18 IgAN BLA 审评进度（关键 P0） |
| NHSA 国家医保 | nhsa.gov.cn | 季度 | 2026 医保目录调整（10-12 月） |
| 荣昌 IR / 季报 | rongchang.com | 季度 | RC18 单产品销售拆分 / 库存比 |
| 中国医师协会风湿病 / 神经病 / 肾脏病学会 | acrabstracts.org / aanorg | 季度 | 临床数据更新 |
| Vor Bio 季报（NASDAQ: VOR） | sec.gov | 季度 | RC18 海外 III 期入组进度 |

### 触发阈值

- RC18 IgAN BLA 获批 → 重大利好（K2 兑现）
- IgAN 进入 2026 医保目录 → 中等利好
- RC18 库存比恶化（>+80% vs 销量 +35%）→ 警示信号

### 通知模板

`【K2 RC18 自免】[来源] [日期] [适应症: 状态] —— 影响：{加强/减弱} K2 兑现；建议动作：{N/A | 见 07_decision_kit}`

---

## K3 — RC48 海外（Pfizer NCT05911295）

### 订阅源

| 来源 | URL | 频率 | 关注内容 |
|---|---|---|---|
| Pfizer 季报 / 10-K | sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000078003 | 季度 | disitamab vedotin 段落 |
| ClinicalTrials.gov | clinicaltrials.gov/study/NCT05911295 | 月度 | 入组数据 + Status 字段 |
| fiercebiotech / endpoints / apexonco | fiercebiotech.com / endpts.com | 每周 | RC48 海外动态报道 |
| 荣昌 IR | rongchang.com | 季度 | 海外合作披露 |
| ClinicalTrials.gov 全部 disitamab 试验 | clinicaltrials.gov + 搜索 disitamab | 月度 | 跟踪所有 RC48 海外 III 期 |

### 触发阈值

- NCT05911295 status: completed/terminated → P0 信号
- Pfizer 10-K 不再提 disitamab → 减弱信号
- 中期分析公告 → 决定 K3 走向

### 通知模板

`【K3 RC48 海外】[来源] [日期] [事件] —— 影响：{阳性 readout / 阴性 readout / 维持 enrollment}; 建议动作：{见 07_decision_kit 加仓 / 减仓矩阵}`

---

## K4 — 业绩兑现（净利质量）

### 订阅源

| 来源 | URL | 频率 | 关注内容 |
|---|---|---|---|
| 荣昌季报 / 半年报 / 年报 | 巨潮 + 港交所 | 季度 | 扣非主业 / Vor Bio warrants 公允价值变动 |
| Vor Bio (NASDAQ: VOR) 股价 | finance.yahoo.com / vor.com | **每日** | warrants 公允价值与股价正相关 |
| Vor Bio 8-K | sec.gov | 不定期 | 临床/商业事件影响股价 |
| 公司电话会议（每季度业绩说明会） | 雪球 / IR | 季度 | 管理层对扣非 / 现金流的口径 |

### 触发阈值

- Vor Bio 股价 -30% (vs 2025-12-31) → P0 警示
- 2026 半年报扣非仍亏 → 减弱 K4 兑现
- 2026 半年报扣非主业 > 3 亿 → 加强 K4 兑现

### 通知模板

`【K4 净利质量】[来源] [日期] [扣非数 / Vor Bio 股价 / warrants 公允价值] —— 影响：{加强/减弱} K4; 建议动作：{见 07_decision_kit}`

---

## K5 — 治理风险

### 订阅源

| 来源 | URL | 频率 | 关注内容 |
|---|---|---|---|
| 上交所公告（A 股 688331） | sse.com.cn → 688331 | **每日**（锁仓后 4-12 周内） | 减持公告 / 增持公告 / 监管问询函 / 关联交易 |
| 港交所公告（H 股 09995） | hkexnews.hk → 09995 | 每日 | 同上港股版 |
| 工商档案 / 招聘网站（核心人员动态） | qcc.com + zhipin/maimai | 季度 | 房健民 / 温庆凯 / 何如意工商任职 |
| 财经媒体（华夏时报 / 第一财经 / 21 财经） | 关键词监控 | 每周 | 减持 / 离职传言 |

### 触发阈值

- 锁仓 2026-06-30 后 4 周内出现减持公告 → 短期 P0
- 何如意 / 房健民 / 温庆凯任一被官方公告离职 → 长期 P0
- 上交所新增问询函 → P0
- 控股股东声明锁仓延期 / 不减持 → 利好缓解

### 通知模板

`【K5 治理】[来源] [日期] [减持比例 / 人员变动] —— 影响：{加强/减弱} 短期 K5 偏空；建议动作：{见 07_decision_kit}`

---

## 行业 / 周期监控（次要）

| 来源 | URL | 频率 | 关注内容 |
|---|---|---|---|
| NHSA 国家医保 | nhsa.gov.cn | 季度 | DRG/DIP 改革 + 创新药支付改革 |
| FDA / EMA 审评趋势 | fda.gov + ema.europa.eu | 季度 | ADC / 双抗审批情景 |
| 行业 BD 数据 | endpts.com / fiercebiotech | 每周 | 中国创新药 BD 大盘趋势 |
| 港股 18A biotech 估值 | wind / 雪球 | 每周 | 信达 / 君实 / 康方 / 再鼎 PS / PE 走势 |

---

## 已订阅源汇总（导入 RSS / monitor 工具）

```yaml
feed_subscriptions:
  daily:
    - hkexnews.hk:09995
    - cninfo.com.cn:688331
    - finance.yahoo.com:VOR
    - sse.com.cn:688331
    - hkexnews.hk:09995
  weekly:
    - sec.gov:Pfizer:0000078003
    - sec.gov:VOR
    - fiercebiotech.com
    - endpts.com
    - apexonco.com
  monthly:
    - clinicaltrials.gov:NCT05911295
    - clinicaltrials.gov:disitamab
    - cde.org.cn:RC18
    - fda.gov:Drugs@FDA
    - abbvie.com/investors
  quarterly:
    - rongchang IR
    - vorbio.com
    - nhsa.gov.cn
    - wind:18A_biotech_valuation
```

## 信息来源

- mat-6601a1：监控源识别 / Pfizer 供应商关系 / 锁仓时点
- mat-9ad4f3：AbbVie/Vor Bio 监管路径
- mat-cf360d：2026Q1 扣非数据（用于 K4 阈值校准）

**训练知识占比 ~40%**（监控工具 + 数据源映射 + RSS/feed 实操）；**资料占比 ~60%**（4 财报具体监控点）。

---

## 2026-05-26 批评者评审完成

**来源**：Workflow 05-critic-review，钢人反方视角

**关键信息**：
- thesis_v1 评分 3.5/5，verdict = request-rewrite
- 最大反方论据 1：SOTP 加权 NPV 540 亿 + 风险加权 -21.5% vs 6/10 整体评分内部不对账（应降到 5/10 中性偏多）
- 最大反方论据 2：K3 Pfizer my_prob 从 v0 偏空跳到 0.30 过激，应在 0.15-0.20 区间
- 最大反方论据 3：K1 RC148 全球峰值假设未显式入 SOTP；竞品 AK112 (FDA 受理 2025-Q4) / CT-388 / MariTide 时间表未同步压制

**对已有判断的影响**：
- 支持了：v1 K# 修订方向（K1↓ / K3↑ / K4↓ / K5↓）大部分合理
- 新增了：内部三口径对账纪律（SOTP / 风险加权 / 整体评分不可分离判定）
- 调整了：rewrite 04_implied_expectations + 07_decision_kit + 05_historical_mirrors 三份；评分应从 6/10 → 5/10

**当前判断更新**：thesis_v1 维持但需 04/05/07 三份重写以达成内部一致；评分调整为 5/10 中性偏多（赔率敏感型仓位不应在 720 亿现价"持有"，应小幅减仓）
