---
output_key: 08_living_feed
slug: us-viking-vktx
variant: opus4.8
---

# 信息流时间线：Viking Therapeutics (VKTX)

> 按时间倒序追加关键事件 / 评审 / 监控翻牌。

---

## 2026-07-22 批评者评审完成

**来源**：Workflow 05-critic-review，独立反方 subagent（干净上下文对抗式、押相反方向＝重仓做空 VKTX）视角

**关键信息**：
- 致命一击＝**$10B 并购锚已被买家饱和结构性抽空**：辉瑞刚吞 Metsera、礼来/诺和/安进各有等同或更优自研，剩"既缺又买得起又没自研"的实质≤2 家＝没有 $15-20B 竞拍。该锚承载 Bull(22%)+Base-up(30%)＝52% 权重。
- 承重腿"52% 的 $10B 结局概率"是**训练估计/单线承重**，且混淆"临床成功"（机制已验证、概率高）与"$10B 并购结局"（历史基率约 10-20%）两个不同概率。
- EV +98% 存**算术偏高**：deep_dilution 是日历驱动的近端事件（$603M 现金卡在 2027 读出、必折价融资），却未打进 base/muddle 回报；bear 目标 $16 过浅（现金烧尽+稀释后应 $5-8）。

**对已有判断的影响**：
- 支持了：环⑤ 的风险清单与 kill 条件方向正确（买家饱和、稀释均已被作者列为 kill）；作者主动标"终局证据薄"诚实。
- 新增了：环②/④ 内部不一致——"并购锚是弹性非地基"自述 与 Base $86/Base-up 30% 权重实际依赖该锚 相矛盾。
- 调整了：EV +98% 判为偏高，须重算（稀释打折 + bear 打深 + 52% 拆两概率）后才可支撑⑥的仓位档位。

**当前判断更新**：
- verdict=**request-more**（承重腿单线承重，按 mandate 封顶不许 approve）。回 02-gather-materials 补三项：① GLP-1/GIP 二期→三期临床成功 base rate + 减重 biotech 被并购档位分布（拆 52%）；② 逐买家（LLY/辉瑞/诺和/安进/罗氏/AZ/默沙东）减重管线缺口尽调（判 $10B 锚是否已死）；③ 治理最新 proxy + 卖方逐家峰值销售模型明细。补料回来后 04 重算 EV。
- 多空方向**暂不翻**：作者最强一条腿（皮下机制已被替尔泊肽验证、78 周外推生物学合理）反方亦不硬攻；争议在"$10B 结局概率"与 EV 幅度，非"药能不能成"。

---

## 2026-07-22 critic 兜底 web-search 复评 → 升级 request-rewrite

**来源**：Workflow 05 Step 6.5，三路并行 sub-agent 深挖（走 adapter，35 条硬料入库 triggered_by=05-critic）

**关键信息**：
- **52% 被 base rate 证伪**：临床 Ph2→Ph3 去风险后 ~55-70%，但"$10B 结局" base rate 仅 9-15%（obesity ≥$250m 并购 2024 至今只有 Metsera 一笔）。作者混淆"临床成功"与"$10B 并购结局"两个概率——**原 +14pct 多头 edge 大概率反向**（真实 $10B 概率 ~10-15% ≤ 市场隐含 38%）。
- **买家池收窄 2-3 家**（诺和最强、默沙东真实、AZ/艾伯维偏授权），辉瑞刚饱和；但价格锚被辉瑞收 Metsera(~$100亿)反向坐实（VK2735 更后期，$10B 是下限）。
- **卖方极度分化**：Goldman 风险调整 $2.8B / 目标价 $30（低于现价！）vs 乐观 $21.6B，PoS ~13%；停药率 18-25% 是核心变量。
- 治理：2025 最新 proxy 已定位（Lian 持股~244万股、薪酬 96.8% 股权）。

**对已有判断的影响**：
- 调整了：verdict request-more → **request-rewrite**。承重腿有 base rate 可重算、降级规则解除。
- 新增了：Goldman $30 低锚（低于现价）+ $10B 结局 base rate 9-15% + 买家池仅 2-3 家，均为原 case 未纳入的硬约束。

**当前判断更新**：
- 原 EV +98% / 标准档买入**判为不成立**——建立在被证伪的 52% 上。stage=04-synthesizing，标 stale：c_investment_case + 07_decision_kit。
- 重写方向：环②纳入 $30 低锚+PoS 分歧；环④把 52% 拆成 P(临床成功)×P($10B|成功)、edge 重估（可能从 long 转 neutral/short-lean）、稀释打进 base/muddle、bear 打深至 $5-8；环⑥据新 EV 下修仓位档位。
- **多空方向可能翻**：待 04 重算 EV 后定。药大概率能成（临床 base rate 高），但"$10B 结局"被高估、现价对 Goldman 低锚已不便宜。

---

## 2026-07-22 case v2 重写完成（request-rewrite 收口）

**来源**：Workflow 05 Step 7.5c，主 agent 直做全快照重写（Scheme C）

**关键信息**：
- `c_investment_case` v1→**v2**、`07_decision_kit` v1→**v2**，均 fresh；stage 回 04-post-synthesis。
- **结论翻转**：v1「标准档买入 / EV +98% / accumulate」→ v2「**观望 / EV +8% / hold**」。current_zone accumulate→hold，position_tier 标准→试探/观望，initial 3%→≤1.5%、full 6%→3%、cluster 12%→10%。
- **edge 反向**：my_prob($10B 结局) 0.52→**0.12**，delta +14pct(long)→**−26pct(neutral)**；但**不做空**（临床 base rate 55-70% 高、右尾轧空风险）。
- 新增可观测 flip-up 触发：`buyer_named`（诺和/默沙东具名尽调→转买入）、`price_to_floor`（≤$30 Goldman 锚→小仓投机）。

**当前判断更新**：
- **观望（现价 $37.95 不买）**。药大概率能成，但"好资产、坏赔率"——市场已把临床成功 price in，$10B 结局被高估，现价对可信低锚 $30 不便宜。
- lingering P1：一手 fetch SEC 2025 proxy（Lian 精确持股%/comp）；逐家券商 rNPV model 明细需用户上传研报。
