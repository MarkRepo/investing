---
mat_id: mat-a6225d
filename: sec/2025_SCHW_10-K_2026-02-25/item_7a_quant_risk.md
source_type: sec-section
extracted: 2026-06-04
quality: high
bias: neutral
addresses: [K3, risk]
rings: [financial-arc, historical-mirror]
---

## 核心数据点与事实
- 注：Item 7A 本身仅为指针（"see Risk Management in Part II – Item 7"），利率敏感量化实质在 item_7_mda 的 Risk Management 节，以下数据取自该节。
- 【NII 利率敏感量化 K3，statically-sized，未来12个月，2025-12-31】+200bp: +8.6%；+100bp: +4.1%；+50bp: +1.7%；−50bp: −2.2%；−100bp: −4.4%；−200bp: −8.8%。→ 呈非对称但接近对称的双向敏感；降息显著压 NII。
- 2024-12-31 同口径：+200bp +8.6%、+100bp +4.6%、−100bp −4.6%、−200bp −9.3%（2024 降息敏感度更高，2025 因 PAL 现金流套保+Senior Notes 套保而下降）。
- 有效久期（含衍生品，2025-12-31）：合并总资产 1.9 年；AFS+HTM 证券组合 3.7 年；CSC Senior Notes 1.9 年。AFS+HTM 占合并总资产约 40%（2024 为 48%，占比下降）。
- EVE：当前对"利率下行"的敞口大于上行（greater exposure to rates decreasing）—— 降息环境下经济价值受损更大。
- 动态模拟假设：sweep deposit/payables 余额 runoff 时用 wholesale borrowing 补，即把 cash sorting 直接建模进利率情景。
- 资本压力两情景自述：(1) 极低利率时表内现金涌入；(2) 现金外流且无其他融资、被迫亏损卖资产 —— 后者正是 cash sorting 极端化的尾部风险定义。

## 叙事主线
因为 SCHW 量化披露 NII 对降息高度敏感（−200bp 压 NII −8.8%）且 EVE 对降息敞口更大 → 所以即便是套保后的"类银行券商"，降息周期对 NII 仍是结构性逆风 → 对 HOOD 判断意味着：当前若进入降息后段，HOOD 的 NII 同样面临单向压缩，且 HOOD 没有 SCHW 的 PAL/Senior Notes 套保工具箱去削峰，敏感度暴露可能更裸。

## 反常识/分歧点
- SCHW 用现金流套保（PAL、margin loan、Senior Notes）主动把 NII 利率敏感度年年压低 —— 这是成熟资产负债管理能力，HOOD 作为年轻券商是否具备同等 ALM 套保能力存疑（局限点）。

## 质量备注
本节为指针，实质数据回填自 item_7。利率敏感表为审计 MD&A 量化披露，可信度高。新鲜度高。
