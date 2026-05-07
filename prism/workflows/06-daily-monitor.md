# Workflow 06 — 日常监控 (Daily Monitor)

**触发**：用户说「监控 {slug}」或每日/每周定期运行  
**定位**：快速扫描新信息，判断是否影响现有判断  
**耗时**：目标 5-10 分钟

---

## Step 1：读取 Kill Criteria 和 Signposts

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
from prism.scripts.topic import set_next_actions, set_user_todos
set_next_actions('{slug}', ['下次监控建议关注：{重点}'])
"
```
