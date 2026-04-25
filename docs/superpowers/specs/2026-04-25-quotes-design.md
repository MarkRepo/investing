# 行情数据：EOD 自动拉取 + 行情页 + K 线/分时图

日期：2026-04-25

## 目标

把当前纯手工贴价的 `prices` 机制升级为：

1. **EOD 定时自动拉取** A 股（akshare）+ 美股（yfinance）的完整日 K 行情
2. **字段扩展**：OHLCV + 成交额 + 换手率 + 量比(5日) + PE(多口径) + PB/PS/PEG + 股息率 + 总/流通市值 + 52 周高低
3. **独立行情页** `/prices/<key>`，含价量面板 + ECharts K 线 + ECharts 分时
4. **页面手动刷新**按钮拉实时快照（内存中，不落库）
5. **失败走告警流**，首页卡片 + 页面顶部状态带同时可见

## 不做

- 不做盘中分钟级自动更新（yfinance 会 429；盘中需求靠手动刷新按钮满足）
- 不入库 intraday 分时数据（分时图打开时即时拉，内存用完即丢）
- 不引入前端框架 / 构建链路（ECharts 走 CDN，现有模板为 server-rendered Jinja）
- 不引入 migration 框架 / schema 版本表（`quotes_daily` 是可重生成的外部数据，加字段一次性脚本解决）
- 不保留旧 `prices` 表和手工贴价页（旧表 0 行，无需迁移）
- 不换算币种（市值/股息按股票本币；展示时从 `meta.currency` 带）
- 不在 adapter 里做并发或缓存（顺序拉，纯函数）

## §1 架构总览

```
companies/{key}/meta.md  (ticker + market 源)
                │
                ▼
     ┌─────────────────────┐
     │ adapters/           │
     │   akshare_adapter   │   A 股 / 北交所
     │   yfinance_adapter  │   美股
     └──────────┬──────────┘
                │ Quote dataclass
                ▼
     ┌─────────────────────┐
     │ io/quotes.py        │   upsert / latest / history / freshness / errors
     └──────────┬──────────┘
                ▼
     ┌─────────────────────┐
     │ data/financials.db  │
     │   quotes_daily      │   全字段日 K
     │   quotes_fetch_errors│  采集错误跟踪
     └─────────────────────┘
                │
     ┌──────────┴──────────────────────────┐
     │                                       │
 EOD 脚本 (scripts/fetch_quotes_eod.py)    路由 (app/routes/prices.py)
 cron / launchd 定时                       /prices/<key>, /refresh, /chart
```

## §2 新增 / 删除 / 改动清单

### 新增

- `app/io/adapters/__init__.py` — `get_adapter(market)` 工厂
- `app/io/adapters/base.py` — `Quote` dataclass + `QuoteAdapter` Protocol + `AdapterError`
- `app/io/adapters/akshare_adapter.py`
- `app/io/adapters/yfinance_adapter.py`
- `app/io/quotes.py` — 统一读写层（替代旧 `app/io/prices.py`）
- `scripts/fetch_quotes_eod.py` — EOD 入口脚本
- `scripts/snapshot_fixtures.py` — 一次性脚本，从真实源抓 fixture 供测试用
- `app/templates/prices/index.html` — 行情页主模板
- `app/templates/prices/empty.html` — 无公司占位
- `app/templates/prices/_panel.html` — 最新行情面板（详情页 include）
- `app/templates/prices/_kline.html` — K 线区块
- `app/templates/prices/_intraday.html` — 分时区块
- `app/templates/prices/_status_bar.html` — 顶部数据新鲜度带
- `static/js/prices.js` — 行情页专用 JS（ECharts 初始化 + 周期切换 + 刷新）
- `tests/fixtures/adapters/**` — akshare / yfinance / error_cases fixtures
- `tests/test_adapter_akshare.py` / `test_adapter_yfinance.py`
- `tests/test_quotes_io.py`
- `tests/test_eod_script.py`
- `tests/test_routes_prices.py`
- `tests/test_alert_flow.py`
- `tests/manual/test_live_adapters.py`（`@pytest.mark.live`）

