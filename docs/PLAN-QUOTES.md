# 行情数据系统实施计划

**Spec**: `docs/superpowers/specs/2026-04-25-quotes-design.md`
**目标**: EOD 自动拉取行情 + 独立行情页 + K 线/分时图 + 失败告警链路
**完成标志**: `pytest -m "not live"` 全绿 + 能用 `/prices/<key>` 看到面板+图 + 首页错误告警生效

---

## 任务依赖顺序

```
T1 Schema  ──┐
             ├─→ T3 io/quotes 基础  ──┐
T2 Adapter   │                          ├─→ T7 EOD 脚本 ──┐
   base ─────┤                          │                  │
             │  T4 io/quotes 错误追踪 ──┤                  │
             │                          │                  │
             ├─→ T5 akshare adapter  ──┤                  │
             └─→ T6 yfinance adapter ──┘                  │
                                                           │
                    T8 清理 io/prices 迁移  ←──────────────┘
                    （其他代码 import 改造）
                                        │
                                        ▼
                    T9 详情页面板 + 列表页按钮 + 首页告警
                                        │
                                        ▼
                    T10 行情页路由 + 模板（ECharts）
                                        │
                                        ▼
                    T11 前端 JS 交互（刷新 / 周期切换）
                                        │
                                        ▼
                    T12 pytest/requirements 收尾
                                        │
                                        ▼
                    T13 手动契约测试 + fixtures 脚本
```

---

## T1. Schema 初始化

**Files**
- Modify: `app/io/financials.py` — `connect()` 里加两张表的 CREATE
- Create: `tests/test_quotes_schema.py`

**新 schema**

在 `connect()` 现有 CREATE TABLE 后追加：

```python
conn.executescript("""
    CREATE TABLE IF NOT EXISTS quotes_daily (
        ticker TEXT NOT NULL, date TEXT NOT NULL, market TEXT NOT NULL,
        open REAL, high REAL, low REAL, close REAL NOT NULL,
        volume INTEGER, amount REAL,
        turnover_rate REAL, volume_ratio_5d REAL,
        pe_ttm REAL, pe_static REAL, pe_forward REAL,
        pb REAL, ps REAL, peg REAL,
        dividend_yield REAL,
        market_cap REAL, float_market_cap REAL,
        shares_outstanding REAL, float_shares REAL,
        high_52w REAL, low_52w REAL,
        source TEXT, fetched_at TEXT,
        PRIMARY KEY (ticker, date)
    );
    CREATE TABLE IF NOT EXISTS quotes_fetch_errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL, market TEXT NOT NULL,
        attempted_at TEXT NOT NULL,
        source TEXT NOT NULL, phase TEXT NOT NULL,
        error TEXT NOT NULL, resolved_at TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_fetch_errors_unresolved
        ON quotes_fetch_errors(ticker, resolved_at) WHERE resolved_at IS NULL;
""")
```

**Tests**
- `test_connect_creates_quotes_daily` — 断言 `PRAGMA table_info(quotes_daily)` 含所有 26 列 + PK(ticker,date)
- `test_connect_creates_quotes_fetch_errors` — 断言表存在 + unresolved 索引存在
- `test_connect_is_idempotent` — 连续调两次 `connect()` 不报错
- 不动现有表；断言 `financials` / `ratios` / `companies` / `price_triggers` / `benchmark` 仍存在

**Done when**: 新建空库启动 app，上述两张表自动出现；老的 7 行 financials / 7 行 ratios 数据不变。

---

## T2. Adapter 基础协议

**Files**
- Create: `app/io/adapters/__init__.py`
- Create: `app/io/adapters/base.py`
- Create: `tests/test_adapter_base.py`

**`base.py` 内容**

```python
from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable


class AdapterError(Exception):
    """Adapter 内部异常，统一包装上游错误"""


@dataclass(frozen=True)
class Quote:
    ticker: str
    date: str          # ISO yyyy-mm-dd
    market: str
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None
    amount: float | None
    turnover_rate: float | None
    # volume_ratio_5d 不在 adapter 填；io 层写入前补
    pe_ttm: float | None
    pe_static: float | None
    pe_forward: float | None
    pb: float | None
    ps: float | None
    peg: float | None
    dividend_yield: float | None    # %（3.0 = 3%）
    market_cap: float | None
    float_market_cap: float | None
    shares_outstanding: float | None
    float_shares: float | None
    high_52w: float | None
    low_52w: float | None
    source: str
    fetched_at: str


@runtime_checkable
class QuoteAdapter(Protocol):
    source: str

    def fetch_daily(self, ticker: str, market: str, start: date, end: date) -> list[Quote]: ...
    def fetch_intraday_today(self, ticker: str, market: str) -> list[tuple[str, float, int]]: ...
    def fetch_snapshot(self, ticker: str, market: str) -> Quote: ...
```

**`__init__.py` 内容**

```python
from app.io.adapters import akshare_adapter, yfinance_adapter
from app.io.adapters.base import Quote, QuoteAdapter, AdapterError

def get_adapter(market: str) -> QuoteAdapter:
    if market == "US":
        return yfinance_adapter
    return akshare_adapter  # SSE / SZSE / BSE
```

**Tests**
- `test_quote_is_frozen` — 赋值 raise
- `test_get_adapter_us_returns_yfinance` — import 比较
- `test_get_adapter_a_returns_akshare` — SSE/SZSE/BSE 三个都返回 akshare
- `test_adapter_error_is_exception` — 可 raise/catch

**Done when**: `from app.io.adapters import Quote, get_adapter, AdapterError` 能正常导入；3 个测试绿。（adapter 模块文件暂时占位空文件有 `source = "xxx"`，T5/T6 填实现）

---

## T3. io/quotes 基础（读写 + 兼容旧 API）

**Files**
- Create: `app/io/quotes.py`
- Create: `tests/test_quotes_io.py`

**`app/io/quotes.py` 主要函数**

