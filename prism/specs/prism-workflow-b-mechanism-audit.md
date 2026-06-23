# Prism 旧流程 → 方案 B 全机制对照审计

> 生成于 2026-06-23（branch `prism-workflow-rebuild-b`）。
> 方法：把旧 26 份 workflow 文档（现 `.bak`）逐文档拆出所有机制，逐条对照 B 模式的三个承载层
> （脚本 / 4 份新文档 / `prism/prompts/`），判定**保留 / 部分保留 / 未保留**及原因。
> 配套：`prism-workflow-rebuild-B-PLAN.md`（计划）、`prism-workflow-rebuild-B.md`（北极星）。

---

## 0. 结论（TL;DR）

- **能力/契约/血教训层：基本全保留。** 旧流程的机制绝大多数本就由**脚本**强制（~70 函数方案 B 一律不动），知识与不变量搬进了 4 份新文档，dispatch 模板搬进了 `prism/prompts/`。
- **被刻意删掉的是"怎么做"的手把手步骤**（Step 1/2/3…）——这是 B 的设计意图（"流程涌现而非规定"），不是回归。机制的**意图/不变量**以"能力段 + doctor + guard"形式保留，**规定动作顺序**不保留。
- **真正需要警惕的"散文知识/纪律"丢失**有 7 处（见 §3），其中脚本仍在、只是新文档没写，未来只靠 4 份文档驱动时 LLM 可能不知道该调/该守。已在本轮修复了评分标度等回归，但这 7 处属"迁移不全"，建议补。

承载层定义：
| 层 | 是什么 | 管什么 |
|----|--------|--------|
| **脚本**（`prism/scripts/*.py`，~70 函数 + 3 新 guard + doctor/search 动词） | 不变量的机械强制 | "对不对"——非法状态 raise |
| **4 新文档**（`_arc` 弧线/不变量/能力 · `_contracts` 契约/编号 · `_knowledge` 投资IP · `_floor` 血教训） | 不可压知识 + 退出不变量 | "为什么这么设计" |
| **`prism/prompts/`**（`critic_independent` · `deep_search` + 原有 `analyst_voice`/`output_quality_rubric`） | dispatch 模板 | subagent 怎么问 |

---

## 1. 按环对照（机制簇 → 承载 → 判定）

图例：✅ 保留 · 🟡 部分（意图在、细节/纪律降级） · ❌ 未保留（散文丢失，脚本可能仍在）

### I1 立题（旧 00-research-topic）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| create_topic 字段校验（company 必 ticker+short_name≤12；question>25字必 search_terms；slug 格式；查重 list_variants） | 脚本 guard（raise） + `_arc` I1 + `_contracts` topic schema | ✅ |
| type 终局倒推/终局由 type 独占（terminal_for_type / _TYPE_TERMINALS） | 脚本 `_TYPE_TERMINALS` + `_contracts` §二终环同源（本轮补回） | ✅ |
| question 三段式 + 红线（禁百科式/禁枚举终局）+ 地理不默认 CN | `_arc` I1 "question 含糊→追问聚焦命门" | 🟡 三段式细则压成一句"追问聚焦"；百科式软警告纪律未单列 |
| 多市场 extra_tickers | 脚本字段 + `_contracts` topic schema + `_floor` F11 | ✅ |
| 早期 ingest（register_inbox_materials 只登元数据不进 thesis，保 bet-first） | 脚本 `register_inbox_materials` | 🟡 函数在；"00 就先登记家底"的时机纪律未写进新文档 |
| **baseline_knowledge**（关键事实[fact-NN]+置信度+time_sensitivity / 盲点 / 第五节强制 query：快变+高中置信 fact 必有 query / §六回写校准 / 被推翻 fact 改 cite） | 脚本 `has_/read_baseline_knowledge` + `_arc` I2（压缩版，本轮补）+ `_floor` F11 | ✅ **见 §3-A**（已修压缩进 I2） |
| thesis_v0 四段式（≤80字+0-10强度 / 必有方向 / 落 type 终局 / K# 可观测可证伪 / 反方非稻草人） | 脚本 set_thesis guard + `_arc` I2（K# 可证伪 6 个月内可验证）+ `_contracts` 编号 | 🟡 K# 可证伪在；四段式具体格式 + "必有方向不能写取决于"未单列（v0 五段式仅 `_contracts` §七提一句） |
| decomposition_v0（命门1-3+置信度 / 每环 B 靶点 / primer 入门目标 v0 / 机械自检） | 脚本 set_decomposition + `_arc` I2 "命门是本研究特有核心不确定性" | 🟡 命门概念在；primer 入门目标 v0 + 终局环 B 靶点强制非空 + 机械自检清单未写进新文档 |
| Coverage 闭环 self-check（每 K# ≥1 todo addresses） | 脚本 `validate_roadmap_thesis_coverage`（doctor I3 本轮接入，只读） | ✅ |
| prescan 三态（full/partial/failed）+ failed 红字横幅 + force_failed | 脚本 set_thesis/check_prescan_health + `_arc` I2 | ✅ |

