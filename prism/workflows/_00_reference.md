# Workflow 00 — 参考细节（执行时按需读 · 不在主执行动线上）

> 本文件收纳 `00-research-topic.md` 主线用 📎 指出来的所有细节：**query 措辞规范 / baseline 模板细节 / 字段清单 / 盖戳判定表 / inline 示例 / 附录 A 历史教训（rationale / 反例 / memory 链接）**。主线保「目标 → 产物 → 验收断言」；来龙去脉与照抄范例查这里。按 Step 号 / §A 号定位。

---

## 附录 A — rationale / 反例 / 历史教训（执行时可跳过，调试 / 维护时查）

> 本附录收纳从各 Step 主流程搬出的"为什么 / 反例 / 历史教训 / memory 链接 / inline worked example"。**主流程逐字未删、只是移出执行动线**；要看某步的来龙去脉，按 Step 号查对应小节。

### 附录 A4.5b — 4.5b 为什么是兜底地板而非第二轮普查

> **4.5b 是兜底地板，不是与 4.5a 并列的第二轮普查。** 若 4.5a 的 baseline §5 优先 query 已覆盖 `build_search_queries` 吐的槽（scope / industry-event 等），4.5b 只需确认覆盖、补未被覆盖的边角槽即可，**不必为已覆盖槽另写 query**。它的作用是兜住"§5 写薄"的情况（机械枚举不依赖 agent 想没想到）。

注意：此时 thesis 还不存在、roadmap 尚无 L4，`build_search_queries` 仅会枚举 **scope + company-event / industry-event / concept-update** 覆盖槽（无 l4-hunting 槽），这是预期的——本轮目的是为"写出靠谱的 thesis_v0"打地基，K# 类覆盖留给 workflow 01 prescan。逐槽 query 措辞按 `_web_prescan_shared.md` Step A 由主 agent 写。

### 附录 A1a — type→终局倒推的不可协商性

**终局不是 user 可选的**（type 锁死），后续所有环节（question / thesis K# / 命门 / 收料 / critic）都围绕这个终局倒推。

### 附录 A1b — question 三段式的 inline 示例与软警告规约

**全维度/百科式 question 的软警告规约**：若用户给的是「全维度/百科式」question，主 agent **不硬收窄**（宽行业地图有时本身是目的），但**必须**：
- 把 question 改写成「以终局赌注为主轴 + 宽覆盖作 scope 备注」
- 在对话显式回述改写后的终局赌注，让用户确认
- 例：用户说「全维度研究中国商业航天：市场空间、竞争格局、政策、技术路线、赛道筛选」
  → 改写为「中国商业航天（deep/CN/不含军工邻接）：预判利润池会落到火箭制造/卫星制造/卫星应用哪几个 arena，押可复用火箭迁移路径为分歧点——共识押卫星应用量产降本，我看好上游零部件标准化受益更确定。宽覆盖（市场空间/竞争/政策/技术）作 scope 背景备注。」

**short_name inline 示例**：
- 例：`display_name='荣昌生物 (RemeGen, SSE 688331)'` (30 字 UI 友好) → `short_name='荣昌生物'` (4 字 搜索友好)
- 例：`display_name='阿里巴巴 (BABA, HKEX 09988)'` → `short_name='阿里巴巴'`

**search_terms inline 示例**：
- 例：`question='荣昌生物作为中国领先的ADC+自免双管线创新药企业，全维度覆盖：商业化兑现节奏、海外授权回流'` → `search_terms=['ADC 商业化', 'BD 海外授权', 'IgAN 管线']`
- 这些关键词写入 `topic.yaml` 的 `scope.search_terms`，后续由 `build_search_queries` 作为 prescan 覆盖槽 hint 消费（脚本只给 hint，不代写 query）

**extra_tickers inline 示例**：
- 荣昌生物 A+H：`ticker='SSE_688331', extra_tickers=['HKEX_09995']`
- 阿里巴巴 H+ADR：`ticker='HKEX_09988', extra_tickers=['NYSE_BABA']`
- 中芯国际 A+H：`ticker='SSE_688981', extra_tickers=['HKEX_00981']`
- 漏填 = 后续 06-daily-monitor 拿不到第二市场资金/估值/公告 → thesis 写"AH 折溢价"时无结构化字段

### 附录 A3 — Step 3 意图分叉的分支细节与兜底

**换模型支详细流程（新变体复用旧料）**：