```python
from __future__ import annotations
import sqlite3
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from app.io import financials as fin_io
from app.io.adapters.base import Quote


# ---- 写入 ----

def upsert(q: Quote, base: Path | None = None, conn: sqlite3.Connection | None = None) -> None:
    owns = conn is None
    conn = conn or fin_io.connect(base=base)
    try:
        vr5 = _compute_volume_ratio_5d(conn, q.ticker, q.date, q.volume)
        conn.execute("""
            INSERT INTO quotes_daily (ticker, date, market, open, high, low, close,
                volume, amount, turnover_rate, volume_ratio_5d,
                pe_ttm, pe_static, pe_forward, pb, ps, peg, dividend_yield,
                market_cap, float_market_cap, shares_outstanding, float_shares,
                high_52w, low_52w, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                market=excluded.market, open=excluded.open, high=excluded.high,
                low=excluded.low, close=excluded.close,
                volume=excluded.volume, amount=excluded.amount,
                turnover_rate=excluded.turnover_rate, volume_ratio_5d=excluded.volume_ratio_5d,
                pe_ttm=excluded.pe_ttm, pe_static=excluded.pe_static, pe_forward=excluded.pe_forward,
                pb=excluded.pb, ps=excluded.ps, peg=excluded.peg,
                dividend_yield=excluded.dividend_yield,
                market_cap=excluded.market_cap, float_market_cap=excluded.float_market_cap,
                shares_outstanding=excluded.shares_outstanding, float_shares=excluded.float_shares,
                high_52w=excluded.high_52w, low_52w=excluded.low_52w,
                source=excluded.source, fetched_at=excluded.fetched_at
        """, (q.ticker, q.date, q.market, q.open, q.high, q.low, q.close,
              q.volume, q.amount, q.turnover_rate, vr5,
              q.pe_ttm, q.pe_static, q.pe_forward, q.pb, q.ps, q.peg, q.dividend_yield,
              q.market_cap, q.float_market_cap, q.shares_outstanding, q.float_shares,
              q.high_52w, q.low_52w, q.source, q.fetched_at))
        conn.commit()
    finally:
        if owns: conn.close()


def _compute_volume_ratio_5d(conn, ticker, date_iso, volume):
    """过去 5 个有 volume 的交易日的平均。不足 5 条返回 None。"""
    if volume is None:
        return None
    rows = conn.execute("""
        SELECT volume FROM quotes_daily
        WHERE ticker=? AND date<? AND volume IS NOT NULL
        ORDER BY date DESC LIMIT 5
    """, (ticker, date_iso)).fetchall()
    if len(rows) < 5:
        return None
    avg = sum(r["volume"] for r in rows) / 5
    if avg <= 0:
        return None
    return volume / avg


# ---- 读取 ----

def last_date_for(ticker: str, base=None) -> str | None:
    conn = fin_io.connect(base=base)
    try:
        r = conn.execute(
            "SELECT MAX(date) AS d FROM quotes_daily WHERE ticker=?",
            (ticker,)
        ).fetchone()
        return r["d"]
    finally:
        conn.close()


def latest_for(ticker: str, base=None) -> dict | None:
    conn = fin_io.connect(base=base)
    try:
        r = conn.execute(
            "SELECT * FROM quotes_daily WHERE ticker=? ORDER BY date DESC LIMIT 1",
            (ticker,)
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def second_latest_for(ticker: str, base=None) -> dict | None:
    conn = fin_io.connect(base=base)
    try:
        r = conn.execute(
            "SELECT * FROM quotes_daily WHERE ticker=? ORDER BY date DESC LIMIT 1 OFFSET 1",
            (ticker,)
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def history_for(ticker: str, limit: int = 252, base=None) -> list[dict]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            "SELECT date, open, high, low, close, volume FROM quotes_daily "
            "WHERE ticker=? ORDER BY date DESC LIMIT ?",
            (ticker, limit)
        ).fetchall()
        return [dict(r) for r in reversed(rows)]  # 返回升序便于前端画图
    finally:
        conn.close()


# ---- 兼容旧 io/prices.py API ----

def latest_price_for(ticker: str, base=None) -> tuple[str, float] | None:
    r = latest_for(ticker, base=base)
    return (r["date"], r["close"]) if r else None


def latest_prices_map(base=None) -> dict[str, tuple[str, float]]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute("""
            SELECT q.ticker, q.date, q.close
            FROM quotes_daily q
            JOIN (SELECT ticker, MAX(date) AS md FROM quotes_daily GROUP BY ticker) m
            ON q.ticker=m.ticker AND q.date=m.md
        """).fetchall()
        return {r["ticker"]: (r["date"], r["close"]) for r in rows}
    finally:
        conn.close()


def daily_move_pct(ticker: str, base=None) -> tuple[float, str, str] | None:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            "SELECT date, close FROM quotes_daily WHERE ticker=? ORDER BY date DESC LIMIT 2",
            (ticker,)
        ).fetchall()
    finally:
        conn.close()
    if len(rows) < 2:
        return None
    latest_d, latest_c = rows[0]["date"], float(rows[0]["close"])
    prev_d,   prev_c   = rows[1]["date"], float(rows[1]["close"])
    if prev_c <= 0:
        return None
    return (latest_c - prev_c) / prev_c * 100.0, latest_d, prev_d


def big_movers(threshold_pct: float = 15.0, base=None) -> list[dict]:
    out = []
    conn = fin_io.connect(base=base)
    try:
        tickers = [r["ticker"] for r in conn.execute(
            "SELECT DISTINCT ticker FROM quotes_daily ORDER BY ticker"
        ).fetchall()]
    finally:
        conn.close()
    for t in tickers:
        res = daily_move_pct(t, base=base)
        if not res: continue
        pct, latest_d, prev_d = res
        if abs(pct) >= threshold_pct:
            out.append({"ticker": t, "pct": pct, "latest_date": latest_d, "prev_date": prev_d})
    out.sort(key=lambda r: abs(r["pct"]), reverse=True)
    return out
```

**Tests** (`test_quotes_io.py`)

用 tmp_path 和直接 INSERT 构造数据（不依赖 adapter）。辅助：

```python
def _insert_raw(base, ticker, date_iso, **kwargs):
    """直接 INSERT 用于测试 fixture"""
    conn = fin_io.connect(base=base)
    cols = ["ticker", "date", "market", "close"] + list(kwargs.keys())
    vals = [ticker, date_iso, "SSE", kwargs.pop("close", 100.0)] + list(kwargs.values())
    ...
```

必测：
- `upsert` 插入全字段能读回
- `upsert` 幂等（同 ticker+date 第二次 upsert 覆盖）
- `volume_ratio_5d`: 库里 0/1/4/5 条过去数据时分别返回 None/None/None/计算值
- `last_date_for` 无数据返回 None；有数据返回 ISO 字符串
- `latest_for` / `second_latest_for` 正确按 date DESC
- `history_for` 返回升序列表
- `latest_price_for`, `latest_prices_map`, `daily_move_pct`, `big_movers` 行为与旧 `prices.py` 一致
- `big_movers` 阈值过滤

**Done when**: 20+ 测试全绿。

---

## T4. io/quotes 错误追踪 + freshness

**Files**
- Modify: `app/io/quotes.py` — 追加函数
- Modify: `tests/test_quotes_io.py` — 追加测试

**追加的函数**

```python
from datetime import datetime, date as date_cls

def record_error(ticker: str, market: str, phase: str, error: str, base=None) -> None:
    source = "yfinance" if market == "US" else "akshare"
    conn = fin_io.connect(base=base)
    try:
        conn.execute("""
            INSERT INTO quotes_fetch_errors (ticker, market, attempted_at, source, phase, error)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, market, datetime.now().isoformat(), source, phase, error))
        conn.commit()
    finally:
        conn.close()


def mark_errors_resolved(ticker: str, base=None) -> int:
    conn = fin_io.connect(base=base)
    try:
        cur = conn.execute("""
            UPDATE quotes_fetch_errors SET resolved_at=?
            WHERE ticker=? AND resolved_at IS NULL
        """, (datetime.now().isoformat(), ticker))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def unresolved_fetch_errors(base=None) -> list[dict]:
    """按 ticker 聚合，每只票返回最近一条 unresolved error。"""
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute("""
            SELECT ticker, market, source, phase, error, MAX(attempted_at) AS attempted_at,
                   COUNT(*) AS count
            FROM quotes_fetch_errors
            WHERE resolved_at IS NULL
            GROUP BY ticker
            ORDER BY attempted_at DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def freshness(ticker: str, base=None, today: date_cls | None = None) -> dict:
    today = today or date_cls.today()
    last_d = last_date_for(ticker, base=base)
    d = (today - date_cls.fromisoformat(last_d)).days if last_d else 9999
    
    conn = fin_io.connect(base=base)
    try:
        row = conn.execute("""
            SELECT error, attempted_at FROM quotes_fetch_errors
            WHERE ticker=? AND resolved_at IS NULL
            ORDER BY attempted_at DESC LIMIT 1
        """, (ticker,)).fetchone()
    finally:
        conn.close()
    
    has_err = row is not None
    if has_err:
        err_age = (today - date_cls.fromisoformat(row["attempted_at"][:10])).days
    
    if not has_err and d <= 3:
        status = "green"
    elif has_err and err_age >= 3:
        status = "red"
    elif d >= 7:
        status = "red"
    else:
        status = "yellow"
    
    return {
        "status": status,
        "last_date": last_d,
        "days_since": d if last_d else None,
        "last_error": {"error": row["error"], "attempted_at": row["attempted_at"]} if has_err else None,
    }
```

**Tests 追加**
- `record_error` 写入一条
- `mark_errors_resolved` 把 ticker 所有未解决的标为 resolved
- `unresolved_fetch_errors` 按 ticker 聚合 + 返回 count
- `freshness` 六个场景：
  - 无数据 → red
  - 1 天内 + 无错 → green
  - 3 天 + 无错 → green
  - 4 天 + 无错 → yellow
  - 7 天 + 无错 → red
  - 有错 3 天 → red
  - 有错 1 天 → yellow

**Done when**: io/quotes.py 完整，测试覆盖所有 freshness 分支。

---

## T5. akshare adapter

**Files**
- Create: `app/io/adapters/akshare_adapter.py`
- Create: `tests/fixtures/adapters/akshare/` + sample files
- Create: `tests/test_adapter_akshare.py`
- Create: `tests/conftest.py`（新增 `mock_akshare` fixture，若已存在就追加）

