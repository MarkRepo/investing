# Workflow 06 — 日常监控 (Daily Monitor)

**触发**：用户说「监控 {slug}」或每日/每周定期运行
**定位**：快速扫描新信息，判断是否影响现有判断
**耗时**：目标 5-10 分钟

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

## 附录：monitoring_tier 三档定义

| Tier | 含义 | 触发 monitor | 需要的 outputs |
|------|------|--------------|----------------|
| `deep` | 持仓 / 候选标的 | 每日 + 重大事件 | 全 8/9/10 份 |
| `watch` | 值得关注但暂不投 | 每周 | 仅 01 + 02 + 06 |
| `dormant` | 历史归档 / 完成研究 | 不主动 | 全部，但不 refresh |