- **重注册 materials**——机械抽取层（年报 `_extracted.md` / 研报 `_vlm/`）是 slug 级共享、命中即跳过，**不重转 PDF**。复用**排除 prescan 校准层**（`addresses==['scope']` 或 `triggered_by` 为 `*-prescan*` 的 web-search 料：价/量/事件快照，时效性强，机械搬运会把过时事实当新赌注，违 `feedback_thesis_after_prescan`）；带 `K#` addresses 的**耐久文档**（财报/研报/drilldown/findings 源 + web-search 挖到的实质文档，validity 锚在出版日）照复用。**新变体一律自跑 prescan**（Step 4.5；复用模式会因本轮 0 注册误报 + prescan URL 不可构造，见 `project_variant_reuse_gotchas` 坑③④）。
- **findings 必须本变体重抽（走 03）**，禁止复制旧变体的 `findings_mat-*.md`。findings 是"本变体 thesis 的 K# 解读"，按变体隔离；复制旧变体 findings 会①污染"苹果对苹果"模型对比（等于让新模型抄旧模型的解读）、②引发 mat_id churn（编号脱钩）。换模型的价值正在于让新模型自己读料、自己解读。
- **`set_parent_materials` 引父级 findings** 仍合法——那是**跨 topic 父子复用**（行业父→竞技场子），与"同 slug 跨变体复制"是两回事。省略 `parent_variant` 时脚本按 `model_registry` 兜底解析（同模型/唯一/全登记自动选，多个异模型含未登记则 raise 让你问用户）。
- 复用同一批 materials 可隔离变量、让模型/架构差异苹果对苹果对比（详见 memory `project_variant_reuse_gotchas`）。

**stub 支判据细节**：（industry 环⑥派生 arena 时 `set_thesis(version=0, stage_set_at='00-init-from-parent')` 种下继承 thesis_v0，stage 仍 `00-init`、无 baseline/prescan/decomposition/todos、manifest 0 料）。判据：`read_topic` 显示 thesis 有 history 但 `outputs_state` 几乎空、`manifest` 0 料。

> 兜底（[skill-routing]）：即便跳过本步直奔 Step 4，`create_topic` 在 slug 已有其他变体时会打 stderr 提示——但那是最后一道防线，本步的"停下问用户"才是正解，勿依赖兜底跳步。

### 附录 A4.0 — 早期 ingest 为什么必须做 + 增量幂等

**为什么**：用户常在开研前把已有料（年报/研报/笔记）放进 `prism/topics/{slug}/inbox/`。若不在这里先登记，manifest 一直是空壳 → 00/01「建 todo 前查重」无家底可查 → 重复建已满足的 todo、重复 web-search。早期 ingest 让"建前查重"从 00 即生效。资料只在 topic 层（无全局 inbox）。

> **增量幂等**：本步是第一遍；用户本轮中途交付的料仍会在 02 / "推进 {slug}" 时被同一 helper 重扫登记（已登记的跳过）。

### 附录 A4.3 — 写训练知识 baseline 为什么必须做

**为什么必须做**：训练知识是研究的第一层数据源（web-search 第二层、用户兜底第三层）。先把"训练时记得什么"显式写下来，后续每条 web-search hit 都能对照"我有的 vs 新拿到的差在哪"。同时这份 baseline 是 Step 4.5a 优先 query 的来源——第四节盲点 → 第五节精准 query → Step 4.5a 主 agent 逐条 WebSearch 入库。

### 附录 A4.5 — Web Pre-scan 为什么必须做

**为什么必须做**：LLM 训练截止与当前时间往往有几个月到一年的差距，对**时效性强的标的**（公司财报/政策动态/股价估值/突发事件），跳过 prescan 直接靠训练知识写 thesis_v0 会把过时事实当成"初判赌注"，导致 K# 设错、user_todos 攻打错方向、后续整轮研究偏航。

### 附录 A4.5a — build_search_queries 不读 baseline 的原因

`build_search_queries` 只枚举 scope + 事件 + L4 的**覆盖槽**（给 hint，不代写 query），**且不读 baseline_knowledge.md**——主 agent 在 Step 4.3 baseline 第五节写的"自评盲点 → 想精准查的 query"必须在这一步手动落地，否则等于白写。

### 附录 A5.0 — thesis 目的 / V# 降级 / 后续何时更新