### I2/I3 定向·路线（旧 01-build-roadmap）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| roadmap L1-L4 分层（L1/L2 坍缩成 primer_scope / L3 争议喂④ / L4 逐条 addresses K# + search_keywords 必填） | `_arc` I3 "L1 假设→L2 证据→L3 来源→L4 todo" + 脚本 coverage | 🟡 L4 addresses + search_keywords 在；"L4 必写 search_keywords 否则跳过 prescan"、"不要拿长 question 当 query"(H4) 纪律未单列 |
| roadmap→thesis 闭环硬闸门（validate_roadmap_thesis_coverage SystemExit） | 脚本 + doctor I3（只读版） | ✅ 升级版闸门→doctor 不变量 |
| A 合同地板 + B 命门靶点 双轴收料 + 三项真欠供显式排期 | `_contracts` §二（8·6·5 + hard 三项）+ `_knowledge` §一 | ✅ |
| 父 topic 复用（list_parent_materials / set_parent_materials / resolve_parent_variant；复用排除 prescan 校准层；findings 必本变体重抽） | 脚本（全在）+ `_floor` F4（slug 级复用 + variant 隔离）+ F7 | ✅ |
| 历史类比落 mirror todo（喂环⑤，三项真欠供之一） | `_contracts` §二 historical/industry/arena-mirror（hard）+ `_knowledge` §一环⑤ | ✅ |
| fetch_report_prism 多市场路由（cninfo/SEC/HKEX/FCA/DART/TDnet/EDINET + fetch_many + guess_year/quarter + E7 命名） | 脚本（全在） | ✅ 脚本；路由表细节不在文档（属"怎么做"，可接受） |
| 一次性 prescan（recency_days=90 / 覆盖各槽 / 事件轴主 agent 自定不套固定后缀=F3 病根） | 脚本 `build_search_queries`/`prism search` + `_floor` F11（F3 病根） | ✅ |

