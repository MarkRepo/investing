"""宏观 LLM 取数的后台 job 系统：单条任务 + 并发闸 + 实时输出缓冲 + SSE 订阅。

为什么存在：web 手动「⟳ 拉取」原来全同步 await 整个 headless `claude -p` 退出（单条 1–3 分钟），
请求挂起 → 前端不 resolve → 页面冻在旧态、刷新即丢「拉取中」（纯前端临时态），而后台 claude 仍在跑。
本模块把每个输入名拆成一个独立后台 job，服务端持有在途真相（刷新后仍正确），经 Semaphore 限并发，
逐行缓冲 claude 的 stream-json 输出供弹框 SSE 实时滚动（可关可重开：重开从缓冲重放再续播）。

边界：job 注册表与输出缓冲是**进程内内存**——服务器重启（--reload 改码）会丢状态，且后台 claude
是子进程会被一并杀。本地单人工具可接受。镜像 monitor_runtime 的模块级状态约定（_headless_count 等）。
"""
from __future__ import annotations

import asyncio
import hashlib
import itertools
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from prism.scripts import claude_runner

# 并发闸：同时最多几条 headless（控成本/负载）。单条独立超时（秒）。终态 job 留存供「查看输出」的 TTL。
MAX_CONCURRENT = 3
SINGLE_TIMEOUT = 360.0          # 单条 6min 硬上限，超时各自 kill、不连累其余
JOB_TTL = 1800.0               # 终态 job 保留 30min，期间弹框可重开看最终输出
MACRO_FETCH_MODEL = os.environ.get("MACRO_FETCH_MODEL", "haiku")  # 降本：默认 haiku，可 env 覆盖
# 取数 headless 砍掉所有 MCP server（strict_mcp 无 mcp_config）→ 只剩内置 WebSearch/WebFetch（原生检索降本）；
# 禁 Bash/Write/Edit → 强制只能检索 + 末尾返回 JSON，杜绝 rogue 落盘/改文件（去 Bash 回合）。
DISALLOWED_TOOLS = ["Bash", "Write", "Edit"]

# 发起重估：拉起真实合成（跑 _macro_regime 全流程）。与取数相反——全能力会话（放开 Bash/Write/Edit + MCP）
# 才能写产出 + 调 append_evaluation 闭环；默认 opus4.8 完整 id（别名 opus 经网关解析成 4.7，与要求不符）；
# 单独长超时（合成远比单条取数久）。复用 job 系统，保留名 __reeval__ 走同一弹框/SSE/续问/缓存栈。
REEVAL_NAME = "__reeval__"
REEVAL_MODEL = os.environ.get("MACRO_REEVAL_MODEL", "claude-opus-4-8")
REEVAL_TIMEOUT = float(os.environ.get("MACRO_REEVAL_TIMEOUT", "2700"))  # 45min

# 输出 + session_id + cost 落盘根目录（prism/logs/ 已 gitignore）。同名覆盖；供 resume-after-restart 与表格审计。
LOG_ROOT = claude_runner.REPO_ROOT / "prism" / "logs" / "macro_fetch"

# 弹框无模型下拉：换模型靠消息开头 `/model <名>` 指令（仿 Claude Code /model），前端解析为主、后端兜底。
_MODEL_DIRECTIVE = re.compile(r"^\s*/model\s+(\S+)\s*(.*)$", re.DOTALL)

TERMINAL = {"done", "failed", "timeout"}

# 进程内状态（镜像 monitor_runtime.py 的模块级约定）
_jobs: dict[str, "Job"] = {}
_inflight: dict[tuple[str, str, str], str] = {}   # (slug,variant,name) -> job_id（仅在途）
_sem: asyncio.Semaphore | None = None             # 懒建以绑定运行中的事件循环
_seq = itertools.count(1)


@dataclass
class Job:
    id: str
    slug: str
    variant: str
    name: str
    entry: dict
    status: str                       # queued | running | done | failed | timeout
    started_at: float
    ended_at: float | None = None
    lines: list[str] = field(default_factory=list)
    event: asyncio.Event = field(default_factory=asyncio.Event)
    result: dict = field(default_factory=dict)
    task: asyncio.Task | None = None
    session_id: str | None = None     # claude 会话 id（result 事件捕获）→ 供 resume 重判


