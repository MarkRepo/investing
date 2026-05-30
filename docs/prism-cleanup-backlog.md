# Prism 清理 + 修复 Backlog

> 记录在案，**暂不执行修复**。来源：2026-05-30 决策链重构（commit `fa81826`）后的旧流程删除安全性审计 + 轻量验证发现的 bug。
> 目标前提：**未来只用"决策链新流程"（`04-synthesize/_company_case|_industry_funnel|_arena_funnel|00-primer`），不再回到旧逐产出流程；有问题基于新流程修。**

---

## 0. 总纲发现：新流程当前并不自洽

旧流程删不掉的根因不是"舍不得"，而是**新决策链路径仍伸手引用 6 个旧文件里尚未折入的权威逻辑**。
所以"清理旧流程"实际上 ≈ "把这些逻辑折入新路径"的工作。在折入完成前，对应旧文件**不能删**。

---

## 1. 旧合成流程文件删除清单（按 verdict 分组）

审计方法：逐文件全仓 grep 入站引用（SKILL 路由 / workflow-doc / 脚本 / 测试 / docs / plan）+ 新路径产出覆盖对比 + 卡壳 topic 扫描。

### A. 保留（已被新流程改造成工具/共享库，删 = 断新流程）
| 文件                                       | 依据                                                                                                                                                  |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `04-synthesize/_shared.md`               | 重定位为共享工具库（gap体检/调度/Scheme C/thesis_v1/命门 delta 重拆/收尾/即兴 web-search）；三路径 + 00-primer + 05-critic + 00-research 全现役引用。仅其内部"01-08 分箱 + dispatch 段"已退休。 |
| `04-synthesize/09-industry-to-arenas.md` | `_industry_funnel.md` 明文"不删"：Step 3（6维评分）+ Step 6.5（sidecar schema）+ Step 6/6b（arena stub 创建 + thesis_v0 继承）被逐字引用。                                  |
| `04-synthesize/10-peer-matrix.md`        | `_arena_funnel.md` 明文"不删"：peer matrix + financial_data 横比 + Step 6.5（sidecar schema）+ Step 7/7b（company stub 创建 + 继承）被逐字引用。                         |

### B. 可删（逻辑已折入新路径，唯一阻碍是测试存在性断言）
| 文件 | 阻碍 | 删除前置 |
|---|---|---|
| `04-synthesize/03-narrative.md` | `test_phase3.py` 断言文件存在 | 移除该断言行；确认 `outputs.py`/`topic.py` 的 `03_narrative_ecology` key 处理（见 §2 注册表） |
| `04-synthesize/06-risks.md` | `test_phase3.py` 断言文件存在 | 同上（`06_risk_blindspots`）；环⑤ 已显式吸收风险/盲点/kill/signpost |

> ⚠️ B 组的"已折入"判定来自审计 agent 单遍阅读。真正删除前应人工二次确认新路径环⑤/③确实覆盖了旧 03/06 的全部 lens。

### C. 先折入再删（新流程仍依赖其未吸收的逻辑）
| 文件 | 未折入的逻辑 | 折入目标 |
|---|---|---|
| `04-synthesize/02-cycle.md` | §2 周期类型 / 历史复盘 / 六维定位 lens | 新路径环①/相应环 |
| `04-synthesize/04-expectations.md` | §模型库 估值模型 A–H **算法细节**（`_company_case §3.3` 唯一来源，现"仅查算法不照搬"） | `_company_case.md`（估值锚环②） |
| `04-synthesize/05-mirrors.md` | 对偶强制镜鉴（≥2 失败镜像 + 成功/失败回报损失区间）；仅 arena 半折入，company/industry funnel 无历史镜像 | 三路径环⑤ |
| `04-synthesize/07-decision-kit.md` | Step 3.5 sidecar YAML schema（dashboard 硬契约权威定义，`_company_case`/`_shared` 逐字引） | 折入新路径 sidecar 步 或 抽成独立 schema 片段 |
| `04-synthesize/08-feed.md` | Step 2 living-feed 追加规范（被 `06-daily-monitor.md` Step 4 引用）；`08_living_feed` 仍是活产出 key | `06-daily-monitor.md` 或新路径 |
| `03b-quality-screen.md` | 治理/业务质量红线 + PASS/FAIL→quarantine 闸门 | `_company_case.md` 收料/抽取门控 |

