# Workflow 06 — 日常监控 (Daily Monitor)

**触发**：用户说「监控 {slug}」或每日/每周定期运行
**定位**：快速扫描新信息，判断是否影响现有判断
**耗时**：目标 5-10 分钟

> **Web 搜索路径**：见 [[_web_search_routing]]（必读）。本步默认走 adapter；
> 仅事实校验类临时单查走 WebSearch tool。

---

## Step 0：gap 体检（每个 topic 扫一遍）

对今天选中的每个 topic（见 Step 1）跑一次：

```bash
python3 -c "
from prism.scripts.gap_detector import detect_gaps, format_summary
print(format_summary(detect_gaps('{slug}', '{variant}')))
"
```

把 report 输出**贴到对话**。重点看 `expired_web_materials`——daily-monitor 是天然的"web-search 刷新"时机：
- expired ≥1 条 → 触发 Step 1b 的 stale 重扫
- 顺带看 uncovered_ks / thin_evidence：如果新数据出现而 K# 仍薄弱，可在 Step 5 next_actions 里加"补 K# 证据"

这是诊断不是 gate——但 06 跑得频繁，是最好的"持续校准"卡点。

---

## Step 1：按 monitoring_tier 选择今日要扫的 topic

```bash
python -c "
from prism.scripts.topic import list_topics
import datetime
today = datetime.date.today()
all_topics = list_topics()

# deep tier: 每日扫
deep = [t for t in all_topics if t.get('monitoring_tier') == 'deep']
# watch tier: 每周二扫
watch = [t for t in all_topics if t.get('monitoring_tier') == 'watch' and today.weekday() == 1]
# dormant: 不主动扫
dormant = [t for t in all_topics if t.get('monitoring_tier') in (None, 'dormant')]

print('=== 今日监控清单 ===')
print('Deep tier（每日）:')
for t in deep:
    print(f'  - {t[\"slug\"]} ({t[\"variant\"]})')
print()
print('Watch tier（每周二）:')
for t in watch:
    print(f'  - {t[\"slug\"]} ({t[\"variant\"]})')
print()
print(f'共 {len(deep) + len(watch)} 个 topic 今日需监控')
"
```

如果用户指定了具体 slug，跳过此步直接处理该 topic。

---

## Step 1a：读取该 topic 的 Kill Criteria 和 Signposts

新流程的 kill / signpost 不在旧 markdown（`06_risk_blindspots.md` / `07_decision_kit.md` **已不再产出**），改读 sidecar + case 环⑤/⑥：

- **company**：`07_decision_kit.yaml` 的 `kill_criteria` / `signposts`
- **industry**：`09_industry_to_arenas.yaml` 的 `upgrade_triggers` / `monitor_metrics`
- **arena**：`10_peer_matrix.yaml` 的 `upgrade_triggers`
- 三类都可回看 case（`c_/i_/a_*_case.md`）环⑤证伪 + 环⑥行动 的原文叙述

```bash
# 读对应 type 的 sidecar（示例 company）
cat prism/topics/{slug}/{variant}/outputs/07_decision_kit.yaml
```

---

## Step 1b：web-search 周月扫 + stale 重扫（**新增**）

在等用户口头报新信息（Step 2）之前，先主动跑 `_web_prescan_shared.md`：

| monitoring_tier | recency_days | 触发频率 |
|---|---|---|
| `deep`    | 7  | 每日 |
| `watch`   | 14 | 每周二（Step 1 已过滤） |
| `dormant` | —  | 不主动 |

重点查询：
- topic 的 signposts 时点 **±7 天** 内的事件（catalyst 兑现/未兑现）
- Kill Criteria 相关关键词
- 该 topic monitor 上一次到今天的 gap 内 K# 相关进展

`triggered_by='06-daily-monitor'`。

**stale 重扫**（同步做）：
```bash
python3 -c "
from prism.scripts.manifest import list_expired_web_search
exp = list_expired_web_search('{slug}', '{variant}')
print(f'{len(exp)} 条 web-search material 已过期 (>90 天)，需用同 query 重跑')
for m in exp:
    print(f'  {m[\"id\"]} | query={m.get(\"search_meta\",{}).get(\"query\")}')
"
```
对每条 expired 用其 `search_meta.query` 重跑 `_web_prescan_shared.md` Step B-F；dedup（按 filename）会自动刷新 `search_meta.searched_at`。

