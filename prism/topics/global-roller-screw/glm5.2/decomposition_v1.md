---
slug: global-roller-screw
variant: glm5.2
version: 1
parent_version: 0
written_at: 2026-06-25
convergence_status: open
stage_set_at: 04-synthesizing
changelog: 厚料(findings 10份)确认 v0 三命门+10入门目标无变化；命门2良率仍低置信(单线承重)；convergence=open 待 chain-critic/05 复核
---

# Decomposition v1 — 行星滚柱丝杠 (命门 + primer 入门目标 · 厚料确认版)

> v1 与 thesis_v1 配对升版。v0 是薄知识拆解，v1 是厚料（4 自有 + 6 父级 findings）浮现后的 delta 重拆。delta 空（命门+入门目标无变化），但承重项缺口显式。

## §changelog (v0→v1)
- **命门**：v0 三命门（Optimus 量产/国产良率/一级vs二级）经 findings 确认无变化——仍是最决定成败的特化问题。无新增/掉队/重排。
- **入门目标**：v0 10 条经 primer 撰写+critic 确认无变化（critic 补齐谐波/反向式/价值量是实现细节，非目标增删）。
- **置信度更新**：命门2（良率）维持低（公开无定量，单线承重风险显式）；命门3（一级vs二级）维持中（新剑 IPO 招股书未公开，K2 透明度缺口）。
- **未撞 2 轮顶**：本 arena 未跑第二收料趟（delta 空，无需），故无 capped 命门。
- **对照全历史无震荡**：命门与入门目标均无增删，无震荡风险。

## §命门现状

### 命门 1：Tesla Optimus 量产爬坡合格率与节奏（K1）
- 置信度：**中**（7-8月投产时点确认 [mat-4aa49d]，但 6月静默信号 + 马斯克历史延迟）
- 每环 B 靶点：环②定价锚（Gen3 量产隐含预期）、环⑤证伪（kill=延期>6月）、环⑥ shortlist（量产兑现=深研档升级触发器）

### 命门 2：国产高端 PRS 良率/单根成本能否从样品到规模化（K4）
- 置信度：**低**（公开无定量良率/成本曲线 [mat-228d8e]——最薄弱，单线承重）
- 每环 B 靶点：环②定价锚×证据强度（PE300 定价良率但无据）、环④ peer 横比（良率=hard filter）、环⑤证伪（kill=良率突破被证伪）
- **escalate**：命门2 低置信 + 单线承重 → suggested_drilldowns（07 专项深挖良率/成本，或专家访谈）

### 命门 3：一级（新剑）vs 二级（五洲）谁攫最厚利润（K2/K3）
- 置信度：**中**（卡位公开但新剑 IPO 招股书未公开，价值量分配靠估算）
- 每环 B 靶点：环④ peer 横比（新剑 vs 五洲 thesis_one_liner）、环⑥ shortlist（新剑头号/五洲二号）

## §primer 入门目标现状（10 条 · 经 critic 校验）

| # | 入门目标 | 覆盖情况 |
|---|---|---|
| 1 | PRS 是什么、与滚珠/谐波差异 | ✓ findings+训练知识（critic 补谐波段） |
| 2 | 人形为何选 PRS | ✓ |
| 3 | 价值链+利润集中段 | ✓ |
| 4 | 海外标杆+国产玩家 | ✓ |
| 5 | 反向式 vs 标准式 | ✓（critic 补机制画面） |
| 6 | 螺纹磨削核心壁垒 | ✓ |
| 7 | 估值倍数 | ✓ peer 估值 |
| 8 | Optimus 量产+需求弹性 | ✓ |
| 9 | 一级 vs 二级卡位 | ✓（critic 补价值量诚实标注） |
| 10 | 未消解争议 | ✓ |

> 10 条入门目标均已在 00_primer 落地 + critic 1 轮收敛（3 处补齐）。

## §机械自检
- [x] 每个 K# 被命门覆盖：K1→命门1, K2→命门3, K3→命门3, K4→命门2, K5→命门1/2 交叉
- [x] A 合同必收类目排期：peer-comparison-financials（环④）/arena-mirror（环⑤waived）/consensus（环②）/mgmt-capital-alloc（环①waived）
- [x] 命门置信度分布：1中/2低/3中，低置信命门2已 escalate suggested_drilldowns
- [x] 每条 primer 入门目标已落地（critic 收敛）
- [x] 终局环 B 靶点非空：环⑥ shortlist 三档（新剑/五洲/恒而达深研）
