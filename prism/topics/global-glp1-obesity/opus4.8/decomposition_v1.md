---
slug: global-glp1-obesity
variant: opus4.8
version: 1
parent_version: 0
written_at: 2026-07-22
stage_set_at: 04-synthesizing
convergence_status: converged
---

# decomposition_v1 — 全球肥胖/GLP-1 减重药物行业（厚料重拆）

## 一、命门现状（命门 + 置信度 + 每环 B 靶点）

- **命门1｜口服的"疗效↔可及性"权衡是否成立**（置信度：中，**厚料细化未坍塌**）
  厚料确认口服放量兑现（orforglipron 获批 + 口服 Wegovy 65% 新处方），但也确认疗效弱（orforglipron 10.5%）。新浮现一层：**LLY 是口服"规模领跑"而非"疗效领跑"**（疗效领跑是 GPCR/VKTX）。权衡仍 open——放量斜率待上市数据验证。B 靶点：环①③④。
- **命门2｜NVO 存量池衰减是斜率还是断崖**（置信度：中→**升信心**）
  厚料确认结构性受压（份额双失、2026 负增指引、CagriSema 败），但装机粘性 + 估值已 de-rate 到 ~12x → 判"结构性慢衰减 + 悲观已定价"，非断崖。低配 NVO 的赔率不对称风险上升。B 靶点：环②④⑤。
- **命门3｜净价路径 = 利润池总闸**（置信度：低→**升为证据充分**）
  厚料充分：TAM 已被 Jefferies 下修 20% 至 $80B，IRA sema $274/$385、TrumpRx $245、LLY 国际价 -25% 均已兑现。仍是最大 beta 不确定源（净价年降 vs 放量增速的净值待观察）。B 靶点：环②③⑤。

> K# ↔ 命门映射：K1→命门1；K2→命门1 疗效侧延伸；K3→命门2；K4→命门2/3；K5→命门3。

## 二、primer 入门目标现状（精修后 13 条 + 覆盖情况）

v0 种子 12 条厚料确认，**新增 1 条**（第 4 条）：
1-3. 四通路机理 / 疗效阶梯 / 三剂型差异 — findings + 训练知识覆盖 ✓
4. **【新增】区分口服"规模/可及性领跑"与"疗效领跑"** — 厚料浮现（orforglipron 规模领先但疗效弱 vs GPCR/VKTX 疗效强），门外人会卡这一层 ✓
5-13. 兑现路径 / 支付链条 / 中美两套逻辑 / 专利仿制 / 竞争力信号 / compounding / 玩家定位 / TAM 口径 / 两种利润池逻辑 — 全覆盖 ✓（第 8 条 biosimilar vs generic、第 13 条两种利润池逻辑经 primer critic 补强）

## 三、changelog（对全历史去重）

- **加了**："LLY 口服规模领跑 vs 疗效领跑"分层（凭 mat-c9c6aa/mat-63a6fb/mat-b1dcfc 厚料）——区别于 v0 笼统"LLY 独占口服"。
- **加了** primer 入门目标第 4 条（凭同批厚料 + primer critic 反馈）。
- **升信心**：命门2（NVO 衰减，凭 mat-77d015/mat-21a243 估值）+ 命门3（净价总闸，凭 mat-ee7fd6/mat-331b3f）。
- **无砍**：v0 三命门均未被证伪，无掉队命门。
- **无震荡**：无重加曾砍条目。

## 四、收敛判定

- ① delta 空？**是**——命门无新增/掉队/重排（仅命门2/3 升信心 + 命门1 细化）；primer 入门目标仅新增 1 条（已入 primer + critic 确认），无待收料缺口。
- ② gap 双轴绿？**是**——detect_gaps 报 no gaps，uncovered_ks / uncovered_ring_inputs 均空。
- ③ 05 critic 无重大反转？**待跑**（chain-critic 首轮，05 可选）。
- 综合：**converged**（未走第二收料趟，delta 空 + 双轴绿）。残留待验证的是"上市后放量斜率"（时间性数据缺口，非命门未解），进 signpost 而非 drilldown。