### 删除

- `app/io/prices.py` — 整体删除
- `app/routes/prices.py` 中旧的手工贴价实现（保留文件名，内容重写）
- `app/templates/prices/index.html` 旧的手工贴价表单（文件复用但内容重写）
- `tests/test_prices_triggers_io.py` — 整体删除
- `tests/test_big_movers.py` — 整体删除后重写为新文件 `tests/test_big_movers_quotes.py`

### 改动（机械性 import 替换 + 接口对齐）

| 文件 | 改动 |
|---|---|
| `main.py` | `from app.io import prices as prices_io` → `from app.io import quotes as quotes_io`；`prices_io.big_movers` → `quotes_io.big_movers` |
| `app/routes/triggers.py` | `from app.io import prices as prices_io` → `from app.io import quotes as quotes_io`；`latest_price_for` → `quotes_io.latest_price_for`（保留同名 API） |
| `app/routes/portfolio.py` | 同上，`latest_prices_map` 保留 |
| `app/io/macro_risks.py` | raw SQL `FROM prices` → `FROM quotes_daily`（行 143） |
| `app/io/performance.py` | raw SQL `FROM prices` → `FROM quotes_daily`（行 135, 207） |
| `app/templates/companies/detail.html` | meta 表格下、"年度快照"上方插入 `{% include "prices/_panel.html" %}`；传入 `latest_quote` 变量 |
| `app/templates/companies/list.html` | 操作列最左加 `<a href="/prices/{{ r.key }}" class="btn btn-mini">行情</a>` |
| `app/templates/home.html` | 在 `big_movers` 附近加"行情拉取失败"卡片 |
| `app/routes/companies.py` | list 和 detail 视图注入行情数据 |
| `tests/test_macro_risks.py` | `prices_io.upsert_close` → 直接 INSERT `quotes_daily` 的 helper 或 `quotes_io.upsert` |
| `tests/test_performance_io.py` | 同上 |
| `pytest.ini` | 新增 `markers = live: ...` + `addopts = -m "not live"` |

## §3 Schema

### `quotes_daily`

```sql
CREATE TABLE IF NOT EXISTS quotes_daily (
    ticker             TEXT NOT NULL,
    date               TEXT NOT NULL,              -- ISO yyyy-mm-dd
    market             TEXT NOT NULL,              -- 'SSE' | 'SZSE' | 'BSE' | 'US'
    open               REAL,
    high               REAL,
    low                REAL,
    close              REAL NOT NULL,              -- 唯一必填（下游触发器依赖）
    volume             INTEGER,                    -- 股数
    amount             REAL,                       -- 成交额（本币）
    turnover_rate      REAL,                       -- % = volume / float_shares * 100
    volume_ratio_5d    REAL,                       -- volume / avg(prev 5d volume)
    pe_ttm             REAL,
    pe_static          REAL,                       -- A 股特有，美股 NULL
    pe_forward         REAL,                       -- 美股特有，A 股 NULL
    pb                 REAL,
    ps                 REAL,
    peg                REAL,
    dividend_yield     REAL,                       -- %（3.0 = 3%）
    market_cap         REAL,                       -- 总市值，本币
    float_market_cap   REAL,                       -- 流通市值
    shares_outstanding REAL,
    float_shares       REAL,
    high_52w           REAL,
    low_52w            REAL,
    source             TEXT,                       -- 'akshare' | 'yfinance'
    fetched_at         TEXT,                       -- ISO timestamp
    PRIMARY KEY (ticker, date)
);
```

### `quotes_fetch_errors`