**Fixture 文件（手写最小样本，不等 T13 的 snapshot_fixtures 脚本）**

`tests/fixtures/adapters/akshare/spot_em_600519.json`（单行从 `stock_zh_a_spot_em` 里切）:
```json
{
  "代码": "600519", "名称": "贵州茅台",
  "最新价": 1698.00, "今开": 1680.00, "最高": 1702.50, "最低": 1675.80,
  "成交量": 23456, "成交额": 3923456789.0,
  "换手率": 0.18, "量比": 0.95,
  "市盈率-动态": 20.3, "市净率": 8.5,
  "总市值": 2134567890000.0, "流通市值": 2134567890000.0,
  "流通股": 125619.78, "总股本": 125619.78,
  "52周最高": 1980.00, "52周最低": 1380.00
}
```

`tests/fixtures/adapters/akshare/hist_600519.csv`（过去 10 个交易日样本）:
```csv
日期,开盘,收盘,最高,最低,成交量,成交额
2026-04-14,1650.00,1660.00,1665.00,1645.00,18000,2988000000
...
```

`tests/fixtures/adapters/akshare/indicator_lg_600519.csv`:
```csv
trade_date,pe,pb,ps
2026-04-14,19.5,8.1,7.0
...
```

`tests/fixtures/adapters/akshare/minute_600519.csv`:
```csv
时间,开盘,收盘,最高,最低,成交量
2026-04-24 09:30:00,1680,1682,1683,1679,5500
2026-04-24 09:31:00,1682,1684,1685,1681,4200
...
```

**adapter 实现**

```python
import akshare as ak
import pandas as pd
from datetime import date, datetime

from app.io.adapters.base import Quote, AdapterError

source = "akshare"


def fetch_daily(ticker: str, market: str, start: date, end: date) -> list[Quote]:
    try:
        hist = ak.stock_zh_a_hist(
            symbol=ticker, period="daily",
            start_date=start.strftime("%Y%m%d"),
            end_date=end.strftime("%Y%m%d"),
            adjust="",
        )
        if hist.empty:
            return []
        spot_df = ak.stock_zh_a_spot_em()
        spot_row = spot_df[spot_df["代码"] == ticker]
        spot = spot_row.iloc[0] if not spot_row.empty else None
        try:
            ind = ak.stock_a_indicator_lg(symbol=ticker)
            ind = ind.set_index("trade_date") if not ind.empty else None
        except Exception:
            ind = None
    except Exception as e:
        raise AdapterError(f"akshare.fetch_daily({ticker}): {type(e).__name__}: {e}") from e
    
    float_shares = float(spot["流通股"]) * 1e4 if spot is not None else None  # 万股 → 股
    now = datetime.now().isoformat()
    
    out = []
    for _, h in hist.iterrows():
        d = str(h["日期"])
        vol = int(h["成交量"]) * 100  # 手 → 股
        amt = float(h["成交额"])
        turnover = (vol / float_shares * 100) if float_shares else None
        
        # 历史 PE/PB/PS 从 indicator_lg；spot 字段只给今天
        is_latest = (d == str(hist.iloc[-1]["日期"]))
        pe_ttm = pe_static = pb = ps = None
        dy = market_cap = float_mc = None
        sh_out = high52 = low52 = None
        
        if ind is not None and d in ind.index:
            pe_ttm = float(ind.loc[d]["pe"]) if pd.notna(ind.loc[d].get("pe")) else None
            pb = float(ind.loc[d]["pb"]) if pd.notna(ind.loc[d].get("pb")) else None
            ps = float(ind.loc[d]["ps"]) if pd.notna(ind.loc[d].get("ps")) else None
        
        if is_latest and spot is not None:
            # spot 给"当下"，把这些填到最新行
            pe_ttm = pe_ttm or float(spot.get("市盈率-动态", 0)) or None
            pb = pb or float(spot.get("市净率", 0)) or None
            market_cap = float(spot.get("总市值", 0)) or None
            float_mc = float(spot.get("流通市值", 0)) or None
            sh_out = float(spot.get("总股本", 0)) * 1e4 or None
            high52 = float(spot.get("52周最高", 0)) or None
            low52 = float(spot.get("52周最低", 0)) or None
        
        out.append(Quote(
            ticker=ticker, date=d, market=market,
            open=float(h["开盘"]), high=float(h["最高"]),
            low=float(h["最低"]), close=float(h["收盘"]),
            volume=vol, amount=amt,
            turnover_rate=turnover,
            pe_ttm=pe_ttm, pe_static=None, pe_forward=None,
            pb=pb, ps=ps, peg=None,
            dividend_yield=None,  # akshare spot 不直给 DY；留 T6 之后的扩充项
            market_cap=market_cap, float_market_cap=float_mc,
            shares_outstanding=sh_out, float_shares=float_shares,
            high_52w=high52, low_52w=low52,
            source="akshare", fetched_at=now,
        ))
    return out


def fetch_intraday_today(ticker: str, market: str) -> list[tuple[str, float, int]]:
    try:
        df = ak.stock_zh_a_hist_min_em(symbol=ticker, period="1", adjust="")
    except Exception as e:
        raise AdapterError(f"akshare.fetch_intraday({ticker}): {e}") from e
    if df.empty:
        return []
    today = date.today().isoformat()
    df = df[df["时间"].astype(str).str.startswith(today)]
    return [(str(r["时间"])[-8:-3], float(r["收盘"]), int(r["成交量"])) for _, r in df.iterrows()]


def fetch_snapshot(ticker: str, market: str) -> Quote:
    try:
        spot_df = ak.stock_zh_a_spot_em()
        row = spot_df[spot_df["代码"] == ticker]
        if row.empty:
            raise AdapterError(f"akshare: ticker {ticker} not found in spot_em")
        r = row.iloc[0]
    except AdapterError:
        raise
    except Exception as e:
        raise AdapterError(f"akshare.fetch_snapshot({ticker}): {e}") from e
    
    float_shares = float(r["流通股"]) * 1e4
    vol = int(r.get("成交量", 0)) * 100
    today = date.today().isoformat()
    return Quote(
        ticker=ticker, date=today, market=market,
        open=float(r["今开"]), high=float(r["最高"]), low=float(r["最低"]),
        close=float(r["最新价"]),
        volume=vol, amount=float(r["成交额"]),
        turnover_rate=float(r["换手率"]) if pd.notna(r.get("换手率")) else None,
        pe_ttm=float(r["市盈率-动态"]) if pd.notna(r.get("市盈率-动态")) else None,
        pe_static=None, pe_forward=None,
        pb=float(r["市净率"]) if pd.notna(r.get("市净率")) else None,
        ps=None, peg=None, dividend_yield=None,
        market_cap=float(r["总市值"]), float_market_cap=float(r["流通市值"]),
        shares_outstanding=float(r["总股本"]) * 1e4, float_shares=float_shares,
        high_52w=float(r.get("52周最高", 0)) or None,
        low_52w=float(r.get("52周最低", 0)) or None,
        source="akshare", fetched_at=datetime.now().isoformat(),
    )
```

**Tests + conftest fixtures**

`tests/conftest.py` 新增：

```python
import json
from pathlib import Path
import pandas as pd
import pytest

FIX_DIR = Path(__file__).parent / "fixtures" / "adapters"

@pytest.fixture
def mock_akshare(monkeypatch):
    def _spot_em():
        rec = json.loads((FIX_DIR / "akshare" / "spot_em_600519.json").read_text())
        return pd.DataFrame([rec])
    def _hist(symbol, period, start_date, end_date, adjust):
        return pd.read_csv(FIX_DIR / "akshare" / f"hist_{symbol}.csv")
    def _ind(symbol):
        return pd.read_csv(FIX_DIR / "akshare" / f"indicator_lg_{symbol}.csv")
    def _min(symbol, period, adjust):
        return pd.read_csv(FIX_DIR / "akshare" / f"minute_{symbol}.csv")
    monkeypatch.setattr("akshare.stock_zh_a_spot_em", _spot_em)
    monkeypatch.setattr("akshare.stock_zh_a_hist", _hist)
    monkeypatch.setattr("akshare.stock_a_indicator_lg", _ind)
    monkeypatch.setattr("akshare.stock_zh_a_hist_min_em", _min)
```

