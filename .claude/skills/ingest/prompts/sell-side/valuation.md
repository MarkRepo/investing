# subagent: valuation

**负责 section**：估值 / 估值分析 / 目标价 / Valuation / Price Target

**targets**：`claims`（**仅**）

---

## 你要产出的东西

### `claims`

估值 section 通常含：

- **评级**（买入 / 增持 / 中性 / 减持 / 卖出 / Buy / Hold / Sell / Overweight / Underweight）
- **目标价**（绝对价格）
- **估值方法** + **倍数**（PE / EV-EBITDA / P/S / DCF / 分部估值 SOTP）
- **隐含空间** / **预期收益**（当前价对目标价的涨跌幅）
- **估值对比**（相对于历史均值 / 同业均值的分位）

系统没有专门字段存"目标价" / "评级"。全部塞进 `claim_text`，用 `subject_tag=consensus_direction` 落地。

**必抽的 3 条**（研报估值的骨干）：

1. **评级 claim**（1 条）：
   ```json
   {
     "claim_text": "[中信证券 2025-10-28] 维持买入评级",
     "subject_tag": "consensus_direction",
     "polarity": "bull",
     "claim_type": "qualitative",
     "timeframe": "long-term",
     "evidence": [{"text": "我们维持公司「买入」评级...", "type": "primary"}],
     "confidence": "high"
   }
   ```

2. **目标价 claim**（1 条）：
   ```json
   {
     "claim_text": "[中信证券 2025-10-28] 目标价 ¥2,200，对应当前价 ¥1,850 隐含 +18.9% 空间",
     "subject_tag": "consensus_direction",
     "polarity": "bull",
     "claim_type": "quantitative",
     "timeframe": "long-term",
     "evidence": [{"text": "给予目标价 2,200 元，较当前股价 1,850 元有 18.9% 的上涨空间", "type": "primary"}],
     "confidence": "high"
   }
   ```

3. **估值方法 + 倍数 claim**（1-2 条）：
   ```json
   {
     "claim_text": "[中信证券 2025-10-28] 采用 PE 估值，给予 FY2026 25x PE（行业均值 22x，历史 5 年中枢 24x）",
     "subject_tag": "consensus_direction",
     "polarity": "neutral",
     "claim_type": "quantitative",
     "timeframe": "FY2026",
     "evidence": [{"text": "...", "type": "primary"}],
     "confidence": "medium"
   }
   ```

### 评级 → polarity 映射

| 评级（中文 / 英文） | polarity |
|---|---|
| 强烈推荐 / 买入 / Buy / Overweight / Strong Buy | bull |
| 推荐 / 增持 / Outperform | bull |
| 中性 / Hold / Neutral / Market Perform | neutral |
| 减持 / Underperform | bear |
| 卖出 / Sell / Underweight | bear |

### 目标价的 polarity

- 目标价 > 当前价 → `bull`
- 目标价 ≈ 当前价（±3%）→ `neutral`
- 目标价 < 当前价 → `bear`

如果研报没给当前价，你也不要去查—— polarity 跟**评级**走，别根据目标价孤立判断。

### 估值方法的 polarity

默认 `neutral`——估值方法本身中性，除非作者明确表达"高于历史中枢可接受"这类判断。作者表达担忧 → `bear`；强调"折价安全边际" → `bull`。

## 其它可选抽取（按研报详尽程度决定抽不抽）

- **分部估值**（SOTP）：如果研报给了每个分部的独立估值，每个分部一条 claim，subject_tag=`consensus_direction`，timeframe 取作者指定的那个 FY
- **历史估值分位**：作者引用"当前 PE 处于历史 10 分位"这类 → 抽 1 条，polarity 看作者语境（通常安全边际视角是 bull）
- **同业对比**：作者列同业公司的 PE/EV-EBITDA 对比表 → **选是否抽**。如果只是陈列数字无判断 → 不抽；作者据此得出"相对低估" → 抽结论那一条

## 控制抽取量

- 最少：3 条（评级 + 目标价 + 估值方法）
- 常见：4-6 条（加 1-2 条分部估值或历史分位）
- 不超过 8 条。超过说明在抽噪音（分业务的估值细节 / 敏感性分析每列）。

## 特有注意事项

1. **目标价带单位**。A 股用"¥"或"元"，美股用"$"。claim_text 里保留原单位。
2. **当前价 / 隐含空间**的"事实"：当前价是研报发布时的瞬时值，不适合独立成 claim（时间属性强，很快过期）——合进目标价 claim 的 claim_text 里作为上下文提示即可。
3. **"维持 / 上调 / 下调评级"**：如果本报告相对前报变动了评级/目标价，这是重要信号：
   - "上调目标价从 ¥1,800 至 ¥2,200" → 单独一条 claim，subject_tag=`consensus_direction`，confidence=high
4. **不产出** `financial_rows`（估值假设数字属于 claim 不属于 fin 表）、`profile_fragments`、`meta_updates`。
5. **DCF 的关键假设**（WACC / 永续增长率 / 预测期内 FCF CAGR）如果作者明写 → 每个关键假设一条 claim，subject_tag=`guidance_reliability`（作者对关键参数的假设可信度）

## 反例

- ❌ claim_text: "目标价 2200" —— 缺单位、缺 polarity 线索
- ❌ `polarity: "positive"` —— 必须 `bull`
- ❌ 把估值方法的每个细节参数（β / Rf / Rm）都抽成独立 claim —— 过度细节
- ❌ 抽"公司合理估值区间 ¥2,000 - ¥2,300" 不取中枢就成两条 claim —— 取区间中枢或目标价即可
- ❌ 产出 `financial_rows` 放目标价 —— 价格不是财务指标
- ❌ 把"同业 PE 对比表"每行都抽成 claim —— 抽作者据此得出的判断那一条
