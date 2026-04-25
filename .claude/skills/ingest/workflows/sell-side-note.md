# workflow: sell-side-note

处理卖方研报。与财报流程的关键差异：

1. **只写 claims**。不写 profile（研报不是事实源）、不写 financials（研报里的预测数字是**未来期观点**，不是已披露历史数字）、不改 meta。
2. **polarity 以研报作者立场为准**。研报说"强烈看多"，claim 就是 `bull`，哪怕你个人不认同。
3. **目标价 / 评级无系统字段**，统一塞 `claim_text` 里，`subject_tag=consensus_direction`。
4. **当前版本只支持单公司研报**。行业研报 / 跨多家公司的研报直接拒绝（下一版再设计"先进 industries/ 还是直接建公司"）。
5. **period 覆盖多 FY**。研报预测通常跨 FY+1/FY+2/FY+3，不做 `period_consistency` 校验（expected 没有唯一值）。

---

## 前置状态

- `SKILL.md` 已判定源类型为研报
- 已知：`file_path`、目标公司 key（`market + ticker`）——若研报封面未写清楚，先 AskUserQuestion 确认

---

## Step 1：输入校验

- 确认 `file_path` 存在且可读
- 预处理参数固定：`--type sell-side --market {a-share|us}`（market 按目标公司决定；不是研报本身的属性）

---

## Step 2：company 存在性检查 + 自动建 meta

```python
from app.io import company as company_io
meta = company_io.read_meta(ticker, market)
```

- 存在 → Step 3
- 不存在 → **自动建 meta**（绝不劝退）。新股研报常常是公司第一份可 ingest 的文档——要求"先 ingest 年报"不切实际（新股根本还没发年报）。按 `annual-report.md` Step 2b 的子流程走：
  1. **抽 name**：从 HEADER / 研报封面抽。A 股研报封面通常写明 "公司简称（股票代码）行业分类"（如 "太湖远大（920118） 基础化工"），直接取中文公司名。
  2. **推 currency**：`US → USD` / `SSE/SZSE/BSE → CNY` / `HK → HKD`。
  3. **问 sector**：AskUserQuestion 走 `VALID_SECTORS = ("consumer","saas","cyclical","bank","biotech")`。研报封面的行业分类（"基础化工"/"电子"/"医药"）是 sector 选择的 hint。
  4. **建**：`company_io.create_company(ticker, market, name, sector, currency)`。
  5. 继续 Step 3，不中止。

**meta 推断弱？不怕**。研报建的 meta 是骨架（name + sector + currency），后续 ingest 年报时 `merged["meta_updates"]` 会补充 website/上市日期等；风险仅是中途一段时间 meta 不完整。比让用户在新股场景被劝退好得多。

---

## Step 3：预处理

```bash
.venv/bin/python -m scripts.preprocess_report "<file_path>" \
    --type sell-side \
    --market {a-share|us} \
    --out /tmp/ingest-<sha8>.sections.json
```

---

## Step 4：解析预处理输出 + 单公司判定 + 元数据补齐

**读预处理 JSON**，关键字段：
- `meta.sha8`
- `meta.institution`（研报专用；抽不到返回 null）
- `meta.publish_date`（研报专用；抽不到返回 null）
- `sections[*]`：按 `action` 分流

### 4a：单公司判定

研报常见三种：
- **单公司深度**（目标）：封面/HEADER 写明公司名 + ticker；investment_thesis 通篇围绕一家
- **行业 + 核心标的**：覆盖 3-10 家同行，其中 1 家用户关心 → **当前版本拒绝**，提示"多公司研报暂不支持，下一版提供行业研报通道"
- **策略宏观**：无特定公司 → **拒绝**

判定方法（主 agent 自己判，不做复杂启发式）：
1. 读 HEADER + investment_thesis 前 2K 字
2. 若里面明显提到 ≥2 家公司（2+ 个 ticker 或 2+ 个带"股份/有限公司"后缀的专名），且 thesis 部分在做同业比较 → 判"非单公司" → 终止并提示用户
3. 若只围绕 1 家（目标公司）展开 → 继续

不确定时 AskUserQuestion 让用户决定"按单公司继续 / 终止"。

### 4b：institution + publish_date 补齐

- `meta.institution` 为 null → AskUserQuestion 让用户给机构名（"中信证券"、"Morgan Stanley"）
- `meta.publish_date` 为 null → AskUserQuestion 给出版日期（ISO `YYYY-MM-DD`）

这两个字段决定 source_id，不能省。