**必测**
- `fetch_daily` 字段映射：open/high/low/close 数字正确、volume 乘 100 正确、amount 正确、turnover_rate 按 vol/float_shares 算对
- `fetch_daily` 最新一行有 pe/pb/market_cap，其他行无
- `fetch_daily` 上游异常（monkeypatch 让 `stock_zh_a_hist` raise）→ AdapterError
- `fetch_daily` 空数据 → 返回 []
- `fetch_snapshot` 字段映射 + ticker 不存在 → AdapterError
- `fetch_intraday_today` 返回 `[(HH:MM, price, vol), ...]` 格式

**Done when**: 10-12 个测试绿。

---

## T6. yfinance adapter

**Files**
- Create: `app/io/adapters/yfinance_adapter.py`
- Create: `tests/fixtures/adapters/yfinance/` + sample files
- Create: `tests/test_adapter_yfinance.py`
- Modify: `tests/conftest.py` 追加 `mock_yfinance`

**Fixture 文件**

`tests/fixtures/adapters/yfinance/info_HIMS.json`:
```json
{
  "trailingPE": 45.3, "forwardPE": 38.1,
  "priceToBook": 12.5, "priceToSalesTrailing12Months": 8.2,
  "trailingPegRatio": 1.8,
  "dividendYield": 0.0,
  "marketCap": 7800000000, "floatShares": 215000000, "sharesOutstanding": 220000000,
  "fiftyTwoWeekHigh": 42.50, "fiftyTwoWeekLow": 12.30
}
```

`tests/fixtures/adapters/yfinance/history_HIMS.csv` + `intraday_HIMS.csv` 类似 akshare。

**adapter 实现**

```python
import yfinance as yf
import pandas as pd
from datetime import date, datetime, timedelta

from app.io.adapters.base import Quote, AdapterError

source = "yfinance"


def fetch_daily(ticker: str, market: str, start: date, end: date) -> list[Quote]:
    try:
        t = yf.Ticker(ticker)
        hist = t.history(start=start, end=end + timedelta(days=1), auto_adjust=False)
        info = t.info or {}
    except Exception as e:
        raise AdapterError(f"yfinance.fetch_daily({ticker}): {type(e).__name__}: {e}") from e
    if hist.empty:
        return []
    
    float_shares = info.get("floatShares")
    shares_out = info.get("sharesOutstanding")
    now = datetime.now().isoformat()
    dates_str = [idx.strftime("%Y-%m-%d") for idx in hist.index]
    latest_str = dates_str[-1]
    
    out = []
    for idx, h in hist.iterrows():
        d = idx.strftime("%Y-%m-%d")
        is_latest = (d == latest_str)
        vol = int(h["Volume"]) if pd.notna(h["Volume"]) else None
        close = float(h["Close"])
        turnover = (vol / float_shares * 100) if vol and float_shares else None
        
        out.append(Quote(
            ticker=ticker, date=d, market="US",
            open=float(h["Open"]) if pd.notna(h["Open"]) else None,
            high=float(h["High"]) if pd.notna(h["High"]) else None,
            low=float(h["Low"]) if pd.notna(h["Low"]) else None,
            close=close,
            volume=vol,
            amount=(vol * close) if vol else None,   # 估算
            turnover_rate=turnover,
            pe_ttm=info.get("trailingPE") if is_latest else None,
            pe_static=None,
            pe_forward=info.get("forwardPE") if is_latest else None,
            pb=info.get("priceToBook") if is_latest else None,
            ps=info.get("priceToSalesTrailing12Months") if is_latest else None,
            peg=info.get("trailingPegRatio") if is_latest else None,
            dividend_yield=((info.get("dividendYield") or 0) * 100) if is_latest else None,
            market_cap=info.get("marketCap") if is_latest else None,
            float_market_cap=(float_shares * close) if is_latest and float_shares else None,
            shares_outstanding=shares_out if is_latest else None,
            float_shares=float_shares,
            high_52w=info.get("fiftyTwoWeekHigh") if is_latest else None,
            low_52w=info.get("fiftyTwoWeekLow") if is_latest else None,
            source="yfinance", fetched_at=now,
        ))
    return out


def fetch_intraday_today(ticker: str, market: str) -> list[tuple[str, float, int]]:
    try:
        df = yf.Ticker(ticker).history(period="1d", interval="1m", auto_adjust=False)
    except Exception as e:
        raise AdapterError(f"yfinance.fetch_intraday({ticker}): {e}") from e
    if df.empty:
        return []
    return [(idx.strftime("%H:%M"), float(r["Close"]), int(r["Volume"])) for idx, r in df.iterrows()]


def fetch_snapshot(ticker: str, market: str) -> Quote:
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        info = t.info or {}
    except Exception as e:
        raise AdapterError(f"yfinance.fetch_snapshot({ticker}): {e}") from e
    
    close = float(fi["last_price"])
    float_shares = info.get("floatShares")
    today = date.today().isoformat()
    return Quote(
        ticker=ticker, date=today, market="US",
        open=float(fi.get("open", close)), high=float(fi.get("day_high", close)),
        low=float(fi.get("day_low", close)), close=close,
        volume=int(fi.get("last_volume", 0)) or None,
        amount=None,
        turnover_rate=None,
        pe_ttm=info.get("trailingPE"), pe_static=None, pe_forward=info.get("forwardPE"),
        pb=info.get("priceToBook"), ps=info.get("priceToSalesTrailing12Months"),
        peg=info.get("trailingPegRatio"),
        dividend_yield=(info.get("dividendYield") or 0) * 100,
        market_cap=info.get("marketCap"),
        float_market_cap=(float_shares * close) if float_shares else None,
        shares_outstanding=info.get("sharesOutstanding"), float_shares=float_shares,
        high_52w=info.get("fiftyTwoWeekHigh"), low_52w=info.get("fiftyTwoWeekLow"),
        source="yfinance", fetched_at=datetime.now().isoformat(),
    )
```

**Tests** 结构同 T5，fixture 用 `mock_yfinance`。必测覆盖：
- `fetch_daily` 字段映射 + 历史行 pe 为 None
- `fetch_daily` 最新行 pe_ttm / pe_forward / market_cap 等从 info 填
- `fetch_daily` 股息率 0.03 → 存 3.0
- `fetch_daily` amount = close × volume
- 429 异常 → AdapterError
- `fetch_snapshot` 从 fast_info 读

**Done when**: 10-12 个测试绿。

---

## T7. EOD 脚本 + run_for_ticker

**Files**
- Create: `scripts/fetch_quotes_eod.py`
- Create: `app/io/company_io.py` — 若不存在，提供 `list_all()` / `load_meta(key)` 扫 `companies/*/meta.md`
- Create: `tests/test_eod_script.py`

**先查/实现 `app/io/company_io.py`**

现有 `app/io/company.py` 可能已有类似功能——先 grep。若存在改名为 `company_io`（或直接用现名）。Plan 假设已有 `app/io/company.py` 提供 `list_all()`，返回 `list[Company]`，`Company` 含 `key`, `ticker`, `market`, `name` 等。如缺，需补。

**`scripts/fetch_quotes_eod.py`**

