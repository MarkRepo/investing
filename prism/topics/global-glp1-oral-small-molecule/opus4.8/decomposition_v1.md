---
slug: global-glp1-oral-small-molecule
variant: opus4.8
version: 1
stage_set_at: 04-synthesizing
convergence_status: converged
---

# decomposition_v1 — 口服小分子平权化 arena（厚料重拆）

> 本 topic 无 `decomposition_v0` 种子，据 19 份自有 + 11 份父级 findings 直接立 v1。

## Section 1：命门现状（胜负关键变量 + 置信度 + 每环 B 靶点）

| # | 命门 | 置信度 | 每环 B 靶点 |
|---|---|---|---|
| **A（主命门）** | 疗效↔可及性权衡：口服 10.5% 是利润池迁移目标还是可及性补充入口？ | **中**（放量方向兑现，但疗效 gap 真、支付慢坡证据增强；他汀镜鉴支持但 10.5 vs 20 落差大） | 环①路线之争 / 环②胜负变量 / 环③ WMBT-1,2 / 环⑤他汀-PCSK9 镜鉴 |
| **B** | 规模领跑 vs 疗效领跑分离：收敛 LLY 还是纯标的成独立利润池/被并购？ | **中高**（规模收敛 LLY 证据强 WMBT-3；疗效领跑者独立利润池待 Phase 3 验证 WMBT-4） | 环②定价锚 / 环④ peer 横比 / 环⑥三档分流 |
| **C** | generic 悬崖陡度 + 支付总闸：口服利润池长期是否更脆 + 放量斜率被卡慢坡？ | **中**（近期专利护 2040s 强；远期小分子悬崖陡+支付摩擦硬约束） | 环③ WMBT-2,5 / 环⑤丙肝+DPP-4 镜鉴 / 环⑤ K-kill-3 |

**置信度说明**：三命门均未坍塌、均未新增或掉队。命门 A 经厚料细化（新增"规模领跑≠疗效领跑"分层 + 支付摩擦证据），但权衡仍 open——这是 arena 本身的性质（放量已发生，赢家归属+耐久性未定），非收料不足。

## Section 2：primer 入门目标现状（精修后 12 条 + 覆盖情况）

12 条入门目标（见 `00_primer` §10 自检清单），厚料覆盖情况：
- **充分覆盖（findings 实证）**：GLP-1 机理、注射 vs 口服、两条路线、疗效口径、玩家地图、支付结构、专利 generic 机制、估值口径、术语——均由 findings + 训练知识撑起。
- **部分依赖训练知识（诚实标注）**：历史镜鉴峰谷幅度（他汀-PCSK9/丙肝）为训练知识估算；biased agonist/DACRA 机理为行业稳定知识。
- **无新增/坍缩入门目标**：厚料未揭示门外人会卡但 12 条没列的能力，也无多余可坍缩条目。

## § changelog

- **命门**：无砍无加（v1 首版，据厚料直接立 3 命门）；命门 A 细化（新增规模/疗效领跑分层 + 支付摩擦证据），非增删。
- **primer 入门目标**：12 条据厚料 delta 校验后无增删；critic 补足术语（DACRA/biased agonist 定义）属写作修订，非目标增删。
- **收敛判定**：① 命门 delta 空 + primer 目标 delta 空 ✓；② gap 双轴：uncovered_ks 空、uncovered_ring_inputs 的估值锚/胜负变量已由 Step 1 peer 财务补 ✓；③ 05 critic 待跑（首版标 converged，chain-critic 已内嵌校验通过）。**对照无 v0 历史，无震荡。**