```sql
CREATE TABLE IF NOT EXISTS quotes_fetch_errors (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker       TEXT NOT NULL,
    market       TEXT NOT NULL,
    attempted_at TEXT NOT NULL,                    -- ISO timestamp
    source       TEXT NOT NULL,                    -- 'akshare' | 'yfinance'
    phase        TEXT NOT NULL,                    -- 'eod' | 'snapshot' | 'intraday'
    error        TEXT NOT NULL,
    resolved_at  TEXT                              -- NULL = 未修复
);
CREATE INDEX IF NOT EXISTS idx_fetch_errors_unresolved
    ON quotes_fetch_errors(ticker, resolved_at) WHERE resolved_at IS NULL;
```

### 初始化位置

两张表的 `CREATE TABLE IF NOT EXISTS` 放到 `app/io/financials.py:connect()` 里，和现有的 schema 初始化代码并排。第一次连库自动建表。

### 旧 `prices` 表处理

当前库里 `prices` 表 0 行，无需迁移。代码里 `connect()` 执行 `DROP TABLE IF EXISTS prices;`（可选；即使不删也只是孤儿表不影响新逻辑）。本 spec 选择**保留旧表为空壳**，不 DROP，避免未知依赖。

## §4 Adapter 协议

### `app/io/adapters/base.py`

```python
from dataclasses import dataclass
from datetime import date
from typing import Protocol

class AdapterError(Exception):
    """Adapter 内部异常，包含原异常的 str 信息"""

@dataclass(frozen=True)
class Quote:
    ticker: str
    date: str            # ISO
    market: str
    open: float | None
    high: float | None
    low: float | None
    close: float         # 必填
    volume: int | None
    amount: float | None
    turnover_rate: float | None
    # volume_ratio_5d 不在 adapter 里算；io 层写入前填
    pe_ttm: float | None
    pe_static: float | None
    pe_forward: float | None
    pb: float | None
    ps: float | None
    peg: float | None
    dividend_yield: float | None   # 统一 % 值
    market_cap: float | None
    float_market_cap: float | None
    shares_outstanding: float | None
    float_shares: float | None
    high_52w: float | None
    low_52w: float | None
    source: str
    fetched_at: str

class QuoteAdapter(Protocol):
    def fetch_daily(
        self, ticker: str, market: str, start: date, end: date
    ) -> list[Quote]:
        """闭区间 [start, end] 日 K。停牌/无数据返回 []。失败 raise AdapterError。"""
    
    def fetch_intraday_today(
        self, ticker: str, market: str
    ) -> list[tuple[str, float, int]]:
        """今日分时 [(HHMM, price, volume)]。内存用，不落库。失败 raise AdapterError。"""
    
    def fetch_snapshot(
        self, ticker: str, market: str
    ) -> Quote:
        """此刻实时快照，手动刷新按钮用。不落库。失败 raise AdapterError。"""
```

### `app/io/adapters/__init__.py`

```python
def get_adapter(market: str) -> QuoteAdapter:
    if market == "US":
        return yfinance_adapter
    return akshare_adapter  # SSE / SZSE / BSE
```

### akshare 实现要点

- 日 K：`ak.stock_zh_a_hist(symbol, period="daily", start_date, end_date, adjust="")`（存原始价，复权前端算；单位：成交量"手"→股 × 100）
- spot（当日全字段）：`ak.stock_zh_a_spot_em()`，按 `代码` 过滤
- 历史估值：`ak.stock_a_indicator_lg(symbol)` 给每日 PE_TTM / PB / PS
- 分时：`ak.stock_zh_a_hist_min_em(symbol, period="1", adjust="")`
- BSE（920xxx）走同一 adapter，akshare 自动识别
- 字段映射：`pe_ttm = 市盈率-动态`（TTM 概念对齐），`pe_static = 市盈率`（静态 = LYR）
- `peg`：akshare 无直接接口，留 `None`（yfinance 侧能给）

### yfinance 实现要点

