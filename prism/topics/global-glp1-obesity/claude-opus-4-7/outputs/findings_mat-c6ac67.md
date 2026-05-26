---
mat_id: mat-c6ac67
filename: sec/2025_NVO_20-F_2026-02-04/item_18_financial.md
source_type: sec-section
extracted: 2026-05-26
quality: low
bias: neutral
---

## 核心数据点与事实

- 20-F Item 18 = Financial Statements 的 SEC 备案位置，但实际财报正本在年报里（20-F 仅 incorporate by reference）
- 本切片 11KB 主要是 audit / signatures / cross-reference 索引，不含三大表实际数字

## K# 引用建议
- **K5 财务/估值**：原始数字在 NVO 年报 PDF（pages 84-85 现金流表 + 资产负债表）
  - Item 5 MD&A 切片（mat-5b9ef4）已总结 2025 年关键 P&L/cash flow 信号
  - 具体三大表数据应通过 financial_data API 拿（Yahoo Finance / akshare 等），不通过读 SEC 切片
- 本份优先级 LOW

## 质量备注

20-F Item 18 是 SEC 监管表格设计要求的"占位段"，实际数字外引到年报。stub finding。