### I4 收料 + web/autofetch 基础设施（旧 02 + _autofetch + _web_prescan + _web_search_routing/aggregation + _baseline）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| 三态盖戳 fetched/empty/error + R1 全覆盖 / R2 有效尝试 / R3 消费前兜底 | 脚本 mark_todo_fetch/pending_unfetched_todos + `_floor` **F10** | ✅ |
| empty 硬闸门（empty_undecided_todos 非空必 AskUserQuestion 决策 waived/will_collect，决策完前不进决策链） | 脚本 empty_undecided_todos + set_stage guard（新）+ `_floor` **A1** | ✅ |
| 闭环键=task/文档身份，禁 K# 自动撮合（auto_resolve_todos/suggest_*coverage* 已删） | 脚本（update_user_todo_status 加 guard）+ `_floor` **F5** | ✅ |
| prescan 与 todo 无交集 | 脚本 + `_floor` **F8** | ✅ |
| 零幻觉 URL（只引工具实返 hit） | 脚本 register_web_search_result 拒占位/编造 + `_floor` **F1** | ✅ |
| H2 失血救回（drop_ratio>0.8 / extract_url_features / domain_tier=llm-judged-official 二次 register / F4 域族晋升） | 脚本 register_web_search_batch + extract_url_features + `_floor` **F9** + `prism search` 动词 | ✅ |
| failure_mode 分流（upstream_empty / all_low_band / none）+ exit 码（20 vs 40≠empty）+ keypool 退避 | 脚本（adapter/keypool 全在）+ `_floor` **A3**（failure_mode 分流） | 🟡 failure_mode 在 A3；exit 码契约/keypool 退避梯/ping-pong 防护属脚本行为，文档不再述（abstracted 进 `prism search`，可接受） |
| add_material（addresses 非空 guard / rings 双轴 / dedup / 自动复制 materials/ / mineru_state=needs） | 脚本 add_material（addresses guard 本轮强化）+ `_contracts` manifest schema | ✅ |
| 研报 mineru vlm 必做（MINERU_TOKEN / 禁 pymupdf） | 脚本 convert + `_floor` **F3** | ✅ |
| gap 体检（detect_gaps 双轴；诊断不是 gate；*-mirror 必报红属预期） | 脚本 detect_gaps/snapshot_gaps + `_floor` **F6** + `_knowledge` §六 | ✅ |
| should_run_step0 智能增量扫（recency_days 决策表） | 脚本 should_run_step0 | ✅ 脚本 |
| **web-search 聚合**（>30 findings 必聚合 / `ws-aggregate-` 虚拟 mat_id / `aggregated_from` 必填否则 04 死循环 / 聚合写作纪律） | `_contracts` §五（本轮补）+ 脚本 `migrate_aggregate_findings` + set_output_referenced_mats | ✅ **见 §3-B**（已修进 §五） |
| Role α/β/γ prescan 豁免（list_unprocessed 默认 exclude_triggered_by） | 脚本默认参数 | ✅ 脚本默认 |

### I5 抽料（旧 03-extract-findings）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| findings frontmatter schema（mat_id/source_type/quality/bias/addresses/rings/conflicts_with） | `_contracts` §五 | ✅ |
| 取舍原则（留数字/分歧/进展，弃泛泛/套话；目标 15-20 条） | `_knowledge` §六 + `_arc` I5（留具体数字弃泛泛 + 六维检查清单） | ✅ |
| 五框架 A-E + F 决策链专项勾（扫 input_contract 类目喂 6 环，命中抽数字+打 rings） | `_arc` I5 六维检查 + `_contracts` §二 rings | 🟡 六维清单在；"F②抽数字锚不只抽看多看空"、"F①管理层当一等公民"等抽取细则压缩 |
| _extracted.md（年报 pymupdf）/ _vlm/full.md（研报 mineru）slug 级复用 + findings 按 variant 隔离 + materials/ 是 slug 级 | 脚本 annual_report_extractor/convert + `_floor` **F4** | ✅ |
| 父级 findings 健康检查（list_missing_parent_findings 三选一补救）+ 跨层借料标来源/本维度自跑/冲突本 topic 赢 | 脚本 list_missing_parent_findings + `_floor` **F7** | ✅ |
| subagent 不写文件（只产 markdown 到 final message，主 agent 落盘） | `_floor` **F2** + `prism/prompts/deep_search` | ✅ |
| 即兴 web-search（冲突触发 ≤3 条/份；triggered_by=03-extract 自动产 inline finding） | 脚本 register_web_search_batch + `_knowledge` §六 + `_arc` I5 | ✅ |
| 深挖 subagent 升级（≤1 层；adapter only；exit40 raise） | `prism/prompts/deep_search`（本轮抽出）+ `_floor` F1/F2 | ✅ |
| build_findings_index 重建（防 compact） | 脚本 + `_arc` I5 + `_knowledge` §六 | ✅ |
| **SEC section 处理**（parent htm skip / section→addresses 映射表 / _meta.yaml 跨 section） | 脚本（manifest parent_mat/sec_section 字段在 `_contracts`） | 🟡 **见 §3-F**：schema 字段在，section→addresses 映射与 htm-skip 过程未文档化 |

