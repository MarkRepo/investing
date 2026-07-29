# findings: mat-e9c3f9 — IonQ FY2025 10-K（命门 K1 量化补料）

- **来源**：IonQ, Inc. FY2025 Form 10-K，filed 2026-02-25，accession 0001193125-26-071562，doc `ionq-20251231.htm`（SEC EDGAR 一手件全文）
- **抓取背景**：01-prescan 当初因 `data.sec.gov` SSL 失败未取到此件，仅有 FY2024 10-K + Q1'26 10-Q；05-critic 判命门 K1「有机成色」定性坐实非量化 → request-more → 本轮重抓成功。
- **addresses**：K1（有机成色/商业化）· K3（毛利/单位经济）· K5（稀释）
- **可信度**：1.0（一手 SEC 审计报表附注）

---

## 🔑 决定性数字：并购贡献 FY2025 合并营收的 ~39%（有机 vs 并购的硬拆分）

10-K「Internal Control over Financial Reporting」段原文（管理层将当年并购排除在 ICFR 评估外时的法定披露）：

> "The Company completed the acquisitions of **id Quantique SA on April 30, 2025, Capella Space Corp. on July 11, 2025, Oxford Ionics Limited on September 16, 2025, and Vector Atomic, Inc. on October 2, 2025.** ... These acquisitions represent approximately **6% of the Company's consolidated total assets (excl. goodwill & intangibles), and approximately 39% of the Company's consolidated revenue as of and for the year ended December 31, 2025.**"

**解读（命门 K1 量化坐实）**：
- 四家主要并购合计贡献 **≈39% × $130.0M = ~$50.7M** 的 FY2025 营收。
- **且这是"部分年度"贡献**——id Quantique 仅并入 8 个月、Capella ~5.5 月、Oxford ~3.5 月、Vector Atomic ~3 月。**按全年 run-rate 折算，并购口径营收占比会显著高于 39%**（FY2026 尤甚）。
- 即 **FY2025 有机营收 ≈ $130.0M × 61% ≈ $79M**（且此有机口径内仍含一次性硬件销售）——**真实有机可持续经常性营收基数落在作者原估 $50-90M 区间的中偏下**，命门 K1「增长含并购/有机成色差」被一手件量化坐实。

---

## Note 15 — 收入 disaggregation（in thousands）

**按来源**：
| 来源 | 2025 | 2024 | 2023 |
|------|------|------|------|
| Quantum hardware（一次性硬件） | 69,946 | 21,594 | 7,083 |
| Platform, consulting & support services | 60,070 | 21,479 | 14,959 |
| **Total** | **130,016** | **43,073** | **22,042** |

→ FY2025 硬件占 **53.8%**、平台/咨询/支持占 46.2%（与 Q1'26 硬件 55.2% 口径一致）。

**按客户地区**：
| 地区 | 2025 | 2024 | 2023 |
|------|------|------|------|
| United States | 86,957 (67%) | 40,714 | 18,703 |
| Switzerland | 16,630 (13%) | 1,547 | 646 |
| Other international | 26,429 (20%) | 812 | 2,693 |

→ **Switzerland $16.6M 几乎全是 id Quantique（日内瓦 QKD 龙头，2025 并购）**；Other international 从 $0.8M(2024) 暴增到 $26.4M(2025) 同样并购驱动。**"国际化增长"叙事高度并购拼装**，与 39% 口径互证。

---

## 🔑 客户集中度（一手件首次量化 — 案子原为缺口）

> "Significant customers are those that represent more than 10% of total revenue. For the years ended December 31, 2025, 2024 and 2023, the Company had **three, two, and two** significant customers, respectively, that accounted for **53%, 77%, and 58%** of total revenue, respectively."

- **FY2025：3 家大客户 = 53% 营收**（2024：2 家 = 77%；2023：2 家 = 58%）。
- 集中度虽较 2024 的 77% 下降（因并购摊薄 + 客户数增至 3），但**仍高度集中**——过半营收系于 3 个客户，任一流失即重大冲击。这是环⑤应补入的已知风险（原案仅定性提"客户集中"）。

---

## 单位经济 / 毛利（坐实"恶化+lumpy"，回应反方质疑 4）

> "Cost of revenue (excluding D&A): FY2025 **$77,488K** vs FY2024 $20,597K，+**276%**"（营收同期 +202%）。

- 毛利（剔 D&A）= $130,016 − $77,488 = **$52,528K → GM 40.4%**（与 case 环①一致）。
- **成本增速 276% > 营收增速 202% → 毛利率结构性压缩被一手件坐实**，非纯 lumpy 噪音。10-K **未披露 hardware vs QCaaS 分部毛利**——反方"lumpy 假象"无法从一手件完全证伪，但"成本增速快于营收"这一硬事实压过"一次性拖累"辩解，恶化趋势成立。

---

## 稀释 / 融资（坐实 K5）

**2025 股权融资（净额）**：
- 2025-10-14：16,500,000 股 @ $93.00 + Series B 权证 → 净 **$1,977.1M**
- 2025-07-09：14,165,708 股 @ $55.49 + Series A 权证 → 净 **$977.2M**
- 2025 ATM（2 月启，3/10 终止）：16,038,460 股 → 净 **$358.3M**
- **合计 2025 股权募资净额 ≈ $3,312M**（现金池唯一来源，坐实"发股堆现金"）。

**round-trip 信号（客户权证）**：2019-11 与一项收入安排同时签发客户权证，可购最多 8,301,202 股；2020-08 归属 543,152 股 @ $1.38（行权至 2029-11）；2024-11 起余 7,758,050 股不再归属、已注销 → "以股权换合同"的历史实证。

**RPO**：2025-12-31 剩余履约义务 ~$370.0M，其中约 40% 未来 12 个月内确认（≈$148M）。

---

## 对各环的影响（供 04 局部重写用）

- **环①/③（K1 命门）**：有机成色从"定性坐实"→"**并购占营收 ~39%（部分年度，全年 run-rate 更高）、有机 ~$79M 含一次性硬件**"精确量化。
- **环②**：可信有机经常性营收基数收窄，模型 A/B 的 Base 锚更实（有机 QCaaS 口径进一步压低）。
- **环⑤**：新增可量化的**客户集中度风险（3 客户=53%）**。
- **反方回应**：质疑 3（"靠买不靠造"）被 39% 口径反向坐实为作者方向；质疑 4（毛利 lumpy）被"成本增速 276%>营收 202%"部分压制。