def _get_sem() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(MAX_CONCURRENT)
    return _sem


# --- 事件 → 人话行（纯函数，可单测）---

def _tool_use_line(block: dict) -> str:
    name = block.get("name", "?")
    inp = block.get("input") or {}
    detail = inp.get("query") or inp.get("command") or inp.get("url") or ""
    detail = str(detail)
    if len(detail) > 120:
        detail = detail[:120] + "…"
    return f"🔧 {name}: {detail}" if detail else f"🔧 {name}"


def _event_to_lines(evt: dict) -> list[str]:
    """把一个 stream-json 事件提炼成 0..N 行人话（assistant 文本/工具调用、result 花费、raw 报错）。"""
    t = evt.get("type")
    if t == "raw":   # 非 JSON 行（如 401 报错文本）原样透出，不丢
        return [evt.get("text", "")]
    if t == "system":   # init：揭示网关实际解析出的模型（破除「自报 haiku / 实跑 opus」歧义）
        model = evt.get("model")
        return [f"· 模型 {model}"] if model else []
    if t == "assistant":
        out: list[str] = []
        for block in (evt.get("message") or {}).get("content") or []:
            bt = block.get("type")
            if bt == "text":
                txt = (block.get("text") or "").strip()
                if txt:
                    out.append(txt)
            elif bt == "tool_use":
                out.append(_tool_use_line(block))
        return out
    if t == "result":
        parts: list[str] = []
        dur = evt.get("duration_ms")
        cost = evt.get("total_cost_usd")
        if isinstance(dur, (int, float)):
            parts.append(f"耗时 {dur / 1000:.0f}s")
        if isinstance(cost, (int, float)):
            parts.append(f"花费 ${cost:.4f}")
        return ["· " + " · ".join(parts)] if parts else []
    return []  # system/init 等不展示


def _sse_data(text: str) -> str:
    """把一行（可能含 \\n 的多行文本，如 claude 的整段回答）编码为合法 SSE event。

    SSE 规范：data 字段以 `\\n` 分隔、空行结束 event。裸 `\\n` 直接塞进 `data: {text}` 会让客户端
    只收到第一行、其余被当作无名字段丢弃（= 「答案只剩第一行就没了」的真因）。故每物理行各加前缀。
    """
    body = "".join(f"data: {ln}\n" for ln in text.split("\n"))
    return body + "\n"


def _terminal_line(job: "Job") -> str:
    cost = job.result.get("cost")
    if job.status == "done":
        suffix = f" · 花费 ${cost:.4f}" if isinstance(cost, (int, float)) else ""
        return f"✓ 完成{suffix}"
    if job.status == "timeout":
        return "⏱ 超时被终止（其余任务不受影响）"
    reason = job.result.get("status") or job.result.get("error") or "未知"
    return f"✗ 失败（{reason}）"


def _make_prompt(slug: str, variant: str, entry: dict) -> str:
    """复用 monitor_runtime 的单条 prompt 组装（原生 WebSearch 检索 + 末尾吐 JSON，由本模块解析落盘）。"""
    from app import monitor_runtime as mrt
    return mrt._build_macro_llm_prompt(slug, variant, [entry])


# --- job 生命周期 ---

def launch(slug: str, variant: str, name: str, *, entry: dict) -> Job:
    """为单个输入名建一个后台取数 job 并立即返回（不等 claude 退出）。

    同名已在途 → 返回现有 job（去重，避免重复烧 token）。必须在事件循环内调用（路由是 async）。
    """
    _prune()
    key = (slug, variant, name)
    existing = _inflight.get(key)
    if existing and existing in _jobs:
        return _jobs[existing]
    job = Job(id=f"job-{next(_seq)}", slug=slug, variant=variant, name=name,
              entry=entry, status="queued", started_at=time.monotonic())
    _jobs[job.id] = job
    _inflight[key] = job.id
    job.task = asyncio.create_task(_run(job))
    return job