### I6 合成（旧 04-synthesize/* 全部）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| 六环决策链（公共骨架 + company④EV加总 / industry④arena6维 / arena④peer横比；不断链） | `_knowledge` §一 | ✅（本轮修回 6维标度 1-5 + 仓位档 >5/null） |
| 8 估值模型 A-H + 原型识别 + 估值矩阵汇总 | `_knowledge` §二 | ✅（逐字） |
| 宏观四层因果链 + 机制纠错八条 + fragility + 象限 + 地理主线 | `_knowledge` §三 | ✅（本轮补回 rule1/2/4/6 层级处置） |
| primer-first / 元目标逐字 / 起点诊断 / depth 降级 / 来源分层三类 / F17 深度门禁 + 注册顺序 | `_knowledge` §四 + 脚本 primer_quality_gate | ✅ |
| arena 6 维（1-5）+ tier 阈值（≥4/2-3/≤2）+ peer 财务脊柱 + F13 | `_knowledge` §五 | ✅（本轮修回标度） |
| 调度模式（主 agent 直做 + 并行 Write；唯一 subagent=critic；≤3 subagent ≤1 嵌套） | `_knowledge` §六 + `_floor` F2 | ✅ |
| chain-critic（链通/分工/目标达成/来源分层/硬落地；首轮断链跑第二轮） | `_knowledge` §六 | ✅ |
| thesis_v1 Scheme C 11 段全快照 + decomposition_v1 + B 轴有界 delta 重拆（≤2 轮 capped） | `_contracts` §七/§八 + 脚本 set_thesis/set_decomposition | ✅ |
| 各 sidecar schema（07_decision_kit / industry_to_arenas / peer_matrix / transmission_map）禁自创字段 + 可观测层 chain_links/honest_gaps/market_implied | `_contracts` §六 | ✅（本轮修回 1-5 标度 + 补回机器↔叙事一致性硬规约） |
| 增量重写判定（list_affected_outputs；fresh 跳过；critic-stale 读反方）+ 断点续跑（set_output_error/list_failed_outputs） | 脚本（全在）+ `_knowledge` §六 | ✅ |
| arena/company stub 创建 + 继承父 thesis_v0（强度父级-1） | 脚本 create_topic/set_thesis + `_knowledge` §一 | 🟡 机制在；"强度父级-1"、stub thesis 四段式继承标注的细则未单列（脚本不强制） |
| 即兴 web-search 上限对照（03≤3/份 · 04≤5/环 · 05≤50hit/轮） | `_knowledge` §六（即兴 web-search） | 🟡 即兴机制在；分环精确上限数字未全列 |
| **company Step 0.5 质量红线门控**（ROIC>WACC/FCF/负债率/商誉<30%/治理红线 → PASS/FAIL/quarantine 归档） | `_knowledge` §一环⑤（红线作证伪/kill，本轮加"非门控"说明）+ 脚本 get_quality_screen_data（可选 surface） | ✅ **见 §3-C**（已决：去 gate 不恢复，红线留环⑤） |
| 宏观横切 hook（company 强制接 transmission_map / macro_stamp / DCF 取 10Y 实际利率弹性 / 自注册 provisional） | 脚本 macro_xcut + `_arc` I8 | 🟡 **见 §3-D**：company 必接 macro 的硬要求 + macro_stamp 细则未进新文档 |

