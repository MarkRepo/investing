---
slug: global-solid-state-battery
variant: claude-opus-4-7
output_key: 08_living_feed
version: 1
generated: 2026-05-19T00:00:00+08:00
type: signal_subscription_feed
---

# 信号源订阅清单：全球固态电池

> 这份不是传统的"研究时间线"日志，而是 **monitor 阶段的信号源订阅清单**——把 thesis 中 5 个 Killer Question（K1-K5）映射到具体可持续抓取的数据源，明确"看什么、多久看一次、怎么抓、出现什么信号要触发动作"。
>
> **使用方法**：每周对 K1-K5 分别跑一遍下方的 feed，把异常信号追加到本文件末尾作为 timeline 记录，重大信号触发 thesis 更新或仓位动作。

---

## 总览

| 维度 | 内容 |
|---|---|
| Thesis anchor | 看多卖铲人（设备 + 关键材料）/ 看空已 price-in 的纯电芯叙事股 |
| 监控目标 | 验证或证伪 K1-K5（车厂 SOP / LFP 降本 / 路线分化 / 半固态安全 / 美国玩家现金跑道） |
| 抓取节奏 | 高频（周）= K2 价格 / K5 美股；中频（月）= K1 IR / K3 招标 / K4 月销；低频（季/年）= 财报 + 招股书 |
| 主要抓取工具 | `gh api` 拉 SEC / 港交所 / 巨潮、`WebFetch` 抓 SMM / 公司 IR、`mineru` 转 PDF、RSS（少量）、手动（招标公告） |
| 警示阈值 | 任一项触发对应 K# 的"翻盘信号"时，写入末尾 timeline 并 ping `prism 推进` 重审 thesis |

---

## K1 ─ 头部车厂全固态 SOP 时间表

> **Killer Question**：任一头部车厂（丰田/日产/本田/宝马）把全固态车规级 SOP 从 2027-2028 推迟到 2030+
> **触发动作**：显著看空全产业链 / 重新校准时间表

### Feed 1.1 ─ 丰田电池战略 PR + 投资者会议

- **源**：丰田 Global Newsroom `https://global.toyota/en/newsroom/corporate/` 过滤 "battery" / "BEV factor"
- **辅源**：丰田 IR Library `https://global.toyota/en/ir/library/`（季度财报 + Integrated Report）
- **频率**：月度（PR）+ 季度（财报当周精读电池章节）
- **抓取方式**：`WebFetch` 拉 newsroom 列表 → 关键词过滤 → 命中再 fetch 全文；财报用 `mineru` 转 PDF
- **预期信号示例**：
  - ✅ 维持判断：「2027 年全固态 SOP, 续航 1000km, 充电 10min」措辞延续
  - 🚨 触发 K1：出现 "phased introduction" / "limited fleet trial" / "post-2028" 等收缩措辞
  - 🚨 触发 K1：电池战略发布会推迟、或电池本部长换人

### Feed 1.2 ─ 三星 SDI IR（005930.KS 子公司口径）

- **源**：Samsung SDI IR `https://www.samsungsdi.com/ir/ir-information/earnings-release.html` + 季度业绩说明会脚本
- **频率**：季度（业绩前 1 周 + 当周）
- **抓取方式**：`WebFetch` 抓季度财报 PDF → `mineru` 转 markdown，重点搜 "ASB" / "all solid state" / "pilot line" / "Suwon"
- **预期信号示例**：
  - ✅ 维持：2027 试产线 ASB sample shipment 进度按节奏
  - 🚨 触发 K1：试产线 ramp-up 推迟 / 客户认证延后 / capex 砍向 LFP

### Feed 1.3 ─ 日产 + 本田 + 宝马 IR

- **源**：
  - 日产 `https://www.nissan-global.com/EN/IR/` ─ Yokohama 试产线 2025 启动 / 2028 SOP
  - 本田 `https://global.honda/en/investors/` ─ Sakura 半固态-全固态过渡口径
  - BMW `https://www.bmwgroup.com/en/investor-relations.html` ─ Neue Klasse 圆柱电池 + Solid Power 联合开发进度
