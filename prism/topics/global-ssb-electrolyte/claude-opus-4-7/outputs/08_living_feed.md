---
slug: global-ssb-electrolyte
output_key: 08_living_feed
version: 1
generated: 2026-05-22T11:00:00+08:00
data_freshness: 2026-Q1
data_freshness_basis: 初始 log 入口；后续每月 / 事件驱动追加
---

# Living Feed：全球固态电解质 + 锂金属上游

> 生成于 2026-05-22；这是本主题的滚动观察日志，按时间倒序记录关键事件、决策更新、验证 / 证伪节点；不是 brief / 06 / 07 的复述

---

## 2026-05-22T15:30 追加 entry：10_peer_matrix 完成，2 家进入 shortlist

**触发事件**：完成 workflow 10-peer-matrix（arena 自动后续），8 家候选公司分流到位。

**分档结论**：
- **shortlist（✓ 深研档）**：赣锋锂业 SZSE 002460（4.5）/ 当升科技 SZSE 300073（4.0）
- **watch（观察档）**：出光兴产 TSE 5019（3.5，等 6/17 中計有報）/ 三井金属 TSE 5706（3.5，等 9 月 IR）/ 三星 SDI KRX 006400（2.5）/ Solid Power SLDP（2.5）
- **eliminated（✗ quarantine）**：容百科技 SSE 688005（2.0，中试线后移 + 硫化物 R&D 仅 0.09%）/ SES AI（1.5，已退出 Li-Metal EV）

**最大 narrative**：日韩派两家（出光/三井）全部在 watch 而非 shortlist——本批 findings 未给出足够 capex/客户硬证据来支撑深研档评分，必须等 6/17 中計 + 9 月 IR 才能升级。

**待决策**（push 给 user）：
1. 是否为 shortlist 创建 stub company topic（`cn-ganfeng-002460` / `cn-dangsheng-300073`）？
2. 是否进入 06-daily-monitor 设 `monitoring_tier=warm`，跟踪 6/17 + 9 月日韩 IR 时点？

---

## 2026-05-22 初始 entry：v1 thesis 锁定，等 6/17 出光中计

**触发事件**：本主题完成 v1 thesis 校准 + 8 份 outputs 产出。

**判断状态**：
- v0 thesis 主线方向正确，所有时点右移 12-18 个月
- K1: +7 → +5（弱化）
- K2: -3 → -5（强化短空）
- K3: +7 → +3（弱化）
- K4: +7 → +2（场景切换至 eVTOL）
- K5: +2 → 0（信息缺口）

**当前持仓建议**：不重仓任何方向；赣锋可建立 5-8% 探索性仓位（多空非对称性最好）；不持仓 SPAC 系 / 中国正极厂期权。

**下一个决策窗口**：2026-06-10（出光中计有報前 1 周）

**待跟踪事件清单**：
1. 6/17 出光兴产中计 2026-2030 capex + 千吨级时点
2. SLDP 2026 Q2 10-Q（5 月末发布）现金余额 + SK On pilot 出货
3. 三井金属 IR 说明会披露 A-SOLiD® 客户名单
4. SMM 6 月报价是否预告硫化物电解质独立 SKU
5. SES 6 月可能的裁员 / 现金链公告
6. CATL 6-7 月可能的凝聚态新品发布

**未解决问题**：
- 路线之争（硫化物 vs 卤化物 vs 复合）仍未消解；当升氯碘卤化物路径有可能绕开硫化锂卡点，但 18-24 个月才能裁决
- USPTO / JPO 一手专利图谱缺失，K5 强度 0 无法变化
- 中国 CASIP 内部企业排序 + 补助分配规则不透明
- 欧洲 ProLogium / Northvolt 全固态进度不明
- 印度 / 东南亚 EV 政策对 SSB 需求拉动未覆盖

**研究下一步优先级**：
1. **最高**：6/17 出光有報跟进 + 三井 IR 说明会
2. **高**：USPTO 硫化物电解质专利图谱（mat-afa444 / mat-ec4e1e 都缺失）
3. **中**：ProLogium 法国 Dunkirk 工厂 + 台湾本部进度
4. **中**：LGES / 三星 SDI 内部固态电池路线（mat-3770c8 已确认信息严重不足）
5. **低**：印度 EV 政策 + 东南亚动力电池工厂规划

---

## Living Feed 使用规约

每次有以下事件之一发生时，**在本文档顶部追加新 entry**（时间倒序），entry 不删除已有内容：

1. **任一 KILL-1 ~ KILL-7 条件被触发或部分触发**
2. **任一 Signposts 节点到期或事件驱动触发**
3. **新 findings 入库（任一 mat_id 新增）**
4. **K1-K5 任一强度调整 ≥2 个等级**
5. **建仓 / 加仓 / 减仓 / 清仓任一 cluster**
6. **盲点被部分消解（如 USPTO 专利图谱产出）**
7. **新 narrative / risk 出现且影响 thesis**

每个 entry 必须包含：
- 触发事件 + 日期
- 判断状态变化（K-question 强度 / cluster thesis_strength）
- 持仓建议变化
- 下一个决策窗口
- 待跟踪事件清单更新
- 未解决问题更新

---

## 信息来源

- 本日志为初始入口；后续 entry 将按事件来源各自援引 mat_id / 一手数据
- v1 thesis 基础 mat_id：自有 10 份 + 父级 6 份（详见 _synthesis_brief.md / 07_decision_kit.yaml）