**UNKNOWN section 处理**：研报 UNKNOWN 通常是"图表说明 / 表格页"，不走 extract。超过 3000 字 UNKNOWN → AskUserQuestion 是否继续（研报 UNKNOWN 多数不含可抽事实）。

---

## Step 4.5：Arena 识别 + Checklist 引导（研报是主要 bootstrap 触发源）

研报往往是 ingest 一家新公司的第一份文档——arena + checklist 的 bootstrap 绝大多数走这里。

### 4.5a：候选 arena 推导

1. **列已有 arenas**：
   ```python
   from app.io import arenas as arenas_io
   existing = arenas_io.list_arenas()   # [{slug, name, participants}]
   ```
2. **取上下文片段**：`investment_thesis` 前 2K 字 + `valuation` 段前 500 字 + `meta.institution` + 公司 context (`ticker / market / name / sector`)。
3. **调 Agent(Explore)**，prompt = `.claude/skills/ingest/prompts/arena/bootstrap-definition.md` + 片段 + 已有 arenas 列表（slug + name + 四维摘要）。
4. **subagent 返回** `{"match": slug | null, "proposed": {slug, name, dimensions, boundaries, participants, notes}}`。

### 4.5b：用户审 + arena 落盘

- **`match` 非 null** → 告知用户"已识别为 arena `{slug}`"，AskUserQuestion 确认复用。确认后：
  ```python
  company_arenas = [match_slug]
  arenas_io.participants_add(match_slug, ticker, market, name, role="challenger")
  ```
  跳到 4.5d（复用已有 checklist，**不跑 bootstrap-checklist**）。

- **`match` 为 null** → AskUserQuestion 给用户 3 选项：
  - "采用候选 arena（slug={proposed.slug}）"：展示四维摘要 + 参与者给用户看
  - "改用已有最接近的（下拉 existing）"
  - "自己改 slug / 改四维" → 用户提供后走下一步
- 用户确定后：
  ```python
  fm = {
      "slug": proposed_slug,
      "name": proposed_name,
      "created": today,
      "last_updated": today,
      "participants": [{"market": market, "ticker": ticker, "name": name, "role": "challenger"}],
  }
  body = f"""## 四维定义
  - **产品/服务**：{dimensions.product}
  - **客户/场景**：{dimensions.customer}
  - **地理范围**：{dimensions.geography}
  - **价位/档次**：{dimensions.tier}

  ## 边界条件（不在本 arena）
  {渲染 boundaries}
  """
  arenas_io.write_definition(proposed_slug, fm, body)
  company_arenas = [proposed_slug]
  ```

### 4.5c：Checklist 生成（仅新建 arena 时跑）

1. **调 Agent(Explore)**，prompt = `.claude/skills/ingest/prompts/arena/bootstrap-checklist.md` + 刚落盘的 `definition.md` 完整内容 + 公司 context。
2. **subagent 返回** `{"slug", "items": [...]}`，每条 item 带 `id / question / why_matters / typical_evidence_section / tags`。
3. **AskUserQuestion** 展示草稿清单，让用户批量编辑：
   - 删除不合适的 item
   - 改 question 措辞 / why_matters / tags
   - 手动追加（若用户希望加一条 LLM 没覆盖的）
4. 用户确认后落盘：
   ```python
   arenas_io.write_checklist(
       proposed_slug,
       items=approved_items,
       changelog_entry={"source_id": source_id, "changes": "initial bootstrap"},
   )
   ```

### 4.5d：读 checklist 到内存（供 Phase B 注入）

```python
checklists_by_slug = {
    slug: arenas_io.read_checklist(slug) for slug in company_arenas
}
# 合并成 item 池，按 id 去重：
item_pool = {}
for slug, cl in checklists_by_slug.items():
    for it in cl["items"]:
        item_pool.setdefault(it["id"], {**it, "arena_slug": slug})
```

### 4.5e：更新 company meta 的 arenas 字段

如果 `company_arenas` 不是 meta 里已有的 arenas 子集 → 追加：
```python
info = company_io.read_meta_with_body(ticker, market)
fm = dict(info["frontmatter"])
fm["arenas"] = sorted(set(fm.get("arenas") or []) | set(company_arenas))
company_io.write_meta(ticker, market, fm, info["body"])
```

---

## Step 5：source_id 生成 + 碰撞检测

读 `source-id-rules.yaml`，研报 format：`研报-{institution}-{date}-{sha8}`
- date 规格化为 `YYYY-MM-DD`（即便原文是"2025 年 10 月 28 日"）
- institution 取原样（"中信证券" / "Morgan Stanley"）