- **频率**：季度
- **抓取方式**：财报当周 `WebFetch` IR 页 + earnings call transcript（订阅 Seeking Alpha 或直接抓公司发布）
- **预期信号示例**：
  - 🚨 触发 K1：任一家把 "by 2028" 改为 "by 2030" 或 "by end of decade"
  - 🚨 触发 K1：BMW 把 Solid Power 列为"评估中"而非"开发合作伙伴"

### Feed 1.4 ─ NEDO / METI 政策动向（日本侧时间表锚）

- **源**：NEDO 新闻 `https://www.nedo.go.jp/english/news_index.html` + METI 蓄电池产业战略发布会
- **频率**：月度扫描
- **抓取方式**：RSS（NEDO 有英文 RSS）+ `WebFetch` 主题过滤 "all-solid-state" / "next-generation battery"
- **预期信号示例**：
  - 🚨 触发 K1：1500 亿日元补贴的里程碑节点（中试线建成日期）官方公告推迟

---

## K2 ─ 液态磷酸铁锂电芯降本曲线

> **Killer Question**：液态 LFP 电芯 2027 Q2 前跌破 0.2 元/Wh
> **触发动作**：看空固态在乘用车场景 / 转向 eVTOL/无人机/高端消费小众场景

### Feed 2.1 ─ SMM 锂电材料 + 电芯周报（主力源）

- **源**：
  - SMM 锂电池价格 `https://newenergy.smm.cn/price/14042-15013`（电芯方形 LFP 280Ah）
  - SMM 碳酸锂电池级 `https://newenergy.smm.cn/price/14042-15010`
  - SMM 镍/钴价 `https://hq.smm.cn/`（三元路线对照）
- **频率**：周（每周一收盘后）
- **抓取方式**：`WebFetch` 抓页面 → 解析当周报价 → 写入本地 CSV trend；如 SMM 改为登录墙，备用源 GGII / 鑫椤资讯
- **预期信号示例**：
  - ✅ 维持：LFP 电芯报价缓慢下行（每季 -5% ~ -8%）
  - 🚨 触发 K2：单季环比 -15% 以上、且碳酸锂同步走低 → 报价穿 0.30 元/Wh 后加速
  - 🚨 触发 K2：报价跌破 0.22 元/Wh（距离 0.20 元/Wh 阈值仅 1 季度差）

### Feed 2.2 ─ GGII（高工锂电）月度数据库

- **源**：GGII `https://www.gg-lb.com/` + 月度数据库订阅（部分付费）
- **频率**：月度
- **抓取方式**：免费版用 `WebFetch` 抓资讯页 + 关键词"出货量""价格"，付费版导出 Excel 后 `mineru` 处理
- **预期信号示例**：
  - 🚨 触发 K2：头部电池厂（CATL/BYD/EVE）单 Wh 制造成本拆解显示已达 0.18-0.20 元区间

### Feed 2.3 ─ CATL / BYD 季报电话会成本口径

- **源**：CATL（300750.SZ）+ BYD（002594.SZ / 1211.HK）季报 + 业绩说明会
- **频率**：季度（业绩当周）
- **抓取方式**：A 股用 `fetch-reports` 从巨潮拉年报/季报 → `mineru` 转 → 全文搜"单瓦时""毛利率""价格联动"；港股 BYD 用 `gh api` 拉港交所披露
- **预期信号示例**：
  - 🚨 触发 K2：CATL 在业绩会明确"LFP 报价已破 0.25 元/Wh"或单 Wh 成本拆解 < 0.20 元
  - 🚨 反向信号（巩固 thesis）：CATL 把 capex 大量切向凝聚态/半固态产线 → 暗示液态降本已触底

---

## K3 ─ 硫化物 vs 氧化物 vs 聚合物 路线分化

> **Killer Question**：任一路线出现决定性技术突破（硫化物干法电极良率 >90% 或氧化物界面阻抗 <50 Ω·cm²）
> **触发动作**：重写终局判断 / 重排产业链受益方

### Feed 3.1 ─ SMM 全固态电解质价格 4 板（路线分化最直接信号）

