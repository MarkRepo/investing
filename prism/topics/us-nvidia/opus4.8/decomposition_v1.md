---
slug: us-nvidia
variant: opus4.8
version: 1
parent_version: 0
written_at: 2026-07-24
convergence_status: capped
---

# decomposition_v1 — 英伟达 (NVDA)

> 基于 thesis_v1 + 31 份 findings 全抽取后的有界 delta 重拆。命门喂 case 决策环，primer 入门目标喂 primer。

## 一、命门现状（命门 + 置信度 + 每环 B 靶点）

- **命门① — 超大厂 AI capex 可持续性与 ROI 兑现**（置信度：v0 低 → **v1 中偏多**）
  - 现状：capex 短期证据明确偏正（$725B/+77%、指引上调、$119B 采购承诺）。但 ROI/GPU 占比一手拆分**仍缺**（P1 缺口）。方向未反转。
  - B 靶点（残留）：超大厂 AI 收入利润率、token 消耗、capex 中 GPU vs 自研/土建/电力拆分。
  - 映射决策环：①④⑤。

- **命门② — 定制 ASIC 对份额/毛利侵蚀速度**（置信度：v0 中 → **v1 中·横盘**）
  - 现状：方向确认（管理层 10-Q 自证 ASIC 侵蚀路径），但**一手规格/份额量化缺**——竞争材料多为标题级快讯，侵蚀速度只能定性。**P0 缺口，两轮未解 → 踢 drilldown。**
  - B 靶点（残留）：AMD MI400/MI500 vs Blackwell/Rubin 峰值算力/显存/功耗/TCO；Trainium/TPU 出货量与自用比例；ASIC 吃增量 vs 存量。
  - 映射决策环：①③⑤。

- **命门③ — 当前 PE 是错杀还是周期见顶折价**（置信度：v0 中 → **v1 中偏多**）
  - 现状：Cisco 200x vs NVDA 核心 28x 强力排除"泡沫顶"；一致预期持续上修。但**报告 PE 便宜锚被股权收益扭曲**（剔除后 27.8x 非 22x），"极度便宜"论被削弱 → 收敛为"合理偏低"。
  - B 靶点（残留）：逐机构目标价分布（仅一致值 $301.62，P2）。
  - 映射决策环：②④。

## 二、primer 入门目标现状（11 条·各条覆盖情况）

| # | 入门目标 | 覆盖 | 备注 |
|---|----------|------|------|
| 1 | AI 数据中心 GPU 是什么/为何离不开 | ✓ | primer §1 |
| 2 | CUDA 为何护城河 | ✓ | primer §2 |
| 3 | rack-scale 卖整柜逻辑 | ✓ | primer §3 |
| 4 | 通用 GPU vs 定制 ASIC | ✓ | primer §4 |
| 5 | 收入依赖少数超大厂的双面性 | ✓ | primer §5（客户集中 54%） |
| 6 | HBM/CoWoS 供给瓶颈 | ✓ | primer §6 |
| 7 | 财年口径差异 | ✓ | primer §7 |
| 8 | AI capex 周期与泡沫担忧 | ✓ | primer §5 |
| 9 | 出口管制机制 | ✓ | primer §9 |
| 10 | 高毛利招竞争/均值回归 | ✓ | primer §8 |
| 11 | 该盯的可观测信号 | ✓ | primer §11 |

11 条全覆盖，无 findings 撑不起的入门目标（primer depth=deep）。

## 三、changelog（v0 → v1）

- 命门①置信度 **低 → 中偏多**（capex 证据落地）。
- 命门②置信度 **中 → 中·横盘**（方向确认但无法量化，标 P0 未解命门 → capped）。
- 命门③置信度 **中 → 中偏多**，内涵修正：从"22x 明显错杀"→"核心 27.8x 合理偏低"（股权收益扭曲报告 PE）。
- 命门增删：无（3 命门维持）。
- primer 入门目标增删：无（11 条 v0 全部保留并覆盖）。
- **收敛状态 = capped**：命门②（ASIC 侵蚀速度量化）撞证据缺口，本轮无一手规格材料可补（adapter 配额今日耗尽），两轮内无法解 → capped，翻成 suggested_drilldowns（P0）。命门①③已收敛至可决策。
