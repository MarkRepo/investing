---
slug: global-glp1-highend-efficacy
variant: opus4.8
version: 1
parent_version: 0
written_at: 2026-07-24
convergence_status: open
---

# decomposition_v1 — GLP-1 三激动/amylin 高端疗效 arena

> v0 薄拆解经 04 findings 校验后的 delta 重拆。命门数不变（1-3），无新增/删除命门；命门 3 证据强度显著升级、命门 1 量化、命门 2 维持 open（VANQUISH-2 binary 未读出）。

## § changelog（v0 → v1）

- **命门 1**：置信度维持"中"，但从"待观察"落到"实证有代价、未封顶"——dysesthesia 剂量依赖量化（12mg 20.9% [mat-6f71bc]）。未震荡。
- **命门 2**：置信度维持"中"，方向校准——疗效轴已被挑战者逼近（amycretin 24.3% no-plateau [mat-053d60]、VK2735 口服 12.2% [mat-d49f82]），但双轴/Ph3 未证，独占权"变窄"非"被破"。VANQUISH-2（2027）仍是最大不确定源，维持 open。
- **命门 3**：**置信度从"低"升为"证据充分"**（唯一实质升级）——净价硬锚（Medicare $245/MFN 新药条款/tirz 折 79% [mat-f91712, mat-c4b77e]）+ PCSK9 定量镜鉴 [mat-61df5e] 齐全。这是最大 delta。
- **未增删命门**：三命门框架对照全历史无震荡；命门 4 缺位仍刻意（K4 介入纪律归环⑥）。
- **入门目标**：v0 的 10 条全部保留，无增删；critic 后在 primer 内精修（QALY 白话、疗效读出"看五个数"自洽、amylin 保瘦体重降档措辞）。

## 一、命门现状（命门 + 置信度 + 每环 B 靶点）

- **命门 1（GCG 安全窗 = 疗效独占兑现闸门）**〔中 · 实证有代价未封顶〕
  reta 30% 实证，但 12mg dysesthesia 20.9% 剂量依赖 [mat-6f71bc]。若真实世界耐受迫使商业剂量下移，"疗效独占"在处方端缩水。**残留缺口**：完整 TRIUMPH 各剂量停药率/心率明细（P0，留 monitor）。

- **命门 2（挑战者双轴逼平 = shortlist 洗牌触发器）**〔中 · open〕
  疗效轴逼近（amycretin 24.3%、VK2735 口服 12.2%），但耐受轴 + 头对头 + Ph3 均未证。**这是 shortlist 排序最大不确定源**，裁决点 = VANQUISH-1 顶线（早于 -2）+ amycretin Ph3 H2H。**残留缺口**：VANQUISH 顶线（binary，2027 未读出）。

- **命门 3（疗效领先 → 利润领先转化）**〔证据充分 · 转化被削弱〕
  净价压制 + PCSK9 镜鉴双重反证，疗效领先→利润领先被系统性削弱。**这是市场为 LLY 付 30x 溢价时踩的最弱一块地**（定价笃定 > 证据强度）。B 靶点已收满料，不再优先砸料。

### 每环 B 靶点（决策链 6 环，已在 case 落地）

- 环①：三靶/双靶/amylin 机理分野 + 高端池利润来源 + 净价客户结构 ✓
- 环②：胜负变量=疗效×耐受双轴 + 净价转化闸；定价锚=LLY 30.2x/NVO 11.76x/VKTX 零营收期权 ✓（定价锚×证据强度张力已点透）
- 环③：5 条 WMBT，标支持度，WMBT-3 最弱 ✓
- 环④：5 家 peer 横比 + K# 校准 + score 倒挂显式解释 ✓
- 环⑤：R1/R2 + KILL-A/B/C + PCSK9/胰岛素双镜鉴 + signpost ✓
- 环⑥：深研(LLY/VKTX)/观察(NVO/AMGN)/淘汰(Roche/Zealand) 三档 + tier=卡位×定价 ✓

## 二、primer 入门目标现状（N=10，全保留）

10 条 v0 目标全部在 primer 落地（§7 自检清单逐条对应）：机理阶梯 #1/#2、减重质量 #3、GCG 双面性 #4、疗效读出方法 #5（critic 后升为"看五个数"）、玩家全景 #6、疗效≠商业三断点 #7、生理上限 #8、净价压制 #9、独立利润池 vs 期权 #10。critic 精修：QALY 白话（#9 支点）、疗效读出自洽（#5）、amylin 保瘦体重降档（#3）。

## 三、收敛判定

- **delta**：命门 3 证据升级（非新增命门），其余命门稳定，对照 v0 无震荡。
- **双轴 gap**：K 轴全绿（K1-K4 均有覆盖）；ring 轴仅剩 peer-comparison-financials（已由 financial_data API 填，非欠供）。
- **convergence_status = open**：因命门 2（挑战者双轴逼平）的裁决点 VANQUISH-2 顶线是 2027 才读出的 binary，本质未闭合——非 capped（无两轮未解僵局），而是"等外部催化剂"的开放。命门 1/3 已收敛。