例：`研报-中信证券-2025-10-28-a3f91b2c`

**碰撞检测**：同年报流程。注意研报容易出现"同机构同日发两份"（上午一份业绩点评 + 下午一份路演纪要）—— sha8 不同就不算碰撞。

---

## Step 6：原文落位到 `sources/`

```python
from app.io import claims as claims_io
with open(file_path, "rb") as f:
    content = f.read()
claims_io.save_source_markdown(ticker, market, Path(file_path).name, content)
```

---

## Step 7：Dispatch subagents（并发 ≤ 5）

读 `section-routing.yaml` 的 `sell-side-generic` key。可派的 section 很少，通常是：

- `investment_thesis` → `prompts/sell-side/thesis.md`
- `forecasts` → `prompts/sell-side/forecasts.md`
- `valuation` → `prompts/sell-side/valuation.md`
- `risk_section` → `prompts/sell-side/thesis.md`（复用 thesis prompt，因为研报风险节多为对立面的 thesis）

全部 `targets: [claims]`。一把并发即可（通常 3-4 个 subagent）。

**共同 prompt 追加**（派每个 subagent 时在主 prompt 末尾加）：

```
本次是卖方研报，不是公司一手披露。你产出的每条 claim 必须：
- polarity 以**研报作者的立场**为准（分析师说看多 → bull），不是你的判断
- claim_text 开头可选择标注 "[{institution} {publish_date}]" 便于后续消费区分
- subject_tag 必须在 subjects_whitelist 里；研报最常用的 tag：
  - `consensus_direction`（目标价 / 评级 / 市场共识方向）
  - `guidance_reliability`（研报给出的预测与公司指引的一致性/偏差）
  - `catalyst`（作者列出的推动因素）
  - `competitive_position` / `pricing_power` / `market_share`（论点的行业结构观点）
- **不要产出** `profile_fragments` / `financial_rows` / `meta_updates` —— 研报不经这些通道
- flags 里如见到"目标价大幅偏离现价"、"预测与公司指引明显不一致"，务必标出
```

**oversize 检查**：sell-side-generic 当前没有设置 `max_chars`。研报正文通常 30K 字内；若某 section 超 100K 字（极罕见），手动降级成 AskUserQuestion。

**同名 section 合并派单**（研报的核心优化——`_section_fallback` 经常产生 N 个同名 investment_thesis）：按 `.claude/skills/ingest/dispatch-merge-rules.md` 的决策树处理。

研报 `investment_thesis` 类**走方案 C**（默认按一级章节号分派，不再全合并）：10 个 thesis 子节 → `thesis__lvl1` / `thesis__lvl2` / `thesis__lvl3` / `thesis__misc` 等 3-5 个子 subagent。这样 claim 抽取更聚焦，arena checklist 填答也能按 heading 主题路由。

合并文本的拼接格式：
```
### {heading_raw_1}
{text_1}

### {heading_raw_2}
{text_2}
```

### 7b：Arena checklist item 路由（若 Step 4.5 有 `item_pool`）

对每个要派的 subagent，算出**该 subagent 应收的 item 子集**，注入 prompt：

1. **按 `typical_evidence_section` 粗分**：
   - item 的 `typical_evidence_section` 含 `investment_thesis` → 候选"投给所有 `thesis__*` 子 subagent"
   - 含 `valuation` → 投给 `valuation` subagent
   - 含 `forecasts` → 投给 `forecasts` subagent（若该 section 存在）
   - 含 `risk_factors` 或 `risk` → 投给 `risk_section` subagent
   - `["any"]` → 只投给 `thesis__*` 系列（研报的综述类）

2. **thesis 子 subagent 的二次细分**（主 agent 在对话里推理，不派专门 subagent 做）：
   - 读每个 `thesis__lvlN` 聚合后的 heading_raw 列表
   - 对照预定义 tag 定义表（见 `prompts/arena/bootstrap-checklist.md`），给每个子 subagent 推理 1-3 个 tag（例："1.1 深耕线缆材料" + "1.2 产品矩阵" → `[competitive_position, technology]`）
   - 从候选 item 里筛 `tags` 与子 subagent tag 有交集的 item

3. **item 密度决策树**（筛完后）：
   - ≤ 20 → 正常派
   - 21-30 → 正常派，prompt 里加"逐条对照，不确定就 level=vague 或 unanswered"
   - \> 30 → pause，AskUserQuestion（说明公司可能属于过多 arena，让用户取舍）

