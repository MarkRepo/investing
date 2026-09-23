---
mat_id: mat-2a0e88
filename: sec/2025_AAOI_10-K_2026-02-26/item_7a_quant_risk.md
source_type: sec-section
extracted: 2026-08-26
quality: high
bias: neutral
addresses: [K2, risk]
rings: [biz-moat-unit-econ]
conflicts_with: [findings_mat-c38dd9.md, findings_mat-03e60b.md]
conflict_note: Item 7A 称 FY2025 汇兑收益「约 $0.1M」，而 MD&A 称 $1.9M、附注 N 表列 $2.039M，同一份 10-K 三处口径不一致。
---

## 核心数据点与事实

- [10-K FY2025 Item 7A] [2025-12-31] 利率风险：**全部债务均为固定利率**（"all debts bore a fixed interest rate and therefore did not generate interest rate risk"），未做任何利率对冲；现金等价物为货币基金与银行存款，公司称利率波动对现金/投资组合无重大影响。→ 2030 转债 2.750%、中国信贷 2.45%-2.95%/4.00%-4.35% 全为固定，短期无利率重定价风险；反面含义是**降息周期中融资成本不会自动下降**。
- [10-K FY2025 Item 7A] [FY2025] 收入端外币敞口极小：**仅 0.7% 收入以人民币计价，0% 以新台币计价**。
- [10-K FY2025 Item 7A] [FY2025] 成本端外币敞口大：**营业费用中 21.7% 以人民币计价、17.8% 以新台币计价（合计 39.5%）**；若 RMB 与 NTD 对美元汇率全年高 1%，营业费用将**多出 $0.8M**。→ 与 opex $191.5M 交叉验证一致（191.5×39.5%×1% ≈ $0.76M，本人推算）。
- [10-K FY2025 Item 7A] [FY2025] 公司明示汇率**直接影响 COGS 与净利，并对营业利润率有重大影响**（"fluctuations in exchange rates directly affect our cost of goods sold and net income (loss), and have a significant impact on our operating margins"），但**未量化 COGS 中 RMB/NTD 占比**——只量化了 opex 部分。
- [10-K FY2025 Item 7A] [2025-12-31] 美元敞口净额：中国子公司持有美元计价**净负债约 $2.3M**，台湾分公司持有**净负债 $39.5M**；若 RMB/NTD 对美元高 1%，其他营业费用将减少 $0.4M。
- [10-K FY2025 Item 7A] [FY2025] 汇兑损益：确认约 **$0.1M 汇兑收益**（非功能币种货币性资产负债重估+交易）。**与 MD&A 的「$1.9M 汇兑收益」及附注 N 表列的「$2.039M foreign exchange transaction gain」冲突。**
- [10-K FY2025 Item 7A] [FY2025] 对冲政策：**从未使用衍生品对冲汇率或利率**（"We have not historically attempted to reduce our market risks through hedging instruments"、"We currently do not use derivative financial instruments to mitigate this exposure"），仅表示未来可能考虑远期/期权。（注：2025-11-27 台新银行 US$2M 信贷额度被设计为衍生品用途额度，年末余额为 0。）
- [10-K FY2025 Item 7A] [2015-10 起] 部分公司间借款被定性为长期投资，其重估汇兑损益走 CTA（累计折算调整）而非利润表——即**部分汇率损失被藏在权益项、不体现在净利中**。FY2025 折算调整为 +$1.931M（见合并权益表）。
- [10-K FY2025 Item 7A] [覆盖范围缺口] Item 7A **只披露利率与汇率两类市场风险，完全没有量化客户信用敞口**；客户/应收集中度的量化数字只在附注 B「Concentration of Credit Risk and Significant Customers」中给出（见 findings_mat-03e60b）。

## 叙事主线

因为收入几乎 100% 以美元计价、而营业费用有 39.5% 以人民币/新台币计价且 COGS 的外币占比未被量化（57.5% 产量在中国、38.2% 在台湾）→ 所以 AAOI 是一个结构性「美元收入、亚币成本」的做空亚币主体，RMB 或 NTD 升值会直接压缩毛利率而公司零对冲 → 对投资意味着 K2「毛利率跃升」除了产品结构与降本，还多一个不可控的汇率变量；同时 2026 年把产能移向台湾与美国（高成本地区）会进一步抬高 NTD/USD 成本占比，这是 40% 毛利率目标之外未被市场计价的逆风。

## 反常识/分歧点

- **市场预期/常识**：AAOI 把产能从中国搬到美国/台湾是纯正面（避 301 关税、拿德州拨款）。**本文表明**：搬迁同时把成本结构从低成本 RMB 挪向 NTD 与美元，而公司自认汇率「对营业利润率有重大影响」且**从不对冲**；台湾分公司已持有 $39.5M 美元净负债敞口，是中国子公司（$2.3M）的 17 倍。
- **披露一致性异常**：同一份 10-K 对 FY2025 汇兑收益给出 $0.1M / $1.9M / $2.039M 三个数字，属披露内控瑕疵（尽管审计师称无关键审计事项）。

## 未回答问题

1. COGS 中以 RMB / NTD 计价的比例是多少？（公司称汇率直接影响 COGS 但只量化了 opex，导致汇率对毛利率的敏感性无法测算）
2. 2026 年美国与台湾产能占比上升后，成本币种结构与单位成本变化幅度？

## 质量备注

- 数据新鲜度：FY2025 10-K（2026-02-26 签署），一手权威。本节篇幅仅 786 词，能抽的量化数字已抽尽，未硬凑。
- 可信度：数字为审计范围内披露，但**本节与 MD&A/附注 N 在汇兑损益上三处不一致**，且客户信用敞口在本节缺失（须由附注 B 补），故本节单独使用价值有限，主要贡献是「39.5% opex 为亚币 + 零对冲 + 全固定利率」这三条结构性事实。
- 与 brief thesis 关系：不直接触及 K1/K3/K4/K5/K6；对 K2 提供一个新增的、thesis_v0 未纳入的毛利率变量（汇率+产能地迁移的成本币种切换）。
