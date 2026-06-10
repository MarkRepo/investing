"""macro_jobs：后台单条取数 job 注册表 + 并发闸 + 输出缓冲 + SSE 订阅。

进程内内存、asyncio 驱动；流式 runner 在测试里被假实现替换（不拉真 claude）。
"""
import asyncio

import pytest

from app import macro_jobs
from prism.scripts import claude_runner

ENTRY = {"name": "ISM PMI", "availability": "llm", "source_url": "https://ism"}


@pytest.fixture(autouse=True)
def _reset(tmp_path, monkeypatch):
    macro_jobs._jobs.clear()
    macro_jobs._inflight.clear()
    macro_jobs._sem = None
    # 落盘指向临时目录，别污染仓库 prism/logs/
    monkeypatch.setattr(macro_jobs, "LOG_ROOT", tmp_path / "macro_fetch")
    yield
    macro_jobs._jobs.clear()
    macro_jobs._inflight.clear()
    macro_jobs._sem = None


# --- 纯函数：事件→人话行 ---

def test_event_to_lines_assistant_text():
    evt = {"type": "assistant",
           "message": {"content": [{"type": "text", "text": "  正在检索  "}]}}
    assert macro_jobs._event_to_lines(evt) == ["正在检索"]


def test_event_to_lines_tool_use_search_query():
    evt = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "tavily_search", "input": {"query": "ISM PMI latest"}}]}}
    lines = macro_jobs._event_to_lines(evt)
    assert len(lines) == 1
    assert "tavily_search" in lines[0] and "ISM PMI latest" in lines[0]


def test_event_to_lines_result_has_cost():
    evt = {"type": "result", "total_cost_usd": 0.0123, "duration_ms": 4200}
    line = macro_jobs._event_to_lines(evt)[0]
    assert "$0.0123" in line


def test_event_to_lines_raw_passthrough():
    evt = {"type": "raw", "text": "Invalid bearer token"}
    assert macro_jobs._event_to_lines(evt) == ["Invalid bearer token"]


def test_event_to_lines_init_shows_model():
    """system/init 带 model → 展示一行「· 模型 <实际模型>」（揭穿网关到底跑哪个模型）。"""
    evt = {"type": "system", "subtype": "init", "model": "claude-haiku-4.5", "session_id": "s"}
    assert macro_jobs._event_to_lines(evt) == ["· 模型 claude-haiku-4.5"]


def test_event_to_lines_init_without_model_silent():
    """无 model 的 system 事件不产行（不污染输出）。"""
    assert macro_jobs._event_to_lines({"type": "system", "subtype": "init"}) == []


def test_read_log_returns_persisted_text():
    """read_log 读回落盘的 .log 全文（供「查看输出」在 job 已超 TTL 后仍能看缓存）。"""
    d = macro_jobs.LOG_ROOT / "s" / "v"
    d.mkdir(parents=True)
    (d / f"{macro_jobs._safe('ISM PMI')}.log").write_text("第一行\n第二行", encoding="utf-8")
    assert macro_jobs.read_log("s", "v", "ISM PMI") == "第一行\n第二行"


def test_read_log_missing_returns_none():
    assert macro_jobs.read_log("s", "v", "不存在") is None


def test_sse_data_splits_multiline():
    """多行文本编码为合法 SSE：每物理行各加 data: 前缀，避免裸 \\n 截断（修「答案只剩第一行」）。"""
    out = macro_jobs._sse_data("第一行\n第二行\n第三行")
    assert out == "data: 第一行\ndata: 第二行\ndata: 第三行\n\n"
    # 单行：一条 data + 收尾空行
    assert macro_jobs._sse_data("只一行") == "data: 只一行\n\n"


# --- launch / 去重 / status ---

def _fake_runner(lines=(), *, gate=None, counter=None, status="ok", rc=0):
    async def runner(prompt, *, on_event, **kw):
        if counter is not None:
            counter["running"] += 1
            counter["max"] = max(counter["max"], counter["running"])
        for ln in lines:
            on_event({"type": "assistant",
                      "message": {"content": [{"type": "text", "text": ln}]}})
        if gate is not None:
            await gate.wait()
        # 末尾吐合法空 JSON 数组：parse 成功 → 终态 done（不触发任何 registry 写入）
        on_event({"type": "result", "total_cost_usd": 0.01, "duration_ms": 1000,
                  "session_id": "sid-fake", "result": "```json\n[]\n```"})
        if counter is not None:
            counter["running"] -= 1
        return (status, rc)
    return runner


