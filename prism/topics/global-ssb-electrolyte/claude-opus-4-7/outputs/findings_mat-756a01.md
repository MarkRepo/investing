# Findings: Solid Power (SLDP) 2025 10-K

- **mat_id**: mat-756a01
- **来源文件**: 2025_SLDP_10-K_2026-02-25.htm（Solid Power, Inc. FY2025 10-K，2026-02-25 提交 SEC）
- **公司定位**: 美股纯硫化物固态电解质 (LPSC 路线) 玩家，自定位"电解质材料商 + cell 设计/工艺许可方"，明确不做商业 cell 制造，路线区别于 QuantumScape (氧化物)、SES (锂金属液固混合)
- **关联 K#**: K3 (硫化物电解质成本/产能) 主要锚点；K4 (锂金属负极) 关键证伪信号；K1 (硫化物量产时间) 间接锚点

---

## 一、K3 — 硫化物 LPSC 价格 8000→4000 元/kg 2027 前

### K3-1: SLDP 2025 年硫化物电解质实际产能仍为 pilot/batch 级，连续工艺 2026 底才上线
> "We currently produce electrolyte on two pilot manufacturing lines using a batch manufacturing process. ... By the end of 2026, we expect to commission a pilot electrolyte line using a continuous manufacturing process." (Item 1)
> "Once installed, we expect this pilot line to expand our annual electrolyte production capacity to up to **75 metric tons**."

含义：截至 2025 财年仍是 batch 工艺，2026 底才有 75 吨/年连续 pilot 线。**K3 的"2027 前 4000 元/kg"目标在 SLDP 体系内根本不在视野**。

### K3-2: 商业级 500 吨/年规划仍停留在"探索合作伙伴"阶段
> "we also intend to pursue a potential partnership for commercial-scale electrolyte production in the Republic of Korea ... a facility capable of producing up to **500 metric tons of electrolyte annually**."
> "However, there can be no assurance that we will establish a partnership to achieve these manufacturing goals in the near term or at all." (Item 1A)

含义：500 吨/年规划没有 capex、没有时间表、没有伙伴 — **SLDP 把"商业级电解质厂"capex 整体外包给（尚不存在的）韩国伙伴**。

### K3-3: 公司未披露任何 $/kg 或元/kg 电解质单价目标
全文 grep "per kg / $/kg / cost target" 仅出现定性"focus on cost reduction efforts"，无量化目标。

含义：相对中国厂商常给出 LPSC 成本下降路径，**SLDP 对 $/kg 路径完全沉默** — K3 中"4000 元/kg 2027 前"的乐观叙事缺乏第三方验证。

### K3-4: SK On 长合 8 吨/2030 前 = $8.3M，单价隐含约 $1,037/kg ≈ ¥7,500/kg ★关键锚点
> "SK On is required to purchase at least **eight metric tons** of electrolyte from Solid Power through 2030 ... we expect to receive at least **$8.3 million** from these electrolyte sales." (Item 1)

**计算**: $8.3M / 8 t = $1,037/kg ≈ **¥7,500/kg**（1 USD ≈ ¥7.2）

含义：10-K 中**唯一**可直接推算的硫化物电解质单价披露，约 ¥7,500/kg。这是 R&D 验证用小批量，且 5 年仅 8 吨累计 = 年均 1.6 吨。**与 K3 的"2027 前 4000 元/kg"对不上**：要么中国商业大宗将比 SLDP 验证级便宜 50%+，要么 SLDP 这个价格包含开发分摊。两种情况都意味着 K3 降本叙事不确定性极高。

### K3-5: Li2S 前驱体仍是供应瓶颈
> "Our electrolyte is made from abundant materials ... **except for the Li2S precursor material** ... we are taking a two-pronged approach to secure supply: sourcing from multiple global entities as well as pursuing development of in-house processes to produce material."
> "Li2S ... not currently produced at a scale we believe necessary to support our proposed commercial operations." (Item 1A)

含义：硫化锂仍是卡脖子环节，SLDP 在自建工艺。**反向支持赣锋/紫金等上游布局稀缺性，但同时警示：如果 Li2S 上游产能开不出来，K3 降本路径就失效**。

### K3-6: 政府补贴 — DOE $50M + 自配 $60M = $110M 做 75 吨/年 pilot
> "DOE ... grant of up to $50 million ... Our cost share obligation under the Assistance Agreement is **$60 million**" (Item 1)

**capex 强度**: $110M / 75 t/yr ≈ **$1.47M/吨年产能 ≈ ¥10.6M/吨年产能 ≈ 1万元/kg 年产能 capex**。

含义：SLDP 为 K3 中观 capex 提供上沿参考。若中国厂商宣称"千吨级硫化物线 5-10 亿元 capex"（50-100 万元/吨年），比 SLDP pilot 强度低一个数量级 — 要么技术工艺有差距，要么中国规划过于乐观。