- **源**：SMM 全固态材料专区
  - LPSC 硫化物电解质 `https://newenergy.smm.cn/price/151036-151039`
  - LATP / LLZO 氧化物电解质 同板
  - 聚合物电解质（PEO 体系）
- **频率**：月度（SMM 这块刚开板，频率会逐步加密）
- **抓取方式**：`WebFetch` 抓 4 板单价 + 评论字段，记录"询单活跃度"标签
- **预期信号示例**：
  - 🚨 触发 K3（硫化物胜出）：LPSC 报价 6 个月内下降 >30% + "成交活跃"标签 → 量产化加速
  - 🚨 触发 K3（氧化物胜出）：LATP/LLZO 报价稳定且月成交量 vs LPSC 拉开 3 倍以上差距
  - 信号信息量：4 板任一板出现"长协订单"披露 = 该路线锁定一家头部车厂

### Feed 3.2 ─ 设备招标公告（卖铲人订单弹性）

- **源**：
  - 先导智能（300450.SZ）公告 `http://www.cninfo.com.cn/new/disclosure/stock?stockCode=300450`
  - 利元亨（688499.SH）公告 同上
  - 海目星（688559.SH）公告 同上
- **频率**：双周扫描（巨潮披露日历）
- **抓取方式**：`fetch-reports` 抓临时公告 → 过滤"中标""框架协议""固态""干法电极""硫化物"
- **预期信号示例**：
  - ✅ 维持卖铲人 thesis：每月 ≥1 单固态相关中标 / 框架
  - 🚨 触发 K3：单笔合同对象指向"硫化物干法电极产线"或"中试 → 量产爬坡"（金额 >5 亿）
  - 🚨 触发反向（卖铲人逻辑弱化）：连续 2 季度无新固态相关订单

### Feed 3.3 ─ 清陶港股招股书 + 卫蓝 IPO 进度

- **源**：
  - 清陶能源港股 IPO 申请文件 `https://www1.hkexnews.hk/`（搜 "Qingtao"）
  - 卫蓝新能源（pre-IPO）从 36 氪 / 投中网公告
- **频率**：季度（IPO 进度）+ 招股书更新即时抓
- **抓取方式**：港交所用 `gh api` 抓披露易；卫蓝用 `WebFetch` 监控 36 氪关键词
- **预期信号示例**：
  - 数据黄金：招股书披露的"客户集中度 / 单 Wh 售价 / 良率 / 产能利用率"——是行业第一手数据
  - 🚨 触发 K3：招股书披露的实际良率显著低于公开宣传（<70%）
  - 🚨 触发 K4 关联：装车数据 / 退货率 / 售后事件披露

### Feed 3.4 ─ 学术 + 专利前哨（路线突破预警）

- **源**：
  - Nature / Science / Joule / Nature Energy 周更（RSS）
  - Google Scholar Alert：keywords "sulfide solid electrolyte dry electrode" / "garnet LLZO interface"
  - CNIPA / USPTO 专利公告：CATL / BYD / 丰田 / 三星 SDI 固态相关申请
- **频率**：周（RSS 自动归档，每周扫一次摘要）
- **抓取方式**：RSS 入 Feedly → 关键词高亮；专利用 patentscope `WebFetch`
- **预期信号示例**：
  - 🚨 触发 K3：顶刊出现"硫化物干法电极良率 >90%"或"界面阻抗 <50 Ω·cm²"工程级文章（不是实验室小样）

---

## K4 ─ 半固态装车命运的时间窗口

> **Killer Question**：半固态电池 2026-2027 装车数据出现重大安全事故
> **触发动作**：重创赛道叙事 / 半固态过渡技术地位崩塌

### Feed 4.1 ─ 装车车型月销量

- **源**：
  - 智己 L6（半固态版）─ 上汽集团（600104.SH）月报 / 智己官方公众号
  - 蔚来 ET7 / ET9（150kWh 半固态包）─ 蔚来 IR `https://ir.nio.com/` 月度交付数据
  - 赛力斯 SF5 / 问界（半固态选装）─ 赛力斯（601127.SH）月报