def _json_runner(final_text, *, session_id="sid-1", capture=None, status="ok", rc=0):
    """假流式 runner：单个 result 事件携带 final_text(=claude 末尾 JSON) + session_id。

    capture（可选 dict）记下传给 runner 的 kwargs 与 prompt，供断言原生检索/禁工具/resume/model。
    """
    async def runner(prompt, *, on_event, **kw):
        if capture is not None:
            capture["kw"] = kw
            capture["prompt"] = prompt
        on_event({"type": "result", "total_cost_usd": 0.04, "duration_ms": 2000,
                  "session_id": session_id, "result": final_text})
        return (status, rc)
    return runner


def test_launch_creates_and_dedupes_inflight(monkeypatch):
    gate = asyncio.Event() if False else None  # placeholder; real gate below

    async def inner():
        g = asyncio.Event()
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _fake_runner(("hi",), gate=g))
        j1 = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await asyncio.sleep(0.02)  # 让 _run 跑到 running
        # 在途时再 launch 同名 → 同一 job
        j2 = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        assert j2.id == j1.id
        assert macro_jobs.get(j1.id) is j1
        st = macro_jobs.status("s", "v")
        assert st["ISM PMI"]["job_id"] == j1.id
        assert st["ISM PMI"]["inflight"] is True
        g.set()
        await j1.task

    asyncio.run(inner())


def test_semaphore_limits_concurrency(monkeypatch):
    async def inner():
        macro_jobs._sem = asyncio.Semaphore(2)
        counter = {"running": 0, "max": 0}
        g = asyncio.Event()
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _fake_runner(gate=g, counter=counter))
        jobs = [macro_jobs.launch("s", "v", f"n{i}",
                                  entry={"name": f"n{i}", "availability": "llm"})
                for i in range(3)]
        await asyncio.sleep(0.05)
        assert counter["max"] == 2          # 并发闸：同时最多 2
        assert counter["running"] == 2      # 第 3 个排队中
        # 排队的那个 status 仍是 queued
        statuses = {j.name: j.status for j in jobs}
        assert sorted(statuses.values()) == ["queued", "running", "running"]
        g.set()
        await asyncio.gather(*[j.task for j in jobs])
        assert all(j.status == "done" for j in jobs)

    asyncio.run(inner())


def test_subscribe_replays_then_streams_to_terminal(monkeypatch):
    async def inner():
        g = asyncio.Event()
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _fake_runner(("第一行", "第二行"), gate=g))
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await asyncio.sleep(0.02)  # 两行已缓冲

        seen = []

        async def consume():
            async for line in macro_jobs.subscribe(job.id):
                seen.append(line)

        consumer = asyncio.create_task(consume())
        await asyncio.sleep(0.02)
        g.set()                  # 放行 → result 事件 + 终态
        await job.task
        await asyncio.wait_for(consumer, timeout=2)

        assert "第一行" in seen and "第二行" in seen      # 重放已缓冲
        assert any("完成" in s for s in seen)             # 终态行
        assert job.status == "done"
        # 终态后 status 反映非在途
        assert macro_jobs.status("s", "v")["ISM PMI"]["inflight"] is False

    asyncio.run(inner())


def test_prune_removes_stale_terminal_jobs(monkeypatch):
    import time

    async def inner():
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _fake_runner(("x",)))
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        assert job.status == "done"
        job.ended_at = time.monotonic() - macro_jobs.JOB_TTL - 1   # 强制过期
        macro_jobs._prune()
        assert macro_jobs.get(job.id) is None

    asyncio.run(inner())


# --- 降本：默认 haiku、原生检索、禁工具 ---

def test_default_model_is_haiku():
    assert macro_jobs.MACRO_FETCH_MODEL == "haiku"


