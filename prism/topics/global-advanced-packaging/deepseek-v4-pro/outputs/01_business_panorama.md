---
slug: global-advanced-packaging
output_key: 01_business_panorama
version: 1
generated: 2026-05-17T15:45:00Z
data_freshness: 2026Q1
data_freshness_basis: TSMC 20-F FY2025 (2026-04-16), Morgan Stanley 2026-05-08, Amkor 10-K FY2025 (2026-02-20), ASE 20-F FY2025 (2026-04-01)
---

# 商业全景：先进封装 CoWoS/SoIC Arena

> 生成于 2026-05-17，训练知识占比约 40%，资料更新截至 2026Q1

## Arena 定义与边界

先进封装是将多颗芯片（CPU/GPU/HBM/IO die）通过硅 interposer、TSV、混合键合等技术集成在同一封装体内的工艺，是 AI 芯片性能的关键物理瓶颈。

**核心技术谱系：**

| 技术 | 定位 | 主导者 | 代表应用 |
|------|------|--------|---------|
| CoWoS (Chip-on-Wafer-on-Substrate) | 2.5D 硅 interposer | TSMC 近乎垄断 | NVDA B200/H200/Rubin, Google TPU |
| SoIC (System-on-Integrated-Chips) | 3D 混合键合堆叠 | TSMC | 下一代 AI 芯片、Apple Silicon |
| InFO (Integrated Fan-Out) | 低成本 2.5D | TSMC | 移动端/边缘 AI |
| EMIB (Embedded Multi-die Interconnect Bridge) | 2.5D 桥接 | Intel | Intel 自家产品 |
| FOCoS (Fan-out Chip-on-Substrate) / VIPack | 2.5D 低成本替代 | ASE | 中端 AI/网络芯片 |
| FCBGA with 2.5D interposer | 2.5D 硅 interposer | Amkor | 部分 AI/HPC 应用 |
| CPO (Co-packaged Optics) | 光学+电气联合封装 | ASE/TSMC | 2027+ 下一代光互联 |

**排除边界**：不包含传统引线键合封装、不包含 PCB 级组装、不包含前道晶圆制造（仅含后道先进封装）。

## 市场规模与结构

| 指标 | 数据 | 来源 |
|------|------|------|
| TSMC CoWoS 产能（2025 年底） | 120 kwpm | Morgan Stanley 2026-05 |
| TSMC CoWoS 产能（2027E） | 165 kwpm | Morgan Stanley 2026-05 |
| Non-TSMC 先进封装产能（2025 年底） | 23 kwpm | Morgan Stanley 2026-05 |
| Non-TSMC 产能（2027E） | 80 kwpm | Morgan Stanley 2026-05 |
| SoIC 产能（2025 年底） | 45 kwpm | Morgan Stanley 2026-05 |
| SoIC 产能（2027E） | 78 kwpm | Morgan Stanley 2026-05 |
| 2026 年 AI 芯片晶圆消耗 | $272 亿 | Morgan Stanley 2026-05 |
| TSMC AI 收入 2024-2029 CAGR | 60% | Morgan Stanley 2026-05 |
| TSMC FY2025 总营收 | NT$3.81 万亿（~$1215 亿） | TSMC 20-F |
| TSMC FY2025 毛利率 | 59.9% | TSMC 20-F |
| TSMC FY2025 CAPEX | NT$1.27 万亿（~$406 亿） | TSMC 20-F |

**集中度**：CoWoS 需求分配 NVDA 59%、AVGO 20%、AMD 9%、其他 12%（MS 数据）。TSMC 在 CoWoS 领域的份额 >80%，远高于前道晶圆代工（~60%）。

## 价值链解析

```
[上游：设备/材料] → [中游：先进封装服务] → [下游：AI芯片客户]
```

