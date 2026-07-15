---
slug: us-coinbase
variant: opus4.8
version: 1
parent_version: 0
written_at: 2026-07-15
convergence_status: open
---

# decomposition_v1 — Coinbase (COIN)

> 厚料重拆（findings + case 决策链 + chain-critic）。delta 有界：命门2 置信度更新、命门1 表述精修，无新增/掉队/重排命门，primer 入门目标 delta 空。convergence_status=open（05-critic-review 尚未跑，条件③待定）。

## §changelog（v0 → v1）

- **命门2 置信度 低→中**：`[mat-c4de6d]` Coinbase-shaped hole（禁令主体=发行人非分销方）实质削弱"禁令击穿链条"空头论点；但 NPRM 未定稿 `[mat-adcede]`，未升到"高"。**凭 mat-c4de6d 复活证据充分，非震荡。**
- **命门1 表述精修（未改置信度=中）**：厚料揭示 Q1'26 S&S 占比抬升是"被动多元化"（分母塌、S&S 绝对额 -14%、内部 52% 集中稳定币）`[mat-fe0dd9]`——命门本身不变，但判定标准精修为"占比 + 绝对额双看"（反映进 kill 条件）。
- **命门3 维持=中·未定**：厚料给双向证据（Q1 费率口径 artifact 上升 vs FY25 -$384M mix 迁移结构性），周期 vs 竞争仍未分离。
- **无新增命门**：Circle 19-23% 集中度、K5 逆周期资本配置均为既有命门的子面/确认证据，不另立。
- **primer 入门目标**：无新增/掉队，仅表述精修（目标4补"S&S 内部集中"、目标8补"Coinbase-shaped hole"、目标10补"剔除自持币重估"）——**入门目标 delta 空**。

## 一、命门现状（命门 + 置信度 + 每环 B 靶点）

- **命门1 — 多元化利润地板的真实性**（置信度：**中·未定**）
  S&S 能否在熊市真正托底利润。厚料判定：**当前是被动多元化**（占比升靠分母塌）+ **内部高度集中稳定币（52%）+ 利率杠杆**。未被证伪也未证成——需看未来 2-4 季 S&S 绝对额能否恢复正增长。→ K1
  - 环①靶点：S&S 四项各自趋势/毛利（已覆盖）；环②靶点：base 反推已含 S&S 修复假设；环⑤靶点：kill=占比+绝对额双降。

- **命门2 — 稳定币监管方向性（护城河 vs 天花板）**（置信度：**中**，v0 低→中）
  GENIUS/CLARITY 对"稳定币余额付收益"的最终裁决。厚料：字面上"Coinbase-shaped hole"暂保住分销方 rewards 链条，方向偏"护城河"；**悬念在 NPRM 终稿**。→ K2
  - 环⑤靶点：kill=最终细则并入分销方返奖；signpost=CLARITY 文本 + GENIUS 细则终稿。

- **命门3 — 周期性崩塌 vs 竞争性侵蚀的区分**（置信度：**中·未定**）
  收入 -31% 里多少是周期性（会回来）、多少是竞争性 take rate 结构下滑（不回来）。厚料：FY25 -$384M mix 迁移是结构性证据、Robinhood 费率上行收敛；但 Q1 费率口径上未坍塌。**未分离——是"周期底"还是"价值陷阱"的核心裁决。**→ K3+K4
  - 环⑤靶点：kill=口径一致下 take rate 连续 2 季结构性下滑；镜鉴=2022 收入 -59% + 顺周期平台价值陷阱。

## 二、primer 入门目标现状（精修后 12 条 + 覆盖情况）

12 条入门目标（见 00_primer §14 自检清单）全部由 primer 覆盖，critic 校验 11/12 达标、1 条（Coinbase-shaped hole 机理）修订后收敛。无 findings 撑不起的入门目标（加密交易所/稳定币/监管是训练知识厚领域，公司事实层由一手 SEC + web 覆盖）。primer depth=deep、gate 通过。

## 三、收敛判定

- ① delta：命门 delta 基本空（仅置信度更新 + 表述精修，无新增/掉队/重排）；primer 入门目标 delta 空。✓
- ② gap 双轴：`detect_gaps` 全绿（no gaps detected），A/B 两轴红项均已被 findings 覆盖。✓
- ③ 05 critic：**未跑**（company 强制进 05-critic-review）→ 暂标 `open`，05 回来无重大反转则定稿 converged。
- 第二收料趟：**未触发**（delta 有界且不涉新命门收料）。