```python
#!/usr/bin/env python3
"""EOD 行情拉取脚本。

Usage:
  python -m scripts.fetch_quotes_eod                      # 所有公司
  python -m scripts.fetch_quotes_eod --markets US
  python -m scripts.fetch_quotes_eod --tickers 600519
  python -m scripts.fetch_quotes_eod --backfill-years 10
"""
import argparse
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from dateutil.relativedelta import relativedelta

from app.io import quotes as quotes_io
from app.io import company as company_io
from app.io.adapters import get_adapter
from app.io.adapters.base import AdapterError


def run_for_ticker(ticker: str, market: str,
                   backfill_years: int = 5,
                   base: Optional[Path] = None) -> dict:
    last = quotes_io.last_date_for(ticker, base=base)
    start = (date.fromisoformat(last) + timedelta(days=1)
             if last else date.today() - relativedelta(years=backfill_years))
    end = date.today()
    if start > end:
        return {"status": "uptodate", "quotes_added": 0, "error": None}
    try:
        quotes = get_adapter(market).fetch_daily(ticker, market, start, end)
        for q in quotes:
            quotes_io.upsert(q, base=base)
        quotes_io.mark_errors_resolved(ticker, base=base)
        return {"status": "ok", "quotes_added": len(quotes), "error": None}
    except AdapterError as e:
        quotes_io.record_error(ticker, market, phase="eod", error=str(e), base=base)
        return {"status": "error", "quotes_added": 0, "error": str(e)}


def run_eod(tickers: Optional[list[str]] = None,
            markets: Optional[list[str]] = None,
            backfill_years: int = 5,
            base: Optional[Path] = None) -> dict:
    companies = company_io.list_all(base=base) if base else company_io.list_all()
    if markets:
        companies = [c for c in companies if c.market in markets]
    if tickers:
        companies = [c for c in companies if c.ticker in tickers]
    
    ok = err = skip = 0
    for c in companies:
        r = run_for_ticker(c.ticker, c.market, backfill_years=backfill_years, base=base)
        if r["status"] == "ok":       ok += 1
        elif r["status"] == "error":  err += 1
        else:                          skip += 1
        time.sleep(0.3 if c.market == "US" else 0.1)
    
    return {"ok": ok, "errors": err, "skipped": skip, "total": len(companies)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tickers", help="comma-sep ticker list")
    p.add_argument("--markets", help="comma-sep market list")
    p.add_argument("--backfill-years", type=int, default=5)
    args = p.parse_args()
    tickers = args.tickers.split(",") if args.tickers else None
    markets = args.markets.split(",") if args.markets else None
    r = run_eod(tickers=tickers, markets=markets, backfill_years=args.backfill_years)
    print(f"EOD: {r['ok']} ok / {r['errors']} errors / {r['skipped']} up-to-date ({r['total']} total)")


if __name__ == "__main__":
    main()
```

**Tests**

用 mocked adapter（monkeypatch `app.io.adapters.get_adapter` 返回 stub）。必测：

- `run_for_ticker` 空库 → 调 `fetch_daily(start ≈ today - 5y, end = today)`，quotes_added == len(quotes)
- `run_for_ticker` 已有 last_date → 调 `fetch_daily(start = last + 1)`
- `run_for_ticker` last_date == today → status "uptodate"，不调 adapter
- `run_for_ticker` adapter 抛 AdapterError → status "error" + errors 表写入
- `run_for_ticker` 成功后 `mark_errors_resolved` 被调（有旧错误时解决）
- `run_eod` 混合成功/失败 → 统计正确
- `run_eod --markets US` → 只处理 US 公司

**Done when**: 6-8 个测试绿。

---

## T8. 清理 io/prices + 迁移 import

**Files**
- Delete: `app/io/prices.py`
- Delete: `tests/test_prices_triggers_io.py`
- Delete: `tests/test_big_movers.py`
- Modify: `main.py`, `app/routes/triggers.py`, `app/routes/portfolio.py`（import 改）
- Modify: `app/io/macro_risks.py`（行 143 的 `FROM prices` → `FROM quotes_daily`）
- Modify: `app/io/performance.py`（行 135, 207 的 `FROM prices` → `FROM quotes_daily`）
- Modify: `tests/test_macro_risks.py`（`prices_io.upsert_close(...)` → helper 直接插入 `quotes_daily`）
- Modify: `tests/test_performance_io.py`（同上）
- **暂时不改** `app/routes/prices.py`（T10 整个重写）

**改 import 规则**

老：
```python
from app.io import prices as prices_io
prices_io.big_movers(...)
prices_io.latest_prices_map(...)
prices_io.latest_price_for(...)
```

新：
```python
from app.io import quotes as quotes_io
quotes_io.big_movers(...)
quotes_io.latest_prices_map(...)
quotes_io.latest_price_for(...)
```

API 语义完全一致（T3 已保证）。

**改 raw SQL 规则**

`app/io/macro_risks.py:143`:
```python
# 旧
SELECT date, close FROM prices WHERE ticker = ? ...
# 新
SELECT date, close FROM quotes_daily WHERE ticker = ? ...
```
`app/io/performance.py:135, 207` 同理。

**改 test 规则**

`tests/test_macro_risks.py` 和 `tests/test_performance_io.py` 里
```python
prices_io.upsert_close(ticker="AAA", close=100.0, d=date(...), base=base)
```
替换为：
```python
from tests.helpers import insert_quote  # 新 helper

insert_quote(base, ticker="AAA", date="2026-04-21", market="SSE", close=100.0)
```

新增 `tests/helpers.py`:
```python
from pathlib import Path
from app.io import financials as fin_io

def insert_quote(base: Path, ticker: str, date: str, market: str = "SSE",
                 close: float = 100.0, volume: int | None = None, **kwargs):
    conn = fin_io.connect(base=base)
    try:
        conn.execute("""
            INSERT INTO quotes_daily (ticker, date, market, close, volume, source, fetched_at)
            VALUES (?, ?, ?, ?, ?, 'manual', datetime('now'))
        """, (ticker, date, market, close, volume))
        conn.commit()
    finally:
        conn.close()
```

（或让 `insert_quote` 接所有 kwargs 再组装——视测试需要）

**Done when**
- `pytest tests/test_macro_risks.py` 绿
- `pytest tests/test_performance_io.py` 绿
- 整个 `pytest -m "not live"` 不因为 import error 失败（即便 prices 路由/模板还没重写，T10 会处理）
- `grep -rn "from app.io import prices" --include="*.py"` 零结果（除了 `app/io/prices.py` 文件本身——但这个已经删了）
- `grep -rn "FROM prices\b" --include="*.py"` 零结果（除了 `app/io/prices.py`）

**注意**：`app/routes/prices.py` 暂时保留但**其内部 import 可能编译失败**（因为它 `from app.io import prices as prices_io`）。T10 会重写这个文件，届时恢复。**可选小修**：在 T8 把 `app/routes/prices.py` 缩成一个占位 router（返回"即将重构"占位），避免 `main.py` import 失败：

```python
# app/routes/prices.py (T8 临时)
from fastapi import APIRouter
router = APIRouter(prefix="/prices", tags=["prices"])

@router.get("")
def index(): return {"status": "rebuilding"}
```

T10 时再完整重写。

---

## T9. 首页告警 + 列表页"行情"按钮 + 详情页最新行情面板

**Files**
- Modify: `main.py`（home 视图）
- Modify: `app/templates/home.html`（告警卡片）
- Modify: `app/templates/companies/list.html`（行情按钮）
- Modify: `app/routes/companies.py`（detail 视图注入 latest_quote）
- Modify: `app/templates/companies/detail.html`（include 最新行情面板）
- Create: `app/templates/prices/_panel.html`（T10 会再扩，先建一个最小版本）
- Create: `tests/test_home_alert.py`
- Create: `tests/test_detail_panel.py`
- Create: `tests/test_list_quotes_button.py`

**main.py home 视图追加**

```python
quote_fetch_errors = quotes_io.unresolved_fetch_errors()
```

传入模板。

**home.html 追加块**（在 `big_movers` 附近）

```html
{% if quote_fetch_errors %}
<section class="alert-card">
  <h2>⚠️ 行情拉取失败（{{ quote_fetch_errors|length }}）</h2>
  <ul class="alert-list">
    {% for e in quote_fetch_errors %}
      <li>
        <a href="/prices/{{ e.ticker }}">{{ e.ticker }}</a>
        <span class="market">{{ e.market }}</span>
        <code>{{ e.source }}</code>
        <span class="error">{{ e.error }}</span>
        <span class="hint">{{ e.attempted_at }}</span>
      </li>
    {% endfor %}
  </ul>
</section>
{% endif %}
```

（CSS 细节写到 `static/style.css` 尾部，复用已有 `.alert-*` / `.badge-*` 规范）

**companies/list.html 的操作列**

找现有 `row-actions` td，在"观察池"按钮**前面**加：
```html
<a class="btn btn-mini" href="/prices/{{ r.key }}">行情</a>
```

**companies/detail.html 插入最新行情面板**