### D. 需人工定夺
| 文件 | 问题 |
|---|---|
| `04-synthesize/01-panorama.md` | 已退休，但 SKILL「生成产出 {output}」单产出重生成路由仍解析到它 + `test_phase3.py` 断言；取决于 §2 的 SKILL 路由重设计结论 |

### 产出覆盖对比结论
- 删旧 01-10 后"旧产、新不产"的全是 **markdown 正文**（10 个 .md）；**三个 .yaml sidecar（07/09/10）完整保留**（schema 逐字照旧步 Step 6.5/3.5）。
- 01-06 六份并列维度 → 折进单份 case 的 6 环；07md/09md/10md → 折进环⑥（yaml 保留）。
- `08_living_feed.md` 在新四文件里无对应，但 **05-critic / 06-daily-monitor 仍写入/升版它**，不会完全消失（仅丢"04 阶段初始落地口径"）。

---

## 2. 跨文件问题（无论删哪些旧文件都要处理）

| 项 | 位置 | 问题 | 状态 |
|---|---|---|---|
| SKILL「生成产出 {output}」路由 | `.claude/skills/prism/SKILL.md` | 旧指向 `04-synthesize/{N}-{name}.md` | ✅ 已改为指增量重写机制（`list_affected_outputs`）+ 同步去旧的描述/产出列表/示例 key |
| 历史验收测试 | `prism/scripts/test_phase1/2/3.py` | 硬断言旧 workflow 文件存在 | ✅ 已退役删除（非默认套件、无行为断言） |
| 过期文档（活文档） | `docs/architecture/prism-design.md` + `market_data.py`/`financial_data.py`/`findings.py` docstring | 引用旧文件结构/名 | ✅ 已更新（文件树/产出树/概述 + 4 处 docstring 重指向新归宿） |
| dated plan / archive | `docs/PLAN-PRISM-FUNNEL.md`、`docs/superpowers/plans/2026-05-07-*`、`prism/workflows/archive/*` | 引用旧文件 | ⏸ 保留不动（历史记录，非活文档） |
| **产出 key 注册表** | `prism/scripts/outputs.py`（`_OUTPUT_KEYS_LABELS`）/ `topic.py` | 见下方"重要修正" | 🚩 **DEFER · 需你决策**（与 §4.2 同源） |

> **§2 注册表 — 重要修正（执行时发现，原 backlog 判断有误）**：
> 原以为"删旧 key"即可。实地核查 `list_outputs`（`outputs.py:91`）逻辑是 **"key 不在该 topic `outputs_state` 就跳过"**——注册表是超集：
> - **删旧 key 只会让已完成的老 topic 不再显示其历史产出**（regress），对新 topic 零收益 → **不该删**。
> - 注册表的真实消费端是 **`app/routes/prism.py`（prism web UI）**，并有 web 契约测试 `tests/test_prism_scripts.py::test_list_outputs_returns_8_base` 锁定"只暴露 8 个标准 panel"。
> - 因此动注册表 = 动 `app/` 层 + 改 web 契约——你已说"app/ 那条线不管了"，故 **DEFER**，不在本轮执行。

---

## 3. 卡壳 topic（删旧文件前必须先迁移 stage）

SKILL 按 `topic.yaml` 的 `stage` 字符串路由；新链无 `10-peer-matrix` 节点 → 这俩删旧文件后无法续跑：

| topic / variant | stage | 备注 |
|---|---|---|
| `global-ssb-electrolyte/claude-opus-4-7` | `10-peer-matrix` | **有未提交改动，正在迁移中**；删旧文件前优先完成其 stage 迁移 |
| `global-in-vivo-gene-edit-rare-disease/claude-opus-4-7` | `10-peer-matrix` | 停在旧链最后一步 |