### I7 评审（旧 05-critic-review）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| 独立反方干净上下文 + 喂什么/瞒什么 + 方向对称（别只做空） | `prism/prompts/critic_independent`（本轮抽出）+ `_arc` I7 | ✅ |
| prescan 门禁封顶 verdict（failed→最高 request-more）+ partial 攻击起点 | `_arc` I7（本轮补）+ 脚本 get_current_prescan_status | ✅ |
| gap 体检起手 + 承重充分性 mandate（命门 K# + hard 输入逐条读内容判） | `_arc` I7 + `_knowledge` §六 + 脚本 detect_gaps | ✅ |
| daily-monitor 破位喂入（get_pending_thesis_review 作 critic 种子） | 脚本 get_pending_thesis_review + `_arc` I8（pending_thesis_review 触发 AskUserQuestion） | 🟡 marker→critic 起手种子的接线未在 I7 单述（机制在脚本） |
| 承重充分性横幅落 case 头（够/单线承重/不足；不足不配 approve） | `_arc` I7（本轮补）+ 脚本（幂等 Edit 约定） | ✅ |
| verdict 三选一 + stage 后效（set_critic_verdict 自动 set_stage/标 stale） | 脚本 set_critic_verdict（强制）+ `_arc` I7 | ✅ |
| Step 6.5 web-search 兜底（request-more 前先兜一轮）+ 6.5b 多子问题升 subagent | `_arc` I7 "缺口可 web-search 兜到的先兜一轮" + `prompts/deep_search` | ✅ |
| suggested_drilldowns 回流（thin/单线承重 → set_suggested_drilldowns append） | 脚本 + `_arc` I7（本轮补） | ✅ |
| request-rewrite 本对话续跑 04（≤4 份 / ≥5 升 thesis / 7.5a confirm 门） | 脚本 list_affected_outputs/set_output_status | 🟡 续跑循环的 confirm 门 + ≥5 升 thesis 提示是"怎么做"过程，未进新文档（脚本状态在） |

### I8 监控 + 深挖（旧 06-daily-monitor + 07-drilldown）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| 绝不自动 confirm（proposal 一律 awaiting_confirm，确认永远用户） | 脚本 + `_arc` I8 | ✅ |
| B 层分叉（kill/翻 bear 标 requires_thesis_review，重评留用户） | 脚本 propose_flips + `_arc` I8 | ✅ |
| scan 分桶（due_signposts/due_kills/price_breach/recurring_review/macro_due/macro_alert） | 脚本 monitor scan + `_arc` I8（本轮补 CLI + macro_due/macro_alert） | ✅ |
| 证据注册下沉 confirm（confirm_flip 时自动 register，triggered_by=06，URL 去重）| 脚本 confirm_flip + `_arc` I8 | ✅ |
| macro 零 LLM 路径（propose_macro_updates 写 kind=macro_input） | 脚本 + `_arc` I8（本轮补） | ✅ |
| monitoring_tier 三档（deep/watch/dormant；watchlist 才是成本闸） | 脚本 set_monitoring_tier + `_arc` I8 | ✅（注：旧 reading_guide 写 dormant/warm/hot 是过期笔误，脚本一直是 deep/watch/dormant） |
| **macro 闭环重估机制**（record_evaluation/regime_eval_log / 可证伪预测每承重边 / score_evaluation/edge_ledger/prior_verdict / apply_holding_staleness / holdings 必覆盖每持仓） | 脚本（全在）+ `_knowledge` §三·闭环重估（本轮补）+ `_arc` I8 macro 子段（本轮补） | ✅ 工作流指引已补：存快照→可证伪硬要求→战绩对账(edge_ledger 降级候选)→体制变盖持仓戳→holdings 全覆盖→reeval_pending 戳 |
| drilldown quick vs load-bearing 分级 + load-bearing 三动作 + resolve_suggested_drilldown + 默认不触发 04 重写 | `_arc` 深挖段（本轮补）+ 脚本 set/resolve_suggested_drilldowns | ✅ |
| drilldown Step 4.6 是否动摇 thesis 显式决策（补佐证/边缘修正/动摇标 stale）+ 收敛句 | `_arc` 深挖段（"动摇 thesis 时回 I6 局部更新 + 升版"） | 🟡 三类处理 + 强信号词触发升级的细则压缩 |