- **频率**：月度（每月 1-5 日上月数据出炉）
- **抓取方式**：蔚来用 `gh api` 拉 SEC 6-K；上汽/赛力斯用 `fetch-reports` 抓 cninfo 临时公告"产销快报"
- **预期信号示例**：
  - ✅ 维持：半固态版本月销持续 >1000 台
  - 🚨 触发 K4 相关：半固态版本占比连续 3 月下滑（说明用户用脚投票）
  - 🚨 触发 K4：媒体出现召回 / 自燃事件 → 立即查 NHTSA + 国家市场监督管理总局缺陷产品管理中心

### Feed 4.2 ─ 安全事件监控

- **源**：
  - NHTSA Recall `https://www.nhtsa.gov/recalls`
  - 国家市场监督管理总局缺陷产品管理中心 `https://www.dpac.gov.cn/`
  - 微博 / 抖音 / 小红书关键词监控（"自燃" + 车型名）
- **频率**：周
- **抓取方式**：NHTSA / 缺陷中心用 `WebFetch` 按车型搜；社交媒体用人工 + 媒体助理监控
- **预期信号示例**：
  - 🚨 触发 K4：任一半固态装车车型出现热失控事故并被官方立案
  - 🚨 即使非半固态原因，舆论扩散到"固态电池不安全" → 整赛道估值短期重创

### Feed 4.3 ─ 卫蓝 / 赣锋锂电分拆 + 客户告别

- **源**：
  - 卫蓝官网 + 36 氪 / 36 投融资数据库
  - 赣锋锂业（002460.SZ / 1772.HK）年报中赣锋锂电分拆披露
- **频率**：季度
- **抓取方式**：A 股 `fetch-reports` 抓赣锋年报；卫蓝用 `WebFetch` 搜新闻
- **预期信号示例**：
  - ✅ 维持：卫蓝完成 D 轮融资 / 赣锋锂电独立 IPO 推进
  - 🚨 触发 K4 关联：蔚来从卫蓝切换电池供应商 → 半固态产业链定价权丧失

---

## K5 ─ 美国玩家现金跑道 + 里程碑兑现

> **Killer Question**：QS / SLDP / Factorial 任一家在 2027 年前破产或被低价收购
> **触发动作**：验证"美国玩家叙事溢价"假说 / 看空美国概念股

### Feed 5.1 ─ QuantumScape 季报（QS, NYSE）

- **源**：
  - SEC EDGAR `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001811414&type=10-Q`
  - QS IR `https://ir.quantumscape.com/`
- **频率**：季度（10-Q 发布当周）
- **抓取方式**：`fetch-reports` 拉 10-Q → `mineru` 转 → 提取 cash + cash equivalents + quarterly burn rate
- **关键指标跟踪**：
  - Cash + short-term investments 余额
  - 季度 net cash used in operating activities + capex（= 总 burn rate）
  - 隐含跑道月数 = 现金 / 月度 burn
- **预期信号示例**：
  - ✅ 维持：跑道 >18 个月 + PowerCo (大众) 联合开发里程碑按节奏
  - 🚨 触发 K5：跑道 <12 个月且无新增融资 → 进入"等死或贱卖"区间
  - 🚨 触发 K5：PowerCo 公告减少订单 / 解除联合开发 / 转向其他电芯方案

### Feed 5.2 ─ Solid Power 季报（SLDP, NASDAQ）

- **源**：SEC EDGAR + Solid Power IR `https://investors.solidpowerbattery.com/`
- **频率**：季度
- **抓取方式**：同 QS
- **关键指标**：cash 余额 + BMW & Ford 合作公告 + EV cell sample shipment 日程
- **预期信号示例**：
  - 🚨 触发 K5：BMW 公开表态"评估其他固态合作伙伴"
  - 🚨 触发 K5：宣布裁员 >20% / CEO 更换 / 暂停某条产线

### Feed 5.3 ─ Factorial Energy + 其他未上市玩家

- **源**：Factorial（pre-IPO）公司新闻 + Stellantis / 现代 / 戴姆勒公告
- **频率**：季度
- **抓取方式**：`WebFetch` 公司主页 + 关键合作方 IR
- **预期信号示例**：
  - 🚨 触发 K5：Factorial 融资降估值（down round）+ Stellantis 减少订单
  - 🚨 反向：Factorial 完成新一轮高估值融资 → 美国玩家叙事溢价延续

