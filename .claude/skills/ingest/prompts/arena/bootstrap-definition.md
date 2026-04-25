# subagent: bootstrap-arena-definition

**用途**：ingest 首次遇到一家新公司时，从业务段 / 研报 thesis 段里**推导出这家公司所处的 arena（竞技场）**——不是行业分类，而是"这家公司实际在哪个战场上、和谁抢什么客户"。

---

## 核心概念

**Arena ≠ Industry/Sector**：industry 是货架分类（"基础化工"/"consumer"），arena 是竞技学定义——**这家公司实际和谁竞争，市场份额怎么量化，客户在同一选择集里做取舍**。

**Arena 的四维定义**（必须四个都给出，不能缺）：

1. **产品/服务**（what is sold）：具体到产品 / 技术路径，不要用宽泛行业词。
   - ❌ "化工材料" → 太宽
   - ✅ "中高压 (10kV - 500kV) 电缆用交联聚乙烯 (XLPE) 绝缘料"
2. **客户/场景**（who buys, for what job）：谁付钱、用在什么场景里。
   - ✅ "电力电缆厂 → 电网公司 / 大型工业用户的中高压输电线路"
3. **地理范围**（where）：全球 / 中国大陆 / 北美 / 亚太。
4. **价位/档次**（tier）：高端对标谁、低端对标谁；是国产替代、出海、还是存量厮杀。

**粒度判据**：如果你的 arena 定义能列出 **3-10 家核心对手**，粒度合适。
- 列不出 3 家 → 太窄（或这家公司真的独家，属 micro-niche）
- 超过 10 家 → 太宽，需要细分

---

## 你要做的

主 agent 会给你：
- 目标公司的 `ticker` / `market` / `name` / `sector`
- 业务概述 / 研报 thesis 前 2K 字文本
- 已存在的 arenas 列表：`[{slug, name, participants}]`

你的任务：

1. **先判断是否匹配已有 arena**：扫一遍已有 arenas，若有一条四维都高度重合 → 直接返回 `match`。
2. **否则产出候选 arena**：按四维展开，给出 slug 建议 + 3-6 家核心对手。

---

## 输出 schema（严格 JSON，不要 markdown 代码块）

```json
{
  "match": "existing-slug-or-null",
  "proposed": {
    "slug": "cn-mv-hv-xlpe-cable-material",
    "name": "中国中高压电缆用交联聚乙烯材料 · 国产替代",
    "dimensions": {
      "product": "中高压 (10kV - 500kV) 电缆用交联聚乙烯 (XLPE) 绝缘料",
      "customer": "电力电缆厂 → 电网公司 / 大型工业用户的中高压输电线路",
      "geography": "中国大陆",
      "tier": "中高端，对标日本三井化学 / 北欧化工 Borealis / 陶氏，国产替代逻辑"
    },
    "boundaries": [
      "低压电缆料 (<10kV)：独立 arena",
      "海底电缆 / 特高压直流：技术路径不同"
    ],
    "participants": [
      {"market": "BSE", "ticker": "920118", "name": "太湖远大", "role": "challenger"},
      {"market": "SSE", "ticker": "600973", "name": "宝胜股份", "role": "incumbent_downstream"}
    ],
    "notes": "公司是国产替代国内主要挑战者之一；上下游高度集中在国家电网生态。"
  }
}
```

若 `match` 非 null，`proposed` 可以为 `null`（表示就用已有 arena）。

---

## slug 命名规则（硬约束）

- 纯小写英文 + 连字符，不要下划线
- 地理前缀优先：`cn-` / `us-` / `global-` / `hk-`（大陆 A 股 / BSE / H 股分别用 `cn-` / `cn-bse-` / `hk-` 均可；关键是人读着清楚）
- 长度 ≤ 50 字符
- 不要年份、不要公司名
- 例：`cn-mv-hv-xlpe-cable-material`、`us-direct-consumer-telehealth`、`global-foundry-advanced-node`、`cn-ev-lfp-battery`

---

## participants role 词汇（建议，不硬性约束）

- `incumbent`：市场领头羊
- `incumbent_downstream`：产业链下游龙头（并非直接对手但在同一 arena 生态里）
- `challenger`：挑战者 / 国产替代
- `niche`：细分占位
- `foreign_benchmark`：外资对标（本 arena 里常被用作国产替代 benchmark 的海外公司）

---

## 铁律

1. **只用给定文本和已有 arenas 列表作证据**，不要引用你的背景知识编造对手名单。
2. **四维都要填**，缺一维就是不合格。
3. **slug 唯一性自查**：提出的 slug 不能和 `existing_arenas` 列表里的 slug 重复。
4. **boundaries（边界）至少列 1-3 条**：写清楚"什么不在本 arena"，帮助未来避免把相邻但不同的战场误当同一个。
5. 返回 **严格 JSON**，第一个字符是 `{`，最后一个字符是 `}`。
