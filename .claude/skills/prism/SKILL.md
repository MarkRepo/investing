---
name: prism
description: LLM 驱动的投资研究系统。触发词：研究 X / prism / 开始研究 / 研究主题 / 推进研究 / 更新产出 / 查看研究进度。用于对行业、竞技场、公司开展结构化投资研究，产出决策链 case + 配套 sidecar，可在 /prism 查看。
allowed-tools: Bash Read Write
---

# Prism — 投资研究系统

## 触发场景与路由

> **B 模式（doctor 驱动）**：不再依赖 stage 状态机，改用 `prism doctor` 报告哪些不变量（I1-I8）未满足，
> LLM 自行决定下一步。四份核心文档：`_arc.md`（推荐弧线+不变量）/ `_contracts.md`（产物契约）/
> `_knowledge.md`（投资 IP：六环/估值/宏观/primer 规约）/ `_floor.md`（血教训 F1-F11）。

| 用户说 | 执行 |
|--------|------|
| 「研究 X」/ 「开始研究 X」 | 读 `prism/workflows/_arc.md`（立题/I1）。**先查重**：定好 slug 后跑 `list_variants('{slug}')`，非空则问用户意图（续做/新变体/另起 slug），勿默认盲建 |
| 「prism 推进 {slug}」/ 「继续研究 {slug}」 | 跑 `prism doctor`（见下方），读诊断报告决定下一步 |
| 「prism doctor {slug}/{variant}」 | `python3 -c "from prism.scripts.doctor import doctor; import json; print(json.dumps(doctor('{slug}','{variant}'), ensure_ascii=False, indent=2))"` 报告 I1-I8 满足状态 + 建议下一步 |
| 「合成 {slug}」/「生成产出 {slug}」 | 读 `prism/workflows/_knowledge.md`（§一 六环决策链 + §二 估值模型）。三类 type 共用六环骨架，差异见 §一.4；primer 规约见 §四。sidecar schema 见 `_contracts.md` §六 |
| 「生成入门 {slug}」/「primer {slug}」/「补 primer」 | 读 `prism/workflows/_knowledge.md` §四（primer 规约）；**全类型统一 primer-first**——原材料 findings+thesis_v0+K#（+按 type 的财务/亲属产出），primer 在 case 之前生成 |
| 「评审 {slug}」 | 读 `prism/workflows/05-critic-review.md` |
| 「监控 {slug}」 | 读 `prism/workflows/06-daily-monitor.md` |
| 「深挖 {slug} 的 {问题}」 | 读 `prism/workflows/07-drilldown.md` |
| 「关联 {slug}」/「relink {slug}」 | 跑 `topic.suggest_relatives('{slug}','{variant}')` 出机械候选（geo/cluster_tags/ticker 跨 sidecar/slug-token 加权打分），把候选完整贴对话→**LLM 判读谁是真父/子**→调 `topic.set_parent('{slug}','{variant}', parent_slug)` 确认。可随时重跑（双向、顺序无关）。建链后合成路径 Step 1 亲属 hook 自动复用亲属成稿产出 |
| 「查看 {slug} 进度」 | 跑 `prism doctor` 输出 I1-I8 满足状态 + arc 当前位置 |

## Prism Root

所有 topic 数据在 `prism/topics/{slug}/`：
- `topic.yaml` — 主状态文件
- `manifest.yaml` — 资料清单
- `outputs/` — 决策链产出：00_primer 领域入门 + 按 type 的单份 case（company `c_investment_case` / industry `i_industry_case` / arena `a_arena_case` / macro `m_regime_read`）+ sidecar yaml（company `07_decision_kit` / industry `09_industry_to_arenas` / arena `10_peer_matrix` / macro `transmission_map`）+ `_prism_reading_guide`（`thesis_v{N}` / `decomposition_v{N}` 在 `{variant}/` 根下）

## Python Scripts（仅用于 CRUD，零 LLM 调用）

```bash
# 创建 topic（variant 以 model_registry 规范名为准，如 'opus4.8'；旧别名 'claude-opus-4-8' 会被自动归一）
python3 -c "from prism.scripts.topic import create_topic; create_topic('slug', '显示名', 'industry', '研究问题', 'CN', 'deep', 'opus4.8')"

# 读 topic
python3 -c "from prism.scripts.topic import read_topic; import json; print(json.dumps(read_topic('slug'), ensure_ascii=False, indent=2))"

# 更新阶段
python3 -c "from prism.scripts.topic import set_stage; set_stage('slug', '02-gather-materials')"

# 更新产出状态
python3 -c "from prism.scripts.topic import set_output_status; set_output_status('slug', '00_primer', 'fresh', version=1)"

# 更新 next_actions
python3 -c "from prism.scripts.topic import set_next_actions; set_next_actions('slug', ['下一步内容'])"

# 更新 user_todos
python3 -c "from prism.scripts.topic import set_user_todos; set_user_todos('slug', ['用户待办'])"

# 创建 manifest
python3 -c "from prism.scripts.manifest import create_manifest; create_manifest('slug')"

# 添加资料
python3 -c "from prism.scripts.manifest import add_material; add_material('slug', 'filename.md', 'sell-side-note')"

# 标记已处理
python3 -c "from prism.scripts.manifest import mark_processed; mark_processed('slug', 'mat-abc123')"
```

## 关键规则

1. **所有 LLM 推断在对话里做** — Python 脚本只做文件读写
2. **每步结束后更新 topic.yaml** — 用脚本写 stage / next_actions / user_todos
3. **产出写入 `prism/topics/{slug}/outputs/{key}.md`**，然后调脚本更新状态
4. **Web 自动反映最新状态** — 无需手动刷新配置
5. **资料只在 topic 层**：用户手动放 / 脚本下载都进 `prism/topics/{slug}/inbox/`（已无全局 inbox），`register_inbox_materials` 登记元数据后由 02/03 处理