- 日 K：`yf.Ticker(ticker).history(start, end, auto_adjust=False)`（不复权）
- `.info` 只给"当下"值，历史行的 PE/PB/PS/PEG/DY/market_cap/52w 一律 NULL；**仅今日那一行**填充这些字段
- `.info["dividendYield"]` 是小数（0.03）→ 存前 × 100
- `amount` yf 不给：用 `close × volume` 估算，不单独拆字段
- 分时：`yf.Ticker(ticker).history(period="1d", interval="1m")`
- snapshot：用 `fast_info`（比 `.info` 轻），只给价和市值
- 所有异常（含 429）catch 后 raise `AdapterError(f"{type(e).__name__}: {e}")`

### 字段单位速查

| 字段 | 单位 |
|---|---|
| `volume` | 股（A 股底层是"手"需 × 100；美股本身就是股） |
| `amount` | 本币元（A 股元，美股美元） |
| `turnover_rate` | %（0.18 代表 0.18%） |
| `volume_ratio_5d` | 比率（0.95 代表 0.95×） |
| `dividend_yield` | %（3.0 代表 3%） |
| `market_cap` / `float_market_cap` | 本币元 |
| PE / PB / PS / PEG | 倍数 |

## §5 IO 层（`app/io/quotes.py`）

### 公开函数

```python
def upsert(q: Quote, base: Path | None = None) -> None: ...
    # 写入前计算 q.volume_ratio_5d：SELECT avg(volume) 过去 5 条 < q.date 的
    # ON CONFLICT(ticker, date) DO UPDATE（全字段覆盖）

def last_date_for(ticker: str, base=None) -> str | None: ...
def latest_for(ticker: str, base=None) -> Quote | None: ...           # 最新一行
def second_latest_for(ticker: str, base=None) -> Quote | None: ...    # 算涨跌幅
def latest_prices_map(base=None) -> dict[str, tuple[str, float]]: ... # 兼容旧 API
def latest_price_for(ticker: str, base=None) -> tuple[str, float] | None: ...  # 兼容旧 API
def daily_move_pct(ticker: str, base=None) -> tuple[float, str, str] | None: ...  # 兼容旧 API
def big_movers(threshold_pct: float = 15.0, base=None) -> list[dict]: ...       # 兼容旧 API
def history_for(ticker: str, limit: int = 252, base=None) -> list[dict]: ...    # K 线图用

def record_error(ticker, market, phase, error, base=None) -> None: ...
    # source 由 market 推导（'US' → 'yfinance'，其他 → 'akshare'），调用方不传
def mark_errors_resolved(ticker: str, base=None) -> int: ...
def unresolved_fetch_errors(base=None) -> list[dict]: ...  # 按 ticker 聚合最近错误

def freshness(ticker: str, base=None) -> dict: ...
    # {"status": "green"|"yellow"|"red", "last_date": str, "last_error": dict|None}
    # green  : last_date 距今 <= 2 交易日 且无未解决错误
    # yellow : last_date 距今 > 2 交易日 或 有未解决错误但距 last_date <= 1 天
    # red    : 有未解决错误且距 last_date > 1 天
```

### `volume_ratio_5d` 计算

写入一行 `q` 时：

```sql
SELECT AVG(volume) FROM (
    SELECT volume FROM quotes_daily
    WHERE ticker = ? AND date < ? AND volume IS NOT NULL
    ORDER BY date DESC LIMIT 5
)
```

若不足 5 条（backfill 早期几天），返回 NULL。

### 兼容接口语义

`latest_prices_map` / `latest_price_for` / `daily_move_pct` / `big_movers` 保持签名和返回值形态与旧 `io/prices.py` 一致，调用方零业务改动，只改 import 路径。

## §6 EOD 脚本

### `scripts/fetch_quotes_eod.py`

核心是单票函数 `run_for_ticker`，batch 函数 `run_eod` 只是循环调用它。手动刷新路由也复用 `run_for_ticker`。

