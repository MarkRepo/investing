# 宏观层 · 全输入源门外汉词典（输入源 gloss 层）设计

> 状态：已与用户逐块确认架构方向，待用户复审本文档后转实现计划
> 日期：2026-06-11 · slug `global-macro-rates-liquidity` · variant `opus4.8` · type=macro
> 前置（均已实现）：
> - `2026-06-07-macro-rates-liquidity-layer-design.md`（第一期 MVP，登记表 + primer + m_regime_read + transmission_map）
> - `2026-06-07-macro-dynamic-monitoring-and-maturation-design.md`（第二期，FRED 自动抓 + 报警带 + Web 输入表）
> - `2026-06-10-macro-cross-cutting-and-judgment-ledger-design.md`（第三期，横切接入 + 判断台账）

---

## 0. 一句话目标

给 macro_inputs 登记表里**每一个输入源**配一份门外汉能真正读懂、真正会用的三层词条（**定义/含义 · 为什么看 · 怎么用**），机械保证**零遗漏**，并落成两处可读表面：① 新生成的姊妹文件 `00b_input_glossary.md`（按族系分组的输入源词典），② 现有 Web「输入源信息表」每条可展开的 gloss。

这是 primer §1 概念词典（机制/心智模型，永恒）的补位：概念词典教"费雪、净流动性、久期"这类**机制**，但 ~120 个**具体输入源**里有大量黑话（JOLTS、SLOOS、FRA-OIS、SOFR−IORB、ACM、CIP 基差、QRA、SRF/FIMA、NFCI、克强指标…）一出现就把门外人挡住，概念词典并不覆盖。本期补的就是"每个具体输入源该怎么读、怎么用"。

---

## 1. 背景与现状（已核实）

- **macro_inputs.yaml**（`global-macro-rates-liquidity/opus4.8`）现有 ~127 条 `name`（含 CIP 合成腿），是输入源的唯一登记中枢，schema/校验在 `prism/scripts/macro_registry.py`。每条已有 `causal_sentence`（一句**机制**因果链，CD/CF 必填，给传导/机读用）。
- **primer §1「术语表」**：约 18–20 条**概念/机制**词条（费雪方程、收益率曲线、曲线四形态、净流动性、信用利差、社融、M1/M2、信贷脉冲、DR007、LPR、MLF/OMO、DXY、USDCNY、中美利差、carry、久期）。它教心智模型，不逐输入源解释。
- **m_regime_read.md「活注解层」**：关键指标已带 `这是什么 / 为什么看它 / 现在说明什么` 三句注解——但**绑当下读数、每月变**。
- **Web「输入源信息表」**：`app/routes/prism.py` + `app/templates/prism/macro_inputs.html` 渲染来源/抓取方式/最近值/报警带。
- **primer 机械门禁范式**：`prism/scripts/test_primer_gate.py` 已示范"结构不达标就把 fresh 降 draft"——本期"覆盖闸门"复用同款哲学。

### 1.1 现状缺口

三处解释输入源的地方各有定位，但**没有一处覆盖全部输入源、且脱开读数地讲"怎么用"**：

| 现有载体 | 是什么 | 缺口 |
|----------|--------|------|
| primer §1 概念词典 | 机制/心智模型，永恒 | 只覆盖高频概念，~40-50 个具体输入源黑话无词条 |
| `causal_sentence` | 一句机制因果链，机读 | 术语化、非大白话；门外人读不懂"怎么用" |
| m_regime_read 活注解 | 逐指标三句注解 | 绑当下读数、每月变；非"这指标永恒怎么读"的稳定词典 |

### 1.2 驱动本设计的用户诉求（brainstorm 中逐条拍板）

1. **覆盖所有参与的输入源**——不是只补高频概念，是登记表里每一条都要有词条；"零遗漏"要被**机械保证**，不靠人记。
2. **不只说"测啥的"，要有指标本身的定义/含义**——门外人先得知道这指标到底是什么。
3. **要让门外人真正"会用"**——高了/低了、走阔/收窄各意味什么、看它做什么决定/影响哪只持仓。
4. **机读、自动同步、零漂移**（贯穿前三期的元诉求）——故走"字段 + 生成器"，不手写散文。

### 1.3 本期定型（逐项为用户拍板结论）

