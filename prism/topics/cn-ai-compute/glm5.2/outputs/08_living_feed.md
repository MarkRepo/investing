---
slug: cn-ai-compute
output_key: 08_living_feed
version: 1
generated: 2026-06-18
---

# 信息流时间线 — 中国算力行业（glm5.2）

---

## 2026-06-18 glm5.2 从零重跑完成（00→05 全流程）

**来源**：glm5.2 主 agent 串行跑完 workflow 00-research-topic → 03-extract-findings → 04-synthesize → 05-critic-review

**关键信息**：
- 新建 glm5.2 variant（与 opus4.8 并存对比），复用 slug 级 materials/inbox 资料但 thesis→outputs 全部由 glm5.2 独立产出。
- thesis_v0 强度 6/10（分化看多，比 opus4.8 v0 的 6.5 更克制）；核心 delta：用 market_data 实时估值修正 opus4.8——capex-beta 层（光模块/ODM）PEG<1 已消化（中际旭创 2027E PE 12x、工业富联 PS 1.45x），命门从"估值双杀"转为"英伟达 capex 见顶"；芯片设计层 5x 英伟达极端透支（寒武纪 PE 305x），转谨慎。
- 命门 1 新增"国产化率叙事 vs BOM 真相落差"：910C 晶圆 80% 台积电（经 Sophgo 绕道）、HBM 95% 三星（经 CoAsia），真自主产能 2026 才起步。
- 11 份 findings 覆盖 K1-K6 + 三命门；3 份年报（寒武纪/工业富联/中际旭创）+ 6 份 inbox 深度整理 + 2 份 web-search 聚合。
- arena 分流：A2 capex-beta 已消化龙头（deep, 4.0）> A1 上游高壁垒耗材（deep, 3.8）> A3 国产芯片设计（watch, 3.0，等回调）> A4 智算中心第三方 IDC（watch, 2.8）> A5 国资智算中心/A6 GPU 创业梯队（eliminated, 1.8）。

**对已有判断的影响**：
- 支持了：国产替代方向不可逆（华为资本配置+长鑫方法论+寒武纪扭亏）；capex-beta 已消化（market_data 实时验证 PEG<1）。
- 新增了：国产化率真相落差（910C BOM 80% 台积电/95% 三星）；推理效率压量风险（DeepSeek-V4 同硬件产出 4 倍）。
- 调整了：芯片设计层从 opus4.8 的笼统"看多国产链"调整为"对 A3 转谨慎等回调"（因 5x 英伟达极端估值）。

**当前判断更新**：
维持 thesis_v0 6/10 分化看多。critic verdict=request-more（命门 1/3 单线承重 + 致命一击 Sophgo 堵死被低估），方向不翻案，待补官方产能数据 + 推理硬件用量测算。

---

## 待跟踪（living feed 后续触发点）

- **K1/K2**：中芯 7nm 官方产能指引、长鑫 HBM3 量产官宣、昇腾物料表官方核验 → 命门 1 真相落差收敛验证。
- **K3**：单位推理网络/光模块用量实证、杰文斯悖论 AI 实证 → 命门 3 净影响定论。
- **K4/K6**：英伟达季度 capex 指引、北美云厂 capex 拐点、1.6T 出货曲线 → 命门 2 capex 见顶验证。
- **K5**：润泽/万国上架率、智算中心利用率回升、跨界玩家退场情况 → 智算中心回报模型验证。
- **黑天鹅**：制裁堵死 Sophgo 绕道（KILL-4 触发）→ 命门 1 "有单无货"。