def _make_reeval_prompt(slug: str, variant: str) -> str:
    """重估启动语：注入现算简报（中文受影响结论）+ 指令读 _macro_regime.md 全流程执行 + 收尾闭环写评估。"""
    brief_block = ""
    try:                                   # 简报组装失败不应阻断重估启动（合成内部也会自查）
        from prism.scripts import eval_snapshot as es
        b = es.assemble_reeval_brief(slug, variant)
        changed = "、".join(c["name"] for c in b.get("changed") or []) or "—"
        breached = "、".join(c["name"] for c in b.get("breached") or []) or "—"
        labels = "、".join(b.get("affected_conclusion_labels") or []) or "—"
        unfetched = len(b.get("unfetched") or [])
        brief_block = (f"\n## 现算重估简报（零-LLM diff）\n"
                       f"- 变化输入：{changed}\n- 越带：{breached}\n"
                       f"- 受影响结论：{labels}\n- 盲区（未抓、无法判断变化）：{unfetched} 条\n")
    except Exception:
        brief_block = "\n（重估简报现算失败，请在合成内自行跑 eval_snapshot.diff_since_last 体检。）\n"
    return (
        f"你在 headless 模式下为 prism 执行宏观 regime **真实重估/合成**。topic={slug} variant={variant}。\n"
        f"这是全能力会话（可 Read/Bash/Write/Edit + MCP，cwd=仓库根）。\n"
        f"{brief_block}\n"
        f"步骤：\n"
        f"1. 读 `prism/workflows/04-synthesize/_macro_regime.md` 并对本 topic **严格全流程执行**"
        f"（Step 0 前置检查/gap/增量判定 → primer → m_regime_read → transmission_map → thesis/decomposition → critic）。\n"
        f"2. 上面简报的「变化输入/越带」对应的「受影响结论」本轮必须重判；无变化的可判 fresh、轻量或跳过重写。\n"
        f"3. **收尾闭环（硬要求）**：合成落地后调 `eval_snapshot.record_evaluation(slug, variant, conclusions, note=...)` "
        f"写评估快照——它用 snapshot_inputs 自动列全输入、据 based_on 标 used、自增 version、自动清 reeval_pending。"
        f"conclusions 覆盖三体制读数（overall/rates_us/rates_cn/liquidity_us/fx_cny/quadrant/fragility），"
        f"每条带中文 label + state + based_on:[{{input, role}}]（role ∈ load_bearing/confirming/background）。\n"
    )


def launch_reeval(slug: str, variant: str, *, model: str | None = None) -> Job:
    """点「发起重估」拉起的真实合成 job：全能力非沙箱、默认 opus4.8、长超时、不写 registry（自己落盘）。

    复用 job 系统，保留名 __reeval__ → 弹框/SSE/续问/缓存栈零改动直接用。同名在途 → 返现有 job（去重）。
    必须在事件循环内调用（路由 async）。
    """
    _prune()
    key = (slug, variant, REEVAL_NAME)
    existing = _inflight.get(key)
    if existing and existing in _jobs:
        return _jobs[existing]
    job = Job(id=f"job-{next(_seq)}", slug=slug, variant=variant, name=REEVAL_NAME,
              entry={"name": REEVAL_NAME}, status="queued", started_at=time.monotonic())
    _jobs[job.id] = job
    _inflight[key] = job.id
    prompt = _make_reeval_prompt(slug, variant)
    job.task = asyncio.create_task(_run(
        job, prompt=prompt, model=model or REEVAL_MODEL, chat=True,
        sandbox=False, timeout=REEVAL_TIMEOUT, apply_json=False))
    return job


def _parse_model_directive(message: str) -> tuple[str | None, str]:
    """解析消息开头的 `/model <名> [剩余]`（仿 Claude Code /model）。

    命中 → (模型名, 剥离指令后的剩余消息)；否则 (None, 原消息.strip())。
    """
    if not message:
        return None, message
    m = _MODEL_DIRECTIVE.match(message)
    if not m:
        return None, message
    return m.group(1), m.group(2).strip()


