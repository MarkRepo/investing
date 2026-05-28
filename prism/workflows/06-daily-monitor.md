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

```bash
cat prism/topics/{slug}/outputs/06_risk_blindspots.md | grep -A 20 "Kill Criteria"
cat prism/topics/{slug}/outputs/07_decision_kit.md | grep -A 30 "Signposts"
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

## Step 4：追加到信息流

将本次监控结果追加到产出 08（living feed），参见 workflow 04-synthesize/08-feed.md Step 2。

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
| `deep` | 持仓 / 候选标的 | 每日 + 重大事件 | 全 8/9/10 份 |
| `watch` | 值得关注但暂不投 | 每周 | 仅 01 + 02 + 06 |
| `dormant` | 历史归档 / 完成研究 | 不主动 | 全部，但不 refresh |
