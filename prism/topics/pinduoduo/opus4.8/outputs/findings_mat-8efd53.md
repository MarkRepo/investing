---
mat_id: mat-8efd53
filename: sec/2025_PDD_20-F_2026-04-29/item_18_financial.md
source_type: sec-section
extracted: 2026-06-05
quality: low
bias: neutral
addresses: [valuation, K4]
rings: [financial-arc]
---

## 核心数据点与事实
- 本节（20-F Item 18）仅为指针："consolidated financial statements of PDD Holdings Inc., its subsidiaries and its consolidated VIE are included at the end of this annual report."（第 139 页起），**不含可抽取的财务表格文本**——SEC 切片器未能把财务报表正文切入本节。
- 财务报表实际数据已由 financial_data API（yfinance 桥接 US ADR）覆盖，作为合成期 financial-arc / valuation-anchor 的取数来源：
  - FY2025A：营收 4318.46亿、归母净利 978.43亿（净利率约22.7%）、毛利率56.28%、ROE 23.67%、FCF 1057.94亿（2024A 1209.62 → 2025A 1057.94，同比下降）。
  - **ROIC API 失真**（2025A 1832% / 2024A 2902%）——因 PDD 现金极厚、轻资产、投入资本分母极小；真实回报锚用 **ROE 23.67%**，勿引 ROIC。

## 叙事主线
本份无分析价值（仅页码指针）→ 真实财务弧线由 API + Item 5 MD&A（mat-24c21f）承载 → 对投资意味着：估值反推/财务弧线请以 mat-24c21f 与财务 API 为准，本 finding 仅作覆盖留痕，避免合成期误判 valuation/K4 缺源。

## 质量备注
低质量（指针节，切片未捕获正文）。保留以闭合 manifest 覆盖；估值与 FY2025 财务数据以 financial_data API + Item 5 MD&A 为准。注意 ROIC 失真，用 ROE 作回报锚。