def _latest_job(slug: str, variant: str, name: str) -> Job | None:
    cands = [j for j in _jobs.values()
             if (j.slug, j.variant, j.name) == (slug, variant, name)]
    return max(cands, key=lambda j: j.started_at) if cands else None


async def say(slug: str, variant: str, name: str, message: str,
              *, model: str | None = None) -> Job | None:
    """弹框里对某行的会话续问（shell 式）：用已存 session_id `--resume` 续上同一上下文（不重搜）。

    取 session_id 顺序：内存里该行最近 job → 落盘 meta（重启/超 TTL 后仍可 resume）。
    无会话可续 → None（路由 404）。消息为空（含只 /model 无文本）→ None：不默认任何操作。
    消息原样发给 claude；若其回 JSON 则照常解析覆盖落盘（显式重判），否则就是普通问答。
    """
    _prune()
    prev = _latest_job(slug, variant, name)
    # 内存 job 优先；其无 session（历史 job 未捕获）则回落落盘 meta（重启/超 TTL 后仍可 resume）。
    session_id = (prev.session_id if prev else None) or (read_meta(slug, variant, name) or {}).get("session_id")
    if not session_id:
        return None
    if not model:                                  # 无显式模型 → 从消息开头 /model 指令解析（弹框防御性兜底）
        model, message = _parse_model_directive(message)
    message = (message or "").strip()
    if not message:                                # 空消息 / 只 /model：不起任务、不默认操作
        return None
    entry = prev.entry if prev else {"name": name}
    job = Job(id=f"job-{next(_seq)}", slug=slug, variant=variant, name=name,
              entry=entry, status="queued", started_at=time.monotonic(),
              session_id=session_id)
    _jobs[job.id] = job
    _inflight[(slug, variant, name)] = job.id
    reeval = name == REEVAL_NAME              # 续问重估会话 → 同样全能力非沙箱、长超时、不写 registry
    job.task = asyncio.create_task(_run(
        job, prompt=message, resume=session_id, model=model, chat=True,
        sandbox=not reeval,
        timeout=REEVAL_TIMEOUT if reeval else SINGLE_TIMEOUT,
        apply_json=not reeval))
    return job


async def _run(job: Job, *, prompt: str | None = None,
               resume: str | None = None, model: str | None = None,
               chat: bool = False, sandbox: bool = True,
               timeout: float = SINGLE_TIMEOUT, apply_json: bool = True) -> None:
    """跑一条 headless：初次取数 prompt=None（用 _make_prompt），对话/重判则传 prompt=消息 + resume=sid。

    chat=False（取数）：status=="ok" 时必须解析出 JSON → 写 registry；解析失败 = 不落值、标 failed、留 raw。
    chat=True（弹框对话）：有 JSON 则照常 apply（显式重判会更新值），无 JSON 也算 done（普通问答，不写、不报错）。
    sandbox=True（取数/对话）：strict_mcp 零 MCP + 禁 Bash/Write/Edit；sandbox=False（重估合成）：全能力会话。
    apply_json=False（重估）：跳过末尾 JSON 解析——重估靠自己的 Write/Bash 落盘，绝不误当取数 payload 覆盖 registry。
    session_id 从任一带它的事件捕获（system/init 必带；result 视网关可能不带）。无论成败，终态都 _persist。
    """
    sem = _get_sem()
    try:
        async with sem:                 # 并发闸：超额 job 停在 queued 直到有空位
            job.status = "running"
            job.event.set()

            def _append(evt: dict) -> None:
                for line in _event_to_lines(evt):
                    job.lines.append(line)
                sid = evt.get("session_id")     # init/result 皆可能带 → 任一捕获，供 resume
                if sid:
                    job.session_id = sid
                if evt.get("model"):            # init.model = 网关实际解析出的模型 → 审计/落盘
                    job.result["model"] = evt.get("model")
                if evt.get("type") == "result":
                    job.result["cost"] = evt.get("total_cost_usd")
                    job.result["duration_ms"] = evt.get("duration_ms")
                    job.result["final_text"] = evt.get("result")
                job.event.set()

            p = prompt if prompt is not None else _make_prompt(job.slug, job.variant, job.entry)
            status, rc = await claude_runner.run_headless_streaming(
                p, on_event=_append,
                model=model or MACRO_FETCH_MODEL,
                mcp_config=None,
                strict_mcp=sandbox,                                   # 沙箱：零 MCP server；重估：放开
                disallowed_tools=DISALLOWED_TOOLS if sandbox else None,  # 沙箱禁工具；重估放开 Bash/Write/Edit
                resume=resume,
                timeout=timeout)
            job.result["status"] = status
            job.result["returncode"] = rc
            if status == "ok":
                items = _parse_json_payload(job.result.get("final_text") or "") if apply_json else None
                if items is not None:
                    _apply_payload(job, items)      # 有 JSON：取数 / 显式重判都更新 registry
                    job.status = "done"
                elif chat or not apply_json:
                    job.status = "done"             # 对话回合 / 重估无 JSON 不算失败（重估自己落盘）
                else:
                    job.status = "failed"           # 取数必须吐 JSON：解析失败 = 不落值、可在弹框对话补救
                    job.result["parse_error"] = True
                    job.lines.append("⚠️ 未能从输出解析出 JSON 数组（值未落盘，可在弹框对话里要求其重判补救）")
            else:
                job.status = {"timeout": "timeout"}.get(status, "failed")
    except Exception as e:              # 拉起失败也要落终态，否则前端永远转
        job.status = "failed"
        job.result["error"] = str(e)
        job.lines.append(f"⚠️ 任务异常：{e}")
    finally:
        job.ended_at = time.monotonic()
        _inflight.pop((job.slug, job.variant, job.name), None)
        _persist(job)
        job.event.set()