4. **prompt 拼接**：在该 subagent 的主 prompt 末尾追加：
   ```
   ## Arena 能力圈填答

   本次 ingest 属 arena：{arena_name} ({slug})
   本 subagent 的 checklist 子集（共 N 条）：
     - {id1}: {question1}
     - {id2}: {question2}
     ...

   产出 `competence_findings.answered`（见 _common.md schema）+ 可选 `proposed_additions`。
   ```

5. **研报 thesis 子 subagent 额外追加**（区别于财报的"留给其它 subagent"策略）：
   ```
   本 section 是研报综述性论证章节。请认真对照 checklist 每一条；没有覆盖到的 item 用 level=unanswered 诚实标出（不要留给其它 subagent——本 ingest 里研报的能力圈填答主要落在 thesis 子 subagent 群里）。
   ```

---

## Step 8：主 agent 汇总

```python
from scripts import ingest_aggregate as agg

outputs = {name: agg.load_json_tolerant(raw) for name, raw in subagent_results.items()}
merged = agg.aggregate(outputs)
merged["claims"] = agg.dedup_claims(merged["claims"])
```

**研报特有后处理**（和季报 Step 8 类似）：

```python
dropped_fragments = merged.pop("profile_fragments", {})
dropped_fin       = merged.pop("financial_rows", [])
dropped_meta      = merged.pop("meta_updates", {})
# 任一非空 → 在收尾报告里标"subagent 误产出 X，已丢弃"
```

研报 subagent 若产出 `financial_rows` 很可能是把预测表误当成"已披露数字"——丢弃，并在 flags 加提醒（预测数字应留在 claims 的 claim_text 里，subject_tag=guidance_reliability）。

**注意**：`merged["competence_findings"]` **保留**（研报 ingest 的核心新增通道），在 Step 10 审阅后写入。

**必须**把 merged 落盘到 `/tmp/ingest-{sha8}.merged.json`（Step 10.5 的 QA 消费它）：

```python
import json
from pathlib import Path
Path(f"/tmp/ingest-{sha8}.merged.json").write_text(
    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

---

## Step 9：交叉校验（精简版）

```python
issues = {
    "empty_section":       agg.check_empty_sections(merged),
    "financials_required": agg.check_financials_required(merged),  # 用于捕获误产出；应为空
}
```

**不跑** `revenue_consistency`（研报无总收入锚）和 `period_consistency`（timeframe 跨多 FY 没有唯一 expected）。

- `empty_section` 非空 → warn，不暂停
- `financials_required` 非空 → 说明 Step 8 的"丢弃 financial_rows"没执行干净，pause 让用户排查

---

## Step 10：统一写入

三件事：

1. **原文落 `sources/`**（Step 6 已做）

2. **写 claims**：

```python
from datetime import datetime, timezone
n, errors = agg.write_claims(
    ticker, market, merged["claims"],
    source_id=source_id,
    source_file=Path(file_path).name,
    extracted_by="claude-opus-4-7",
    extracted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
)
if errors:
    # 报给用户，建议重抽单个 subagent；不做部分写入
    ...
```

3. **competence 写入**（审阅后）：

```python
findings = merged.get("competence_findings", {"answered": [], "proposed_additions": []})

# 合并同 q_id 跨 subagent 的多答（取 level 最高 + evidence 最长）
consolidated = arenas_io.consolidate_answers(findings["answered"])

# 审阅前展示：
#   - consolidated（按 arena 分组展示）
#   - findings["proposed_additions"]
```

**AskUserQuestion 审阅**：

- 选项 A：approve 全部 answered + approve 所有 proposed_additions
- 选项 B：approve answered，拒绝所有 proposed（适合 checklist 已经比较成熟）
- 选项 C：逐条筛选（多选）
- 选项 D：跳过 competence 写入（本次只产 claim，competence 不落盘）

**写入**（对每个 arena）：

```python
for slug in company_arenas:
    checklist = arenas_io.read_checklist(slug)
    # 过滤属于本 arena 的 answered（item_pool 里记录了 arena_slug）
    answered_for_this_arena = [
        a for a in consolidated
        if item_pool.get(a["q_id"], {}).get("arena_slug") == slug
    ]
    arenas_io.append_notes(
        slug, ticker, market, name,
        answered_items=answered_for_this_arena,
        source_id=source_id,
        checklist_version=checklist["version"],
    )
    # proposed_additions：若用户 approve 了针对本 arena 的新 item
    approved_new = [...]   # 主 agent 在审阅时已分好归属
    if approved_new:
        new_items = checklist["items"] + approved_new
        arenas_io.write_checklist(
            slug, new_items,
            changelog_entry={
                "source_id": source_id,
                "changes": f"added {len(approved_new)} item(s) from {source_id}",
            },
        )
