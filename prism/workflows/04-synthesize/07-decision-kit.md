# 产出 07 — 决策辅助 (Decision Kit)

**定位**：把前 6 份产出的核心结论压缩成投资决策直接需要的形式  
**训练知识比例**：约 30%（主要是整合前 6 份产出的结论）  
**产出文件**：`prism/topics/{slug}/outputs/07_decision_kit.md`

**前置条件**：产出 01-06 必须至少有 4 份已生成（status=fresh）

---

## Step 0：前置检查

```bash
python -c "
from prism.scripts.topic import read_topic
t = read_topic('{slug}')
fresh = [k for k, v in t['outputs_state'].items() if v['status'] == 'fresh']
print('已生成产出：', fresh)
"
```

如果不足 4 份 fresh，停止并提示先完成更多产出。

---

## Step 1：读取已有产出

```bash
cat prism/topics/{slug}/outputs/01_business_panorama.md
cat prism/topics/{slug}/outputs/02_cycle_positioning.md
cat prism/topics/{slug}/outputs/03_narrative_ecology.md
cat prism/topics/{slug}/outputs/04_implied_expectations.md
cat prism/topics/{slug}/outputs/05_historical_mirrors.md
cat prism/topics/{slug}/outputs/06_risk_blindspots.md
```

---

## Step 2：撰写决策辅助

### 2.1 一页纸摘要

```
主题：{display_name}
研究问题：{question}
生成日期：{date}

【商业理解】
{3 句话：这是什么生意，护城河在哪里，增长驱动是什么}

【周期定位】
当前处于：{位置}
方向：{向上/横盘/向下}，置信度：{高/中/低}

【叙事】
主流叙事：{一句话}
是否认同：是/部分/否，原因：{一句话}

【隐含预期】
市场假设：{一句话}
我的判断：{偏乐观/中性/偏悲观}

【类比】
最像：{案例}，教训：{一句话}

【核心风险】
最大已知风险：{一句话}
最大盲点风险：{一句话}
```

### 2.2 核心假设清单（What Would Have To Be True）

投资成立需要以下假设为真：
1. {具体、可验证的假设}
2. {具体、可验证的假设}
3. {具体、可验证的假设}

如果以上假设有任何一个被证伪，投资逻辑需要重新评估。

### 2.3 Signposts（路标事件）

接下来 3-12 个月，以下事件/数据将帮助验证或证伪上述假设：

| 时间 | 事件/数据 | 多方信号 | 空方信号 |
|------|----------|----------|----------|
| | | | |

### 2.4 研究成熟度评估

- **信息完整性**：{高/中/低}（已覆盖多少关键维度）
- **观点确信度**：{高/中/低}（证据有多支持）
- **建议下一步**：{继续深挖哪个方向 / 等待哪个催化剂 / 还缺什么资料}

---

## Step 3：写入文件 + 更新状态

output_key = `07_decision_kit`

---

## Step 4：汇报

```
✅ 决策辅助已生成 → v{N}
核心假设数量：{N} 个
关键 Signpost 数量：{N} 个
研究成熟度：{评级}
```