def test_run_uses_native_search_and_disallowed_tools(monkeypatch):
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)
    cap = {}
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner("```json\n[]\n```", capture=cap))

    async def inner():
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        kw = cap["kw"]
        assert kw["strict_mcp"] is True        # 零 MCP server
        assert kw["mcp_config"] is None        # 原生 WebSearch/WebFetch
        assert kw["disallowed_tools"] == ["Bash", "Write", "Edit"]  # 禁落盘/改文件
        assert kw["model"] == macro_jobs.MACRO_FETCH_MODEL

    asyncio.run(inner())


# --- 去 Bash 回合：解析末尾 JSON → 直接写 registry ---

def test_run_parses_json_and_records_observation(monkeypatch):
    from prism.scripts import macro_registry as reg
    calls, flags = [], []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, n, **kw: calls.append((n, kw)))
    monkeypatch.setattr(reg, "flag_scriptable",
                        lambda s, v, n, **kw: (flags.append((n, kw)) or True))
    payload = ('已检索 ISM 官网。\n```json\n'
               '[{"name":"ISM PMI","value":48.7,"as_of":"2026-06-01",'
               '"evidence":"ISM官网","acq_note":"检索官网最新","scriptable":true,"note":"需ISM端点"}]\n```')
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner(payload, session_id="sid-xyz"))

    async def inner():
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        assert job.status == "done"
        assert job.session_id == "sid-xyz"               # 捕获 session（供 resume）
        assert calls and calls[0][0] == "ISM PMI"
        assert calls[0][1]["value"] == 48.7
        assert calls[0][1]["as_of"] == "2026-06-01"
        assert calls[0][1]["evidence"] == "ISM官网"
        assert calls[0][1]["acq_note"] == "检索官网最新"
        assert flags and flags[0][0] == "ISM PMI"          # scriptable&value → 升档
        assert flags[0][1]["note"] == "需ISM端点"

    asyncio.run(inner())


def test_run_parse_failure_marks_failed_keeps_raw(monkeypatch):
    from prism.scripts import macro_registry as reg
    called = []
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: called.append(1))
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner("我没找到官方最新值，无法给出结果。"))

    async def inner():
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        assert job.status == "failed"          # 解析失败 = 不落值
        assert not called                       # 未写 registry
        assert any("JSON" in ln for ln in job.lines)   # 留痕可「重判」补救

    asyncio.run(inner())


def test_null_value_not_flagged_scriptable(monkeypatch):
    """诚实留空：value=null 即使 scriptable=true 也不升档（与 registry 闸门一致）。"""
    from prism.scripts import macro_registry as reg
    recorded, flags = [], []
    monkeypatch.setattr(reg, "record_observation",
                        lambda s, v, n, **kw: recorded.append((n, kw)))
    monkeypatch.setattr(reg, "flag_scriptable",
                        lambda s, v, n, **kw: (flags.append(n) or True))
    payload = ('```json\n[{"name":"ISM PMI","value":null,"as_of":null,'
               '"evidence":"","acq_note":"未找到官方最新","scriptable":true,"note":"x"}]\n```')
    monkeypatch.setattr(claude_runner, "run_headless_streaming", _json_runner(payload))

    async def inner():
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        assert job.status == "done"
        assert recorded and recorded[0][1]["value"] is None  # 落空但留痕
        assert flags == []                                    # 不升档

    asyncio.run(inner())


# --- resume 交互 / 换模型重判 ---

def test_say_resumes_with_session_id_and_model(monkeypatch):
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)
    payload = ('```json\n[{"name":"ISM PMI","value":49.0,"as_of":"2026-06-02",'
               '"evidence":"e","acq_note":"重判","scriptable":false,"note":""}]\n```')
    cap = {}

    async def inner():
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner(payload, session_id="sid-9"))
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        assert job.session_id == "sid-9"
        # 换 sonnet 重判：resume 同一会话、不重搜
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner(payload, session_id="sid-9", capture=cap))
        rj = await macro_jobs.say("s", "v", "ISM PMI", "用 sonnet 重判", model="sonnet")
        assert rj is not None
        await rj.task
        assert cap["kw"]["resume"] == "sid-9"
        assert cap["kw"]["model"] == "sonnet"
        assert cap["prompt"] == "用 sonnet 重判"

    asyncio.run(inner())


