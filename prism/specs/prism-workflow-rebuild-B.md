# Prism Workflow 重构 · 方案 B（doctor 驱动 / 护栏内自由）

> 北极星设计。决定于 2026-06-22。目标：能力不变（中间数据/状态/web/产出全保留）、
> 质量不降、复杂度最低、LLM 自由最大。落点 ~1500-1800 行，**但真正的指标是"LLM 要同时
> 拿住的概念数"从「8 套 stage 流程 × N 步」塌成「动词 + doctor + 不变量」。**
> 受控迁移：先落共享层（不碰旧文件）→ 03 试点验证 doctor → 质量不降再铺开。

---

## 1. 设计原则

**系统由"产物契约 + 不变量 + 领域知识"定义，流程涌现而非规定。**

- 脚本管"对不对"——动词自带校验，非法状态直接 raise（不变量 = 脚本 guard）。
- 文档管"为什么这么设计"——只剩不可压的领域知识 + 无法机械化的底线。
- "怎么做"全部还给 LLM——路径、顺序、怎么搜、怎么读、何时开 subagent，自由发挥。
- stage 不再是"必须照走的状态机"，而是"带强制退出不变量的推荐弧线"。LLM 看 `doctor`
  报告哪条不变量未满足，自己决定下一步；可乱序、可批处理、可跳过已满足项。

**张力声明**：最大自由 ≠ 无约束。决策链与血教训是当年放任自由踩坑换来的质量脚手架，
该刚的用脚本 guard 刚到底。B = **护栏内自由**。

---

## 2. 新文件架构

```
workflows/
  _contracts.md   ~250  产物契约单源：topic.yaml / 各 sidecar / findings frontmatter /
                        编号体系(K#/R#/F#/KILL) / input_contract 8·6·5 表
  _knowledge.md   ~700  不可压投资 IP：6 环参数化(一份通用+三类差异) / 8 估值模型 /
                        宏观四层+机制纠错八条 / 来源分层+depth 降级
  _floor.md       ~120  血教训不变量(全 stage 适用)。能进 guard 的进 guard，此处只留无法机械化的
  _arc.md         ~120  推荐弧线图 + 每环退出不变量(I1..I8) + 各"能力"一段话(收料/抽料/合成/评审/监控/深挖)
  (删除 00..07 八份 stage 程序文档；其内容要么进 guard，要么进上面四份)
```

旧 `00..07.md`、`_web_prescan_shared.md`(383) 等程序文档 **整体退役**：流程进 doctor，
schema 进 _contracts，知识进 _knowledge，血教训进 _floor/guard，web 检索降为一个动词。

---

## 3. 不变量目录（新骨架 · 替代 stage 程序）

弧线不变量（推荐顺序，但 LLM 可任意可行顺序满足；doctor 报告未满足项）：

| ID | 名称 | 必须成立 | 强制方 |
|----|------|---------|--------|
| I1 | 立题 | topic.yaml 存在；type∈{company,industry,arena,macro}；scope.question 有；长 question→search_terms；company→ticker | 脚本(create_topic raise) |
| I2 | 定向 | thesis_v0 有可证伪 K#，frontmatter 含 revised_after_prescan/data_freshness；decomposition_v0 有 | 脚本(frontmatter 校验) |
| I3 | 路线 | roadmap 覆盖每个 K#（每条 L4 狩猎 addresses≥1 K#）；search_keywords 有 | 脚本(validate_roadmap_thesis_coverage) |
| I4 | 收料 | 每份 actionable inbox 资料登记入 manifest，addresses 非空 + rings；无 todo 处于 unattempted/error（R1/R2/R3 满足或诚实降级 empty/user） | 脚本 guard |
| I5 | 抽料 | 每份 actionable 资料 processed→findings 笔记存在、frontmatter 合法、addresses 有；索引已重建 | 脚本(set_stage guard + add_material schema) |
| I6 | 合成 | primer 过"门外人真懂"门；case 覆盖 6 环全部硬落地；sidecar 存在；thesis_v1 为 Scheme C 全快照十一段；来源分层已标；缺口诚实标注非编造 | 存在性/coverage 脚本 + 质量散文 |
| I7 | 评审 | critic verdict 已定；承重充分性横幅在；prescan_status 门禁已遵守 | 脚本(set_critic_verdict) |
| I8 | 监控 | monitoring tier 已设；proposal 一律 awaiting_confirm（绝不自动 confirm） | 脚本 |

横切不变量（FLOOR / 血教训，跨所有环恒成立）：

| ID | 不变量 | 强制方 |
|----|--------|--------|
| F1 | 每条 web finding 来自真实 hit，禁凭记忆补 URL | 脚本(register_web_search_batch 只收实 hit) |
| F2 | subagent 只产 markdown 到 final message，主 agent 落盘；禁 subagent 写文件 | 散文(无法机械强制)+dispatch facade 约定 |
| F3 | 研报/行业报告必经 mineru vlm；失败→报用户+跳过，禁 pymupdf 偷工 | 脚本(转换器锁 vlm)+散文 |
| F4 | _extracted/_vlm 为 slug 级确定性产物（跨 variant 复用）；findings 按 variant 隔离 | 脚本(路径布局) |
| F5 | todo 身份 = 文档非 K#；脚本零自动撮合，闭环须显式 | 脚本(无 auto_resolve)+散文 |
| F6 | gap 是诊断不是 gate：永不阻断推进，只供线索 | 脚本(gap_detector 不 raise)+散文 |
| F7 | 跨层借来的产出必标来源；本维度自跑，冲突本 topic 赢 | 散文 |