```python
def run_for_ticker(
    ticker: str, market: str,
    backfill_years: int = 5,
    base: Path | None = None,
) -> dict:
    """
    把一只票的日 K 带到最新状态。智能选择 backfill 或 incremental。
    Returns: {"status": "ok"|"error"|"uptodate", "quotes_added": int, "error": str|None}
    """
    last = quotes_io.last_date_for(ticker, base=base)
    start = (date.fromisoformat(last) + timedelta(days=1)
             if last else date.today() - relativedelta(years=backfill_years))
    end = date.today()
    if start > end:
        return {"status": "uptodate", "quotes_added": 0, "error": None}
    try:
        adapter = get_adapter(market)
        quotes = adapter.fetch_daily(ticker, market, start, end)
        for q in quotes:
            quotes_io.upsert(q, base=base)
        quotes_io.mark_errors_resolved(ticker, base=base)
        return {"status": "ok", "quotes_added": len(quotes), "error": None}
    except AdapterError as e:
        quotes_io.record_error(ticker, market, phase="eod", error=str(e), base=base)
        return {"status": "error", "quotes_added": 0, "error": str(e)}

def run_eod(
    tickers: list[str] | None = None,
    markets: list[str] | None = None,
    backfill_years: int = 5,
    base: Path | None = None,
) -> dict:
    """
    Batch：遍历 companies，对每只调 run_for_ticker。
    Returns: {"ok": int, "errors": int, "skipped": int, "total": int}
    """
    companies = _load_companies_from_meta(base=base)
    if markets:
        companies = [c for c in companies if c.market in markets]
    if tickers:
        companies = [c for c in companies if c.ticker in tickers]
    
    ok, err, skip = 0, 0, 0
    for c in companies:
        r = run_for_ticker(c.ticker, c.market, backfill_years=backfill_years, base=base)
        if   r["status"] == "ok":        ok += 1
        elif r["status"] == "error":     err += 1
        else:                            skip += 1  # uptodate
        time.sleep(0.3 if c.market == "US" else 0.1)
    
    return {"ok": ok, "errors": err, "skipped": skip, "total": len(companies)}

def _load_companies_from_meta(base=None) -> list[Company]:
    """扫 companies/*/meta.md，提取 (key, ticker, market)"""
```

### CLI

```
python -m scripts.fetch_quotes_eod                       # 所有公司，5 年回补
python -m scripts.fetch_quotes_eod --markets SSE,SZSE,BSE
python -m scripts.fetch_quotes_eod --markets US
python -m scripts.fetch_quotes_eod --tickers 600519,HIMS
python -m scripts.fetch_quotes_eod --backfill-years 10
```

### 调度（推荐 cron）

```cron
# A 股 / 北交所：北京时间 16:30（收盘后 90 分钟）
30 16 * * 1-5  cd /Users/yangqi/investing && .venv/bin/python -m scripts.fetch_quotes_eod --markets SSE,SZSE,BSE >> data/eod.log 2>&1

# 美股：北京时间次日 05:30（美东 16:30 收盘后 1 小时）
30 5  * * 2-6  cd /Users/yangqi/investing && .venv/bin/python -m scripts.fetch_quotes_eod --markets US >> data/eod.log 2>&1
```

可选：同时提供 `~/Library/LaunchAgents/com.investing.quotes-eod.plist`，内容作为 CLI 文档（DEVELOPER-GUIDE.md 里附一份）。**不做自动安装**。

## §7 路由 & 模板

### 路由清单（`app/routes/prices.py` 完全重写）

| 路径 | 方法 | 返回 | 作用 |
|---|---|---|---|
| `/prices` | GET | 302 | 跳 `/prices/<第一家公司 key>`；无公司时渲 `empty.html` |
| `/prices/{key}` | GET | HTML | 行情页 |
| `/prices/{key}/refresh` | POST | JSON | 手动刷新快照 |
| `/prices/{key}/chart` | GET | JSON | K 线周期聚合数据 |

