"""daily-monitor 的 web-server 内调度运行时。

调度层活在跑着的 FastAPI 进程里(不用系统 crontab、不用 CronCreate):
  - lifespan 起一个 asyncio 后台循环,每天算到下一个 6:00 本地时间 → sleep → 跑 cycle
  - web 端「立即巡检」按钮触发同一个 `run_monitor_cycle`

cycle 两条路:
  - **price breach(零 LLM)**:本进程直接 `monitor.propose_price_breaches` 写 queue
  - **signpost/kill 到期(需判读)**:把当日所有到期项批成 **1 个 headless `claude -p`**
    (经 `claude_runner.run_headless_async`)——LLM 仍由 Claude 做,web 只当触发器

防御:每日 headless 硬上限 `MAX_HEADLESS_PER_DAY`(默认 1),watchlist 是唯一成本闸。
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from pathlib import Path

MONITOR_HOUR = 6  # 每日 6:00 本地时间触发
MAX_HEADLESS_PER_DAY = 1
HEADLESS_PROMPT = (
    "你在 headless 模式下执行 prism daily-monitor 巡检。"
    "请完整读取并严格执行 prism/workflows/06-daily-monitor.md 的步骤:"
    "跑 `python3 -m prism.scripts.monitor scan` 拿到期 event,"
    "为每个到期 signpost/kill 写 web-search query 自动搜并判读,"
    "调 prism.scripts.monitor.propose_flips 写 proposal(只翻牌、不写 thesis 草案,"
    "kill 触发标 requires_thesis_review=True)。不要 confirm——确认永远留给用户在 web 端点。"
)

LOG_PATH = Path(__file__).resolve().parent.parent / "prism" / "logs" / "monitor.log"

# 进程内当日 headless 计数(date -> count),防一天内手动+定时叠加超限
_headless_count: dict[str, int] = {}
_cycle_lock = asyncio.Lock()


def _log(msg: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().isoformat(timespec="seconds")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def _seconds_until_next(hour: int, now: datetime | None = None) -> float:
    """到下一个 hour:00 本地时间的秒数(已过今天该点则算明天)。"""
    now = now or datetime.now()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def run_monitor_cycle(trigger: str = "scheduled") -> dict:
    """跑一次巡检。price 直接 propose;有非价格到期则拉 1 个 headless claude。

    返回 {trigger, price, due_signposts, due_kills, headless}。并发安全(lock 串行化)。
    """
    from prism.scripts import monitor

    async with _cycle_lock:
        result: dict = {"trigger": trigger}
        # ① 价格破位(零 LLM,本进程直接写 queue)
        try:
            price = await asyncio.to_thread(monitor.propose_price_breaches)
            result["price"] = price
        except Exception as e:
            result["price"] = {"error": str(e)}
            _log(f"price proposals failed: {e}")

        # macro 输入到期/越带（零 LLM）：写 macro_input proposal
        try:
            macro_res = await asyncio.to_thread(monitor.propose_macro_updates)
            _log(f"macro: scanned={macro_res.get('scanned_macro', 0)} "
                 f"added={macro_res.get('added', 0)}")
        except Exception as e:
            _log(f"macro propose failed: {e}")

        # ② scan 看有无需判读的到期项
        try:
            scan = await asyncio.to_thread(monitor.scan_due_events)
        except Exception as e:
            _log(f"scan failed: {e}")
            result["error"] = str(e)
            return result
        n_sp = len(scan["due_signposts"])
        n_kill = len(scan["due_kills"])
        result["due_signposts"] = n_sp
        result["due_kills"] = n_kill
        if scan["unparseable"]:
            _log(f"⚠️ {len(scan['unparseable'])} 个 event 日期无法解析(永不触发): "
                 f"{[u.get('locator') for u in scan['unparseable']]}")

        # ③ 有到期(非价格)→ 拉 headless claude 判读
        if n_sp or n_kill:
            today = date.today().isoformat()
            if _headless_count.get(today, 0) >= MAX_HEADLESS_PER_DAY:
                _log(f"headless 已达当日上限 {MAX_HEADLESS_PER_DAY},跳过({trigger})")
                result["headless"] = "skipped_daily_limit"
            else:
                _headless_count[today] = _headless_count.get(today, 0) + 1
                _log(f"拉起 headless claude 判读 {n_sp} signpost + {n_kill} kill（{trigger}）")
                result["headless"] = await _launch_headless()
        else:
            result["headless"] = "no_due_events"
        _log(f"cycle done: {result}")
        return result


async def _launch_headless() -> str:
    from prism.scripts import claude_runner
    try:
        rc, out, err = await claude_runner.run_headless_async(HEADLESS_PROMPT)
        if rc == 0:
            return "ok"
        _log(f"headless exit={rc} stderr={err[:500]}")
        return f"exit_{rc}"
    except asyncio.TimeoutError:
        _log("headless 超时被 kill")
        return "timeout"
    except Exception as e:
        _log(f"headless 拉起失败: {e}")
        return f"error: {e}"


async def scheduler_loop() -> None:
    """后台循环:睡到下一个 6:00 → 跑 cycle → 再睡。被 cancel 时干净退出。"""
    _log(f"scheduler 启动,每日 {MONITOR_HOUR:02d}:00 触发")
    try:
        while True:
            wait = _seconds_until_next(MONITOR_HOUR)
            _log(f"下次巡检 {wait/3600:.1f}h 后")
            await asyncio.sleep(wait)
            try:
                await run_monitor_cycle(trigger="scheduled")
            except Exception as e:
                _log(f"scheduled cycle 异常: {e}")
            await asyncio.sleep(60)  # 跨过 6:00 整点,避免同分钟重复触发
    except asyncio.CancelledError:
        _log("scheduler 停止")
        raise
