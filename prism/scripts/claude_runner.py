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
import os
import shutil
import subprocess
from pathlib import Path

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