**目的**：让 LLM 在 Step 4.5 prescan 数据校准之后、阅读卖方深度研报之前先把"赌注"押下，后续所有研究都是去验证或推翻这个 thesis。
避免研究变成"百科全书式覆盖"，强制每条资料都要回答"这支持还是推翻我的初判？"

**不再单列"研究中重点验证项 V#" 段** —— V# 本质是 K#/Q# 的派生细化，作用是引导 workflow 01 路线图，但与 user_todos 重复。改为：**user_todos 直接承担验证项角色**，每条 todo 的 `addresses=[K#]` 标明它在攻打哪个论证目标（在 Step 5.3 体现；Q# 已降级，新 topic 不再用）。这样 thesis 收敛为 4 段，K# 覆盖闭环 self-check 矩阵保持二维（K × todo），不引入 V# 第三维。

**后续何时更新 thesis**：
- workflow 04 合成完成后写 `thesis_v1.md`（基于资料修正）
- workflow 05 critic 评审后若有重大反转写 `thesis_v2.md`
- workflow 07 drilldown 后或 workflow 99 决策记录前写新版本
- 每次 set_thesis 都 append 到 history，不删除旧版本——保留判断演化轨迹

### 附录 A5.0a — backfill_addresses_by_mapping 完整参考（fact-NN 模式专用）

> ⚠️ **适用前提（F2 订正）**：本步仅在 prescan 阶段（4.5a/adapter）把 web 材料 addresses 标成 baseline 事实编号 `fact-NN`（或 Q#）时才有意义。**当前默认约定（4.5a register 示例 + adapter `--addresses scope`）用的是 `scope`**——此时 `backfill_addresses_by_mapping` 没有 fact-NN 可重映，`updated_count` 恒为 0，本步是 no-op，**直接跳过**。
>
> 且 `scope` 本就不计入 K# 覆盖（addresses 三态表 scope=✗），所以漏跑**不会**让 gap_detector"误报 K# 全 0"——K# 覆盖实际来自 02/03 收的真材料（addresses 标 K#/Q#），与本步无关。
>
> **何时真要跑**：你显式改了 prescan 让命中按 `fact-NN` 标 addresses（想让 prescan 料也进 K# 覆盖），thesis 写完后才需要下面这段把 fact-NN → K# 重映。

```python
from prism.scripts.manifest import backfill_addresses_by_mapping

# 主 agent 写 thesis_v0 时已知道每个 K# 的论据来自哪些 fact-NN
# （baseline_knowledge.md 第二/三节列出了 fact-NN 内容，第六节有部分校准）
mapping = {
    # 'fact-04': ['K3'],          # 例：RC48 适应症 → K3 (RC48 终止/续)
    # 'fact-05': ['K3', 'K1'],    # 例：RC48-Seagen BD → K3 + K1 (RC148 BD 镜像)
    # 'fact-17': ['K4'],          # 例：财务数据 → K4 (业绩兑现)
    # ... 主 agent 列全 baseline 所有 fact-NN 与 K1..Kn 的映射
}
r = backfill_addresses_by_mapping(slug, variant, mapping)
print(f'backfill: {r["updated_count"]} 材料更新')
if r["unmapped_facts"]:
    print(f'⚠ 未覆盖的 fact: {r["unmapped_facts"]} — 补到 mapping 重跑或显式标注与本 thesis 无关')
```

**纪律（仅在用 fact-NN 标注的前提下）**：
- 必须在 set_thesis(version=0) **之后**调（先有 thesis 再有 K#）
- mapping 必须覆盖 baseline 里出现过且仍与本 thesis 相关的 fact-NN（脚本返回 `unmapped_facts` 给诊断）
- 一个 fact 可对应多个 K#（如 BD 历史 ref 同时支撑 K1 镜像 + K3 历史）
- **scope 约定下无需关心本段**：prescan 料以 scope 入库、不计 K# 覆盖，K# 论据由 02/03 真材料提供
- 升 thesis（v1/v2）时同样调一次（K# 可能新增）

### 附录 A5.2 — Q# 降级的来龙去脉

