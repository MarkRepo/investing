---
slug: global-glp1-highend-efficacy
variant: opus4.8
version: 2
parent_version: 1
written_at: 2026-07-28
convergence_status: open
---

# decomposition_v2 — GLP-1 三激动/amylin 高端疗效 arena

> 05-critic round-2 复评后与 thesis_v2 配对升版。**命门数与结构不变（1-3，无增删）、各命门置信度不变**；唯一实质 delta = **命门3 的"行动映射"从单边（押守住重仓 LLY）校正为对称（跨守住/崩两结局做杠铃）**——这是 round-2 反方抓到的"诊断-行动不一致"病根的分解层记录。

## § changelog（v1 → v2）

- **命门 1（GCG 安全窗）**：置信度维持"中·实证有代价未封顶"，无变化。
- **命门 2（挑战者双轴逼平）**：置信度维持"中·open"，无变化（VANQUISH-2 2027 binary 仍未读出）。
- **命门 3（疗效→利润转化）**：置信度维持"证据充分·转化被削弱"，**证据强度不变**——但**新增一条分解层洞见**：命门3崩是本 case 自判**最高概率死因**（pre-mortem #1），因此其不确定性在选股层**必须对称配置**（杠铃），而非单边押守住。这修正了 v1 "判命门3最弱却把最暴露该风险的 LLY 当唯一核心"的诊断-行动不一致。
- **未增删命门**：三命门框架对照全历史无震荡；命门 4 缺位仍刻意（K4 介入纪律归环⑥）。

## 一、命门现状（命门 + 置信度 + 每环 B 靶点）

- **命门 1（GCG 安全窗 = 疗效独占兑现闸门）**〔中 · 实证有代价未封顶〕
  reta 30% 实证，12mg dysesthesia 20.9% 剂量依赖 [mat-6f71bc]。残留缺口：完整 TRIUMPH 各剂量停药率/心率（P0，留 monitor）。

- **命门 2（挑战者双轴逼平 = shortlist 洗牌触发器）**〔中 · open〕
  疗效轴逼近（amycretin 24.3%、VK2735 口服 12.2%），耐受轴+头对头+Ph3 未证。裁决点 = VANQUISH-1 顶线 + amycretin Ph3 H2H。残留缺口：VANQUISH 顶线（binary，2027）。

- **命门 3（疗效领先 → 利润领先转化）**〔证据充分 · 转化被削弱 · **最高概率死因**〕
  净价压制 + PCSK9/胰岛素镜鉴双重反证。**行动映射（v2 核心）**：因是最高概率死因，选股须对称配置——命门3守住 → LLY 疗效溢价腿赢；命门3崩/商品化 → NVO 走量腿赢 + LLY 靠 orforglipron 商品层部分兜。B 靶点已收满料。

### 每环 B 靶点（决策链 6 环，v2 已在 case 落地）

- 环①：机理分野 + 高端池利润来源 + 净价客户结构 ✓
- 环②：胜负变量 + 定价锚（LLY 42.44x TTM 刷新/NVO 11.53x/VKTX 零营收期权）✓
- 环③：5 条 WMBT，WMBT-3 最弱 ✓
- 环④：5 家 peer 横比 **改双情景（命门3守住/崩）列** + 跨情景稳健性评分 + NVO 升 shortlist ✓
- 环⑤：R1/R2 + KILL-A/B/C + **KILL-D 补硬阈值** + PCSK9/胰岛素双镜鉴 + signpost ✓
- 环⑥：深研(LLY/NVO 杠铃双核 + VKTX 期权)/观察(AMGN)/淘汰(Roche/Zealand) ✓

## 二、primer 入门目标现状（N=10，全保留）

10 条 v0/v1 目标全部在 primer 落地，无增删。v2 未触 primer（primer 仍 fresh、critic_passed）。

## 三、收敛判定

- **delta**：命门3 行动映射对称化（非新增命门、非证据强度变化），其余命门稳定，对照 v1 无震荡。
- **双轴 gap**：K 轴全绿；ring 轴 peer-comparison-financials 已由 financial_data API 于 2026-07-27 一手补拉（不再欠供）。
- **convergence_status = open**：命门 2 裁决点 VANQUISH-2（2027 binary）未读出，本质未闭合；命门 1/3 已收敛（命门3 的收敛体现为"对称配置"而非"押单边"）。