### Feed 5.4 ─ PowerCo / 大众固态电池量产里程碑

- **源**：大众 IR `https://www.volkswagen-group.com/en/investor-relations-15795` + PowerCo 官网
- **频率**：季度
- **抓取方式**：`WebFetch` + 大众年度可持续报告
- **预期信号示例**：
  - 🚨 触发 K5：PowerCo 把 QS 路线从"主力"降为"评估" → QS 估值灾难
  - ✅ 反向：PowerCo Salzgitter / St. Thomas 工厂披露具体投产时间表 → 强化卖铲人逻辑

---

## 信号汇总执行表（Weekly / Monthly Cadence）

| Cadence | Feeds | 预期工作量 |
|---|---|---|
| 每周一 | 2.1 SMM 报价 / 3.1 SMM 电解质 4 板 / 3.4 学术专利 RSS | 30 分钟扫读 + 异常入 timeline |
| 每月 5 日 | 4.1 装车月销 / 4.2 安全事件扫描 | 1 小时 |
| 每月 15 日 | 1.1 丰田 PR / 1.4 NEDO / 3.2 设备招标双周扫 | 1 小时 |
| 季度（财报当周） | 1.2 三星 SDI / 1.3 日产本田宝马 / 2.3 CATL BYD / 5.1 QS / 5.2 SLDP / 5.4 大众 | 4-6 小时（密集 5 个交易日） |
| 季度（IPO 进度） | 3.3 清陶港股 / 4.3 卫蓝 + 赣锋锂电 | 2 小时 |

---

## 与 thesis 的回环约定

每次 feed 抓取出现"🚨 触发"信号时：

1. 在本文件末尾追加一条 timeline 记录
2. 评估对 K1-K5 的支持/否定权重
3. 累计 ≥2 个 K 触发 → 调起 `prism 推进 global-solid-state-battery` 重审 thesis
4. 单一 K 触发"决定性证据"（如 QS 真的破产 / 丰田真的推迟到 2030）→ 立刻调起 thesis v1 修订

---

## 时间线（追加区）

## 2026-05-19 信号源订阅清单建立

**来源**：04-synthesize / 08_living_feed 首版生成
**关键信息**：把 thesis v0 的 K1-K5 映射到 5 大类共 17 个具体 feed item，覆盖：头部车厂 IR / SMM 锂电价格 / 设备招标 / 装车月销 / 美股季报
**对已有判断的影响**：
- 支持了：thesis v0 的 Killer Question 设计可被持续验证（每个 K 都至少有 2 个独立信号源）
- 新增了：SMM 全固态电解质 4 板（K3）和卫蓝 IPO（K4）是当前公开市场最稀缺的高信息密度信号源，需重点关注

**当前判断更新**：维持 thesis v0（看多卖铲人 / 看空 price-in 的电芯叙事股）。后续以本清单为 monitor 阶段的标准抓取流程。

---

## 信息来源

- SEC EDGAR：QuantumScape (CIK 0001811414)、Solid Power 10-Q/10-K 公开披露
- HKEX 披露易：清陶能源港股 IPO 申请文件入口
- 巨潮资讯网：先导智能、利元亨、海目星、上汽集团、赛力斯、CATL、BYD A 股公告
- SMM 上海有色网：锂电材料 / 电芯 / 全固态电解质周月度报价
- GGII 高工锂电：月度数据库（部分付费）
- NEDO / METI：日本政府蓄电池战略与补贴节点
- 各公司 IR 页面：丰田 / 三星 SDI / 日产 / 本田 / 宝马 / 蔚来 / 大众
- NHTSA Recall / 国家市场监督管理总局缺陷产品管理中心：召回与安全事件
- 顶刊与专利 RSS：Nature/Science/Joule + CNIPA/USPTO 关键词追踪
- Thesis v0（claude-opus-4-7，2026-05-19）：K1-K5 Killer Question 设计的 anchor
