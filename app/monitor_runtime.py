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

        # macro FRED 自动抓取（零 LLM）：在 macro scan 之前，使扫描看到最新 observed。
        # 对每个 type==macro 的 topic 抓取（与 watchlist 解耦——抓取廉价，保持 observed 新鲜；
        # 是否写 proposal 仍由下游 watchlist 门控）。失败吞掉、不阻断周期。
        try:
            from prism.scripts import fred_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                fred_summary = await asyncio.to_thread(
                    fred_fetch.run_fred_fetch, t["slug"], t["variant"])
                _log(f"fred fetch [{t['slug']}/{t['variant']}]: {fred_summary}")
        except Exception as e:
            _log(f"fred fetch failed: {e}")

        # macro akshare 自动抓取（零 LLM）：中国宏观，fetch_method=='akshare' 的 scripted 项调 akshare 函数。
        # 与 fred/recipe 同为脚本通道，故同样在 macro scan 之前刷新 observed。失败吞掉、不阻断周期。
        try:
            from prism.scripts import akshare_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                ak_summary = await asyncio.to_thread(
                    akshare_fetch.run_akshare_fetch, t["slug"], t["variant"])
                _log(f"akshare fetch [{t['slug']}/{t['variant']}]: {ak_summary}")
        except Exception as e:
            _log(f"akshare fetch failed: {e}")

        # macro yfinance 自动抓取（零 LLM）：市场行情序列（MOVE/DXY/^TNX 等专有指数），
        # fetch_method=='yfinance' 的 scripted 项。与 fred/recipe/akshare 同为脚本通道，
        # 故同样在 macro scan 之前刷新 observed。失败吞掉、不阻断周期。
        try:
            from prism.scripts import yfinance_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                yfin_summary = await asyncio.to_thread(
                    yfinance_fetch.run_yfinance_fetch, t["slug"], t["variant"])
                _log(f"yfinance fetch [{t['slug']}/{t['variant']}]: {yfin_summary}")
        except Exception as e:
            _log(f"yfinance fetch failed: {e}")

        # macro macromicro 自动抓取（零 LLM）：FRED/akshare/yfinance 都缺的专有序列（如日频 JPY 3M OIS）。
        # fetch_method=='macromicro' 的 scripted 项，两步法（token+数据接口）。内建限流退避，每日 1 次不触发。
        # 与其余脚本数值通道同样在 macro scan 之前刷新 observed。失败吞掉、不阻断周期。
        try:
            from prism.scripts import macromicro_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                mm_summary = await asyncio.to_thread(
                    macromicro_fetch.run_macromicro_fetch, t["slug"], t["variant"])
                _log(f"macromicro fetch [{t['slug']}/{t['variant']}]: {mm_summary}")
        except Exception as e:
            _log(f"macromicro fetch failed: {e}")

        # macro barchart 自动抓取（零 LLM）：外汇 3M 远期点（EURUSD.H/USDJPY.H），CIP 基差远期腿。
        # fetch_method=='barchart' 的 scripted 项，两步法（XSRF cookie+core-api）。失败吞掉、不阻断周期。
        try:
            from prism.scripts import barchart_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                bc_summary = await asyncio.to_thread(
                    barchart_fetch.run_barchart_fetch, t["slug"], t["variant"])
                _log(f"barchart fetch [{t['slug']}/{t['variant']}]: {bc_summary}")
        except Exception as e:
            _log(f"barchart fetch failed: {e}")

        # macro ecb 自动抓取（零 LLM）：日频 EUR 3M OIS 混合（MMSR 锚+€STR 顺延），CIP 基差欧元腿。
        # fetch_method=='ecb' 的 scripted 项，ECB SDMX CSV。失败吞掉、不阻断周期。
        try:
            from prism.scripts import ecb_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                ecb_summary = await asyncio.to_thread(
                    ecb_fetch.run_ecb_fetch, t["slug"], t["variant"])
                _log(f"ecb fetch [{t['slug']}/{t['variant']}]: {ecb_summary}")
        except Exception as e:
            _log(f"ecb fetch failed: {e}")

        # macro SAFE 自动抓取（零 LLM）：外管局 Excel 月度表（银行结售汇差额 / 代客涉外收付差额），
        # fetch_method=='safe' 的 scripted 项，2 跳（文章页→最新 Excel）。与其余脚本数值通道同样在 macro scan 之前刷新 observed。失败吞掉、不阻断周期。
        try:
            from prism.scripts import safe_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                safe_summary = await asyncio.to_thread(
                    safe_fetch.run_safe_fetch, t["slug"], t["variant"])
                _log(f"safe fetch [{t['slug']}/{t['variant']}]: {safe_summary}")
        except Exception as e:
            _log(f"safe fetch failed: {e}")

        # macro recipe 自动抓取（零 LLM）：fetch_method=='recipe' 的 scripted 项（含按名派生，如 CIP 基差）。
        # **必须在上述各腿通道之后**跑——派生项读最新 observed 合成；故在此（macro scan 之前）末位刷新。
        # 失败吞掉、不阻断周期。
        try:
            from prism.scripts import recipe_fetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                rec_summary = await asyncio.to_thread(
                    recipe_fetch.run_recipe_fetch, t["slug"], t["variant"])
                _log(f"recipe fetch [{t['slug']}/{t['variant']}]: {rec_summary}")
        except Exception as e:
            _log(f"recipe fetch failed: {e}")

        # macro 取文自动下载（零 LLM）：带 text_fetch 的输入按其值路由 fetcher 下原文存本地缓存。
        # 与 fred/recipe 同为脚本通道——立场判读仍走 LLM（不在此跑），但原文缓存随定时保持新鲜，
        # 故和它们并列在 macro scan 之前刷新。失败吞掉、不阻断周期。加新取文源自动纳入本循环。
        try:
            from prism.scripts import textfetch
            from prism.scripts import topic as topic_io
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                text_summary = await asyncio.to_thread(
                    textfetch.run_textfetch, t["slug"], t["variant"])
                if text_summary:
                    _log(f"text fetch [{t['slug']}/{t['variant']}]: {text_summary}")
        except Exception as e:
            _log(f"text fetch failed: {e}")

        # macro 输入到期/越带（零 LLM）：写 macro_input proposal
        try:
            macro_res = await asyncio.to_thread(monitor.propose_macro_updates)
            _log(f"macro: scanned={macro_res.get('scanned_macro', 0)} "
                 f"added={macro_res.get('added', 0)}")
        except Exception as e:
            _log(f"macro propose failed: {e}")

        # macro headless LLM 取数：定时巡检**不再自动拉**（出于成本/耗时）——只算「到期待手动拉取」
        # 提示，由用户在 web 端点击 ⟳ 拉取（走 app.macro_jobs 后台 job）。零 LLM、零 token。
        # event/policy 仅到期入提示、series 恒入（见 due_llm_monitor_names）。
        try:
            from prism.scripts import macro_registry as reg
            from prism.scripts import topic as topic_io
            due_reminder: list[str] = []
            for t in topic_io.list_topics():
                if t.get("type") != "macro":
                    continue
                try:
                    registry = await asyncio.to_thread(reg.read_registry, t["slug"], t["variant"])
                except FileNotFoundError:
                    continue
                due_reminder.extend(reg.due_llm_monitor_names(registry))
            if due_reminder:
                result["macro_due_reminder"] = due_reminder
                _log(f"{len(due_reminder)} 条 llm/event 到期待手动拉取: {due_reminder}")
        except Exception as e:
            _log(f"macro due reminder failed: {e}")

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
        # claude -p 把报错（如 401 Invalid bearer token）写到 stdout，不是 stderr——两路都记
        _log(f"headless exit={rc} stdout={out[-500:].strip()} stderr={err[:500].strip()}")
        return f"exit_{rc}"
    except asyncio.TimeoutError:
        _log("headless 超时被 kill")
        return "timeout"
    except Exception as e:
        _log(f"headless 拉起失败: {e}")
        return f"error: {e}"


