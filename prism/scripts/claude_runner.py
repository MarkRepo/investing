"""可复用的 headless `claude -p` 拉起器。零业务逻辑——纯进程拉起。

daily-monitor 的 web 调度器、手动「立即巡检」、以及未来任何"让 Claude 在后台跑一段
受控 prompt"的需求都走这里,不再各自散写 subprocess.Popen。

关键约束:
  - **显式继承 `os.environ`**:headless `claude -p` 要读 `~/.claude/settings.json` 的
    MCP env(web-search provider key);不继承环境 = 自动搜静默失效。
  - claude 路径:优先 `shutil.which("claude")`,回退 `~/.local/bin/claude`。
  - 同步 `run_headless`(CLI/测试)+ 异步 `run_headless_async`(web lifespan 循环不能
    被阻塞)两个入口。
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # …/investing

# headless 巡检含多次 web-search + 判读,给足时间;防御性硬上限避免僵死进程长挂
DEFAULT_TIMEOUT = 1800  # 30 min


class ClaudeNotFound(FileNotFoundError):
    """找不到 claude 可执行文件。"""


def resolve_claude() -> str:
    """定位 claude 可执行文件路径。找不到 → ClaudeNotFound。"""
    found = shutil.which("claude")
    if found:
        return found
    fallback = Path.home() / ".local" / "bin" / "claude"
    if fallback.exists():
        return str(fallback)
    raise ClaudeNotFound(
        "找不到 claude 可执行文件(已查 PATH 与 ~/.local/bin/claude)"
    )


def _build_argv(
    prompt: str,
    *,
    skip_permissions: bool,
    extra_args: list[str] | None,
) -> list[str]:
    argv = [resolve_claude(), "-p", prompt]
    if skip_permissions:
        argv.append("--dangerously-skip-permissions")
    if extra_args:
        argv.extend(extra_args)
    return argv


def run_headless(
    prompt: str,
    *,
    cwd: str | Path = REPO_ROOT,
    timeout: int = DEFAULT_TIMEOUT,
    skip_permissions: bool = True,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """同步拉起 headless claude。给 CLI / 测试用。

    返回 CompletedProcess(returncode/stdout/stderr 文本)。继承 os.environ。
    超时抛 subprocess.TimeoutExpired。
    """
    argv = _build_argv(prompt, skip_permissions=skip_permissions, extra_args=extra_args)
    return subprocess.run(
        argv,
        cwd=str(cwd),
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


async def run_headless_async(
    prompt: str,
    *,
    cwd: str | Path = REPO_ROOT,
    timeout: int = DEFAULT_TIMEOUT,
    skip_permissions: bool = True,
    extra_args: list[str] | None = None,
) -> tuple[int | None, str, str]:
    """异步拉起 headless claude,给 web 调度器(asyncio 事件循环)用——不阻塞循环。

    返回 (returncode, stdout, stderr)。超时则 kill 子进程并抛 asyncio.TimeoutError。
    """
    argv = _build_argv(prompt, skip_permissions=skip_permissions, extra_args=extra_args)
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(cwd),
        env=os.environ.copy(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    return (
        proc.returncode,
        (out or b"").decode("utf-8", "replace"),
        (err or b"").decode("utf-8", "replace"),
    )


def _build_streaming_argv(
    prompt: str,
    *,
    skip_permissions: bool,
    model: str | None,
    mcp_config: str | None,
    strict_mcp: bool,
    disallowed_tools: list[str] | None,
    resume: str | None,
) -> list[str]:
    """组流式 argv：stream-json 逐行吐 NDJSON + 可选降本/隔离/续会话 flags。

    `--strict-mcp-config` 无 `--mcp-config` = 零 MCP server，只剩内置 WebSearch/WebFetch（原生检索降本）；
    传 `--mcp-config <f>` 才载 <f>。`--disallowedTools <逗号串>`：禁掉某些工具（如取数禁 Bash/Write/Edit
    → 强制只能检索 + 末尾返回 JSON，杜绝 rogue 落盘/改文件）。`--resume <sid>`：续上既有会话上下文
    （prompt 即追问语，可配不同 --model 换模型重判而不重搜）。
    """
    argv = [resolve_claude(), "-p", prompt,
            "--output-format", "stream-json", "--verbose"]
    if skip_permissions:
        argv.append("--dangerously-skip-permissions")
    if model:
        argv.extend(["--model", model])
    if strict_mcp:
        argv.append("--strict-mcp-config")
    if mcp_config:
        argv.extend(["--mcp-config", mcp_config])
    if disallowed_tools:
        argv.extend(["--disallowedTools", ",".join(disallowed_tools)])
    if resume:
        argv.extend(["--resume", resume])
    return argv


async def run_headless_streaming(
    prompt: str,
    *,
    on_event: Callable[[dict], None],
    cwd: str | Path = REPO_ROOT,
    timeout: float = DEFAULT_TIMEOUT,
    model: str | None = None,
    mcp_config: str | None = None,
    strict_mcp: bool = False,
    disallowed_tools: list[str] | None = None,
    resume: str | None = None,
    skip_permissions: bool = True,
) -> tuple[str, int | None]:
    """流式拉起 headless claude，逐行解析 stream-json 调 `on_event`，给后台 job 实时输出用。

    每读到一行：能 `json.loads` → 传解析后的事件 dict；否则包成 `{"type":"raw","text":行}`
    透出（claude -p 把 401 这类报错写 stdout 非 JSON——stderr 合流进 stdout 后这里仍能见，
    呼应 monitor_runtime 的日志盲点修复）。

    返回 (status, returncode)：status ∈ {"ok", "timeout", f"exit_{rc}"}。
    超时按整体 deadline 计：到点 kill 子进程并返回 ("timeout", None)，绝不挂死。
    """
    argv = _build_streaming_argv(
        prompt, skip_permissions=skip_permissions,
        model=model, mcp_config=mcp_config, strict_mcp=strict_mcp,
        disallowed_tools=disallowed_tools, resume=resume)
    proc = await asyncio.create_subprocess_exec(
        *argv,
        cwd=str(cwd),
        env=os.environ.copy(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,  # 合流：stdout 报错（如 401）也被逐行捕获
    )
    deadline = time.monotonic() + timeout
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
            if not line:  # EOF
                break
            text = line.decode("utf-8", "replace").rstrip("\n")
            if not text.strip():
                continue
            try:
                evt = json.loads(text)
                if not isinstance(evt, dict):
                    evt = {"type": "raw", "text": text}
            except json.JSONDecodeError:
                evt = {"type": "raw", "text": text}
            on_event(evt)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return ("timeout", None)
    await proc.wait()
    rc = proc.returncode
    status = "ok" if rc == 0 else f"exit_{rc}"
    return (status, rc)