| 维度 | 决定 |
|------|------|
| 词条形态 | **分层**：primer §1 概念词典（机制）不动 + 新增输入源词典（具体输入源逐条） |
| 每条结构 | **三层**：`define`（定义/含义）· `read`（为什么看/测什么）· `use`（怎么用：高低/走阔各意味什么 + 影响什么决策/持仓） |
| 真相源 | **做法一**：gloss 写进 macro_inputs.yaml（唯一真相源），`macro_registry` 登记 + 校验字段 |
| 与 causal_sentence 关系 | **并存不替**：causal_sentence 继续给机制/传导/机读；gloss 是门外人教学层，读者不同，允许少量信息重叠 |
| 放置 | **独立姊妹文件** `00b_input_glossary.md`（生成），与 m_regime_read / transmission_map 并列；primer §1 加一句指向 |
| Web 表 | **顺手接入**：同一份 gloss 渲染进现有输入源表（每条可展开"定义/怎么用"） |
| 覆盖保证 | **覆盖闸门**：缺 gloss 的被追踪输入被机械列出；填充期软告警，补齐后翻硬门禁 |
| 撰写 | ~120×3 句由 LLM 按 tier/family 分波起草（A load_bearing 先行），用户抽审 |

---

## 2. 数据模型（macro_inputs.yaml + macro_registry.py）

每条 input entry 新增两个字段：

```yaml
- name: JOLTS 职位空缺/离职率
  # ...现有字段不动（tier/targets/mechanism/causal_sentence/observed/...）...
  family: 增长就业                          # 族系，用于词典/Web 分组
  gloss:
    define: 美国劳工部(BLS)月度调查，统计企业未填补的职位空缺数与主动离职率(quits)
    read:   空缺/离职率＝劳动力市场松紧的温度计；离职率反映打工人敢不敢主动跳槽的信心
    use:    离职率回落+空缺下降＝就业降温→Fed 有降息空间→利好长久期成长；反之偏鹰、压成长股
```

**字段语义**
- `family`（str）：族系分组键。生成器用一份**有序 canonical 族系清单**控制分组与展示顺序（贴 primer 教学骨架，见 §4）。free string 但须在 canonical 清单内（否则校验报错，杜绝拼写漂移）。
- `gloss`（dict）：门外人三层词条。三键 `define/read/use` 均为短句（建议各 ≤ 60 字，大白话、首次出现的缩写就地展开）。

**在 `macro_registry.py` 的改动**
- 模块顶部 schema 注释补 `family` / `gloss` 两字段说明。
- `validate_registry` 增校验：
  - `family` 若存在须在 `CANONICAL_FAMILIES` 内；
  - `gloss` 若存在须含 `define/read/use` 三键且非空（半填=错，避免开天窗）。
- 新增 `CANONICAL_FAMILIES` 有序元组（族系清单 + 顺序）。
- 覆盖检查辅助：`inputs_missing_gloss(registry) -> list[str]`（返回"被追踪却缺 gloss/family"的 name），供生成器与门禁共用（"被追踪"定义见 §5）。

> CIP 合成腿（`Spot EURUSD`、`EUR 3M OIS` 等，monitoring=false、background）也要 gloss，但其 `use` 标注"供 X 基差合成、不单独读"，并在词典里归到所属合成项的族系下（见 §5 覆盖范围）。

---

## 3. 生成器（新脚本，零 LLM）

新脚本（暂名 `prism/scripts/input_glossary.py`）：

1. `read_registry(slug, variant)` 读登记表。
2. 按 `CANONICAL_FAMILIES` 顺序分组 inputs（组内按 tier→importance→name 稳定排序）。
3. 渲染每条：`define` 一行 + `read` 一行 + `use` 一行；末尾自动**交叉链**——
   - 若该输入的机制能对上 primer §1 某概念词条（如 HY/IG OAS→「信用利差」），加"见〈概念词条〉"；映射用一份显式 `CONCEPT_LINKS` 小表（输入 name → 概念词条锚），不做模糊匹配。
   - 加"· 表内追踪"指向 Web 输入源表。
4. **两个产出表面**：
   - **`00b_input_glossary.md`**：生成完整 frontmatter（slug/variant/type=macro-input-glossary/generated/companion）+ 按族系分组的词典正文。整文件由生成器写（它是纯生成产物，非手写）。
   - **primer §1 指向句**：primer 是手写产物，故只在 §1 末尾注入一行指向（用标记 `<!-- BEGIN auto:gloss-pointer -->…<!-- END -->` 包裹，生成器只重写这一行，不碰 primer 其余正文）。
5. `00b_input_glossary.md` 作为普通 `outputs/*.md`，复用现有 markdown 输出视图与链接规约（同 primer 链到 m_regime_read），**不需新路由**。

生成器入口：`python -m prism.scripts.input_glossary <slug> <variant>`（与现有脚本风格一致）。

---

## 4. 族系清单（CANONICAL_FAMILIES，初稿）

贴 primer 的 L1→L4 + 三体制 + 中国第二块教学骨架，初稿如下（实现时按实际 inputs 微调）：