### `GET /prices/{key}` 视图逻辑

```python
@router.get("/{key}")
def detail(request: Request, key: str):
    meta = company_io.load_meta(key)
    latest = quotes_io.latest_for(meta.ticker)
    prev   = quotes_io.second_latest_for(meta.ticker)
    kline  = quotes_io.history_for(meta.ticker, limit=252)        # 默认 1 年日 K
    try:
        intraday = get_adapter(meta.market).fetch_intraday_today(meta.ticker, meta.market)
        intraday_err = None
    except AdapterError as e:
        intraday, intraday_err = [], str(e)
        quotes_io.record_error(meta.ticker, meta.market, phase="intraday", error=str(e))
    return templates.TemplateResponse(request, "prices/index.html", {
        "meta": meta, "latest": latest, "prev": prev,
        "kline": kline, "intraday": intraday, "intraday_err": intraday_err,
        "freshness": quotes_io.freshness(meta.ticker),
        "all_companies": company_io.list_all(),  # dropdown
    })
```

### `POST /prices/{key}/refresh` 语义：**把这只票带到最新**

按库里当前状态自适应：

| 库里状态 | 行为 | 预计耗时 |
|---|---|---|
| 空（新票从未 EOD） | 5 年 backfill → 入库 → snapshot | 5-15 秒 |
| 有数据但 `last_date < today` | 增量 `last_date+1 → today` → 入库 → snapshot | 1-3 秒 |
| 有数据且 `last_date == today` | 仅 snapshot | <1 秒 |

实现（复用 EOD 的 `run_for_ticker`）：

```python
@router.post("/{key}/refresh")
def refresh(key: str):
    meta = company_io.load_meta(key)
    # 1) 带到最新（backfill / incremental / noop）
    r = eod_script.run_for_ticker(meta.ticker, meta.market)
    # 2) 即便 1 失败也尝试 snapshot（snapshot 常常独立可用，如 fast_info 路径）
    try:
        snap = get_adapter(meta.market).fetch_snapshot(meta.ticker, meta.market)
        snap_err = None
    except AdapterError as e:
        quotes_io.record_error(meta.ticker, meta.market, phase="snapshot", error=str(e))
        snap, snap_err = None, str(e)
    # 3) 返回完整的新状态（前端整页重渲染用）
    return {
        "ok": r["status"] != "error" or snap is not None,
        "quotes_added": r["quotes_added"],
        "daily_error": r["error"],
        "snapshot_error": snap_err,
        "latest": quotes_io.latest_for(meta.ticker).to_dict() if ... else None,
        "prev":   quotes_io.second_latest_for(meta.ticker).to_dict() if ... else None,
        "kline":  quotes_io.history_for(meta.ticker, limit=252),
        "snapshot": snap.to_dict() if snap else None,
        "freshness": quotes_io.freshness(meta.ticker),
    }
```

前端行为：
- 按钮 `aria-busy` + disabled，显示 spinner；长时（> 2s）时展示 "正在回补历史..." 提示
- 成功响应：**整页重渲染**——面板数字 / K 线 ECharts `setOption` / 状态带颜色 / 小标签 `刷新于 15:32:18（新增 N 条）`
- 部分失败（例：backfill 失败但 snapshot 成功）：面板更新 + 黄色 flash `刷新部分成功：<daily_error>`
- 完全失败：红色 flash + 按钮恢复可点
- **10 秒节流**：按钮按下后 10 秒内禁用（防误触连点）

### `GET /prices/{key}/chart?period=1d|1w|1M`

返回：

```json
{
  "period": "1w",
  "ohlcv": [
    {"date": "2026-04-20", "open": 1680, "high": 1720, "low": 1670, "close": 1698, "volume": 12500000},
    ...
  ]
}
```

后端按周/月 groupby 聚合 `quotes_daily`。默认 `period=1d` 时不聚合直接返回。