### 编号/契约/阅读（旧 _reading_guide_canonical + _input_contract + _baseline）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| 编号体系 K#/R#/F#/KILL/±10·N10 刻度/WWHTBT/mat-XXX 命名空间/v0→v1 是信号 | `_contracts` §一 | ✅ |
| input_contract 8·6·5 + hard 三项 + served_by + 终环同源 + 训练知识不计覆盖 | `_contracts` §二 | ✅ |
| 来源边界三分类（训练知识/findings[mat-XXX]/特色判断） | `_contracts` §九 + `_knowledge` §四 | ✅ |
| **stage 状态机**（01-roadmap→…→06-monitoring→done 线性序 + next_stage） | — | ⛔ **设计替换**：被 I1-I8 不变量 + doctor 取代；topic.yaml.stage 字段保留作 dashboard 兼容，不再驱动流程 |
| **_prism_reading_guide.md 生成**（00-primer 从 canonical 模板 cp 到每 topic） | canonical 模板已删；内容在 `_contracts` §一/§九 | ✅ **见 §3-G**（已验证无害）：无 live 代码生成它，wechat_export 仅过滤；单源在 `_contracts` |

### subagent 协议（旧 _subagent_deep_search + _subagent_fetch_material）
| 机制簇 | 承载 | 判定 |
|---|---|---|
| deep-search subagent（adapter only / exit40 raise / sidecar / final message 格式 / 升级判定） | `prism/prompts/deep_search`（本轮抽出） | ✅ |
| **fetch-material subagent**（dispatch 下载 PDF / ls -la 验证 >50KB / 不改 manifest） | — | ❌ **见 §3-E**：未抽进 prompts（主 agent 可直接 fetch_report，影响小） |

---

## 2. "刻意不保留"（B 设计意图，非回归）

这些**应当**消失，是 B 的核心——"怎么做"还给 LLM：

1. **所有 Step 1/2/3… 手把手程序顺序**（00-07 每份的分步脚本演示）。意图保留为 `_arc` 能力段 + doctor 报告 + guard，规定顺序不保留。
2. **stage 线性状态机**（next_stage 链）。替换为 I1-I8 退出不变量；LLM 看 doctor 自驱，可乱序/批处理/跳过已满足项。
3. **跨文件复制粘贴的同一段**（如三类 case 各抄一遍六环 / 多处重复 prescan SOP）。去重为单源（`_knowledge` 六环参数化 + `prism search` 动词）。
4. **教 LLM 通用技能的散文**（怎么搜、怎么读 PDF、怎么开 subagent 的通用解释）。

---

## 3. 真正需要补的"迁移不全"清单（脚本在、新文档没写）

> 这些**不是** B 设计意图删的，是搬运时漏了的散文知识/纪律。脚本多数仍在，但未来只靠 4 份文档驱动时，
> LLM 不会知道该调/该守。按影响排序：

**A. baseline_knowledge（中高影响）— ✅ 已修（压缩版进 `_arc` I2）** — 评估结论：**B 模式下仍必要**（它在 define-time/I2 操作化 F11，让 LLM 自报"自以为确定但极可能过时"的 fact 并强制校准——slot 式 prescan 抓不到这类风险）；但 6 段重型文件不必要。压缩为四要素（关键事实双标签 / 盲点 / 第五节强制 query：快变+高中置信必有 query / 第六节回写），二(人物)/三(产业链)折叠，〇基本信息保持 company-only。三类通用、company 最吃重（快变 fact 最多）、industry 最轻（多 慢变）。已写进 `_arc` I2 LLM 判断首条 + 保留 `{variant}/baseline_knowledge.md` 作 [fact-NN] cite 与回写审计；time_sensitivity 三分类仍单源在 `_floor` F11。

**B. web-search 聚合机制（中影响）— ✅ 已修（进 `_contracts` §五）** — 在 findings schema 后加"聚合 finding（单 K# >30 条 web hit）"子节：阈值（≤10 不聚 / 11-30 摘要 / >30 必聚）、`ws-aggregate-` 虚拟 ID、`aggregated_from` 必填（缺失→04 死循环原因）、`data_window`、引用传虚拟 ID、4 条写作纪律、回填脚本。

