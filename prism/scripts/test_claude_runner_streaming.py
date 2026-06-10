"""run_headless_streaming：逐行解析 stream-json、超时 kill。纯进程层，假 subprocess。"""
import asyncio
import json

import pytest

from prism.scripts import claude_runner


class _FakeStdout:
    """按预置行逐行吐；行尽后吐 b'' 表示 EOF。可选 hang=True 永不返回（测超时）。"""
    def __init__(self, lines, *, hang=False):
        self._lines = list(lines)
        self._hang = hang

    async def readline(self):
        if self._hang:
            await asyncio.sleep(10)  # 永不在测试超时前返回
        if self._lines:
            return self._lines.pop(0)
        return b""


class _FakeProc:
    def __init__(self, lines, *, hang=False, returncode=0):
        self.stdout = _FakeStdout(lines, hang=hang)
        self.returncode = returncode
        self.killed = False

    def kill(self):
        self.killed = True

    async def wait(self):
        return self.returncode


def _patch_exec(monkeypatch, proc):
    captured = {}

    async def fake_exec(*argv, **kwargs):
        captured["argv"] = list(argv)
        captured["kwargs"] = kwargs
        return proc

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    return captured


def test_parses_stream_json_events_in_order(monkeypatch):
    lines = [
        json.dumps({"type": "system", "subtype": "init"}).encode() + b"\n",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}).encode() + b"\n",
        json.dumps({"type": "result", "total_cost_usd": 0.01}).encode() + b"\n",
    ]
    proc = _FakeProc(lines, returncode=0)
    captured = _patch_exec(monkeypatch, proc)

    events = []
    status, rc = asyncio.run(claude_runner.run_headless_streaming(
        "p", on_event=events.append, timeout=5,
        model="sonnet", mcp_config=".mcp.json", strict_mcp=True))

    assert [e["type"] for e in events] == ["system", "assistant", "result"]
    assert status == "ok"
    assert rc == 0
    # argv 含 stream-json 流式 flags 与降本 flags
    argv = captured["argv"]
    assert "--output-format" in argv and "stream-json" in argv
    assert "--verbose" in argv
    assert "--model" in argv and "sonnet" in argv
    assert "--strict-mcp-config" in argv
    assert "--mcp-config" in argv and ".mcp.json" in argv
    # stdout/stderr 合流，确保 stdout 报错（如 401）也被捕获
    assert captured["kwargs"]["stderr"] == asyncio.subprocess.STDOUT


def test_non_json_line_surfaced_as_raw(monkeypatch):
    """非 JSON 行（如 401 报错文本）以 raw 事件透出，不丢。"""
    lines = [b"Invalid bearer token\n",
             json.dumps({"type": "result", "total_cost_usd": 0}).encode() + b"\n"]
    proc = _FakeProc(lines, returncode=1)
    _patch_exec(monkeypatch, proc)

    events = []
    status, rc = asyncio.run(claude_runner.run_headless_streaming(
        "p", on_event=events.append, timeout=5))

    assert events[0]["type"] == "raw"
    assert "Invalid bearer token" in events[0]["text"]
    assert status == "exit_1"
    assert rc == 1


def test_timeout_kills_process(monkeypatch):
    proc = _FakeProc([], hang=True)
    _patch_exec(monkeypatch, proc)

    events = []
    status, rc = asyncio.run(claude_runner.run_headless_streaming(
        "p", on_event=events.append, timeout=0.05))

    assert status == "timeout"
    assert proc.killed is True


def test_disallowed_tools_added_to_argv(monkeypatch):
    """disallowed_tools → argv 加 `--disallowedTools <逗号串>`，强制只能检索+返回 JSON。"""
    proc = _FakeProc([b"" ], returncode=0)
    captured = _patch_exec(monkeypatch, proc)

    asyncio.run(claude_runner.run_headless_streaming(
        "p", on_event=lambda e: None, timeout=5,
        disallowed_tools=["Bash", "Write", "Edit"]))

    argv = captured["argv"]
    assert "--disallowedTools" in argv
    i = argv.index("--disallowedTools")
    assert argv[i + 1] == "Bash,Write,Edit"


def test_resume_added_to_argv(monkeypatch):
    """resume=<sid> → argv 加 `--resume <sid>`，续上同一会话上下文。"""
    proc = _FakeProc([b""], returncode=0)
    captured = _patch_exec(monkeypatch, proc)

    asyncio.run(claude_runner.run_headless_streaming(
        "p", on_event=lambda e: None, timeout=5, resume="sid-abc-123"))

    argv = captured["argv"]
    assert "--resume" in argv
    i = argv.index("--resume")
    assert argv[i + 1] == "sid-abc-123"


def test_native_path_has_no_mcp_config(monkeypatch):
    """原生检索路径：strict_mcp=True 且 mcp_config=None → 有 --strict-mcp-config 但无 --mcp-config（零 MCP server）。"""
    proc = _FakeProc([b""], returncode=0)
    captured = _patch_exec(monkeypatch, proc)

    asyncio.run(claude_runner.run_headless_streaming(
        "p", on_event=lambda e: None, timeout=5,
        strict_mcp=True, mcp_config=None))

    argv = captured["argv"]
    assert "--strict-mcp-config" in argv
    assert "--mcp-config" not in argv