# --- 末尾 JSON 解析 → 写 registry（不经 Bash/CLI）---

def _parse_json_payload(text: str) -> list[dict] | None:
    """从 claude 末尾输出鲁棒提取 JSON：优先 ```json fenced 块（取最后一个能解析的），
    退化为裸 [...] / {...}。返回 list[dict]；全失败返回 None（=不落值，诚实留空）。"""
    if not text:
        return None
    candidates: list[str] = [b.strip() for b in
                             re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL) if b.strip()]
    lb, rb = text.find("["), text.rfind("]")
    if 0 <= lb < rb:
        candidates.append(text[lb:rb + 1])
    lc, rc = text.find("{"), text.rfind("}")
    if 0 <= lc < rc:
        candidates.append(text[lc:rc + 1])
    for c in reversed(candidates):       # 末块优先（最终答案通常在最后）
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return [obj]
        if isinstance(obj, list):
            return obj
    return None


def _apply_payload(job: Job, items: list[dict]) -> None:
    """逐条把解析结果写进 registry：record_observation（含 value=null 的诚实留空），
    scriptable&value 非空再 flag_scriptable（registry 闸门兜底）。单条异常不连累其余。

    名字容错：LLM 偶尔改动输入名（如漏 "FOMC 声明/纪要" 的空格→"FOMC声明/纪要"）。
    精确名匹配不上时，用「去空白归一化」回退映射到登记表真实名，避免观测被静默丢弃。"""
    from prism.scripts import macro_registry as reg
    # 登记表真实名 + 归一化索引（去所有空白），供 LLM 名字漂移时回退匹配
    try:
        reg_names = [e["name"] for e in reg.read_registry(job.slug, job.variant).get("inputs") or []]
    except Exception:
        reg_names = []
    _norm = lambda s: re.sub(r"\s+", "", s or "")
    canon = {_norm(n): n for n in reg_names}
    applied = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        nm = item.get("name")
        if not nm:
            continue
        if nm not in reg_names:              # 精确匹配不上 → 归一化回退
            nm = canon.get(_norm(nm), nm)
        value = item.get("value")
        as_of = item.get("as_of")
        try:
            reg.record_observation(
                job.slug, job.variant, nm,
                value=value, as_of=as_of,
                evidence=item.get("evidence"), acq_note=item.get("acq_note"),
                stance=item.get("stance") or None,
                # 去重指纹：路由起 job 前已塞进 entry（见 prism.py fetch-llm）。
                # 落盘后下次取数对比，相同即跳过二次判读。无则不写（向后兼容）。
                fingerprint=job.entry.get("_pending_fingerprint"))
        except Exception as e:           # 未知输入/读写异常：记一行、跳过，不毁整 job
            job.lines.append(f"⚠️ 跳过「{nm}」：{e}")
            continue
        applied += 1
        if item.get("scriptable") and value is not None:
            try:
                reg.flag_scriptable(job.slug, job.variant, nm, note=item.get("note") or "")
            except Exception:
                pass
        if nm == job.name:               # 本行的值/时间存进 result，供 meta 落盘 + 表格显示
            job.result["value"] = value
            job.result["as_of"] = as_of
    job.result["applied"] = applied


