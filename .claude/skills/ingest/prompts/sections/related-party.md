# subagent: related-party

**负责 section**：关联方交易 / Item 13 Certain Relationships and Related Transactions / 第五节/第六节 重要事项（A 股的关联交易披露通常在"重要事项"节）

**targets**：`profile.§5` / 少量 `claims`

---

## 你要产出的东西

### 1. `profile_fragments.§5_related_party`

```markdown
## 关联方与集中度

- **前五大客户占比**：{X}%（原文引用）
- **前五大供应商占比**：{X}%
- **关联方交易占收入比**：{X}%
- **关联方交易占采购比**：{X}%
- **最大单一关联方**：{关联方名称}，交易金额 {原文单位}，占 {X}%
- **关联方性质**：
  - 控股股东：{名称}
  - 同一控制下其它关联企业：{名称清单}
  - 董事/高管关联：{是否存在}
```

未披露的字段 → `未披露`（不要编）。

### 2. `claims`（仅异常或可证伪事件）

- 关联采购/销售金额同比大幅变化（> 30%）→ `subject_tag: related_party`
- 新发生的关联方担保/借款 → `subject_tag: related_party`
- 关联方占款 / 资金占用问题 → `subject_tag: related_party`，polarity=bear
- 关联交易公允性疑问（如原文有"独立董事发表异议"）→ `subject_tag: related_party`，polarity=bear

**不抽**：
- 常规关联方服务合同（金额占比 <1%）
- "公司严格按关联交易制度执行"这类合规套话

## subject_tag 使用指南

- `related_party` — 主要 tag
- `concentration_risk` — 客户/供应商集中度过高
- `management_credibility` — 关联方交易损害中小股东利益的事件

## 特有注意事项

1. **A 股"重要事项"节包含范围广**（除关联方外还有诉讼、担保、承诺事项）：
   - 关联方交易部分 → 本 subagent 处理
   - 诉讼/担保 → 如果独立成段，其实该 risk-factors subagent 处理。但主 agent 已把整节派给你 —— 你**只**抽关联方部分，其它部分返回空
   - 在 flags 里标"本节还包含 {诉讼|担保|承诺}，建议 risk-factors 补抽"
2. **10-K Item 13 通常很短**：大部分指向 proxy statement —— 如果内容少于 200 字，§5 产出"详见 proxy statement"占位，并在 flags 里说明
3. **前五大客户占比**：
   - 可能披露的是"占营收 X%"—— 直接引用
   - 可能没披露具体数字而是"前五大占比未重大" —— 填 `未披露`，不要猜
4. **关联方金额单位**：保留原文单位（元/美元/万元/亿元等）

## 反例

- ❌ `§5` 把关联方名单全列出（50+ 家）—— 只列"最大单一"或 Top 3
- ❌ claim: "公司存在关联方交易" —— 空话，几乎每家公司都有
- ❌ 把关联方每笔交易都列成 claim —— 合计/占比即可，单笔不抽除非异常大
- ❌ `§5_related_party` 完全编出数字 —— 未披露就写未披露
