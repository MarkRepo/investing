# Claim 抽取 Prompt（给 Claude 对话用）

从研报/财报/电话会纪要里抽取**原子级 claim**，按受控词表打标签，输出严格 JSON。
Python 端只做 schema 校验 + 写入 `companies/{market}_{ticker}/claims.jsonl`，不碰 LLM API。

---

## 流程

1. 在 Claude 对话里把研报全文（markdown/纯文本）贴进去
2. 附上 `controlled-vocab/subjects.yaml`（或只列出 id，见下方 fallback 列表）
3. 附上下方 **系统指令** 作为要求
4. 把 Claude 返回的 JSON 粘贴进研究工作台 → "批量导入 claims" 文本框
5. 失败会整批拒绝并列错因，修正后重粘

> **为什么要整批拒绝**：claims.jsonl 是审计证据链，不允许部分导入污染。

---

## 系统指令（复制到对话）

```
你是研究助理。任务：从用户给出的研报原文里抽取 atomic claims。

【输出格式】只返回 JSON（无 markdown、无前后说明文字），顶层对象：
{
  "source_id": "MS-YYYY-MM-DD | JPM-YYYY-QN | 10K-YYYY 等短 id（用户给）",
  "source_file": "原文在 sources/ 下的文件名",
  "extracted_by": "claude-<model>-<短标识>",
  "extracted_at": "ISO8601 UTC，如 2026-04-23T09:15:00Z",
  "claims": [
    {
      "claim_text": "一句话、可证伪、不超过 80 字",
      "subject_tag": "必须在受控词表 id 列表内",
      "polarity": "bull | bear | neutral",
      "claim_type": "quantitative | qualitative",
      "timeframe": "2026Q1 | long-term | (省略)",
      "evidence_text": "原文里的支撑句，尽量直引（必填，最多 200 字）",
      "confidence": "high | medium | low"
    }
    ...
  ]
}

【抽取原则】
1. atomic：一个 claim 只表达一件可独立判真伪的事。复合句必须拆。
2. 可证伪：空话（"公司前景光明"）不要抽。
3. 忠实：不要发挥，不要脑补，不要跨章节综合。证据必须出现在原文里。
4. 打标：subject_tag 严格匹配受控词表 id。遇到词表外的题材，polarity=neutral
   且 subject_tag 选最近的一个，并在 claim_text 开头加 "[可能需要新增 tag]"
   方便维护者发现。宁可错过也不要发明新 tag。
5. 每篇研报 claim 数量期望：定性研报 8-20 条；财报电话会 15-40 条。过少可能漏抽，
   过多可能把解读和引用搅在一起。
6. polarity 以研报论述方向为准（作者推多→bull，推空→bear，陈述事实→neutral），
   不是你自己的判断。

【受控词表】（subjects.yaml 里的 id 列表，见本 repo）
```

---

## Fallback：subject_tag id 列表

当前受控词表（DESIGN §3.6，id 可能会扩）：

**收入维度**：revenue_growth, revenue_mix, pricing_power, volume_trend
**盈利维度**：gross_margin, operating_leverage, margin_trend
**经营维度**：channel_inventory, working_capital, capex_cycle
**竞争维度**：market_share, competitive_position, new_entrants
**治理维度**：management_credibility, capital_allocation, related_party
**风险维度**：regulatory_risk, concentration_risk, cyclical_risk
**估值维度**：guidance_reliability, consensus_direction, catalyst

需要新增 tag 时：先手动编辑 `controlled-vocab/subjects.yaml` 加新 id，再让 LLM 重抽。

---

## 输出示例（合法）

```json
{
  "source_id": "MS-2026-04-10",
  "source_file": "morgan-stanley-hims-2026-04-10.md",
  "extracted_by": "claude-opus-4-7",
  "extracted_at": "2026-04-23T09:15:00Z",
  "claims": [
    {
      "claim_text": "2026Q1 付费用户 220 万，同比 +30%",
      "subject_tag": "revenue_growth",
      "polarity": "bull",
      "claim_type": "quantitative",
      "timeframe": "2026Q1",
      "evidence_text": "HIMS reported Q1 subscribers of 2.2M, up 30% YoY from 1.7M",
      "confidence": "high"
    },
    {
      "claim_text": "GLP-1 compound 豁免条款可能撤回，影响减重业务收入线",
      "subject_tag": "regulatory_risk",
      "polarity": "bear",
      "claim_type": "qualitative",
      "timeframe": "long-term",
      "evidence_text": "FDA 近期表态 compounding 例外可能收紧，HIMS 减重业务高度依赖此豁免",
      "confidence": "medium"
    }
  ]
}
```

## 反例（不要这么写）

- ❌ `"claim_text": "HIMS 前景光明"` — 不可证伪
- ❌ `"claim_text": "增长快且利润率改善且估值合理"` — 复合句，应拆成 3 条
- ❌ `"subject_tag": "moat"` — 不在受控词表
- ❌ `"polarity": "positive"` — 必须是 bull/bear/neutral
- ❌ `evidence_text` 为空 — 无证据等于主观发挥