> **S1 · Q# 降级**：旧版在此另生成一套 `Q1-Q8` 研究维度编号，与 thesis 的 K# 形成双轨、且与 user_todos 重复（与 5.0 删 V# 同源问题）。**新 topic 不再生成 Q#**：
> - **能押注、可证伪的维度** → 升格为 5.0 thesis 的 **K#**（Killer Question），进入 thesis 脊柱；
> - **纯背景/理解性维度**（"这是什么生意/技术分类/产业链长什么样"）→ **坍缩成一行 primer scope 备注**，交给 00_primer 处理，不单列编号、不进 todo addresses。
>
> 简言之：研究维度要么变成可下注的 K#，要么变成 primer 的讲解范围。中间态的 Q# 取消。
> （旧 topic 已有的 Q# addresses 仍有效，gap_detector 本就只认 K#；`extract_research_questions` 保留向后兼容。）

### 附录 A5.3 — todo 闭环语义 / 产即收衔接 / 建 todo 前查重展开

> **闭环语义（钉死 · 详见 `_autofetch_protocol.md` 闭环键节 + memory `feedback_todo_closure_key`）**：闭环键是 **task/文档身份不是 K#**，闭环只走 `mark_todo_fetch`/`update_user_todo_status` 的 task 子串（禁止 K# 交集自动 done）。**本步特化**：A 合同必收类目（consensus/mgmt-capital-alloc/historical-mirror）**可以不挂任何 K#**；下面 5.3 的 Coverage self-check 是**反方向**校验（每个 K# 至少有 1 条 todo 瞄准），与「todo 收齐没」无关。

> **产即收衔接**（总规约见 `_autofetch_protocol.md` 产即收节）：本阶段（00）产的 pending todo **由 00 自己在 Step 6.5 当场抓**。**关键时序（00 特化）**——todo 产在 thesis_v0（5.0）**之后**、赌注已锁定，此时 eager-fetch **不污染 bet-first**：bet-first 由 Step 4.5 prescan 前置（只校准事实、`scope` 入库、永不碰 todo）担保，与"fetch 放哪一步"无关。01 Step 5.6 **只补抓 01 自己 Step 2/3 新增**的 L4/A合同 todo（并按 R3 重试 00 遗留的 `error`），不重抓 00 已 `fetched`/`empty` 的。

**建 todo 前查重展开**（主 agent 先 `read_manifest` 扫已有料，按文档身份判：已有料 → 建成 done 填 covered_by 或不建；没有 → 建 pending）。按文档身份判（不是 K# 撞 K#）——一份挂 K2 的旧价新闻不等于"年报全文"已收。

### 附录 A5.4 — decomposition 前移的理由与冷启动可靠性原理

> **为什么前移到这里**：拆解（把"赌注"拆成 1-3 个**命门**——最决定成败、最该砸资源验证的特化问题；**以及"门外人入门要掌握什么"的 primer 入门目标**）本是合成活动，但它**驱动收料方向**。前移到 00 用薄知识产一份 `decomposition_v0`，让 01/02 既照 A 合同地板收料、又照命门 B 靶点收料、还照 primer 入门目标补背景料。深度版（v1）留到 04 写作期做有界 delta 重拆（见 `04-synthesize/_shared.md`）。
>
> **冷启动断点 = 训练知识 + baseline + prescan**：此刻还没厚资料，命门基于 thesis_v0 + K# + `baseline_knowledge.md`（含 §六 prescan 校准）拆。**薄拆解可靠性原理上无法认证**（任何裁判也薄知识绑定）→ **v0 不做 LLM critic**，只做置信度 tag（收料对冲用）+ 机械自检。真正的可靠性闸门是 04 厚料 delta 重拆。

### 附录 A6.5 — eager-fetch 为什么在这里

> **为什么在这里**：Step 6 刚把 5.3 的 user_todos 写进 topic.yaml。按 `_autofetch_protocol.md` 总规约「谁产 todo 谁当场收」——**00 产的 todo 必须在 00 当场抓**，不甩给用户、不推给 01。本步在 thesis_v0（5.0）**之后**，赌注已锁定，eager-fetch **不污染 bet-first**（bet-first 由 4.5 prescan 前置 + prescan 不碰 todo 担保，与 fetch 置点无关）。
>
> 收料协议完全复用 `_autofetch_protocol.md`（R1 全覆盖 / R2 有效尝试 / R3 重试），与 workflow 01 Step 5.5/5.6 同源；闭环键 = **task/文档身份**（`mark_todo_fetch` + `update_user_todo_status`，**禁止 K# 交集自动 done**）。
>
> 作用域 = Step 6 写入的全部 `pending` todo（含 `hard`）。唯一与 01 的不同：00 此刻**还没有 roadmap**，收料对象是 `user_todos`（非 `roadmap.material_priority`），report 类 todo 的 ticker 由主 agent 按公司名现场映射。