def test_say_rehydrates_session_from_meta(monkeypatch):
    """重启后内存无 job：say 从落盘 meta 读 session_id 重建壳 job 续问。"""
    import json as _json
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)
    d = macro_jobs.LOG_ROOT / "s" / "v"
    d.mkdir(parents=True, exist_ok=True)
    safe = macro_jobs._safe("ISM PMI")
    (d / f"{safe}.meta.json").write_text(
        _json.dumps({"name": "ISM PMI", "session_id": "sid-old"}), encoding="utf-8")
    cap = {}
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner("```json\n[]\n```", capture=cap))

    async def inner():
        rj = await macro_jobs.say("s", "v", "ISM PMI", "重判", model="opus")
        assert rj is not None
        await rj.task
        assert cap["kw"]["resume"] == "sid-old"

    asyncio.run(inner())


def test_say_unknown_returns_none(monkeypatch):
    async def inner():
        rj = await macro_jobs.say("s", "v", "无此输入", "hi")
        assert rj is None

    asyncio.run(inner())


def test_say_falls_back_to_meta_when_inmemory_job_lacks_session(monkeypatch):
    """内存里有该行 job 但 session_id=None（历史 job 未捕获）→ 仍回落到落盘 meta 的 session，不 404。"""
    import json as _json
    import time
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)
    d = macro_jobs.LOG_ROOT / "s" / "v"
    d.mkdir(parents=True, exist_ok=True)
    safe = macro_jobs._safe("ISM PMI")
    (d / f"{safe}.meta.json").write_text(
        _json.dumps({"name": "ISM PMI", "session_id": "sid-meta"}), encoding="utf-8")
    cap = {}

    async def inner():
        t = time.monotonic()
        stale = macro_jobs.Job(id="job-stale", slug="s", variant="v", name="ISM PMI",
                               entry=ENTRY, status="failed", started_at=t, ended_at=t)
        macro_jobs._jobs[stale.id] = stale          # 内存有 job 但 session_id 仍为 None
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("```json\n[]\n```", session_id="sid-meta", capture=cap))
        rj = await macro_jobs.say("s", "v", "ISM PMI", "在吗")
        assert rj is not None
        await rj.task
        assert cap["kw"]["resume"] == "sid-meta"

    asyncio.run(inner())


# --- /model 行内指令（弹框不再给模型下拉，仿 Claude Code /model）---

def test_parse_model_directive():
    assert macro_jobs._parse_model_directive("/model sonnet 用官方源重判") == ("sonnet", "用官方源重判")
    assert macro_jobs._parse_model_directive("/model opus") == ("opus", "")
    assert macro_jobs._parse_model_directive("  /model haiku  再查一次  ") == ("haiku", "再查一次")
    assert macro_jobs._parse_model_directive("普通追问，不换模型") == (None, "普通追问，不换模型")
    assert macro_jobs._parse_model_directive("") == (None, "")


def test_say_parses_inline_model_directive(monkeypatch):
    """无 model 参时，从消息开头 /model <名> 解析模型并剥离指令，余下作 prompt。"""
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)
    cap = {}

    async def inner():
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("```json\n[]\n```", session_id="sid-d"))
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("```json\n[]\n```", session_id="sid-d", capture=cap))
        rj = await macro_jobs.say("s", "v", "ISM PMI", "/model sonnet 用官方源重判")
        assert rj is not None
        await rj.task
        assert cap["kw"]["model"] == "sonnet"
        assert cap["prompt"] == "用官方源重判"

    asyncio.run(inner())


def test_say_empty_message_returns_none(monkeypatch):
    """空消息（含只 /model 无文本）→ 不起任务、返回 None：不默认任何操作（shell 式）。"""
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)

    async def inner():
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("```json\n[]\n```", session_id="sid-e"))
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task                          # 建立可 resume 的会话
        assert await macro_jobs.say("s", "v", "ISM PMI", "   ") is None      # 纯空白
        assert await macro_jobs.say("s", "v", "ISM PMI", "/model opus") is None  # 只切模型、无文本

    asyncio.run(inner())


