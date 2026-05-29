---
name: prism
description: LLM 驱动的投资研究系统。触发词：研究 X / prism / 开始研究 / 研究主题 / 推进研究 / 更新产出 / 查看研究进度。用于对行业、竞技场、公司开展结构化投资研究，产出 8 份标准产出，可在 /prism 查看。
allowed-tools: Bash Read Write
---

# Prism — 投资研究系统

## 触发场景与路由

| 用户说 | 执行 |
|--------|------|
| 「研究 X」/ 「开始研究 X」 | 读 `prism/workflows/00-research-topic.md` |
| 「prism 推进 {slug}」/ 「继续研究 {slug}」 | 读 `topic.yaml` 判断当前 stage，跳转对应 workflow |
| 「生成产出 {output}」/ 「更新 {slug} 的 {output}」 | 读对应 `prism/workflows/04-synthesize/{N}-{name}.md` |
| 「合成 {slug}」/「生成产出 {slug}」 | 按 `topic.type` 读决策链路径文档（替代 _shared+01-08）：company → `04-synthesize/_company_case.md`；industry → `04-synthesize/_industry_funnel.md`；arena → `04-synthesize/_arena_funnel.md`。三类都是"理解先行 + 6 环决策链"，funnel 的环⑥ 折入旧 09/10 选拔 |
| 「生成入门 {slug}」/「primer {slug}」/「补 primer」 | 读 `prism/workflows/04-synthesize/00-primer.md`；**全类型统一 primer-first**——原材料 findings+thesis_v0+K#（+按 type 的财务/亲属产出），不依赖 01-08/thesis_v1。primer 由各路径 Step 2 在 case 之前调用 |
| 「评审 {slug}」 | 读 `prism/workflows/05-critic-review.md` |
| 「监控 {slug}」 | 读 `prism/workflows/06-daily-monitor.md` |
| 「深挖 {slug} 的 {问题}」 | 读 `prism/workflows/07-drilldown.md` |
| 「记录决策 {slug}」 | 读 `prism/workflows/99-decision-record.md` |
| 「关联 {slug}」/「relink {slug}」 | 跑 `topic.suggest_relatives('{slug}','{variant}')` 出机械候选（geo/cluster_tags/ticker 跨 sidecar/slug-token 加权打分），把候选完整贴对话→**LLM 判读谁是真父/子**→调 `topic.set_parent('{slug}','{variant}', parent_slug)` 确认。可随时重跑（双向、顺序无关）。建链后合成路径 Step 1 亲属 hook 自动复用亲属成稿产出 |
| 「查看 {slug} 进度」 | 直接读 `topic.yaml` 输出当前状态表格 |

## Prism Root

所有 topic 数据在 `prism/topics/{slug}/`：
- `topic.yaml` — 主状态文件
- `manifest.yaml` — 资料清单
- `outputs/` — 标准产出 markdown（00_primer 领域入门 + 01-08 核心 + industry 加 09 / arena 加 10 + 配套 _prism_reading_guide）

## Python Scripts（仅用于 CRUD，零 LLM 调用）

```bash
# 创建 topic
python3 -c "from prism.scripts.topic import create_topic; create_topic('slug', '显示名', 'industry', '研究问题', 'CN', 'deep')"

# 读 topic
python3 -c "from prism.scripts.topic import read_topic; import json; print(json.dumps(read_topic('slug'), ensure_ascii=False, indent=2))"

# 更新阶段
python3 -c "from prism.scripts.topic import set_stage; set_stage('slug', '02-gather-materials')"

# 更新产出状态
python3 -c "from prism.scripts.topic import set_output_status; set_output_status('slug', '01_business_panorama', 'fresh', version=1)"

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
5. **资料放 `prism/inbox/manual/`**（用户手动）或 `prism/inbox/auto/`（脚本下载）
