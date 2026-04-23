# consensus-map 分析 Prompt（claims.jsonl → 共识/分歧/独特视角）

把一家公司的 `claims.jsonl` 按 `subject_tag` 聚合，输出**共识 / 分歧 / 独特视角**三视图，
帮你快速看清"哪些判断是市场一致预期，哪些是分歧所在，哪些是少数派独家观点"。

DESIGN §3.6：`claims.jsonl` 的消费者是 consensus-map skill。本 prompt 就是那个 skill 的实现。

---

## 何时用

- 读完 5-10 份研报后，claims.jsonl 攒到 50+ 条
- 写 V0 前，先用 consensus-map 看清全局再下笔
- 季报发布后，把新增 claim 也丢进去再跑一次，看共识有没有漂移

---

## 流程

1. 从本地把目标公司的 `companies/{market}_{ticker}/claims.jsonl` 全文粘进 Claude 对话
2. 附上本 prompt 作为系统指令
3. Claude 返回 markdown 报告
4. 自己拷贝关键结论到 V0 的 §4（共识 vs 独立判断）或 `competence-check.md` 补缺口

> **为什么不自动化**：consensus-map 是读出来消化的，不是给系统查询的。所以它是 LLM 对话产物，**不落盘**。需要引用时拷贝片段进 V0。

---

## 系统指令（复制到对话）

```
你是研究助理。任务：把用户贴进来的 claims.jsonl（每行一个 JSON 对象）按
subject_tag 聚合，输出共识/分歧/独特视角三视图。

【输入】多行 JSON，每行包含：claim_text, subject_tag, polarity, claim_type,
timeframe, evidence_text, confidence, source_id, source_file。

【聚合规则】
1. 按 subject_tag 分组。同一 tag 下列出所有 claim。
2. 每组内再按 polarity 拆：bull / bear / neutral 各一列。
3. 统计：
   - 共识（consensus）：同 tag 同 polarity 的 claim 来自 ≥3 个不同 source_id
   - 分歧（divergence）：同 tag 既有 bull 又有 bear（各来自 ≥2 个 source_id）
   - 独特视角（unique）：同 tag 某 polarity 只有 1 个 source_id，但 confidence=high
     且 claim_type=quantitative
4. 不要合并/改写原 claim_text。引用时直接抄，带 source_id 方便回溯。
5. 数字类 claim 之间如果口径不一致（例如 "Q1 用户 220 万" vs "Q1 用户 180 万"），
   标注为【口径冲突】而不是 divergence——这是需要人工核对的数据问题，不是观点分歧。

【输出格式】返回 markdown：

# {ticker} consensus map

生成时间：{ISO8601}
claims 总数：{N}
覆盖 source：{M} 份
subject_tag 覆盖：{K} 个

## 1. 共识（≥3 源同向）
### {subject_tag} — {bull/bear/neutral}
- "…claim_text…" (src: MS-2026-04-10)
- "…claim_text…" (src: JPM-2026-03-22)
- "…claim_text…" (src: 10K-2025)
**一句话综合**：{你的自然语言概括，保留信息不加料}

## 2. 分歧（同 tag 双向争论）
### {subject_tag}
**多头**：
- "…" (src: ...) confidence=high, quantitative
- "…" (src: ...)
**空头**：
- "…" (src: ...) confidence=medium, qualitative
- "…" (src: ...)
**争议焦点**：{bull/bear 各自最有力的证据在哪里，一两句点明}

## 3. 独特视角（单一来源高置信定量）
### {subject_tag} — {polarity}
- "…claim_text…" (src: ...)
  evidence: "…原句直引…"
  **为何值得单独看**：{只有这一家提到、但证据扎实，可能信息不对称}

## 4. 口径冲突（需人工核对）
### {subject_tag}
- src A: "Q1 用户 220 万"
- src B: "Q1 用户 180 万"
**可能原因**：{订阅口径 vs 月活？统计截止日不同？}
**建议动作**：查年报/公告原文

## 5. 空白地图
列出**没有任何 claim 覆盖**的 subject_tag（从 DESIGN §3.6 受控词表对照）：
- {tag_id}
- ...

这部分对应"能力圈缺口"——如果这些 tag 在你的 competence-check 里是必答项，
要么补研究材料再抽，要么承认知识不全不买。

【输出原则】
- 保留原 claim_text 和 evidence，不要润色、不要合并
- source_id 必带，方便回溯原文
- 统计口径冲突 != 多空分歧，分开处理
- 空白地图放最后，它是最容易被忽视的信号
```

---

## 使用示例输出（片段）

````markdown
# HIMS consensus map

生成时间：2026-04-23T10:00:00Z
claims 总数：67
覆盖 source：6 份
subject_tag 覆盖：12 个

## 1. 共识（≥3 源同向）
### revenue_growth — bull
- "2026Q1 付费用户 220 万，同比 +30%" (src: MS-2026-04-10)
- "订阅用户基数高速扩张，Q1 YoY 超 25%" (src: JPM-2026-03-22)
- "订阅制 ARR 规模同比 +32%" (src: 10K-2025)
**一句话综合**：三家机构+年报都确认 2026Q1 订阅用户 ~30% YoY，增长共识牢固。

## 2. 分歧（同 tag 双向争论）
### regulatory_risk
**多头**：
- "FDA compounding 豁免 2026 内难撤回" (src: WF-2026-02) confidence=medium
**空头**：
- "GLP-1 compound 豁免条款可能撤回，影响减重业务收入线" (src: MS-2026-04-10)
- "监管风险是本股 TAM 上限的关键变量" (src: BAR-2026-03)
**争议焦点**：bull 依赖"历史上 FDA 很少逆转"的经验判断；bear 指出 FDA 已有近期表态
收紧信号。本质是政策判断题，无定量证据。

## 5. 空白地图
以下 tag 未被任何 claim 覆盖：
- capital_allocation
- related_party
- working_capital
**含义**：事实层可能够用（meta.md 覆盖），但研报普遍不讨论治理与营运资金。
能力圈自检若涉及此部分，需补年报附注或公司公告。
````

---

## 反例

- ❌ Claude 把 6 条 claim 合并改写成 1 条"机构普遍看好" → 丢失来源和原文，不可回溯
- ❌ 把数字口径冲突误标为 bull/bear 分歧 → 应进 §4 口径冲突
- ❌ 不输出 §5 空白地图 → 丢失"我没调查过什么"的信号，决策失重
