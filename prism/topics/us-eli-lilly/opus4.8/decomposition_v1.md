---
slug: us-eli-lilly
variant: opus4.8
version: 1
parent_version: 0
written_at: 2026-06-12
convergence_status: converged
---

# decomposition_v1 — 礼来 (Eli Lilly, NYSE: LLY)

> 厚料浮现后的命门 + primer 入门目标重拆。delta（收料触发集：命门新增/掉队/重排 ∪ 入门目标新增/掉队）为空 → 收敛，无第二收料趟。仅置信度更新 + reframe，记入下方 changelog。

## 一、命门现状（命门 + 置信度 + 每环 B 靶点）

- **命门1 — 减重 franchise 单位经济性是否随口服化/竞争/专利侵蚀而结构性下行？**（置信度：**中**，确认·近端证据更充分）
  - 厚料：量价剪刀逐季趋陡（价 −6%→−10%→−5%→−13%，中国 NRDL −25%）`[mat-fb28e6/79ee55]`、CVS 停 Zepbound 优选 `[mat-f6b1d0]`、政策锚价 $245/月 `[mat-685abe]`。但化合物专利 2036-2038 + autoinjector 2039 给注射剂时间护城河，量增仍净盖过价跌。
  - **承重墙**：命门1 与命门3 是同一枚硬币（净价跌则 margin 难扩到 41%）。
  - 靶点：环④主战场（核心分歧落到净价/margin delta）、环⑤ KILL-1。

- **命门2 — 第二曲线兑现速度能否赶上 GLP-1 增速换挡？**（置信度：中低 → **中**，上调 + reframe）
  - 厚料：retatrutide T2D+肥胖 P3 双线达标 `[mat-07afed]`、orforglipron(Foundayo) 已 FDA 获批 `[mat-fb28e6]`。
  - **reframe**："第二曲线"实为 **incretin franchise 延伸（下一代 GLP-1）**，非真多元化——Kisunla/肿瘤/免疫仍小（Verzenio 增速换挡 +8%）。命门2 本质 = "万一整个 incretin 赛道商品化，多元化对冲够不够"。
  - 靶点：环① 梁一护城河、环③ WMBT-4、环⑤ KILL-3。

- **命门3 — ~31x/~$1T 隐含增长假设 vs 真实可持续的 gap？**（置信度：**中**，确认·已量化）
  - 厚料：一致预期曲线落地（营收 65→85→98→111B，EPS 36→44→~50）`[mat-4c9c90/a3e10f]`；**浮现 load-bearing 假设=隐含 2028E 净利率扩到 ~41%（制药史高位）**。当前价已计入一致预期全兑现 + ~22-23x 终值倍数。
  - 靶点：环② 反推 + 三模型；环④ edge=净利率 41% vs 我 38%（delta −3pct）；环⑥ 买入框。

## 二、primer 入门目标现状（精修后 12 条 + 覆盖情况）

v0 的 12 条经厚料 delta：缺口项（产能 7 / 政策 6 / 专利 12）已被 findings 补齐；目标5 reframe 为"第二曲线主要是下一代 incretin"；目标9 sharpen 为商品化时间表（化合物 2036-38 / 数据保护 2027 / 器件 2039 / IRA 渐进）。无新增/坍缩目标。

1-10、12 条：**已覆盖**（primer §0-§10 + 来源分层，critic 2 轮收敛确认门外人可读）。
11 条（安全性争议）：**shallow**——仅 bear 定性框架，NAION/肌肉流失流行病学量化缺失（诚实标注，已知缺口，非新问题）。

## 三、changelog（砍/加 + 为什么，对全历史去重防震荡）

- **无命门增删**（命门 1/2/3 全保留，杠杆序 1>2>3 不变）。
- **命门2 置信度 中低→中**：凭 retatrutide P3 双线达标 `[mat-07afed]` + orforglipron 获批 `[mat-fb28e6]`（v0 标"管线 readout 盲点最大"，厚料已补）。
- **命门2 reframe**：明确"第二曲线=下一代 incretin 而非真多元化"——非掉队/非重排，是框定收窄（不影响收敛判定）。
- **命门3 量化**：新增 load-bearing 假设"2028E 净利率 ~41% 史高赌注"，凭 `[mat-a3e10f]` 一致预期净利率隐含计算。
- **primer 入门目标无增删**：仅目标5 reframe + 目标9 sharpen，缺口项 6/7/12 已由 findings 闭合，目标11 仍 shallow（诚实标）。
- **去重核对**：无重加曾砍命门/目标；对照 v0 history 无震荡。

## 四、收敛判定

三条同时满足 → **converged**：① delta 空（命门 delta 空 + 入门目标 delta 空，仅置信度更新/reframe，不触发第二收料趟）；② gap 双轴绿（uncovered_ks 空 + uncovered_ring_inputs 空，残留为 hard/付费的净价绝对序列 + 安全性量化，已诚实标缺）；③ 05 critic 待跑——首轮内嵌 chain-critic 已过（链通），05 对抗式重审后若无重大反转则定稿。