### K3-7: 政策风险 — 特朗普行政命令暂停 IIJA 拨款
> "On January 20, 2025, an executive order ... paused disbursement of funds appropriated through the Bipartisan Infrastructure Law ... our continued receipt of funding under the Assistance agreement could be delayed or cancelled." (Item 1A)

含义：DOE $50M 补贴存在中止风险，可能推迟 SLDP 连续电解质线进度，K1 时间表向后偏移。

---

## 二、K4 — 锂金属负极路线（核心证伪信号）

### K4-1: SLDP 主推 cell 设计已是硅基负极 (Si-anode)，不是锂金属 ★★强证伪
> "Our current cell design is a multi-layered stacked pouch design made with a lithium nickel manganese cobalt oxide ('NMC') cathode, **silicon-based anode**, and separator."
> "While our cell research and development efforts are focused on electrolyte product competitiveness, our research and development teams are also working on lithium metal and anode-free cells. ... **Each of these technologies are significantly earlier in development than our current NMC-silicon cell design.**" (Item 1)

含义：**对 K4 论断的强烈证伪信号**。SLDP 作为最纯粹的硫化物全固态创业公司，已经把锂金属负极降级为研究阶段，主推 NMC-Si。

对比意义：
- 如果连 SLDP 都选硅基，**赣锋金属锂业务在全固态时代的需求拉动远低于市场预期**
- 但 SLDP 仍采购 "lithium metal foil"（Item 1A），说明并未完全放弃 — 是"硅 + 锂金属"双轨
- "anode-free" 也在研究 — 长期可能颠覆所有上游金属锂逻辑

### K4-2: 锂金属在供应清单中仍存在
> "key supplies, such as Li2S, NMC, **silicon, lithium metal foil**, and manufacturing tools." (Item 1A)

含义：硅和锂金属并列 — 双路线并行。**赣锋角度：金属锂仍是 SLDP 研发样品采购品，但已退出主路线 → 短中期需求量很小**。

---

## 三、K1 — 硫化物全固态量产时间（间接锚点）

### K1-1: BMW i7 demo 车 2025 年 5 月发布
> "BMW Group's introduction of an **i7 test vehicle** featuring our cells and solid-state battery technology in **May 2025** was a significant achievement." (Item 1)

含义：BMW i7 demo 确认（"test vehicle"，不是量产）。**K1 的"全固态 2027-2030 量产"从 BMW-SLDP 一线看仍是 demo 阶段**。

### K1-2: BMW JDA 已多次延期，2025 年底 BMW 可单方面终止
> "in September 2024, we further amended our JDA with BMW ... **BMW will have termination rights in certain circumstances beginning on December 31, 2025**" (Item 1)

含义：BMW 耐心有边界，2026 后若里程碑未达成，BMW 可退出 — 重大下行风险。

### K1-3: Samsung SDI + BMW 三方协议 2025/10 — BMW 把 cell 制造让给三星
> "In October 2025, we announced a collaboration with Samsung SDI and BMW AG ... we agreed to provide electrolyte to Samsung SDI, **which Samsung SDI will use to fabricate separator and/or catholyte and build cells**." (Item 1)

含义：**SLDP 退化为"电解质材料供应商"，BMW 不再依赖 SLDP cell 工艺**。K1 主线从"SLDP-BMW 直接量产 cell"切到"三星 SDI 量产 + SLDP 做材料"。

### K1-4: SK On 韩国 pilot 线 site acceptance 2026 Q1 完成
> "we have substantially completed the deliverables for site acceptance testing of the SK On Line and expect site acceptance to be complete in **the first quarter of 2026** ... we plan to begin delivering electrolyte to SK On under the electrolyte supply agreement in 2026." (Item 1)

含义：**K1 硫化物全固态量产链路上一个可被验证的近期节点**，值得 2026 Q2 财报追踪。

### K1-5: Ford 已退出，2026 Q1 JDA 到期不续
> "in connection with the **winding up of our cell development activities with Ford**" (Item 1)

含义：美国 OEM 在固态电池上的耐心比想象低。SLDP 客户从 3 个缩到 2 个。

---

## 四、安全性与技术成熟度（K3/K4 二阶证据）

### S-1: 2023-2024 出现 cell 热失控事件
> "during late 2023 and early 2024, **a few EV cells we produced went into thermal runaway during testing** ... we cannot guarantee that we or our partners will successfully mitigate the problem." (Item 1A)

含义：**"全固态本质上更安全"是 K3 营销卖点，SLDP 自己披露热失控直接削弱该卖点**。

### S-2: 硫化物遇水生成硫化氢的工业安全风险
> "our employees could be exposed to **toxic hydrogen sulfide as a result of the components we use being exposed to moisture**" (Item 1A)