### 模板布局（`prices/index.html`）

按第 5 块草图：顶部状态带 + 左侧价量/估值/规模面板 + 右侧 K 线（上）+ 分时（下）。切换公司 dropdown 直接 `location.href = /prices/<key>`。

### 详情页面板（`prices/_panel.html`，在 `companies/detail.html` include）

精简 6 行，展示主要字段 + "→ 打开行情页"链接。

### 列表页"行情"按钮（`companies/list.html`）

操作列最左加：
```html
<a class="btn btn-mini" href="/prices/{{ r.key }}">行情</a>
```

### 首页告警卡片（`home.html`）

视图注入：
```python
quote_fetch_errors = quotes_io.unresolved_fetch_errors()
```
模板按 `fired_triggers` 同款式渲染。

### ECharts 引入

仅 `prices/index.html` 的 `{% block extra_head %}`：
```html
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
```

### 前端 JS（`static/js/prices.js`）

- K 线 ECharts 初始化（candlestick + volume 副图 + dataZoom）
- 分时 ECharts 初始化（line + 昨收参考线）
- 周期切换：`fetch('/prices/<key>/chart?period=...').then(...)` 重设 option
- 手动刷新：POST `/refresh`，成功更新面板数字 + "刷新于" 标签；按钮 10 秒节流
- 服务端把 kline/intraday 数据 inline 到 `<script id="quotes-data" type="application/json">` 供 JS 读取

## §8 错误告警链路

### 数据流

```
adapter raise AdapterError
   ↓
调用者 catch (io.quotes / EOD 脚本 / route)
   ↓
quotes_io.record_error(ticker, market, source, phase, error)
   ↓
quotes_fetch_errors 表
   ↓
首页 `unresolved_fetch_errors()` → 告警卡片
/prices/<key> `freshness()` → 顶部状态带 + 分时区占位
```

### 成功自动解除

`quotes_io.upsert` 成功后调用 `mark_errors_resolved(ticker)`，把该 ticker 所有 `resolved_at IS NULL` 的记录填上 now。

### `freshness` 分级

算法（按**日历日**阈值，不维护交易日历；阈值宽松以覆盖周末）：

```python
d = (today - last_date).days if last_date else 9999
has_err = len(unresolved_errors) > 0
e = min(err.attempted_at 距今天数 for err in unresolved_errors) if has_err else None

if not has_err and d <= 3:          return "green"
if has_err and e >= 3:              return "red"
if d >= 7:                          return "red"
return "yellow"                     # 其余情况
```

| 状态 | 含义 | UI |
|---|---|---|
| green | 数据 ≤ 3 天内 且无未解决错误 | ✅ 绿色带 |
| yellow | 数据 4-6 天陈旧，或近 2 天刚出错 | ⚠️ 黄色带 |
| red | 数据 ≥ 7 天陈旧，或错误持续 ≥ 3 天未恢复 | 🔴 红色带 |

阈值可在实现时调，本 spec 定义是初始默认值。

### 重试

行情页状态带带 `[重试]` 按钮 → POST `/prices/{key}/refresh`，成功后自动解除所有 unresolved 错误。

## §9 测试策略

### 分层

1. **Adapter 单元** — `monkeypatch` `akshare`/`yfinance` 模块，走 fixture CSV/JSON
2. **IO 单元** — `tmp_path` 做 base，真 SQLite
3. **路由** — FastAPI `TestClient` + mocked adapter
4. **EOD 脚本** — `run_eod(base=tmp_path, tickers=[...])` + mocked adapter
5. **告警端到端** — 触发失败 → 断言首页/行情页 UI → 恢复 → 告警消失
6. **手动契约**（`@pytest.mark.live`，默认 skip） — 真调 akshare/yfinance 检查接口形状

### Fixture

`tests/fixtures/adapters/{akshare,yfinance}/*.{csv,json}` 由 `scripts/snapshot_fixtures.py` 一次性生成；上游接口变形后重跑。

