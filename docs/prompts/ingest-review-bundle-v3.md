<!-- prompt_version: v3 -->

# Ingest Review Bundle v3 Prompt

你在读一份投资研报。任务：抽取一个可以辅助投资决策、且能在多份研报间融合
的论点+证据图。

输入：MinerU 产出的 `full-clean.md`（如有 keep_images 也可读）。
输出：一个 JSON bundle（schema 见末尾）。

## 抽取原则（按重要性）

1. **以叙事为先，按报告主线组织 claim。**
   作者想让读者得出什么投资判断？这是 bundle 的灵魂。
   按报告自身逻辑切分 claim，不要套框架。
   30 页通常 10-30 条；65 页通常 25-50 条；80 页通常 30-60 条。
   不刻意凑数，也不刻意压缩。

2. **每条 claim 必须有 1-5 条原文证据。**
   evidence.quote ≤120 字直引；图片信息末尾标 `(from image)`。
   evidence.why 一句话说明「该事实如何支持 claim」（≤30 字）。
   只能用"原文综合分析"支撑的 claim → 删除或并入。

3. **实体粒度：报告里点名的公司/品牌各自独立产 claim。**
   不要把"四家公司均受益"压成一条；分四条，挂到对应 scope。
   原因：跨研报融合时它们是独立实体。

4. **同类多实例必须独立成 claim。**
   "第一壁/偏滤器/磁体"是 3 条独立 claim，不是 1 条。
   "宠物食品/用品/医疗/服务"是 4 条。
   人口因素（银发/单身/丁克）也是多条。

5. **叙事关联用 relations 显形。**
   报告通常有一条主线："因为 A → 所以 B → 因此推荐 C"。
   relations 不是装饰：summary.threads 由 relations 反向推导。
   每条 claim 至少 1 条 relation（无论 in 还是 out），避免 isolated。

6. **summary.threads 是 claim 的分组视图。**
   通常 2-4 条主叙事线；每条串 3-8 条 claim。
   一条 claim 可同时属于多条 thread。

7. **semantic_key 是跨研报匹配的钩子（≤15 字）。**
   论点核心名词+动词组合。例：
     claim: "磁体在产业链中占金额敞口最高（24.9%）"
     semantic_key: "磁体 金额敞口 最高"
   不同研报对同一观点的 semantic_key 应自然趋同。

8. **confidence 默认 medium，仅在以下条件升降：**
   - high：原文有具体数字 + 多源印证或权威来源
   - low：仅图片描述、远期预测、强假设推断

9. **不能由本报告得出的结论 → cannot_conclude。**
   不要为"完整"编造。

10. **notes 显式标注：**
    - skipped_sections：哪些章节没读
    - weak_evidence：哪些 claim 质量低（可引 claim id）

## 不做什么

× 不要套必提类别清单。报告有就提，没有就不提。
× 不要给 claim 强制写 reasoning_chain / investment_implication /
  block_type / dimension_hint —— 这些字段不存在。
× 不要把 atomic_facts 和 claim 拆开，证据直接挂在 claim 下。
× 不要为了形式齐全编造数字或公司名。

## Schema

严格 JSON，无 markdown 围栏，无解释。顶层结构：

```json
{
  "schema_version": "v3",
  "meta": {
    "source_id": "<短id，如 institution-industry-YYYY-sha8>",
    "source_title": "<研报标题>",
    "institution": "<出具机构>",
    "published_at": "YYYY-MM-DD",
    "source_type": "<industry_report|company_report|annual|quarterly|sell_side|transcript>",
    "primary_scope": {
      "kind": "<industry|company>",
      "ref": "<industry_slug 或 MARKET_TICKER>"
    },
    "touches": {
      "industries": ["<slug>"],
      "companies": ["<MARKET_TICKER>"],
      "arenas": [],
      "brands": []
    }
  },
  "claims": [
    {
      "id": "c1",
      "text": "<单句论点，≤80字>",
      "type": "<thesis|judgment|risk|catalyst>",
      "scope": "<industry/{slug}|company/{MARKET_TICKER}|arena/{slug}|brand:{名}|cross_cutting>",
      "direction": 1,
      "confidence": "medium",
      "evidence": [
        {
          "quote": "<≤120字直引>",
          "page": null,
          "why": "<≤30字，该事实如何支持claim>"
        }
      ],
      "relations": [
        {
          "to": "c2",
          "kind": "<because_of|leads_to|tension_with|refines>"
        }
      ],
      "semantic_key": "<≤15字核心名词+动词>",
      "as_of": "YYYY-MM-DD"
    }
  ],
  "summary": {
    "one_liner": "<≤40字全报告核心判断>",
    "threads": [
      {
        "title": "<≤20字>",
        "claim_ids": ["c1", "c2"]
      }
    ],
    "cannot_conclude": ["<≤30字>"]
  },
  "notes": {
    "skipped_sections": ["<跳过的章节名>"],
    "weak_evidence": ["<质量低的claim说明，可引id>"]
  }
}
```