含义：硫化物路线大批量生产时需 H2S 处理 — **中国厂商通常没强调的隐性成本，进一步压缩 K3 的"4000 元/kg"可行性**。

### S-3: SLDP 自承认硫化物"目前没有商业市场"
> "**There is currently no commercial market for sulfide-based solid electrolytes and one may never emerge.** Even if sulfide-based solid electrolytes are commercially adopted, we may not be able to effectively compete." (Item 1A)

含义：来自纯硫化物玩家自己的法律披露 — K1/K3 叙事最尖锐反向锚点。

---

## 五、财务与估值锚点

### F-1: 2025 营收 $21.7M，几乎全是合作/补贴收入，无商业电解质销售
- Total revenue and grant income: $21.7M (2025) vs $20.1M (2024) +8% YoY
- Collaborative: $15.8M（主要来自 SK On 线安装协议）
- Government: $6.0M（主要来自 DOE Assistance Agreement）
- **0 商业电解质销售收入**

### F-2: 2025 经营费用 $122.6M
- Direct costs $20.6M / R&D $72.5M / SG&A $29.4M
- 年烧约 $100M，R&D 占比 60%

### F-3: 现金充裕 — $336.5M 流动性 + 2026 年初再增 $122.2M = ~$459M
> "2026 ... combined capital expenditures and cash flow from operations ... between **$85 million and $100 million**"

**跑道约 4-5 年**。SLDP 财务上不会在 2027-2028 倒下，但财务存活 ≠ 商业化成功。

### F-4: 员工总数仅 ~230 人
对比中国硫化物玩家（容百整个公司数千人）— SLDP 是典型 small specialized R&D firm 模式。

### F-5: COO 2025 年离职
进入商业化阶段前关键运营岗位空缺 — 治理小负面信号。

---

## 六、竞争格局（K3/K1 的中国关联锚点）

### C-1: 10-K 直接点名中国 CASIP 平台
> "formation of the **China All-Solid-State Battery Collaborative Innovation Platform ('CASIP')** was announced in 2024. CASIP has government-backed investment funds and intends to have a supply chain for solid state batteries **up and running by 2030**." (Item 1A)

含义：SLDP 官方承认 CASIP 是直接竞争威胁并把时间锚定 2030。与中国"2027-2030 全固态量产"叙事时间窗口吻合，但 SLDP 把 CASIP 写在 Risk Factors，意味着担心被中国规模化能力压制。

---

## 七、综合判断与对论文影响

### 对 K3（硫化物 8000→4000 元/kg）：**显著看跌该论点的乐观速度**
1. SLDP 唯一可推算单价（SK On 协议）= ¥7,500/kg，且是研发批量，2030 才完成 8 吨累计
2. SLDP 75 吨/年 pilot 都要到 2026 底，500 吨"商业级"还没有合作方
3. SLDP capex 强度（$110M/75 吨年）暗示中国厂商 capex 规划可能过于乐观
4. 公司全文不愿给 $/kg 量化目标
5. Li2S 仍是供应瓶颈
6. 硫化氢工业安全成本通常被中国预算低估
- **建议**：K3 概率从 base case 下调，或时间线从"2027 前"放宽到"2028-2030"

### 对 K4（锂金属负极）：**强烈证伪信号**
1. SLDP 主推 NMC-Si 硅基，明确把锂金属/anode-free 列为"显著更早期"
2. 锂金属仅作为研发用 foil 采购
- **建议**：K4 中"锂金属是固态电池经济性关键"的论点需重写。**短中期赣锋金属锂业务的固态需求拉动应大幅下调预期**。可能向"硅基负极 + 局部锂金属应用"双路线收敛

### 对 K1（硫化物全固态量产时间）：**中性偏负面**
- 正面：BMW i7 demo（2025/5）、三星 SDI 加盟（2025/10）、SK On 线 2026 Q1 启用
- 负面：Ford 退出、BMW 把 cell 制造让给三星（SLDP 退化为材料商）、SLDP 2023-24 热失控、SLDP 自承认"商业市场可能永远不出现"、CASIP 2030 才规划完成
- **建议**：K1 的"2027 全固态商业上车"放宽到 2028-2030；保留竞争路线选项

### 主要差异 vs 中国厂商叙事
- 中国（容百、当升、赣锋）：千吨级中试 + 元/kg 大幅降本 + 锂金属/硅碳并行
- 美国 SLDP：75 吨 pilot + 单价 ¥7,500/kg + 硅为主锂金属研究
- **本质分歧**：中国押"规模快速摊薄成本"，SLDP 押"先做对再做大" — 哪条路对，2026-2027 SK On 线运行数据 + 中国头部硫化物中试投产是验证窗口