> 若任一弧线环无法用不变量表达、只能靠"按步骤走"，则 B 在该环退回方案 A（保留薄程序）。
> 03 试点的目的就是验证 I4/I5 能否纯靠不变量+doctor 驱动。

---

## 4. doctor 输出契约 + 样例

`prism doctor {slug} {variant}` —— 零 LLM，读 topic.yaml + manifest + findings 索引 +
outputs + gap_detector + prescan_status，报告：满足/未满足的不变量、阻断项、非阻断诊断、建议下一步、floor 提醒。LLM 读它自驱。

```
$ prism doctor cn-ai-compute opus4.8
topic: cn-ai-compute (industry) · variant opus4.8 · arc≈I5
satisfied: I1 I2 I3 I4
unmet:
  I5 抽料: 6/9 actionable 资料已 processed；3 份未抽 (mat-a1, mat-b2, mat-c3)
  blockers: 无 (无 unattempted/error todo)
diagnostics (非阻断):
  gap: K4 单源薄证；ring `industry-mirror` 未覆盖
suggested-next: 抽 mat-a1/b2/c3 → 满足 I5 → 进合成 I6
floor: 研报必 vlm · subagent 不写文件 · gap 仅诊断
```

LLM 看到这个，自己决定：批量抽三份料、或先去补 industry-mirror 的料、或判断 K4 薄证可
接受先推进——**不需要"读 stage 03 照步骤做"**。

---

## 5. 动词集（薄包装 facade，纯增量，现有 ~70 函数不动）

| 动词 | 作用 | 内部 |
|------|------|------|
| `prism doctor {slug} {variant}` | 状态体检+不变量报告+建议 | 串 read_topic/manifest/findings/gap_detector/prescan |
| `prism search ...` | web 检索：路由/落盘/去重/只收实 hit，一步到位 | 包 web_prescan + adapter（替代 383 行 SOP） |
| `prism fetch ...` | 物理抓取财报/公告到 inbox | 包 fetch_report/akshare 等 |
| `prism finding add {slug} {variant} --mat {id}` | 落盘+标 processed+重建索引+强制 frontmatter | manifest/findings |
| `prism case save / critic save / drilldown save / primer save` | 各产出落盘+状态更新+格式强制 | outputs/topic |
| `prism material add` | 登记资料，强制 addresses 非空+rings | manifest（guard） |

guard 增强：`set_stage()` 内置 unattempted/error 阻断；`add_material()` 强制 addresses。
prompt（独立反方/critic/deep-search）移 `prism/prompts/`，文档只 ref。

---

## 6. "能力"说明取代"stage 程序"（_arc.md 内）

每个能力只写一段：目标 + 该能力特有的 LLM 判断 + ref。例（抽料）：

> **抽料**：把资料转成 findings（满足 I5）。逐份 读→抽→写：留具体数字/可证伪事实/与共识
> 相悖点/矛盾，弃泛泛判断；六维(业务/财务/叙事/预期/镜鉴/风险)作检查清单不强制条数；
> 抽时扫 input_contract rings；冲突即 `prism search`（单份≤3）；单料不足撑 K# 可 dispatch
> 深挖 subagent(≤1)。工具：`prism finding add`。底线：见 F2/F3/F4/F6。

对比旧 03 的 647 行：同样能力，~12 行。差额全进了 doctor(流程)、_contracts(schema)、
_floor(底线)、脚本 guard(强制)。

---

## 7. 受控迁移与验收

1. **落共享层**（不碰旧文件）：_contracts / _knowledge(6 环参数化) / _floor / _arc。
2. **加最小动词**：`doctor` + `finding add` + `material add` guard（03 所需）。
3. **03 试点**：用 doctor 驱动跑 I4→I5，旧 00..03 存 `.bak`。
4. **双关验收**（与前几轮一致）：
   - 数据契约：真实 slug 跑动词后 `read_topic`+outputs 文件树+sidecar dump **diff 为空**。
   - 端到端：已有完整 case 的 slug 重跑 I5→I6→I7，6 环硬落地齐、来源分层在、critic 照常、
     无静默丢料/编造。**这正是验证 F1-F7 与决策链质量是否真保住。**
5. 通过→删 `.bak`，扩到合成(I6,最大去重杠杆)→I1-I3→I7/I8→search 动词收口 prescan。
   任一环验收不过→该环回退方案 A。

---

## 8. 与方案 A 的区别（备忘）

A=同 8-stage 骨架收紧文档(~2400)，LLM 仍"读 stage→照做"，只兑现目标 ~70%。
B=换骨架(contract+不变量+doctor)，LLM"看 doctor→护栏内自驱"，概念面塌缩，~1500-1800。
B 的"从 0"指设计从 0，护栏不清零。