def _build_macro_llm_prompt(slug: str, variant: str, entries: list[dict]) -> str:
    """组 headless LLM 取数 prompt（纯函数，可测）。每个输入按 llm_acquisition_mode 派发：
    local_file=Read 本地缓存文件判读 / fixed_page=WebFetch 固定页判读 / search=WebSearch 检索。

    降本要点（去 Bash 回合）：claude **不调用任何 Bash/macro_record/写文件工具**——逐条检索判读后，
    **最后只输出一个 fenced ```json 数组**，由 Python 解析直接落盘（少 1–2 个 agent 回合、不重读上下文）。
    检索一律用内置 WebSearch（必要时 WebFetch 读固定页），local_file 模式用 Read 读本地文件。
    web 后台 job（单条）与 resume 重判路径共用本 prompt。"""
    from prism.scripts import macro_registry as reg
    from prism.scripts.macro_registry import _PRISM_ROOT, STANCE_SCALES
    has_local = any(reg.llm_acquisition_mode(e) == "local_file" for e in entries)
    has_web = any(reg.llm_acquisition_mode(e) in ("fixed_page", "search") for e in entries)
    tool_limit = []
    if has_local:
        tool_limit.append("Read（读本地缓存文件）")
    if has_web:
        tool_limit.append("WebSearch / WebFetch")
    lines = [
        "你在 headless 模式下为 prism 宏观输入表执行 LLM 取数。逐条处理下列输入，"
        "按各条指定方式取数后判读。绝不编造：某条拉不到就令其 value=null，不要写值、不要猜。",
        "",
        f"主题：{slug} / {variant}",
        "",
        f"工具限制：只用 {'、'.join(tool_limit) or 'WebSearch / WebFetch'}。"
        "**不要调用 Bash、不要写或改任何文件、不要试图自行落盘**——"
        "落盘由调用方的 Python 程序读你输出的 JSON 完成。",
        "",
        "promote（降本待办）：处理每条时判断「该源能否用稳定脚本/recipe 自动拉取」，"
        "把结论放进 scriptable(true/false) 与 note 字段；"
        "拉不到数值（value=null）时 scriptable 一律 false。",
        "",
        "输出格式（**全部处理完后，整段回复的最后只放这一个代码块，不要再有多余文字**）：",
        "```json",
        "[",
        '  {"name": "<输入名，与下表一致>", "value": <数值或 null>,',
        '   "stance": "<立场档位或 null，仅下方注明了立场轴的输入填写>",',
        '   "as_of": "<YYYY-MM-DD 或 null>",',
        '   "evidence": "<采用源 URL/引文>", "acq_note": "<本次取数判定理由>",',
        '   "scriptable": <true/false>, "note": "<若 scriptable：缺什么 recipe；否则空串>"}',
        "]",
        "```",
        "",
        "待取输入：",
    ]
    for e in entries:
        name = e.get("name", "")
        mode = reg.llm_acquisition_mode(e) or "search"
        scale = e.get("stance_scale")
        if mode == "local_file":
            abs_path = str(_PRISM_ROOT / e["local_cache_path"])
            scale_hint = (f"判断鹰鸽/松紧立场，填入 stance 字段（轴：{scale}，"
                          f"档位：{'、'.join(STANCE_SCALES[scale])}）。value 填 null。"
                          if scale and scale in STANCE_SCALES else "")
            how = (f"本地缓存文件 —— 用 Read 工具读 {abs_path}，"
                   f"根据文件内容判读最新状态。{scale_hint}"
                   "evidence 填文件中的来源 URL 或日期。")
        elif mode == "fixed_page":
            how = (f"固定页起点 {e.get('source_url')} —— 用 WebFetch 读该索引/落地页正文判读，"
                   "顺最新条目找数值。")
        else:
            how = ("检索式 —— 无稳定起点，用 WebSearch 构造 query 定位最新官方值，"
                   "把采用的源 URL/出处写进 evidence。")
        lines.append(f"- {name}：{how}")
    return "\n".join(lines)


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