**C. company 质量红线门控（中影响）— ✅ 已决：去掉 gate，不恢复** — 决策（用户）：用户既已选定研究本公司，默认已过基础调研，进 case 前自动 quarantine 否决属越权，且违 F6（gap 是诊断不是 gate）。实际 B 模式下该 gate 已de-facto消失（唯一调用方 `_company_case` Step 0.5 已删，无新文档调 `get_quality_screen_data`）。处置：**不恢复前置 gate**；红线保留为 `_knowledge` §一环⑤ 的证伪/kill 诊断内容（已在），并加一行说明"红线是环⑤诊断/kill 不是 quarantine 门控"。`get_quality_screen_data` 脚本保留，可作环⑤可选输入surface红旗，但不门控。

**D. macro 闭环重估机制（中影响）** — 旧 `_macro_regime` Step 5：`record_evaluation`（写 regime_eval_log，自动校验，**可证伪预测每承重边必带 expected 方向否则报错**）/ `score_evaluation` + `edge_ledger` 跨版台账 + `prior_verdict` / `apply_holding_staleness`（体制变给依赖持仓盖 stale）/ holdings 必覆盖每持仓。脚本全在（record_evaluation/macro_xcut/eval_score）。新文档 `_knowledge` §三 只有框架 + 八条纠错；`_arc` I8 只有 propose_macro_updates。**闭环重估的工作流指引整段丢失**。→ 建议在 `_knowledge` §三 末补"macro 闭环重估"小节或 `_arc` I8 macro 子段。

**E. fetch-material subagent 协议（低影响）** — 旧 `_subagent_fetch_material`：dispatch 下载 subagent + ls -la 验证 >50KB + 不改 manifest。未抽进 `prism/prompts/`。影响小（主 agent 可直接 `fetch_report_prism.fetch`）。→ 可选补 `prompts/fetch_material.md`。

**F. SEC section 抽取过程（低影响）** — 旧 03 §2.1D：parent htm skip + section→addresses 映射表（item_1_business→[scope,K3,K5] 等）+ _meta.yaml 跨 section。`_contracts` manifest 保留了 parent_mat/sec_section 字段，但映射表与 htm-skip 过程没了。→ 影响仅限抽 10-K 的 topic，可选补。

**G. _prism_reading_guide.md 生成依赖（已验证：无害）** — 旧 00-primer 从 `_reading_guide_canonical.md`（已删）cp 到每 topic 生成 `_prism_reading_guide.md`。**已查证**：无任何 live 代码从模板生成该文件；唯一引用 `wechat_export.py:68/70` 是一条**排除**正则（把内部文件挡在公众号导出之外），文件不存在也不报错。内容已并入 `_contracts` §一/§九。结论：删模板**不破运行时**，仅"新 topic 不再自动生成 per-topic 阅读指南"——而该 per-topic 文件已无强依赖（单源在 `_contracts`）。→ **无需处置**（如想保留 per-topic 阅读指南体验，可让 primer 生成时改 cp `_contracts` 的相关节，可选）。

---

## 4. 建议处置（更新于 2026-06-23）

1. **A ✅ 已修**（压缩 baseline 进 `_arc` I2）· **B ✅ 已修**（聚合进 `_contracts` §五）· **C ✅ 已决**（去 gate 不恢复，红线留环⑤）。
2. **D（macro 闭环重估）**：✅ 已补。`_knowledge` §三末加"闭环重估"小节（存快照 / 可证伪硬要求 / 战绩对账 edge_ledger / 体制变盖持仓戳 / holdings 全覆盖 / reeval_pending），`_arc` I8 macro 子段加操作指针 + 主动词。脚本不动，无代码风险。
3. **E/F（低影响）**：可延后，按需补。**G**：已验证无害，无需处置。
4. 补完 D（若决定补）后再删 `.bak`（当前 26 份 `.bak` 仍是完整出处，随时可回查/回填）。

> 一句话：**框架层特性（variant 隔离、资料复用、父子链、契约、血教训、编号、不变量）全保留**；丢的是 7 处散文知识/纪律（A-G，脚本多数仍在）+ 刻意删的手把手程序。补完 A-D 即可认为"能力/质量不降"在文档层也站得住。