def test_say_chat_reply_without_json_is_done(monkeypatch):
    """普通对话回合：claude 回散文（无 JSON）→ done（不算失败、不写 registry、不留 JSON 告警）。"""
    from prism.scripts import macro_registry as reg
    recorded = []
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: recorded.append(1))
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)

    async def inner():
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("```json\n[]\n```", session_id="sid-c"))
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("我用的是 ISM 官网 6 月发布页，没有改值。"))
        rj = await macro_jobs.say("s", "v", "ISM PMI", "你刚才用的哪个源？")
        assert rj is not None
        await rj.task
        assert rj.status == "done"                          # 对话回合不算失败
        assert not recorded                                 # 无 JSON → 不写 registry
        assert not any("JSON" in ln for ln in rj.lines)     # 不留「未解析出 JSON」告警

    asyncio.run(inner())


def test_run_captures_session_id_from_init_event(monkeypatch):
    """session_id 从 system/init 事件捕获（result 事件可能不带）→ 修 say 404。"""
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)

    async def runner(prompt, *, on_event, **kw):
        on_event({"type": "system", "subtype": "init", "session_id": "sid-init"})
        on_event({"type": "result", "total_cost_usd": 0.01, "duration_ms": 100,
                  "result": "```json\n[]\n```"})        # result 无 session_id
        return ("ok", 0)

    monkeypatch.setattr(claude_runner, "run_headless_streaming", runner)

    async def inner():
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        assert job.session_id == "sid-init"             # 从 init 捕获，非 None

    asyncio.run(inner())


def test_run_captures_model_from_init_event(monkeypatch):
    """实际模型从 system/init.model 捕获进 job.result['model'] 并落进 meta（审计「到底跑哪个模型」）。"""
    import json
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)

    async def runner(prompt, *, on_event, **kw):
        on_event({"type": "system", "subtype": "init",
                  "session_id": "sid-init", "model": "claude-haiku-4.5"})
        on_event({"type": "result", "total_cost_usd": 0.01, "duration_ms": 100,
                  "result": "```json\n[]\n```"})
        return ("ok", 0)

    monkeypatch.setattr(claude_runner, "run_headless_streaming", runner)

    async def inner():
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        assert job.result.get("model") == "claude-haiku-4.5"
        meta = json.loads((macro_jobs.LOG_ROOT / "s" / "v"
                           / f"{macro_jobs._safe('ISM PMI')}.meta.json").read_text(encoding="utf-8"))
        assert meta.get("model") == "claude-haiku-4.5"

    asyncio.run(inner())


# --- 发起重估：拉起真实合成 job（全能力、非沙箱、opus4.8 默认、不写 registry）---

def test_launch_reeval_creates_job_with_reserved_name(monkeypatch):
    cap = {}
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner("合成完成", capture=cap))

    async def inner():
        job = macro_jobs.launch_reeval("s", "v")
        assert job.name == macro_jobs.REEVAL_NAME == "__reeval__"
        assert job.status == "queued"
        await job.task

    asyncio.run(inner())


def test_launch_reeval_runs_full_capability_non_sandbox(monkeypatch):
    """重估是全能力会话：非沙箱（strict_mcp False、不禁工具）、长超时、默认 opus4.8 完整 id。"""
    cap = {}
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner("ok", capture=cap))

    async def inner():
        job = macro_jobs.launch_reeval("s", "v")
        await job.task
        kw = cap["kw"]
        assert kw["strict_mcp"] is False             # 放开 MCP
        assert kw["disallowed_tools"] is None        # 放开 Bash/Write/Edit
        assert kw["timeout"] == macro_jobs.REEVAL_TIMEOUT
        assert kw["model"] == macro_jobs.REEVAL_MODEL == "claude-opus-4-8"

    asyncio.run(inner())


def test_launch_reeval_model_override(monkeypatch):
    cap = {}
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner("ok", capture=cap))

    async def inner():
        job = macro_jobs.launch_reeval("s", "v", model="claude-sonnet-4-6")
        await job.task
        assert cap["kw"]["model"] == "claude-sonnet-4-6"

    asyncio.run(inner())