# --- 落盘：输出 + session_id + cost（同名覆盖）---

def _safe(name: str) -> str:
    """把输入名变成安全文件名：非[字母数字/CJK]→_，再接 8 位 sha1 避免撞名/含 `/`。"""
    base = re.sub(r"[^0-9A-Za-z一-鿿]+", "_", name).strip("_") or "x"
    return f"{base}-{hashlib.sha1(name.encode('utf-8')).hexdigest()[:8]}"


def read_meta(slug: str, variant: str, name: str) -> dict | None:
    """读某行上次落盘的 meta（cost/ended_at/session_id/value...）；无则 None。供表格审计 + resume 重建。"""
    path = LOG_ROOT / slug / variant / f"{_safe(name)}.meta.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_log(slug: str, variant: str, name: str) -> str | None:
    """读某行上次落盘的 .log 全文（取数输出）；无则 None。供「查看输出」在 job 超 TTL/重启后仍看缓存。"""
    path = LOG_ROOT / slug / variant / f"{_safe(name)}.log"
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _persist(job: Job) -> None:
    """终态把输出 + session_id + cost 写盘（同名覆盖）。落盘失败不应影响 job 终态。"""
    try:
        d = LOG_ROOT / job.slug / job.variant
        d.mkdir(parents=True, exist_ok=True)
        safe = _safe(job.name)
        (d / f"{safe}.log").write_text("\n".join(job.lines), encoding="utf-8")
        meta = {
            "name": job.name,
            "session_id": job.session_id,
            "status": job.status,
            "model": job.result.get("model"),
            "cost": job.result.get("cost"),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "value": job.result.get("value"),
            "as_of": job.result.get("as_of"),
        }
        (d / f"{safe}.meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:                    # 落盘是 best-effort，不掩盖 job 状态
        pass


def get(job_id: str) -> Job | None:
    _prune()
    return _jobs.get(job_id)


def status(slug: str, variant: str) -> dict[str, dict]:
    """页面渲染/轮询用：{name: {status, job_id, started_at, inflight}}（每名取最新 job）。"""
    _prune()
    out: dict[str, dict] = {}
    for job in _jobs.values():
        if job.slug != slug or job.variant != variant:
            continue
        prev = out.get(job.name)
        if prev is None or job.started_at >= prev["started_at"]:
            out[job.name] = {
                "status": job.status,
                "job_id": job.id,
                "started_at": job.started_at,
                "inflight": job.status not in TERMINAL,
            }
    return out


async def subscribe(job_id: str):
    """SSE 用异步生成器：先重放已缓冲行，再续播新行，直到终态吐一行收尾后结束。

    关弹框只断这个生成器（EventSource.close），不动后台 job；重开新建生成器 → 从头重放缓冲再续播。
    """
    job = _jobs.get(job_id)
    if job is None:
        return
    idx = 0
    while True:
        job.event.clear()
        while idx < len(job.lines):
            yield job.lines[idx]
            idx += 1
        if job.status in TERMINAL:
            yield _terminal_line(job)
            return
        await job.event.wait()


def _prune() -> None:
    """清掉超 TTL 的终态 job（在途的永不清）。每次访问入口顺手调。"""
    now = time.monotonic()
    stale = [jid for jid, j in _jobs.items()
             if j.status in TERMINAL and j.ended_at is not None
             and (now - j.ended_at) > JOB_TTL]
    for jid in stale:
        _jobs.pop(jid, None)