1. 增长就业（NFP/失业率/初请/JOLTS/ISM/零售/GDPNow/工业增加值…）
2. 通胀（核心 PCE/CPI/PPI/5y5y/油价/中国 CPI/PPI…）
3. 货币政策（美）（联邦基金/点阵图/FedWatch/FOMC/官员讲话…）
4. 流动性·数量（WALCL/TGA/RRP/净流动性/准备金/SLOOS/QRA/赤字…）
5. 利率·曲线结构（2Y/10Y/30Y/TIPS/期限溢价/2s10s…）
6. 信用与风险偏好（IG/HY/CMBS OAS/MOVE/VIX/NFCI/CAPE/breadth…）
7. 资金面咬合（SOFR−IORB/FRA-OIS/swap line·SRF·FIMA…）
8. 汇率·跨境套利（广义美元/DXY/CIP 基差及腿/日元 carry/BoJ/ECB/BIS/TIC/黄金…）
9. 中国货币·流动性（社融/M1·M2/信贷脉冲/DR007/LPR/MLF/7天 OMO…）
10. 中国增长·外需（官方/财新 PMI/社零/固投/出口/克强指标…）
11. 其他/跨资产代理（比特币/大宗/AI-capex 代理/持仓拥挤…）

> 顺序即词典展示顺序与 Web 表分组顺序，单一真相。

---

## 5. 覆盖闸门（机械保证零遗漏）

- **"被追踪输入"定义**：登记表 `inputs` 全集（含 monitoring=false 的 CIP 腿——它们也参与判断，门外人也会在词典/表里看到）。
- `inputs_missing_gloss(registry)` 列出缺 `gloss`（三键不全）或缺 `family` 的 name。
- **两段式严格度**：
  - **填充期（软）**：生成器在 `00b` 顶部和 stderr 打印"尚缺 N 条：[…]"，但仍生成已填部分——允许按波次推进。
  - **补齐后（硬）**：挂一个 pytest（仿 `test_primer_gate` 风格）：`inputs_missing_gloss` 非空即 fail。一旦全部填齐就打开此门禁，此后任何人加新输入忘了写 gloss → 测试红，机械堵漏。
- 与现有 `validate_registry` 协同：validate 管"字段格式对不对"，门禁管"覆盖全不全"。

---

## 6. Web「输入源信息表」接入

- `app/routes/prism.py`：把每条 input 的 `gloss`/`family` 一并传给模板（数据已在 registry 内，无新增取数）。
- `app/templates/prism/macro_inputs.html`：
  - 按 `family` 分组（顺序用 `CANONICAL_FAMILIES`，未知 family 兜底到"其他"）。
  - 每条加可展开区（`<details>` 或点击展开）显示 `define/read/use` 三层。
  - 缺 gloss 的条目显示占位（如"词条待补"），与门禁的待补清单呼应。
- 不动抓取/报警/eval-trace 等现有逻辑，纯展示增量。

---

## 7. 撰写计划（内容是真正的工作量）

~120 条 × 3 句大白话由 LLM 起草，读每条 `name`/`causal_sentence`/`note`/`source` + 宏观知识，**按波次**：

- **波 1**：tier A 且 `importance: load_bearing`（真正搬动判断的核心输入）。
- **波 2**：tier A `confirming`。
- **波 3**：tier B。
- **波 4**：tier C + CIP 合成腿 + background。

每波：写 gloss → 跑生成器 → 自检（定义准不准、use 是否门外人可上手、有无术语未展开）→ 用户抽审 → 进下一波。准确性优先（这些是真金融定义，不能编）。

---

## 8. 非目标（YAGNI）

- 不改 m_regime_read 活注解层（它绑读数、是另一层，保留）。
- 不把 gloss 反向塞回 causal_sentence 或合并两字段（读者不同）。
- 不做多语言、不做 gloss 的版本历史/审计。
- 不为 `00b_input_glossary.md` 起专属路由（复用 outputs markdown 视图）。
- 不在本期推广到其他 topic 的 primer（本期只 macro）。

---

## 9. 验收

1. macro_inputs.yaml 每条被追踪输入有合法 `family` + 三键齐全的 `gloss`；`validate_registry` 通过。
2. `inputs_missing_gloss` 返回空；覆盖门禁 pytest 绿。
3. `python -m prism.scripts.input_glossary global-macro-rates-liquidity opus4.8` 生成 `00b_input_glossary.md`，按族系分组、含交叉链、frontmatter 完整。
4. primer §1 含一行指向姊妹词典（标记包裹、可重生成）。
5. Web 输入源表按族系分组、每条可展开三层 gloss；缺词条显占位。
6. 生成器二次运行幂等（同输入同输出，markers 内容稳定）。