### 上游：封装设备与材料
- **封装设备**：bumping（sputter/电镀）、bonding（TCB/hybrid bonding）、测试（handler/socket/探针卡）——测试设备 CAGR 35%+
- **关键材料**：硅 interposer、TSV 填充材料、underfill、热界面材料——interposer 面积持续增大是核心趋势
- **设备商**：ASMPT（后端设备龙头，MS OW），Hon Precision（handler）、WinWay（socket）、MPI（探针卡）

### 中游：先进封装服务 —— 三层格局

| 层级 | 参与者 | FY2025 营收 | 毛利率 | 定位 |
|------|--------|------------|--------|------|
| **Tier 1** | TSMC | NT$3.81T（$1215亿） | 59.9% | 绝对王者，CoWoS >80% 份额 + SoIC 100% |
| **Tier 2** | ASE | NT$6,454亿（$206亿） | 17.7% 整体 / 23.8% 封装测试 | 全球最大 OSAT，技术组合最全（CoWoS/CPO/3D IC） |
| **Tier 3** | Amkor | $67亿 | 14.0% | 2.5D FCBGA，CAPEX 下降中 |

**差距根源**：TSMC 的 60% 毛利率 vs ASE/Amkor 的 15-24%——不是市场规模的差距，是利润池分配的差距。TSMC 吃掉了先进封装价值链中最肥的部分（前道+后道一体化），OSAT 只能拿到"剩下的"。

### 下游：AI 芯片客户
- **NVDA**（CoWoS 最大客户 59%）：采购承诺 $391 亿（+74% YoY）——需求端最强信号
- **AVGO**（20%）：Google TPU + Meta MTIA 定制 ASIC
- **AMD**（9%）：MI 系列 GPU
- **云厂商自制**（Google TPU/Amazon Trainium/MS Maia）：占比上升中，进一步扩大 CoWoS 需求基础

## 商业模式

**TSMC 模式（Foundry + Packaging 一体化）**：
- 晶圆制造和先进封装捆绑提供，客户锁定极深
- 毛利率 60%，净利率 45%——平台型利润而非代工利润
- 2025 CAPEX $406 亿（含 Fab 23/24 先进封装专用厂），议价权随稀缺性增加而提升

**OSAT 模式（ASE/Amkor）**：
- 第三方独立封装服务，没有晶圆制造绑定
- 毛利率 14-24%，净利率 5-8%——代工型利润
- ASE 2025 CAPEX ~$43 亿，Amkor ~$9 亿（且下降）——资本投入差距是份额差距的放大器

**关键差异**：TSMC 可以将先进封装的成本包含在整体 wafer 报价中（不单独定价），客户无法拆分比较；OSAT 必须按封装服务单独报价，价格透明、议价空间小。

## 竞争格局

**格局类型**：极度不对称的三层结构

| 层级 | 格局 | 护城河 |
|------|------|--------|
| CoWoS/SoIC | TSMC 近乎垄断（>80%） | 前道+后道一体化、客户锁定、CAPEX 碾压 |
| 2.5D 替代方案 | ASE VIPack + Amkor FCBGA | 成本优势、不与客户的前道供应商竞争 |
| 传统封装 → 先进转型 | 长电科技/通富微电 | 中国国产替代政策保护 |

**核心竞争要素排序**：
1. 前道+后道一体化能力（TSMC 独占）> 
2. 客户关系和认证壁垒（切换成本极高）> 
3. 技术先进性（bump pitch/interposer 尺寸/良率）> 
4. 成本（ASE/Amkor 的优势维度）

## 信息来源

- 训练知识 40%（封装技术分类、商业模式分析、竞争格局定性）
- mat-cff05b: Morgan Stanley 2026 半导体（CoWoS 供需数据、产能预测、需求分配）
- mat-851944: TSMC 20-F FY2025（营收、毛利率、CAPEX、风险披露）
- mat-452283: Amkor 10-K FY2025（营收、毛利率、CAPEX、技术组合）
- mat-c94528: ASE 20-F FY2025（营收、封装/测试增速、技术组合、CAPEX）
- mat-b19f7c: NVDA FY2026 10-K（采购承诺 $391B、CoWoS 依赖披露）