在 meta 表格（行 16 左右）之后、"年度快照"之前插入：
```html
{% if latest_quote %}
  {% include "prices/_panel.html" %}
{% endif %}
```

**app/routes/companies.py 的 detail 视图**

加 `latest_quote` / `prev_quote` / `freshness`：
```python
latest_quote = quotes_io.latest_for(ticker)
prev_quote = quotes_io.second_latest_for(ticker)
freshness = quotes_io.freshness(ticker)
return templates.TemplateResponse(request, "companies/detail.html", {
    ...,
    "latest_quote": latest_quote,
    "prev_quote": prev_quote,
    "freshness": freshness,
})
```

**prices/_panel.html 最小版本**

```html
<section class="quote-panel">
  <header>
    <h2>最新行情</h2>
    <a class="btn btn-mini" href="/prices/{{ key }}">→ 打开行情页</a>
  </header>
  <div class="freshness freshness-{{ freshness.status }}">
    {% if freshness.status == 'green' %}✅{% elif freshness.status == 'yellow' %}⚠️{% else %}🔴{% endif %}
    {{ latest_quote.date }}{% if freshness.days_since and freshness.days_since > 0 %} · {{ freshness.days_since }} 天前{% endif %}
  </div>
  <div class="quote-row">
    收 <strong>{{ '%.2f'|format(latest_quote.close) }}</strong>
    {% if prev_quote %}
      {% set pct = (latest_quote.close - prev_quote.close) / prev_quote.close * 100 %}
      <span class="{{ 'up' if pct > 0 else 'down' }}">{{ '%+.2f%%'|format(pct) }}</span>
    {% endif %}
    · 开 {{ '%.2f'|format(latest_quote.open) if latest_quote.open else '—' }}
    · 高 {{ '%.2f'|format(latest_quote.high) if latest_quote.high else '—' }}
    · 低 {{ '%.2f'|format(latest_quote.low) if latest_quote.low else '—' }}
  </div>
  {% if latest_quote.volume or latest_quote.amount %}
  <div class="quote-row">
    {% if latest_quote.volume %}量 {{ '{:,}'.format(latest_quote.volume) }}{% endif %}
    {% if latest_quote.amount %} · 额 {{ '{:,.0f}'.format(latest_quote.amount) }}{% endif %}
    {% if latest_quote.turnover_rate %} · 换 {{ '%.2f%%'|format(latest_quote.turnover_rate) }}{% endif %}
    {% if latest_quote.volume_ratio_5d %} · 量比 {{ '%.2f'|format(latest_quote.volume_ratio_5d) }}{% endif %}
  </div>
  {% endif %}
  {% if latest_quote.pe_ttm or latest_quote.pb or latest_quote.dividend_yield %}
  <div class="quote-row">
    {% if latest_quote.pe_ttm %}PE {{ '%.1f'|format(latest_quote.pe_ttm) }}×{% endif %}
    {% if latest_quote.pb %} · PB {{ '%.1f'|format(latest_quote.pb) }}×{% endif %}
    {% if latest_quote.dividend_yield %} · DY {{ '%.2f%%'|format(latest_quote.dividend_yield) }}{% endif %}
  </div>
  {% endif %}
</section>
```

**Tests**（TestClient）
- `GET /` 有 unresolved errors → HTML 包含 "行情拉取失败" + ticker 名
- `GET /` 无 errors → HTML 不包含该段
- `GET /companies` → 每个公司行有 `href="/prices/<key>"`
- `GET /companies/SSE_600519` latest_quote 存在 → 面板出现 + `href="/prices/SSE_600519"`
- `GET /companies/SSE_600519` 无 latest_quote → 面板不出现

**Done when**: 5 个测试绿 + 手动 curl/浏览器查看 home 和 detail 看到新元素。

---

## T10. 行情页路由 + 模板（主菜）

**Files**
- Rewrite: `app/routes/prices.py`
- Rewrite: `app/templates/prices/index.html`
- Create: `app/templates/prices/empty.html`
- Create: `app/templates/prices/_status_bar.html`
- Create: `app/templates/prices/_kline.html`
- Create: `app/templates/prices/_intraday.html`
- Modify: `app/templates/prices/_panel.html`（T9 最小版 → 扩展到完整左侧面板）
- Create: `static/js/prices.js`（空骨架，T11 填逻辑）
- Modify: `static/style.css`（追加 prices 页样式）
- Create: `tests/test_routes_prices.py`

**路由**

```python
from datetime import date
from typing import Literal
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import APP_TEMPLATES_DIR
from app.io import company as company_io
from app.io import quotes as quotes_io
from app.io.adapters import get_adapter
from app.io.adapters.base import AdapterError
from scripts.fetch_quotes_eod import run_for_ticker

router = APIRouter(prefix="/prices", tags=["prices"])
templates = Jinja2Templates(directory=str(APP_TEMPLATES_DIR))


@router.get("")
def index(request: Request):
    companies = company_io.list_all()
    if not companies:
        return templates.TemplateResponse(request, "prices/empty.html", {})
    return RedirectResponse(f"/prices/{companies[0].key}")


@router.get("/{key}")
def detail(request: Request, key: str):
    meta = company_io.load_meta(key)
    ticker = meta.ticker
    latest = quotes_io.latest_for(ticker)
    prev = quotes_io.second_latest_for(ticker)
    kline = quotes_io.history_for(ticker, limit=252)
    
    intraday, intraday_err = [], None
    if latest is not None:  # 库里有数据才尝试拉分时（新票分时等回补后再拉）
        try:
            intraday = get_adapter(meta.market).fetch_intraday_today(ticker, meta.market)
        except AdapterError as e:
            intraday_err = str(e)
            quotes_io.record_error(ticker, meta.market, phase="intraday", error=str(e))
    
    return templates.TemplateResponse(request, "prices/index.html", {
        "meta": meta,
        "key": key,
        "latest": latest, "prev": prev,
        "kline": kline, "intraday": intraday, "intraday_err": intraday_err,
        "freshness": quotes_io.freshness(ticker),
        "all_companies": company_io.list_all(),
    })


@router.post("/{key}/refresh")
def refresh(key: str):
    meta = company_io.load_meta(key)
    r = run_for_ticker(meta.ticker, meta.market)
    
    snap = None
    snap_err = None
    try:
        snap = get_adapter(meta.market).fetch_snapshot(meta.ticker, meta.market)
    except AdapterError as e:
        snap_err = str(e)
        quotes_io.record_error(meta.ticker, meta.market, phase="snapshot", error=str(e))
    
    latest = quotes_io.latest_for(meta.ticker)
    prev = quotes_io.second_latest_for(meta.ticker)
    kline = quotes_io.history_for(meta.ticker, limit=252)
    
    return {
        "ok": r["status"] != "error" or snap is not None,
        "quotes_added": r["quotes_added"],
        "daily_error": r["error"],
        "snapshot_error": snap_err,
        "latest": latest,
        "prev": prev,
        "kline": kline,
        "snapshot": _quote_to_dict(snap) if snap else None,
        "freshness": quotes_io.freshness(meta.ticker),
    }


@router.get("/{key}/chart")
def chart(key: str, period: Literal["1d", "1w", "1M"] = "1d"):
    meta = company_io.load_meta(key)
    rows = quotes_io.history_for(meta.ticker, limit=5000)  # 拉大量，前端按需
    if period == "1d":
        return {"period": period, "ohlcv": rows}
    # 聚合
    return {"period": period, "ohlcv": _aggregate(rows, period)}


def _aggregate(rows: list[dict], period: str) -> list[dict]:
    """按周/月聚合。key: 周的周一（ISO）或月首日。"""
    from collections import OrderedDict
    buckets = OrderedDict()
    for r in rows:
        d = date.fromisoformat(r["date"])
        if period == "1w":
            key = (d - timedelta(days=d.weekday())).isoformat()
        else:  # 1M
            key = d.replace(day=1).isoformat()
        if key not in buckets:
            buckets[key] = {"date": key, "open": r["open"], "high": r["high"],
                            "low": r["low"], "close": r["close"], "volume": r["volume"] or 0}
        else:
            b = buckets[key]
            b["high"] = max(b["high"], r["high"]) if r["high"] else b["high"]
            b["low"] = min(b["low"], r["low"]) if r["low"] else b["low"]
            b["close"] = r["close"]
            b["volume"] += r["volume"] or 0
    return list(buckets.values())


def _quote_to_dict(q):
    from dataclasses import asdict
    return asdict(q)
```