### 附录 A6.5e — 硬闸门为什么必须做 + 与 01 同源

> **为什么必须做**：Step 6.5b/c 的「产即收 + R1 全覆盖」如果只靠散文纪律，主 agent 容易在 prescan 已跑完 10+ query 后把「我觉得搜不到」标记为 `empty`，跳过实际搜索。6.5e 硬闸门现在做了两层校验：
> 1. `pending_unfetched_todos` 拦截 `unattempted`（从未调到过 `mark_todo_fetch`）
> 2. `verify_empty_todos_searched` 拦截无痕 `empty`（`web_search_log` 中找不到对应搜索记录，adapter 自动留痕，原生 WebSearch tool 需调 `log_native_websearch()`）
>
> **Momenta 实战案例**：3 条 `empty` 中 2 条是伪 empty——补搜后全部命中。如果有这道脚本校验，标 `empty` 时就会因为 `web_search_log` 无痕而 `SystemExit(1)`，提前阻断。
>
> **与 01 Step 5.8 同源**：01 已有等效闸门，02 Step 6 也接入了同一套 `verify_empty_todos_searched`。

---

## inline 示例 / 字段清单 / 措辞规范（主线 📎 指向这里）

### Step4 · create_topic 全参

```bash
python3 -c "
from prism.scripts.topic import create_topic
create_topic(
    slug='{slug}',
    display_name='{display_name}',
    topic_type='{type}',
    question='{question}',
    geo='{geo}',
    depth='{depth}',
    variant='{variant}',
    # company 类型必填 ticker；industry / arena / concept 不填
    ticker='{ticker_or_None}',          # e.g. 'SSE_688331' / 'HKEX_09995' / 'US_AAPL'
    # AH 双重 / ADR / 多重上市必填；单市场或非 company 留 None
    extra_tickers={extra_tickers_or_None},  # e.g. ['HKEX_09995'] / ['NYSE_BABA'] / None
    # company 必填 / industry/arena 可选；≤12 字，纯主体名（搜索查询用）
    short_name='{short_name}',  # e.g. '荣昌生物'（display_name 通常含 ticker/英文名 不能直接搜）
    # question 超 25 字时必填；脚本不做关键词提取，长 question 漏填会 raise
    search_terms={search_terms_or_None},  # e.g. ['ADC 商业化', 'BD 海外授权', 'IgAN 管线'] / None
)
print('创建成功')
"
```

### Step4.5 · adapter 路径与 sidecar

> **Web 搜索路径**：本步走 **adapter**（详见 [[_web_search_routing]]）。
>
> ```bash
> python3 -m prism.scripts.web_search search "<query>" \
>     --intent news --days 90 \
>     --max-results 5 --output sidecar \
>     --slug <slug> --variant <variant> \
>     --triggered-by 00-prescan-baseline \
>     --addresses scope
> ```
>
> **sidecar 模式只写 raw 不入库**（2026-05-28 修法）：上面命令会把 raw hit 写到 `prism/topics/{slug}/inbox/_websearch_raw/{ts}_{qhash}.json`，**不**调 register。主 agent 用 `review-digest` 看 index 判 tier（勿 Read 整 json，见 `_web_prescan_shared.md` Step C）→ 调 `register_web_search_batch` 入库。
> 退出码 40（all_exhausted）→ WebSearch tool fallback，再用 `postprocess` 子命令兜回 sidecar（postprocess 自动调 register），详见 [[_web_search_routing]] §双向 Fallback。
>
> domain_tier 由主 agent 在 H2 救回流程里判（参 `_web_prescan_shared.md` Step C），adapter 不预判权威源。

**执行三段：先跑 baseline 优先 query → 再跑覆盖槽 prescan（`build_search_queries` 清单逐槽写 query）→ 回写 baseline 校准结果。三段都做完才进 Step 5。**

### Step4.5a · 读 §5 + register 范例 + 限流细则

```bash
# 1. 读 baseline 第五节
sed -n '/## 五、需要 web-search 校准的优先项/,/^##/p' prism/topics/{slug}/{variant}/baseline_knowledge.md
```