迁移动作：把 stage 改到新链对应阶段（`04-post-synthesis` 或 `done`）。其余 44 个 topic 的 stage 均不在旧名集合内。

---

## 4. 独立 Bug（与本次重构无关，轻量验证时发现）

### 4.1 gap_detector B 轴计数层错配
- **现象**：`detect_gaps` 的 B 轴（K# 覆盖）只数 `manifest.materials[].addresses`，**不数 `findings[].addresses`**（`gap_detector.py:198-204`）。
- **后果**：凡是在 03-extract-findings 阶段按 **findings 层**打 K# 标签（而非材料层）的 topic，B 轴一律误报"K# 全 0 覆盖"。`global-ssb-electrolyte` 实测：findings 层 K1:3/K2:2/K3:6/K4:1/K5:0，但 B 轴报 K1–K5 全 0。
- **影响面**：抽查全仓两种打标习惯并存——`cn-commercial-space`/`cn-rongchang-bio`/`cn-innovative-drug` 在材料层打标（B 轴正常）；`cn-dangsheng`/`cn-ganfeng`/`global-ssb-electrolyte` 等只在 findings 层打标（B 轴全误报）。
- **与流程无关性**：findings 带 addresses 是新旧流程的 03 共同产物；本次重构只给 findings 加了 `rings`，未动 `addresses`。bug 成因是脚本读错层。
- **修复方向**：B 轴证据计数改为 **findings 层 ∪ 材料层并集**（向后兼容材料层已打标的老 topic）。需配回归测试：构造"findings 有 addresses、材料无"的 fixture，断言 B 轴正确计数。修后 `global-ssb` 应得 `uncovered=[K5], thin=[K4]`。
- **改前**：按 CLAUDE.md 先跑 `gitnexus_impact` on `detect_gaps`（真实调用方在 workflow .md 的 `python -c` + 测试，代码图可能低估，对照 02/03/04/05/06 .md）。
- ✅ **已修复（2026-05-30）**：`detect_gaps` 证据计数改为 **manifest 材料 ∪ findings（own + reuse）按 mat_id 去重**。
  - **执行中修正**：原以为证据在 own findings 层。实测 global-ssb/cn-dangsheng/cn-ganfeng 的 K# 标**全在 reuse（父 parent_materials）findings 上，own 全无标**。父证据经 parent_materials 已进合成上下文、是可用证据，且 gap 是"诊断不是 gate"（reuse 护栏属合成期职责）→ **计入 reuse**，否则借父证据的子 topic 误报全红。
  - 验证：global-ssb → `uncovered=[K5], thin=[K4]`（符合预期）；cn-dangsheng → `uncovered=[], thin=[K4]`；cn-ganfeng → `uncovered=[], thin=[K1,K5]`。
  - 回归测试 +3（own findings 计入 / 材料与同源 finding 去重 / reuse 父 finding 计入），`gap_detector` 10 passed。