**模板骨架**

`prices/index.html`:
```html
{% extends "base.html" %}
{% block title %}{{ meta.name }} 行情{% endblock %}
{% block extra_head %}
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<link rel="stylesheet" href="/static/style.css"/>
{% endblock %}
{% block content %}
<header class="prices-header">
  <h1>{{ meta.name }} <small>({{ meta.market }}:{{ meta.ticker }})</small></h1>
  <form class="switcher" method="get">
    <select onchange="location.href='/prices/' + this.value">
      {% for c in all_companies %}
        <option value="{{ c.key }}" {% if c.key == key %}selected{% endif %}>
          {{ c.market }}:{{ c.ticker }} {{ c.name }}
        </option>
      {% endfor %}
    </select>
  </form>
  <button id="refresh-btn" class="btn" data-key="{{ key }}">↻ 刷新</button>
</header>

{% include "prices/_status_bar.html" %}

<div class="prices-layout">
  <aside class="prices-panel">
    {% include "prices/_panel.html" %}
  </aside>
  <section class="prices-charts">
    {% include "prices/_kline.html" %}
    {% include "prices/_intraday.html" %}
  </section>
</div>

<script id="quotes-data" type="application/json">
{
  "key": "{{ key }}",
  "ticker": "{{ meta.ticker }}",
  "kline": {{ kline|tojson }},
  "intraday": {{ intraday|tojson }},
  "intraday_err": {{ intraday_err|tojson }}
}
</script>
<script src="/static/js/prices.js"></script>
{% endblock %}
```

`_status_bar.html`:
```html
<div class="status-bar status-{{ freshness.status }}">
  {% if freshness.status == 'green' %}✅{% elif freshness.status == 'yellow' %}⚠️{% else %}🔴{% endif %}
  数据至 {{ freshness.last_date or '— 尚无数据' }}
  {% if freshness.days_since %}· {{ freshness.days_since }} 天前{% endif %}
  {% if latest %}· 来源 {{ latest.source }}{% endif %}
  {% if freshness.last_error %}
    <div class="error-detail">
      ❌ {{ freshness.last_error.error }}
      <small>（{{ freshness.last_error.attempted_at }}）</small>
    </div>
  {% endif %}
</div>
```

`_kline.html`:
```html
<div class="chart-wrap">
  <div class="chart-toolbar">
    <button class="period-btn active" data-period="1d">日 K</button>
    <button class="period-btn" data-period="1w">周 K</button>
    <button class="period-btn" data-period="1M">月 K</button>
  </div>
  <div id="kline-chart" style="width:100%;height:420px"></div>
</div>
```

`_intraday.html`:
```html
<div class="chart-wrap">
  <h3>今日分时</h3>
  {% if intraday_err %}
    <div class="hint error">今日分时暂不可用：{{ intraday_err }}</div>
  {% elif not intraday %}
    <div class="hint">暂无分时数据（非交易时段或新票未回补）</div>
  {% else %}
    <div id="intraday-chart" style="width:100%;height:260px"></div>
  {% endif %}
</div>
```

`_panel.html` 扩展为完整左侧面板（在 T9 基础上加 "估值/规模" 分组、格式化、量比/换手率等）。结构见 spec 第 5 块草图。

`empty.html`:
```html
{% extends "base.html" %}
{% block content %}<h1>行情</h1><p>还没有公司。<a href="/companies/new">创建第一家</a></p>{% endblock %}
```

**CSS 追加到 `static/style.css`** — 最小版本：

```css
/* prices page */
.prices-header { display:flex; gap:12px; align-items:center; margin-bottom:12px }
.prices-layout { display:grid; grid-template-columns: 280px 1fr; gap:16px }
.prices-panel { background:#f7f7f7; padding:12px; border-radius:6px }
.prices-charts { display:flex; flex-direction:column; gap:16px }
.chart-wrap { background:#fff; border:1px solid #ddd; padding:12px; border-radius:6px }
.chart-toolbar { display:flex; gap:8px; margin-bottom:8px }
.period-btn.active { background:#333; color:#fff }
.status-bar { padding:6px 12px; border-radius:4px; margin-bottom:12px }
.status-green  { background:#e6f4ea; color:#1e7a3a }
.status-yellow { background:#fff8e1; color:#8a6d1a }
.status-red    { background:#fde8e8; color:#b42318 }
.status-bar .error-detail { margin-top:4px; font-size:0.9em }
/* alert card on home */
.alert-card { background:#fde8e8; padding:12px; border-radius:6px; margin:16px 0 }
.alert-card .alert-list { margin:0; padding-left:20px }
.alert-card code { background:#fff; padding:2px 6px; border-radius:3px }
/* quote panel */
.quote-panel { background:#f7f7f7; padding:10px 12px; border-radius:6px; margin:12px 0 }
.quote-panel .freshness { font-size:0.9em; margin-bottom:6px }
.quote-panel .quote-row { line-height:1.8; font-size:0.95em }
.quote-panel .up   { color:#1e7a3a }
.quote-panel .down { color:#b42318 }
```

**Tests** (`test_routes_prices.py`)
- `GET /prices` 无公司 → 200 + empty.html 内容
- `GET /prices` 有公司 → 302 + Location: `/prices/<key>`
- `GET /prices/<key>` 库里有数据 → 200 + HTML 包含最新行情数字 + kline JSON
- `GET /prices/<key>` 库里无数据 → 200 + 面板显示"尚无数据" + 状态带红
- `GET /prices/<key>/chart?period=1d` → JSON ohlcv 数组
- `GET /prices/<key>/chart?period=1w` → JSON 按周聚合
- `POST /prices/<key>/refresh` 成功 → JSON `ok=true, quotes_added>=0`
- `POST /prices/<key>/refresh` adapter 全挂 → JSON `ok=false` + error 字段

`static/js/prices.js` T10 留空 stub（`console.log('prices.js loaded')`），T11 填。

**Done when**: 打开 `http://127.0.0.1:8000/prices/SSE_600519` 能看到骨架（面板 + 空图容器 + 状态带）；8 个路由测试绿。

---

## T11. 前端 JS（ECharts + 刷新 + 周期切换）

**Files**
- Rewrite: `static/js/prices.js`
- （可选）浏览器手工验证：启动 app，库里喂 fixture 数据，打开页面看图

**`static/js/prices.js`**

