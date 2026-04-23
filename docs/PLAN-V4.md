# V4 缺口补齐计划

> **依据**：对比 `DESIGN.md` 与工程实现的缺口盘点（2026-04-23）。
> **定位**：补 V1/V2/V3 都没覆盖到的 DESIGN 要求项，分两类：
> - **"PLAN 从未计划"** ：DESIGN 里写了但 PLAN.md 甚至都没放进 parking lot 的事实层工具、观察池纪律 gate、自律仪表盘
> - **"计划了没做"** ：PLAN §8 parking lot 写了 V3，但 V3 实施时漏做（主题敞口、极端风险自动触发、折现率建议值、复盘节奏提醒）
> **版本**：2026-04-23 · v4.0

---

## 范围

五个 Phase，按优先级（高→低）：

### Phase 1 · 事实层（§2.4 / §3.1 / §8 坑 9）
- **1.1** `industries/{sector}/` IO + 路由：`landscape.md` / `players.md` / `competence-map.md`
- **1.2** `meta.md` 编辑页（扩展 `app/io/company.py`）
- **1.3** `profile-YYYY.md` 编辑页 + **年报来源校验**（写入时要求 `source_file` 指向 `sources/` 下的年报，否则警告"不从新闻抽"）

### Phase 2 · 观察池纪律（§3.9 / §8 坑 1）
- **2.1** prefilter 列扩展：加 `source_type` (枚举: `quant_screen` / `qual_radar` / `product_experience`)；入 researching 前校验 `date_added + 7 天 ≤ today`
- **2.2** 预筛三问 gate：prefilter → researching 必须通过 3 个 yes + 理由 ≥30 字
- **2.3** researching 超期标红：`target_finish < today - 7d` 时 UI 红标

### Phase 3 · 组合规则补齐（§3.8）
- **3.1** 主题敞口：`meta.md` 加 `themes: []` 字段；`rules.md` 加 `max_theme_pct` limit；`evaluate()` 新增 `theme_exposure` 违规
- **3.2** 极端风险自动触发：
  - VIX 持续 7 天 > 40 → 违规 `vix_sustained_spike`
  - 信用利差单月扩大 > 100bp → 违规 `credit_widening`（从 regime 历史比较）
  - 单一行业头部公司一周内同步 -20% → 违规 `sector_crash`（从 prices + meta sector）

### Phase 4 · 自律仪表盘（§8 坑 3 / §9）
- **4.1** 无 V0 快照买入：扫 journal 里 action ∈ {buy, add}、v0_snapshot_path 为空 的条目
- **4.2** 情绪卖出：journal 里 action ∈ {sell, trim}、body 含 V0 "什么不算推翻"关键词（利率/地缘/央行/VIX 等）
- **4.3** 复盘节奏：`journal/quarterly-reviews/` 里连续 2 个季度缺失 → 首页红卡（"要不要买指数基金"）
- **4.4** 聚合路由 `/discipline`

### Phase 5 · 小项
- **5.1** claim 月度抽检：`/research/audit?month=YYYY-MM` 随机抽 10%
- **5.2** 估值折现率随钟摆建议值：valuation 编辑页按 regime.verdict + `ust_10y_yield` 给出建议
- **5.3** DESIGN 加 v1.3 补丁：对话驱动路径反转说明

---

## 非目标

- **不重构已实现的模块**（performance / review / catalysts / regime / competence_map / rules 全部保留）
- **不接外部 API**（VIX / OAS 等数据仍手工录入 regime.md；系统只做比对）
- **不做实时监控**（极端风险规则由用户打开 `/portfolio` 时计算，不跑后台任务）
- **不建议值自动写入**（折现率建议只显示，不修改 valuation.md）

---

## 测试策略

- 每个 Phase 新建模块跟现有风格一致：
  - `app/io/*.py` → `tests/test_*_io.py`
  - 路由 → `tests/test_routes_smoke.py` 增量
- 现有 187 测试必须全绿
- V4 结束目标：240+ 测试、零回归

---

## 执行顺序

Phase 1 → 2 → 3 → 4 → 5，每 Phase 收工时跑全量 pytest。
