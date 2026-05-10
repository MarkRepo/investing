# 组合管理与决策纪律

系统提供完整的投资组合管理工具链：持仓 → 规则 → 触发器 → 催化 → 纪律 → 审查 → 归因。

## 持仓管理

### `app/io/portfolio.py`

操作 `portfolio/positions.md`，一个 Markdown 表格。

核心功能：
- 读取当前持仓列表
- 计算单票仓位占比
- 与 rules.md 中的限制对比

### `app/io/rules.py`

操作 `portfolio/rules.md`，包含 frontmatter 限制 + body 正文：

```python
def read() -> tuple[dict, str]    # 返回 (limits_dict, body_markdown)
def write(limits: dict, body: str) -> None
def evaluate(positions) -> list    # 检查仓位是否超限
```

限制类型：
- `max_single_pct`：单票最大占比（如 0.15 = 15%）
- `max_sector_pct`：单行业最大占比
- `min_cash_pct`：最小现金占比
- `max_theme_pct`：单主题最大占比

### `app/io/triggers.py`

操作 `portfolio/triggers.md`，Markdown 表格：

```python
def list_all() -> list             # 所有触发器
def update() -> None               # 检查最新行情，更新 triggered_at
def delete(trigger_id) -> None     # 删除或重置触发器
```

触发器类型：
- `stop_loss`：止损 → action = "sell" / "stop_loss_exit"
- `take_profit`：止盈 → action = "sell" / "scale_out"
- `buy_trigger`：买入信号 → action = "buy" / "scale_in"

## 催化事件

### `app/io/catalysts.py`

操作公司/行业目录下的 `catalysts.yaml` 或嵌入在 meta 中的催化信息。

```python
def upcoming(within_days: int = 7) -> list  # 未来 N 天内的催化事件
```

## 决策日志

### `app/io/journal.py`

操作 `journal/decisions/{YYYY}-Q{n}/` 目录下的决策文件。

每条决策记录包含：
- Frontmatter：日期、ticker、action、price、仓位变动、V0 快照路径和 hash
- 过程评分：process_quality, process_rigor, process_rule_adherence, process_emotional_control
- 结果评分（事后填写）：pnl_3m, pnl_6m, pnl_12m, result_quality, result_luck_factor
- 偏见自查：bias_conviction, bias_reason_conviction, bias_confirmation, bias_reason_confirmation

### `app/io/discipline.py`

```python
def review_gaps() -> list              # 查找未评审的决策
def unreviewed_decisions() -> list     # 返回 pending 状态的决策
```

## 季度审查

### `app/io/review.py`

```python
def quarter_summary() -> dict          # 汇总当季审查指标
def list_quarters() -> list            # 列出所有已有审查季度
```

## 财报审查

### `app/io/earnings_review.py`

```python
def pending_reviews() -> list          # 待处理的财报审查
```

## 宏观环境

### `app/io/regime.py`

操作 `macro/regime.md`，判定当前宏观环境状态：

```python
def read() -> dict                     # 解析 regime 文件
def write(verdict: str, ...) -> None   # 写入新判定
def current_quarter() -> str           # 计算当前季度（如 "2026-Q2"）
def latest() -> dict                   # 最新 regime 条目
def list_quarters() -> list            # 所有已有季度
```

判定字段：
- `valuation_percentile`：估值分位
- `credit_spread_bps`：信用利差（bps）
- `vix_level`：VIX 水平
- `ust_10y_yield`：10 年期美债收益率
- `retail_sentiment`：散户情绪（bullish / neutral / bearish）
- `macro_reaction`：宏观反应（risk_on / risk_off）
- `verdict`：最终判定（hot / neutral / cold / panic）

## 收益归因

### `app/io/performance.py`

```python
def summarize_returns() -> dict        # 按头寸/周期归因收益
```

加载 positions + quotes history 计算 PnL。

## 质量缺口

### `app/io/qa.py`

```python
def read_warnings() -> list            # 读取 scope 级别的警告
def update_status(warning_id, status) -> None  # 标记 resolved/dismissed/open
def read_gap_markdown() -> str         # 生成缺口报告
def summarize_by_scope() -> list       # 按 scope 分组的 open warnings 计数
```

规则类型：
- `fidelity`：保真度问题
- `empty_evidence`：证据为空
- `self_contradict_specific`：自相矛盾
- `polarity_mismatch`：极性不一致
- `proposed_dup`：候选重复
- `checklist_company_contamination`：checklist 公司污染

## 能力圈

### `app/io/competence_map.py`

管理投资者的能力圈映射，记录对哪些公司/行业有深度理解。

## 行情数据

### `app/io/quotes.py`

```python
def big_movers(threshold_pct: float = 15.0) -> list   # 大幅波动（±15%）
def unresolved_fetch_errors() -> list                  # 未解决的抓取错误
```

### 行情适配器

`app/io/adapters/`：

| 适配器 | 市场 | 底层库 |
|---|---|---|
| `akshare_adapter.py` | A 股 / 港股 | AkShare（新浪财经接口） |
| `yfinance_adapter.py` | 美股 | yfinance |

统一 `QuoteAdapter` 协议：

```python
class QuoteAdapter(Protocol):
    def fetch_daily(self, ticker: str, market: str, start: str, end: str) -> list[Quote]: ...
    def fetch_intraday_today(self, ticker: str, market: str) -> list[Quote]: ...
    def fetch_snapshot(self, ticker: str, market: str) -> Quote: ...
```

`Quote` 数据类包含：ticker, date, market, OHLCV, PE/PB/PS/PEG, dividend_yield, market_cap 等字段。

### EOD 行情回填

```bash
python -m scripts.fetch_quotes_eod \
  --markets SSE,SZSE,US \
  --backfill-years 3
```

## 财务报表

### `app/io/financials.py`

从 `data/financials.db` 读取：

```python
def get_financials(ticker: str, market: str) -> list   # 获取公司多期财报
```

### 财务数据抓取

```bash
# A 股
python -m scripts.fetch_financials_cn --ticker 603011 --market SSE

# 美股
python -m scripts.fetch_financials_us --ticker AAPL --market US
```

列映射通过 `config.py` 的 `CN_COL_MAP`（中文列 → snake_case）和 `US_COL_MAP`（yfinance Title Case → snake_case）处理。

## 全文搜索

### `app/io/search.py`

跨公司、观察池、日志、组合的全文搜索。