```

**不写** financials、**不写** profile、**不写** meta（研报原则不变）。

---

## Step 10.5：QA checkpoint（自动落盘告警 + 缺口清单）

Step 10 写完即跑。结果会出现在首页 `🔎 QA 未处理告警` widget 和 `/qa/{market}_{ticker}` 页面，带 fix_hint 和 resolve/dismiss 按钮。

```bash
.venv/bin/python -m scripts.ingest_qa warn \
    --merged /tmp/ingest-{sha8}.merged.json \
    --preprocess /tmp/ingest-{sha8}.sections.json \
    --arena {primary_arena_slug} \
    --write --scope {market}_{ticker}

.venv/bin/python -m scripts.ingest_qa gap \
    --company {market}_{ticker} \
    --write
```

- 6 条规则：`fidelity` / `self_contradict_specific` / `empty_evidence` / `polarity_mismatch` / `proposed_dup` / `checklist_company_contamination`
- 幂等：同 key（scope+source_id+rule+target）不重复写；`dismissed` 状态不自动重开
- `--arena` 指向本次 ingest 的 arena slug；多 arena 时挑一个"主" arena 跑即可（其它 arena 的 checklist 污染/dup 检查需要单独再跑）
- 把两步的退出消息记下来（warn 的 `added=X skipped_dup=Y reopened=Z`；gap 的 `✓ 落盘 path`），在 Step 11 收尾报告里展示

---

## Step 11：收尾报告

```
已 ingest 研报：companies/{market}_{ticker}/sources/{filename}
✓ claims.jsonl  +{N} 条 (source_id={source_id})
{✓|⊘} arenas/{slug}/competence-notes.md  {更新 M 条答案 / 用户跳过}
{✓|⊘} arenas/{slug}/checklist.yaml       {bump 到 vX (新增 K 条) / 无新增}
{✓|⊘} companies/{key}/meta.md.arenas    {追加 [{slugs}] / 已有}
✓ companies/{key}/qa_warnings.jsonl     +{W} 告警 · open={W_open}（首页 QA widget 会提示）
✓ companies/{key}/qa_gaps.md            已刷新（/qa/{key} 可看）
⊘ financials.db  研报不写
⊘ profile-*.md   研报不写

机构：{institution}
发布日期：{publish_date}
评级：{rating (若抽到)}
目标价：{target_price (若抽到)}
Arena：{arena_name} ({slug})

{若有} 丢弃的 subagent 产出：
  - financial_rows: {len(dropped_fin)} 条（研报不经此通道；应保留为 guidance_reliability claim）
  - profile_fragments / meta_updates: 同上

下一步建议：
- 用本次 claims 做 consensus 方向对照：`/research/{key}?subject=consensus_direction`
- 和最近一份年报的 claims 做分歧分析：对照研报作者观点 vs 公司自述
- 查看 arena 认知库：`arenas/{slug}/competence-notes.md`
- 本次抽到的 flags：
  - {flag 1}
  - {flag 2}
```

---

## 失败模式

| 场景 | 处理 |
|---|---|
| 预处理检测不出研报（form_detection 负例多） | 研报格式太乱，AskUserQuestion 确认是否强制继续 |
| 多公司研报混入 | Step 4a 判定后**拒绝**，提示"下一版支持行业研报" |
| institution / publish_date 抽不到 | AskUserQuestion 由用户输入 |
| company meta 不存在 | Step 2 自动建 meta（新股研报是常见 bootstrap 触发源，不中止） |
| Step 4.5 bootstrap-arena-definition subagent 返回无效 JSON / 四维缺 | AskUserQuestion 让用户手填 arena 四维，或跳过 arena 环节（本次 ingest 只写 claim，competence 不落盘） |
| Step 4.5 bootstrap-checklist 产出 >15 条或含未知 tag | IO 层 `write_checklist` 会拒绝；主 agent 回到审阅步让用户删到 15 条 / 修 tag |
| Step 7b 某子 subagent item 数 > 30 | pause，AskUserQuestion 让用户删 checklist 或裁 arena |
| subagent 产出 financial_rows | Step 8 丢弃并打 flag；若 `financials_required` 非空 pause |
| 预测 claim 数量异常高（>50 条单报） | dedup 后仍异常 → 通常是 forecasts subagent 把每行表格的每一列都独立抽成 claim；AskUserQuestion 让用户决定是否精简 |