### 4.2 新流程 case 文档不在 dashboard 显示（执行 Step 5 时发现）
- **现象**：新流程产出的 `c_investment_case` / `i_industry_case` / `a_arena_case` **不在 `_OUTPUT_KEYS_LABELS` 也不在 `_EXTRA_OUTPUTS_LABELS`**（`outputs.py:12-30`），而 `list_outputs` 只显示这两张表里的 key。实测 `global-ssb-electrolyte` 的 `a_arena_case.md` 在盘上但 `list_outputs` 未列出。
- **后果**：**按新流程跑完的 topic，其核心 case 正文在 prism web UI 上看不到**（只看得到 sidecar yaml 经由别的路径、以及旧 key）。
- **根因**：重构加了新 case 键的产出与 `set_output_status` 注册（`outputs_state`），但**没把它们加进 web 展示注册表**；`topic.py:1254-1256` 有 type→case key 映射但 `outputs.py` 展示侧没跟上。
- **修复方向（与 §2 注册表同源，一起做）**：把 `c_/i_/a_*_case` 加入 `_OUTPUT_KEYS_LABELS`（或 `_EXTRA_OUTPUTS_LABELS`）；同步评估 `decomposition_v{N}` 是否要像 thesis 一样在 UI 露出。**牵动 `app/routes/prism.py` + web 契约测试 `test_list_outputs_returns_8_base`**（该测试断言"恰 8 个 base panel"，加键需同步改测试与契约）。
- **决策点（给用户）**：是否要在 prism web UI 上显示新 case 文档？要 = 接受动 `app/` 层 + 改 web 契约测试；不要 = 维持现状（case 文档只在文件系统/对话里看）。
- ✅ **已修复（2026-05-30，用户授权"修 #1"）**：把 `c_/i_/a_*_case` 三键加进 `_OUTPUT_KEYS_LABELS`（**state-gated**：仅当 synthesis 经 `set_output_status` 写入 `outputs_state` 后才显示）。
  - **关键发现：8-base 契约无需改动**。新建 topic 的 `outputs_state` 由 `_outputs_for_type` seed，**不含** case 键；`list_outputs` base 循环"键不在 outputs_state 就跳过"——故 fresh 行业 topic 仍恰返 8 panel，`test_list_outputs_returns_8_base` 原样绿（未动 `app/routes/prism.py`，body 路由 `read_output_html` 按 key 通用解析 `outputs/{key}.md`，case 正文自动渲染）。
  - **比 `_EXTRA_OUTPUTS_LABELS` 更优**：extra 表强制 status 恒 "fresh"+从 frontmatter 取版本；state-gated 取真实 status/version/last_error。
  - 验证：`global-ssb-electrolyte/claude-opus-4-7` 的 `a_arena_case` 现列为 panel（status=fresh, v2, file_exists=True）；+1 回归测试 `test_list_outputs_shows_decision_chain_case_after_synthesis`。web 契约 test_prism_scripts **19 passed**。
  - 残留小 quirk（未处理，超出本次范围）：新流程 topic 的 outputs_state 仍 seed 旧 01-08 键 → 这些以 "pending" 空 panel 显示。用户只要求让 case 露出，未要求隐藏旧 panel。

---

## 执行状态（2026-05-30）
1. ✅ **迁移卡壳 topic**（§3）——2 个 topic stage → `04-post-synthesis`；并修了 `_arena_funnel` 让 arena 跑完置旧名 `10-peer-matrix` 的根因 bug。
2. ✅ **SKILL 路由重设计 + 退役 test_phase1/2/3**（§2）。
3. ✅ **折入 C 组**（§1.C）——04→`_valuation_models.md`；05 对偶强制→三路径环⑤；02 周期→industry 环①；08→06-daily-monitor（含修 06 两处旧死引用）；03b→`_company_case` Step 0.5；07 转正保留。
4. ✅ **删 B 组 + 折入后 C 组 + D 组**（§1）——删 01/02/03/04/05/06/08/03b 共 8 个；213 测试绿。
5. 🔸 **过期文档已清**（活文档 prism-design.md + docstring）；**产出 key 注册表 DEFER**（§2 修正 + §4.2，牵动 app/，待你决策）。
6. ✅ **修 B 轴 bug**（§4.1）——`detect_gaps` 改为 materials ∪ findings（含 reuse）按 mat_id 去重；+3 回归测试；3 个真 topic 验证。

> **§4.2 已修（2026-05-30，用户授权"修 #1"）**：新 case 在 web UI 显示——见上 §4.2 ✅。未动 `app/routes/prism.py`、未改 8-base 契约（state-gated 巧解）。
> **唯一遗留（待你决策）**：§2 删旧 key——结论是**不该删**（删只会让老 topic 不显示历史产出，零收益），故无需动作；保持现状即可。
> **测试状态**：prism/scripts 216 passed；web 契约 test_prism_scripts **19 passed**（+1 case 显示回归）。tests/ 另有 20 失败+84 错误+3 收集错误，**全为既有 app/ ingest+web 层破损（import app.* 失败），与本次工作无关**（已逐一核实失败模块均不 import 本次改动的模块）。
