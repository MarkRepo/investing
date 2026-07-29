---
slug: global-autonomous-driving
variant: opus4.8
version: 1
parent_version: 0
written_at: 2026-07-28
convergence_status: capped
stage_set_at: 04-synthesizing
---

# decomposition_v1 — 自动驾驶行业（厚料重拆 · B 轴）

> B 轴 = 命门拆解（喂 case 决策环）+ primer 入门目标（喂理解地基）。v0 薄知识起草，本版为读遍 44 份 findings 后的厚料重拆。

## 一、命门现状（命门 + 置信度 + 每环 B 靶点）

- **命门 1 — 上游卖铲人"选对铲子"**（置信度 v0 中 → **v1 中高**）
  厚料坐实：地平线 47.66% 一超[mat-a678a9]、Thor 750/2000 跳票[mat-abba71]、OEM 自研流片+比亚迪 4nm[mat-021ccc/94c77d]、舱驾融合。押国产芯片证据强化。**残留**：地平线高算力域控（征程6P）能否上探高端、PS16.7 溢价能否兑现。→ K1/K2/K5/K7。

- **命门 2 — robotaxi 单位经济学拐点真伪与时点**（置信度 v0 低 → **v1 中**，但仍最低）
  厚料丰富：黄金交叉 2.1 vs 2.4 元[mat-a81878]、武汉 UE 平衡[mat-e5fb63]、RT6<3万美元[mat-041e4e]、完整 BOM[mat-a9b6a2]。**但核心残留未解**：UE"平衡"仅覆盖直接运营成本、不含资本/研发摊销[mat-e5fb63]；无补贴无价格优势[mat-a81878]；跨城复制是否真跑通还是武汉中票价特例。→ **这是撞料后仍未解的顽固命门，翻 suggested_drilldowns。** → K3。

- **命门 3 — 端到端时代软件价值攫取者**（置信度 v0 中 → **v1 中高**）
  厚料坐实：Momenta 64.5%狭义/13.3%整体口径[mat-0ac4e9/f720f4]、华为含五界67.9%[mat-0ac4e9]、一二级倒挂696亿[mat-079b09]、智驾平权下探7.88万[mat-eb5378]。看空纯软、押软硬一体（华为）证据强化。→ K4/K6。

**机械自检**：K1→命门1；K2→命门1；K3→命门2；K4→命门3；K5→命门1；K6→命门3；K7→命门1 ✓（无游离 K#）。

## 二、每环 B 靶点现状

- 环①：价值链利润池分布 ✓（芯片集中/激光雷达分化/软件红海/robotaxi烧钱）+ 财务弧线 ✓（禾赛由亏转盈）。
- 环②：龙头估值倍数 ✓（market_data 拉到 8 家；缺 Momenta 实时倍数、Nvidia 拆分、AUR）。
- 环③：5 条 WMBT 落地 ✓。
- 环④：9 个 arena 6 维评分 ✓。
- 环⑤：4 个历史镜鉴（图森/达摩院/Cruise/光伏类比）✓。
- 环⑥：三档分流 + tier=吸引力×定价 ✓ + 建 2 个深挖 stub ✓。

## 三、primer 入门目标现状（精修后 13 条 + 覆盖情况）

v0 种子 12 条 → v1 **13 条**（+1 新增）：
1-4. SAE分级 / 端到端·VLA·世界模型 / 价值链分层 / 纯视觉vs激光雷达 [训练知识展开] — 均独立成节写透 ✓
5. 利润池分布 [收料] — findings 覆盖 ✓
6. TOPS/制程/舱驾融合 [训练知识展开] — critic 补 制程/定点 后 ✓
7. 玩家阵营 [收料] — ✓
8. robotaxi 单位经济学变量 [附带] — ✓
9. 数据飞轮+两种飞轮 [训练知识展开] — ✓
10. 中美欧监管 [收料] — ✓
11. 智驾平权传导 [训练知识展开] — critic 消歧后 ✓
12. arena 吸引力信号 [附带] — ✓
13. **[v1 新增] 三大口径陷阱识别**（份额独立方案商vs整体/盈利UEvs全面/估值PSvsPE）— findings 揭示门外人最易被误导处，已有 findings 覆盖、无需二次收料 ✓

## 四、§ changelog（对全历史去重）

- **命门**：无增删无重排，仅置信度上调（命门1/3 中→中高，命门2 低→中）。凭据：44 份 findings 整体印证 thesis_v0 方向。
- **primer 入门目标**：**+1 新增「口径辨识」**（凭 mat-0ac4e9/079b09/e5fb63 揭示的份额/盈利/估值三重口径陷阱，是门外人核心盲点）；无坍缩/删除。该新增由现有 findings 覆盖，**不触发第二收料趟**。
- **对照全历史**：无震荡（无复活被砍条目）。
- **收敛判定**：命门 delta 基本空（仅置信度更新）+ primer delta（+1 已覆盖）；gap 双轴：uncovered_ks 空、uncovered_ring_inputs（arena-scoring）已由 market_data 填。**命门2 残留（robotaxi 含摊销真盈利）标 capped 候选，踢 07-drilldown**。convergence_status 首轮标 **open**，待 chain-critic 回来定稿。
