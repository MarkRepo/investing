# AAOI 抽取 brief（workflow 03 共享上下文）

topic: us-aaoi | variant: opus5 | type: company | 价格锚: 2026-08-25 收盘 $113.15, 市值 $9.61B, P/S(TTM) 16.1x

## thesis_v0 核心（偏空 3.5/10）
生意侧变好（自有 InP 激光 fab + 美国产能 + Amazon 锁量），但**每股价值在漏损**、且**毛利率在收入翻倍时反而下滑**。
结论：不买（$113）/ 持有者降观察仓；目标价 $75-100；介入线 ≤$85；EV≈$100（−11%）。
核心命门 = 「30%→40% 毛利率」与「稀释后每股」能否同时成立。

多方最强反驳（务必主动找证据，不要只找支持看空的料）：①真瓶颈是 InP 激光芯片、AAOI 是极少数自有 fab 的非中国厂、2027 fab 产能 +350%；②Amazon 用 7.945M 权证/$40亿采购上限替代长约 = 需求担保；③301 关税 + 美国本土制造 + 德州 $20.9M 拨款 = 结构性护城河；④5 季连创纪录 + 一致预期 FY27 仅为管理层口径 44%，上修空间大；⑤CPO 放量或推后到 2029。

## K# 脊柱（Killer Questions，抽 finding 时对号入座）
- **K1｜收入曲线**：2026Q4 GAAP 收入 ≥$370M？<$330M 即证伪。（Q3'26 指引 $255-290M；管理层 FY26 「约 $1.1B」）
- **K2｜毛利率跃升**：非 GAAP GM 2027 任一季 ≥34%？2027H1 两季均 ≤31% 即证伪 40% 目标。（Q2'26 GAAP GM 27.7% vs 去年 30.3%；FY2025 30.0%）
- **K3｜稀释边界**：2027Q4 完全稀释股数 ≤105M？>115M 即漏损成立。（加权股数 Q2'25 56.77M → Q2'26 81.57M → Q3'26 指引 ~92.8M；2026-08 新签最高 $600M ATM；Amazon 权证 7.945M @$23.6954；2030 转债 ~2.885M @$43.31）
- **K4｜1.6T 兑现**：2026Q4 前 ≥2 家超大厂 1.6T 量产认证并按月发货？到 2027Q1 仍 1 家且月出货 <3 万只即证伪。（2026-03 >$200M 1.6T 首单，公司称 2026Q3 晚些发货）
- **K5｜产能利用率**：2026Q4 名义产能 65 万只/月时，反推实际月出货 >25 万只（利用率 >40%）？<25 万只即证伪「需求超产能」。（2027 末目标 93 万只/月）
- **K6｜客户结构升级**：是否出现第二个类 Amazon 锁量/权证结构？出现即需下调看空强度。（FY2025 前十客户占 96.6%；Digicomm 占 FY2025 收入 53.1%，2026-06-30 应收 $314M 中 $211M 欠自它；2017-2019 曾被微软流失打回原形）

## rings（决策链输入合同，命中即在 frontmatter 标 rings:）
- `consensus` / `valuation-anchor` — 卖方目标价、隐含增速/PE、一致预期 EPS/倍数、历史估值带。**要抽具体数字锚，不是"看多看空"**
- `mgmt-capital-alloc` — 掌舵人任期/track record、回购/分红/并购历史金额与回报、激励与治理、融资选择（ATM vs 转债 vs 权证）
- `historical-mirror` — 相似剧本怎么崩（2017-19 微软流失、2023 拟出售中国工厂退出光模块业务、板块历史倍数崩塌）
- `biz-moat-unit-econ` — 单位经济、ASP/成本/良率、自供比例、护城河来源
- `bull-bear` / `peer-comparison-financials` — 多空论据、同业倍数与毛利率同口径横比（旭创 15.3 / 新易盛 15.7 / Lumentum 26.4 / AAOI 16.1 / Fabrinet 3.3 P/S）

## finding 文件格式（写到 prism/topics/us-aaoi/opus5/outputs/findings_{mat_id}.md）
```markdown
---
mat_id: mat-xxxxxx
filename: {原文件名}
source_type: {manifest 里的 source_type}
extracted: 2026-08-26
quality: high|medium|low
bias: bull|bear|neutral
addresses: [命中的 K#]
rings: [命中的 ring code]        # 没命中可省略
conflicts_with: [其他 finding 文件名]   # 可选
conflict_note: 一句话                    # 仅 conflicts_with 非空时
---

## 核心数据点与事实
{bullet；格式「[来源] [时间] [主体/指标] [数值/结论]」}

## 叙事主线
因为 {X 数据依据} → 所以 {判断 Y} → 对投资意味着 {Z}   （3 句以内）

## 反常识/分歧点
{「市场预期/常识：xxx，本文表明：xxx」or「无」}

## 未回答问题
{1-3 条 or 省略此节}

## 质量备注
{数据新鲜度 / 分析师倾向 / 可信度及原因 / 与已有发现是否矛盾}
```

## 抽取取舍原则
- **保留**：有具体数字的事实（量、价、时间、占比）；与其他资料矛盾的信息；具体合同/客户/产能/认证进展；独有测算逻辑
- **省略**：无数据支撑的泛论；行业常识铺垫；风险提示套话；中间推导步骤；多份资料重复的共识数据
- 强度按 source_type 分流：`annual-report`/`sell-side-note`/`industry-research`/`sec-section` 抽 15-20 条；`web-search` 新闻/公告类抽 3-8 条即可，1-2 页公告 1-3 条；**绝不为凑数硬榨**
- 文件路径解析：`./.venv/bin/python -c "from prism.scripts.manifest import get_material_path; print(get_material_path('us-aaoi','{filename}'))"`，或直接 `prism/topics/us-aaoi/materials/{filename}`
- **数字必须来自资料原文**，不得用训练记忆补；资料与训练知识冲突时在质量备注里标明冲突点