def test_launch_reeval_does_not_write_registry(monkeypatch):
    """重估靠自己的 Write/Bash 落盘——即便输出含 JSON 也绝不当取数 payload 覆盖 registry。"""
    from prism.scripts import macro_registry as reg
    recorded = []
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: recorded.append(1))
    payload = '```json\n[{"name":"ISM PMI","value":48.0}]\n```'
    monkeypatch.setattr(claude_runner, "run_headless_streaming", _json_runner(payload))

    async def inner():
        job = macro_jobs.launch_reeval("s", "v")
        await job.task
        assert job.status == "done"
        assert not recorded                          # apply_json=False → 不写 registry

    asyncio.run(inner())


def test_launch_reeval_dedupes_inflight(monkeypatch):
    async def inner():
        g = asyncio.Event()
        monkeypatch.setattr(claude_runner, "run_headless_streaming", _fake_runner(gate=g))
        j1 = macro_jobs.launch_reeval("s", "v")
        await asyncio.sleep(0.02)
        j2 = macro_jobs.launch_reeval("s", "v")       # 在途再点 → 同一 job
        assert j2.id == j1.id
        g.set()
        await j1.task

    asyncio.run(inner())


def test_say_reeval_continuation_is_non_sandbox(monkeypatch):
    """弹框续问重估会话：name==__reeval__ → 同样全能力非沙箱（不被重新沙箱化）。"""
    cap = {}

    async def inner():
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("ok", session_id="sid-r"))
        job = macro_jobs.launch_reeval("s", "v")
        await job.task
        assert job.session_id == "sid-r"
        monkeypatch.setattr(claude_runner, "run_headless_streaming",
                            _json_runner("ok", session_id="sid-r", capture=cap))
        rj = await macro_jobs.say("s", "v", macro_jobs.REEVAL_NAME, "只重判 rates_us，其余跳过")
        assert rj is not None
        await rj.task
        assert cap["kw"]["resume"] == "sid-r"
        assert cap["kw"]["strict_mcp"] is False
        assert cap["kw"]["disallowed_tools"] is None
        assert cap["kw"]["timeout"] == macro_jobs.REEVAL_TIMEOUT

    asyncio.run(inner())


# --- 落盘：输出 + session_id 持久化、同名覆盖、_safe 处理 / ---

def test_persist_writes_log_and_meta_overwrite(monkeypatch):
    from prism.scripts import macro_registry as reg
    monkeypatch.setattr(reg, "record_observation", lambda *a, **k: None)
    monkeypatch.setattr(reg, "flag_scriptable", lambda *a, **k: True)
    payload = ('```json\n[{"name":"ISM PMI","value":50.0,"as_of":"2026-06-03",'
               '"evidence":"e","acq_note":"n","scriptable":false,"note":""}]\n```')
    monkeypatch.setattr(claude_runner, "run_headless_streaming",
                        _json_runner(payload, session_id="sid-p"))

    async def inner():
        import json
        job = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job.task
        d = macro_jobs.LOG_ROOT / "s" / "v"
        safe = macro_jobs._safe("ISM PMI")
        assert (d / f"{safe}.log").exists()
        meta = json.loads((d / f"{safe}.meta.json").read_text(encoding="utf-8"))
        assert meta["session_id"] == "sid-p"
        assert meta["value"] == 50.0
        assert meta["name"] == "ISM PMI"
        assert meta.get("ended_at")            # 有 iso 时间戳
        # 再拉一次 → 覆盖，仍只有一个 meta 文件
        job2 = macro_jobs.launch("s", "v", "ISM PMI", entry=ENTRY)
        await job2.task
        assert len(list(d.glob("*.meta.json"))) == 1

    asyncio.run(inner())


def test_safe_name_handles_slash():
    safe = macro_jobs._safe("LPR 1Y/5Y")
    assert "/" not in safe                       # 不产生子目录
    assert macro_jobs._safe("LPR 1Y/5Y") == safe   # 同名稳定
    assert macro_jobs._safe("M1/M2/剪刀差") != safe  # 不同名不撞