主 agent 对每条优先 query 按 `_web_prescan_shared.md` Step B.1 并发限流规约跑：
1. **5 并发一批 + 批间 10s**（不要一次 message 里塞 10 个 WebSearch 并行，会触发**静默**限流）
2. 调 `register_web_search_batch(triggered_by='00-prescan-baseline', ...)`，**显式读返回的 `failure_mode`**（'upstream_empty' / 'all_low_band' / 'none'）
3. ≥3 条 `failure_mode='upstream_empty'` → 等 30s 串行重试这些 query（30s 一条）；`'all_low_band'` 走 H2 救回不是重试
4. 串行重试仍多数 upstream_empty → 转 _web_prescan_shared.md Step B.2 兜底（WebFetch 已知权威 URL）

```python
from prism.scripts.web_prescan import register_web_search_batch
r = register_web_search_batch(
    slug='{slug}', variant='{variant}',
    query='baseline 第五节优先项的具体 query',
    addresses=['scope'],  # 此阶段还无 K#，先用 scope 占位
    triggered_by='00-prescan-baseline',
    hits=[...],
)
if r['failure_mode'] == 'upstream_empty':
    # 真的限流——等 30s 串行重试本 query；连 3 个转 B.2 兜底
    ...
elif r['failure_mode'] == 'all_low_band':
    # 非限流，H2 救回未启动——extract_url_features + LLM 判 tier + 二次 register
    ...
```

### Step4.5c · 第六节回写模板

```markdown
## 六、prescan 校准结果（{iso_ts} 回写）

> Step 4.5 prescan 入库 N 份 web-search material 后，对照第一节 fact-NN 的更新：

### 被推翻（高优先级——thesis_v0 不要再引用原 fact）
- `[fact-03]` 训练时"2024 EV 销量 1450 万"，被 `[mat-xxxx]` 推翻：实际 1520 万 → 误差 4.8%
- `[fact-07]` 训练时"公司 PE 18x"，被 `[mat-yyyy]` 更新：当前 28x → 估值认知必须重置

### 被验证（可继续引用，置信度提升）
- `[fact-01]` 2024 全球 EV 1450 万 → `[mat-zzzz]` 一致，置信度 高 → 高+

### 仍未校准（thesis_v0 引用时标 uncertain）
- `[fact-NN]` ...
```

### Step6 · set_user_todos 范例 + 字段约束

```bash
python3 << 'EOF'
from prism.scripts.topic import set_stage, set_next_actions, set_user_todos
from prism.scripts.web_prescan import check_prescan_health

slug = '{slug}'
variant = '{variant}'
h = check_prescan_health(slug, variant, expected_queries={n_priority_queries})

set_stage(slug, '01-roadmap-pending', variant)
set_next_actions(slug, [
    '运行 workflow 01-gather：制定路线图 + 自动收料 + 登记',
    '收集 P0 资料后运行 workflow 01-gather 登记',
], variant,
    prescan_status=h['status'],
    prescan_failure_reason=h['failure_reason'],
)
set_user_todos(slug, [
    {
        'task': '下载头部车厂全固态 SOP 时间表声明（IR/技术发布会）',
        'priority': 'P0',
        'info_tier': 'half_public',
        'addresses': ['K1'],
        'source_hint': '公司 IR 网站，需英日文阅读',
    },
    {
        'task': '下载3份对比卖方深度报告（中信建投/中金/申万任选3家）',
        'priority': 'P0',
        'info_tier': 'public',
        'addresses': ['K3', 'K6'],
        'source_hint': '同花顺/Wind/卖方公众号',
    },
    # ... 更多 todo
], variant)
EOF
```

字段约束（由 `_normalize_todo` 校验，不合规会直接 raise）：
- `priority`: P0 / P1 / P2
- `info_tier`: public / half_public / hard
- `addresses`: list[str]，元素为 `K#`（thesis Killer Question 号）
- `status`: pending / in_progress / done（缺省 pending）


### Step6.5a · 茅五泸多 ticker fetch 循环