---

## Step 2：用户提供新信息

询问用户：「今天有什么新信息需要评估？」

如果没有新信息，检查：
- 是否有定期数据发布（月度销量/PMI/价格指数）
- 公司是否有公告
- 行业是否有政策动态

---

## Step 3：逐条评估新信息

对每条新信息：

```
信息：{一句话描述}
来源：{来源}
日期：{日期}

影响评估：
□ 触发了 Kill Criteria？ 是/否
□ 验证了哪个 Signpost？ {或"无"}
□ 否定了哪个核心假设？ {或"无"}
□ 需要更新哪份产出？ {或"无需"}

结论：维持判断 / 小幅调整 / 需要重新评估
```

---

## Step 4：追加到信息流（living feed · 追加式日志）

`08_living_feed.md` 是**追加式日志**（不是综合产出精华汇编）：每次有新信息在末尾追加，不改历史；综合判断在 case / sidecar / brief，本文件只记"事件序列 + 触发反应"。

**文件不存在时，初次创建**（控制在 800-1200 字，只记三块：研究启动 + 当下不确定性 + catalyst 时点）：

```markdown
---
slug: {slug}
output_key: 08_living_feed
version: 1
generated: {timestamp}
---

# 信息流时间线：{display_name}

> 按时间顺序记录重要信息和判断变化。每次更新在末尾追加，不修改历史记录。
> 综合判断与 K# 校准请看 case / sidecar / brief，本文件只记录"事件序列 + 触发反应"。

## {YYYY-MM-DD} 研究启动 v1
**来源**：{topic_type} 研究{父级如有}
**主要事项**：研究问题 / v0 thesis 强度 / 资料覆盖 {N} 份 findings
**当时已知的主要不确定性**（3-5 条，每条 ≤1 句）：…
**已排好的 catalyst 时点**（仅时间+事件名，判断标准在 sidecar signposts）：…
```

**文件已存在时，末尾追加**（每条 200-500 字）：

```markdown

---

## {YYYY-MM-DD} {触发更新的事件简述}
**来源**：{资料名称 / 市场事件 / 数据发布}
**关键信息**：{具体事实，有数据带数据}
**对已有判断的影响**：支持了 {哪个假设} / 否定了 {哪个，或"无"} / 新增了 {哪个不确定性，或"无"}
**当前判断更新**：{如无变化写"维持原判断"}
```

追加后 `set_output_status('{slug}', '08_living_feed', 'fresh', '{variant}', version=N+1)`。

---

## Step 5：更新 next_actions

```bash
python -c "
from prism.scripts.topic import set_next_actions, read_topic
t = read_topic('{slug}', '{variant}')
current = t.get('next_actions', [])
current.append('下次监控建议关注：{重点}')
set_next_actions('{slug}', current, '{variant}')
"
```

---

## Step 6：仪表盘刷新（修 S5）

06-daily-monitor 通常不直接动 set_output_referenced_mats / set_thesis / set_critic_verdict，所以 dashboard **不会自动重建**。若本轮监控触发了 signposts/kill-criteria 状态变化（典型来自 04/05 重跑），那些路径已自动刷新；若仅本 workflow 手动追加 living_feed 想立即看 dashboard，再手动跑：

```bash
python -m prism.scripts.dashboard
```

否则等下次 04/05/thesis 升版自动触发即可。

---

## 附录：monitoring_tier 三档定义

| Tier | 含义 | 触发 monitor | 需要的 outputs |
|------|------|--------------|----------------|
| `deep` | 持仓 / 候选标的 | 每日 + 重大事件 | 全部（00_primer + case + sidecar yaml + thesis + living_feed） |
| `watch` | 值得关注但暂不投 | 每周 | 00_primer + case 核心环（②定价 / ⑤证伪 / ⑥行动）+ living_feed |
| `dormant` | 历史归档 / 完成研究 | 不主动 | 全部，但不 refresh |