### `pytest.ini`

```ini
[pytest]
markers =
    live: hits real external APIs; skipped by default
addopts = -m "not live"
```

### 必测用例（节选）

- Adapter 字段映射：每个 `Quote` 字段从 fixture 源字段到期望值
- Adapter 单位换算：成交量手→股、股息率小数→%
- 停牌：源空 → `fetch_daily` 返回 `[]`
- Adapter 异常：上游异常 → `AdapterError` 带原异常信息
- `upsert` 幂等（同 key 覆盖）
- `volume_ratio_5d`：<5 天历史返回 NULL；≥5 天按公式算
- `freshness` 三档边界
- `record_error` + `mark_errors_resolved` 配对
- `run_for_ticker` 空库 → 5 年 backfill（断言调 `fetch_daily` 的 start 约等于 today - 5y）
- `run_for_ticker` 有数据 → 增量拉 `last_date+1 → today`
- `run_for_ticker` up-to-date → 返回 `{"status": "uptodate"}` 不调 adapter
- `run_for_ticker` 上游失败 → 返回 `{"status": "error"}` + errors 表写入
- `run_eod` 一只失败其他继续；结果字段正确统计 ok/errors/skipped
- 失败恢复：第一次失败 → 第二次成功 → `resolved_at` 填入 + errors 不再 unresolved
- 路由 `/refresh` 空库场景：触发 backfill，响应 `quotes_added > 0` + `kline` 非空
- 路由 `/refresh` 已最新场景：不动库，仅返回 snapshot
- 路由 `/refresh` backfill 失败但 snapshot 成功：`{"ok": true, "daily_error": "...", "snapshot": {...}}`
- 路由 `/prices` 跳转、`/prices/<key>` 渲染、`/chart` 周期聚合
- 列表页含"行情"按钮；详情页含面板；首页有告警时显示卡片无告警时不显示
- 告警端到端：错误 → UI → 恢复 → UI

### 覆盖率目标（软）

- `app/io/quotes.py` ≥ 85%
- `app/io/adapters/*` ≥ 80%
- `app/routes/prices.py` ≥ 75%
- `scripts/fetch_quotes_eod.py` ≥ 70%

## §10 依赖

`requirements.txt` 新增：

```
akshare>=1.12
yfinance>=0.2.40
pandas>=2.1
python-dateutil>=2.8
```

（`pandas` 实际上 akshare 强制带上；`python-dateutil` 给 `relativedelta`）

ECharts 走 CDN，无 Python 端依赖。

## §11 文件路径变更汇总

| 旧 | 新 |
|---|---|
| `app/io/prices.py` | `app/io/quotes.py` |
| 旧 `app/routes/prices.py`（手工贴价） | 新 `app/routes/prices.py`（行情页） |
| 旧 `app/templates/prices/index.html`（贴价表单） | 新 `app/templates/prices/index.html`（行情页） |
| — | `app/io/adapters/__init__.py` |
| — | `app/io/adapters/base.py` |
| — | `app/io/adapters/akshare_adapter.py` |
| — | `app/io/adapters/yfinance_adapter.py` |
| — | `scripts/fetch_quotes_eod.py` |
| — | `scripts/snapshot_fixtures.py` |
| — | `app/templates/prices/{empty,_panel,_kline,_intraday,_status_bar}.html` |
| — | `static/js/prices.js` |

## §12 本 spec 外（后续版本候选）

- 盘中分钟级自动更新（需要解决 yfinance 限流 + 常驻调度）
- K 线前复权 / 后复权切换
- 自选股分组（在 `/prices` 页 dropdown 里分组：持仓 / 观察池 / 已研究）
- 多股对比（同图叠加多条 K 线，归一化涨跌）
- 技术指标叠加（MA / MACD / RSI）
- 北向资金流向（akshare 有接口，入 extra 字段或独立表）