```javascript
(function() {
  'use strict';
  const data = JSON.parse(document.getElementById('quotes-data').textContent);
  const klineDom = document.getElementById('kline-chart');
  const intradayDom = document.getElementById('intraday-chart');
  
  const klineChart = klineDom ? echarts.init(klineDom) : null;
  const intradayChart = intradayDom ? echarts.init(intradayDom) : null;
  
  function klineOption(ohlcv) {
    const dates = ohlcv.map(r => r.date);
    const candles = ohlcv.map(r => [r.open, r.close, r.low, r.high]);
    const volumes = ohlcv.map(r => r.volume || 0);
    return {
      tooltip: {trigger:'axis', axisPointer:{type:'cross'}},
      grid: [{left:60, right:20, top:40, height:'55%'}, {left:60, right:20, top:'72%', height:'20%'}],
      xAxis: [
        {type:'category', data:dates, gridIndex:0, axisLabel:{show:false}},
        {type:'category', data:dates, gridIndex:1}
      ],
      yAxis: [
        {scale:true, gridIndex:0},
        {gridIndex:1, axisLabel:{show:false}}
      ],
      dataZoom: [
        {type:'inside', xAxisIndex:[0,1], start:70, end:100},
        {show:true, xAxisIndex:[0,1], top:'95%', start:70, end:100}
      ],
      series: [
        {name:'K', type:'candlestick', data:candles, itemStyle:{color:'#d62728', color0:'#2ca02c', borderColor:'#d62728', borderColor0:'#2ca02c'}},
        {name:'Vol', type:'bar', data:volumes, xAxisIndex:1, yAxisIndex:1}
      ]
    };
  }
  
  function intradayOption(rows) {
    const times = rows.map(r => r[0]);
    const prices = rows.map(r => r[1]);
    return {
      tooltip: {trigger:'axis'},
      xAxis: {type:'category', data:times, boundaryGap:false},
      yAxis: {scale:true},
      series: [{type:'line', data:prices, smooth:false, showSymbol:false}]
    };
  }
  
  if (klineChart && data.kline && data.kline.length) {
    klineChart.setOption(klineOption(data.kline));
  }
  if (intradayChart && data.intraday && data.intraday.length) {
    intradayChart.setOption(intradayOption(data.intraday));
  }
  window.addEventListener('resize', () => {
    klineChart && klineChart.resize();
    intradayChart && intradayChart.resize();
  });
  
  // 周期切换
  document.querySelectorAll('.period-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const period = btn.dataset.period;
      const res = await fetch(`/prices/${data.key}/chart?period=${period}`);
      const json = await res.json();
      klineChart && klineChart.setOption(klineOption(json.ohlcv), true);
    });
  });
  
  // 手动刷新
  const refreshBtn = document.getElementById('refresh-btn');
  let throttleUntil = 0;
  refreshBtn && refreshBtn.addEventListener('click', async () => {
    if (Date.now() < throttleUntil) return;
    throttleUntil = Date.now() + 10000;
    refreshBtn.disabled = true;
    const orig = refreshBtn.textContent;
    refreshBtn.textContent = '正在刷新...';
    try {
      const res = await fetch(`/prices/${data.key}/refresh`, {method:'POST'});
      const r = await res.json();
      if (r.ok) {
        if (r.kline && r.kline.length) klineChart.setOption(klineOption(r.kline), true);
        // 面板数字替换：交给后端模板层——简化为整页刷新
        location.reload();
      } else {
        alert('刷新失败: ' + (r.daily_error || r.snapshot_error || '未知错误'));
      }
    } catch (e) {
      alert('刷新请求失败: ' + e.message);
    } finally {
      setTimeout(() => {
        refreshBtn.disabled = false;
        refreshBtn.textContent = orig;
      }, 10000);
    }
  });
})();
```

**手工测试步骤**
1. 启动 `uvicorn main:app --reload`
2. 往库里插一些 fixture 数据（可用 `sqlite3 data/financials.db` 直接 INSERT 10 行日 K）
3. 浏览器打开 `/prices/SSE_600519`
4. 确认：K 线图出现（红绿蜡烛）+ 成交量副图 + dataZoom 条
5. 点"周 K"按钮 → 图变化
6. 点"↻ 刷新"按钮 → 会触发真 adapter（可能 429 / 网络错误，视环境）；页面整体刷新

**Done when**: 手工验证清单全过。

---

## T12. pytest + requirements

**Files**
- Modify: `pytest.ini`
- Modify: `requirements.txt`

**pytest.ini**
```ini
[pytest]
markers =
    live: tests that hit real external APIs (akshare, yfinance); skipped by default
addopts = -m "not live"
```

**requirements.txt** 追加：
```
akshare>=1.12
yfinance>=0.2.40
pandas>=2.1
python-dateutil>=2.8
```

（pandas 其实随 akshare 装上）

**安装 + 验证**
```bash
source .venv/bin/activate
pip install -r requirements.txt
pytest -m "not live"
```

**Done when**: 新依赖装好；全套测试（除 live 外）绿。

---

## T13. 手动契约测试 + fixtures 生成脚本

**Files**
- Create: `tests/manual/__init__.py`
- Create: `tests/manual/test_live_adapters.py`
- Create: `scripts/snapshot_fixtures.py`

**`tests/manual/test_live_adapters.py`**

```python
"""实际调用外部 API 的契约测试。默认 skip，手动 `pytest -m live` 触发。"""
import pytest

pytestmark = pytest.mark.live


def test_akshare_spot_em_has_expected_columns():
    import akshare as ak
    df = ak.stock_zh_a_spot_em()
    assert not df.empty
    for col in ["代码", "名称", "最新价", "成交量", "成交额",
                "换手率", "量比", "市盈率-动态", "市净率",
                "总市值", "流通市值", "流通股", "总股本"]:
        assert col in df.columns, f"akshare spot_em 缺字段 {col}"


def test_akshare_hist_has_expected_columns():
    import akshare as ak
    df = ak.stock_zh_a_hist(symbol="600519", period="daily",
                            start_date="20260401", end_date="20260424", adjust="")
    assert not df.empty
    for col in ["日期", "开盘", "收盘", "最高", "最低", "成交量", "成交额"]:
        assert col in df.columns


def test_yfinance_info_has_expected_keys():
    import yfinance as yf
    info = yf.Ticker("AAPL").info
    for key in ["trailingPE", "marketCap", "floatShares",
                "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]:
        assert key in info, f"yfinance info 缺字段 {key}"


def test_yfinance_history_has_expected_columns():
    import yfinance as yf
    hist = yf.Ticker("AAPL").history(period="5d", auto_adjust=False)
    assert not hist.empty
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert col in hist.columns
```

**`scripts/snapshot_fixtures.py`**

```python
#!/usr/bin/env python3
"""一次性脚本：从真实源抓 fixture 保存到 tests/fixtures/adapters/。"""
import json
from pathlib import Path

FIX = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "adapters"


def snapshot_akshare():
    import akshare as ak
    out = FIX / "akshare"
    out.mkdir(parents=True, exist_ok=True)
    # spot (单行)
    df = ak.stock_zh_a_spot_em()
    row = df[df["代码"] == "600519"].iloc[0].to_dict()
    (out / "spot_em_600519.json").write_text(json.dumps(row, ensure_ascii=False, indent=2))
    # hist
    ak.stock_zh_a_hist(symbol="600519", period="daily",
                       start_date="20260401", end_date="20260424", adjust="")\
      .to_csv(out / "hist_600519.csv", index=False)
    # indicator
    ak.stock_a_indicator_lg(symbol="600519").tail(20).to_csv(out / "indicator_lg_600519.csv", index=False)
    # minute
    ak.stock_zh_a_hist_min_em(symbol="600519", period="1", adjust="")\
      .head(50).to_csv(out / "minute_600519.csv", index=False)
    print("akshare fixtures written to", out)


def snapshot_yfinance():
    import yfinance as yf
    out = FIX / "yfinance"
    out.mkdir(parents=True, exist_ok=True)
    t = yf.Ticker("HIMS")
    (out / "info_HIMS.json").write_text(json.dumps(t.info, indent=2, default=str))
    t.history(period="1mo", auto_adjust=False).to_csv(out / "history_HIMS.csv")
    t.history(period="1d", interval="1m", auto_adjust=False).to_csv(out / "intraday_HIMS.csv")
    print("yfinance fixtures written to", out)


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("akshare", "both"): snapshot_akshare()
    if which in ("yfinance", "both"): snapshot_yfinance()
```

**Done when**：
- `pytest -m live` 在有网络的环境能跑（可能因限流/停牌间歇性失败，预期）
- `python -m scripts.snapshot_fixtures akshare` 能生成新 fixture（实际跑不强制，只要脚本可执行不报错即可）

---

## 最终验收

```bash
# 1. 测试全绿
pytest -m "not live" -v

# 2. 启动 app
uvicorn main:app --reload

# 3. 手动跑一次 EOD（对一只票）
python -m scripts.fetch_quotes_eod --tickers 600519

# 4. 浏览器验证
open http://127.0.0.1:8000/                        # 首页（若无错误，无告警卡片）
open http://127.0.0.1:8000/companies               # 每行有"行情"按钮
open http://127.0.0.1:8000/companies/SSE_600519    # 最新行情面板出现
open http://127.0.0.1:8000/prices                  # 重定向到第一家公司
open http://127.0.0.1:8000/prices/SSE_600519       # 行情页 + K 线 + 分时
```

---

## 不做项（spec §12 已列，此处重申）

- 盘中分钟级自动更新
- K 线复权切换
- 多股对比、技术指标、北向资金
- 自选股分组
- migration 框架（加字段走 `ALTER TABLE ADD COLUMN` + 一次性脚本）