```python
from scripts.fetch_report_prism import fetch
from prism.scripts.topic import mark_todo_fetch, update_user_todo_status

# 例：todo "下载茅五泸三家 2025 年报 + 2026Q1 季报"
tickers = {'茅台': 'SSE_600519', '五粮液': 'SZSE_000858', '泸州老窖': 'SZSE_000568'}
got = []
for name, tk in tickers.items():
    try:
        got.append(fetch(tk, report_type='annual', year=2025, slug=slug, variant=variant))
        got.append(fetch(tk, report_type='quarterly', year=2026, quarter=1, slug=slug, variant=variant))
    except Exception as e:
        print(f'{name} {tk} ✗ {e}')
# fetch() 登记 manifest，并按公司名把命中 todo 的 status 置 in_progress；但**不设 fetch_status、不闭环 done**
# → 必须由下面的 mark_todo_fetch + update_user_todo_status 显式闭环（闭环键 = task 子串/文档身份）
mark_todo_fetch(slug, variant, '茅五泸三家 2025 年报', 'fetched', note=f'cninfo {len(got)} 份')
# covered_by 要 manifest 主键：material dict 的字段名是 `id`（不是 `mat_id`）；fetch() 返回 Path，需按 filename 反查
from prism.scripts.manifest import read_manifest
_idx = {m['filename']: m['id'] for m in read_manifest(slug, variant)['materials']}
covered_ids = [_idx[p.name] for p in got if p.name in _idx]
update_user_todo_status(slug, variant, '茅五泸三家 2025 年报', 'done', covered_by=covered_ids)
```

### Step6.5a-ann · A 股公告 list/download 范例

> `fetch()` 默认 `with_announcements=False`，**不再隐式拉全年公告**（旧默认会把可转债发行人的
> `kzz` 全量公告流——临床/回购/董事会/辞职/议事规则——全灌进抽取队列）。公告改走显式三步，
> 由 LLM 看标题决定拉哪些（关键词黑名单杀不准催化剂、也漏不掉治理噪音）。**本段用 `./.venv/bin/python`。**

```python
from scripts.fetch_report_prism import list_announcements_cn, download_announcements_cn

# 1) 列表（只拿标题，不下载）——对每个目标 ticker
anns = list_announcements_cn('SSE_688506', days=180)
for i, a in enumerate(anns):
    print(i, a['date'], a['category_key'], a['title'])
```

2) **主 agent 读标题清单，按 thesis/K# 判定 selected**（判断留对话里，不写进脚本）：
   - **拉**：临床读出/适应症获批/BLA·NDA 受理/BD·License/重大合作/业绩预告·快报/与命门直接相关的自愿披露；
   - **丢**：议事规则/信息披露·薪酬管理制度/辞职·换届/股东会通知·会议资料/利润分配·权益分派/回购进展/募投变更/独董提名等程序治理件。
   - 清单 >50 条时按日期窗口 + 标题**批量**判定，不逐条纠结。

```python
# 3) 只下载选中的（download + register，source_type='announcement'）
selected = [anns[i] for i in (0, 3, 7)]   # ← 主 agent 判定的下标
got = download_announcements_cn('SSE_688506', slug, variant, selected)
# 盖 fetch_status / 闭环 todo 照 _autofetch_protocol.md（按 task 子串/文档身份，不用 K# 求交）
```

### Step6.5d · next_actions 范例 + 对照表

```python
from prism.scripts.topic import set_next_actions, read_topic
t = read_topic(slug, variant)
remain = [td['task'] for td in t['user_todos'] if td.get('fetch_status') == 'empty']
set_next_actions(slug, [
    f'00 eager-fetch 已抓 N 份入库；剩 {len(remain)} 条公开无源待你决策（waived/will_collect）',
    '运行 workflow 01-gather（01 只补抓自己新增的 L4/A合同 todo + 按 R3 重试 00 的 error）',
], variant)
```

并在对话输出一张表（同 01 Step 5.6 格式），逐条标 `fetch_status`：

```
| todo | info_tier | 获取方式 | fetch_status |
|------|-----------|----------|--------------|
| 茅五泸 2025 年报+Q1 季报 | half_public | cninfo 直下 | fetched（mat-xxx…） |
| 卖方拐点研报×3 | public | exa→转载全文 | fetched（mat-xxx） |
| 飞天高频批价序列 | half_public | exa+semantic 0 命中 | empty（待你决策） |
```

### Step5.3 · info_tier / 优先级 P0-P2 定义

**信息差等级定义**：
- `public` 公开普及 — Google/Wind 一搜就有，价值低（但作为研究起点）
- `half_public` 半公开 — 需登录/付费/外文/拼凑，是 alpha 主要来源
- `hard` 难获取 — 专家访谈/产业链调研/圈内信息，价值最高但收集成本大

**优先级原则**：
- P0 = 缺了它整个研究无法推进的（约 3-5 项）
- P1 = 重要补充，影响 thesis 强度但不影响方向（约 3-5 项）
- P2 = 锦上添花，等核心研究完后补（不超过 3 项）

