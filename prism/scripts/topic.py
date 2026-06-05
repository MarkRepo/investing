"""Create, read, and update topic.yaml files. Zero LLM calls."""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from prism.scripts import model_registry

PRISM_ROOT = Path(__file__).resolve().parent.parent

# 决策链产出 key（按 topic.type）。
# 用途（file-first 改造后）：create_topic **不再** seed 这些为 pending——它们只在
# 产出文件落地时由 set_output_status/set_output_referenced_mats 的 setdefault 惰性注册。
# 本表现在只剩一个职责：给 list_affected_outputs 提供"首次合成该产哪些"的 canonical
# 枚举源（outputs_state 为空 {} 时 union 进来，缺失 key 视作 ref=None → reason='new'，
# 与旧"预置槽"行为字节等价）。
# 这样既消除了"未开工却显示 pending primer/case"的死 slot 污染，又不丢首次合成枚举。
# 旧 8 维并列产出（01_business_panorama … 07_decision_kit）已随决策链重构退休、不在表内；
# 遗留 topic 仍可能带这些 key，list_affected_outputs 走 union 照旧处理、list_outputs
# 用 skip-if-absent 渲染，互不影响。
_DECISION_CHAIN_OUTPUTS = {
    "company": ["00_primer", "c_investment_case", "08_living_feed"],
    "industry": ["00_primer", "i_industry_case", "08_living_feed"],
    "arena": ["00_primer", "a_arena_case", "08_living_feed"],
}

_DEFAULT_OUTPUT_STATE = {
    "version": 0, "last_updated": None, "status": "pending", "data_freshness": None,
    # 04-synthesize 写入：本 output 上次合成时引用的 manifest mat_ids。
    # list_affected_outputs 据此判定有无新材料，决定是否要重写本 output。
    "referenced_mat_ids": None,
    # 单份产出失败时由 set_output_error 写入：{"at": iso_ts, "message": str}。
    # 成功调 set_output_referenced_mats 时会自动清空，做到"再跑一遍就抹掉错误"。
    "last_error": None,
}


_MARKET_PREFIXES = ("SSE", "SZSE", "BSE", "HKEX", "US", "NASDAQ", "NYSE")


def _infer_market(ticker: str, geo: str) -> str:
    """推断股票代码所属市场。

    优先级：显式前缀 > geo + 数字首位启发
    - HKEX_09995 → HKEX（修：原版会落入 SZSE 兜底）
    - SSE_688331 / SZSE_300073 → 直接用前缀
    - 裸数字 + geo=CN → 按首位推断 SSE/SZSE/BSE
    - 其他 → US
    """
    if not ticker:
        return ""
    if "_" in ticker:
        prefix, code = ticker.split("_", 1)
        if prefix in _MARKET_PREFIXES:
            return prefix
        ticker = code  # 不认识的前缀，剥离后走数字启发
    if geo != "CN":
        return "US"
    if ticker[:1] in ("6", "9", "5"):
        return "SSE"
    elif ticker[:1] in ("0", "3"):
        return "SZSE"
    elif ticker[:1] == "8":
        return "BSE"
    return "US"


_TICKER_RE = re.compile(r"^[A-Z]+_[A-Za-z0-9]+$")


def _validate_ticker(ticker: str, field: str = "ticker") -> None:
    """校验 ticker 格式 {EXCHANGE}_{CODE}。不区分 known/unknown exchange — 未知前缀走兜底。"""
    if not isinstance(ticker, str) or not _TICKER_RE.match(ticker):
        raise ValueError(
            f"{field} 格式必须是 '{{EXCHANGE}}_{{CODE}}'（如 'SSE_688331' / 'HKEX_09995' / 'US_AAPL'），得到: {ticker!r}"
        )


def _outputs_for_type(topic_type: str) -> list[str]:
    """create_topic 初始 seed 的 outputs_state key（决策链产出，修 F1）。

    未知 type 兜底只 seed 00_primer + 08_living_feed（最小活产出集）。
    """
    return _DECISION_CHAIN_OUTPUTS.get(topic_type, ["00_primer", "08_living_feed"])


def next_stage(topic_type: str, current_stage: str) -> str | None:
    if current_stage in ("done", "quarantined"):
        return None

    # reopen stage：thesis 升版后 reverse-check 发现 roadmap 漏 K#，回到补 material
    if current_stage == "01-roadmap-reopen":
        return "02-gather-materials"

    if topic_type in ("industry", "arena"):
        # 第 6 阶段统一 05-critic-review（与 company/default 同形）。industry/arena 的
        # 选拔/同行矩阵已并进 04 合成期 case 环⑥ + sidecar（属第 5 阶段产物，不是定稿动作）；
        # 唯一的定稿动作是 critic 评审，对 industry/arena 非强制——可在对话跑评审、或 web 点
        # 「完成」直接 done（见 app/routes/prism.py mark-done）。旧名 09-arena-shortlist /
        # 10-peer-matrix 已退休（曾破坏 SKILL stage 路由，见 _arena_funnel.md 收尾段）。
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "04-post-synthesis",
            "05-critic-review",
            "done",
        ]
    elif topic_type == "company":
        # 修 7: 04 后强制走 critic-review；verdict='approve' 才到 done
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "00-quality-screen",
            "04-synthesizing",
            "04-post-synthesis",
            "05-critic-review",
            "done",
        ]
    else:
        flow = [
            "00-init",
            "01-roadmap",
            "02-gather-materials",
            "03-extracting",
            "04-synthesizing",
            "04-post-synthesis",
            "05-critic-review",
            "done",
        ]

    try:
        idx = flow.index(current_stage)
        if idx + 1 < len(flow):
            return flow[idx + 1]
        return None
    except ValueError:
        for stage in flow:
            if stage > current_stage:
                return stage
        return None


# ── 阶段 → 读者向进度（单一事实源；index / variants / detail 三处共用）──────────
# 把流水线的细 stage 收敛成 7 个读者看得懂的大阶段，让人「一眼看出研究完成没 + 到哪了」，
# 替代曾经在数退休产出槽的 n/m 数字（那个分母是 outputs_state 残留的旧 8 维死 key，对读者零含义）。
# type-agnostic：三类 topic 第 6 阶段统一为 05-critic-review（评审）——company 必跑、
# industry/arena 可选（对话跑评审或 web 点完成均到 done）。进度条跨 type 对齐。
STAGE_PHASE_NAMES = ["立项", "规划", "收料", "抽取", "合成", "评审", "完成"]

# stage 串 → 大阶段序号（1..7）
_STAGE_PHASE_INDEX = {
    "00-init": 1,
    "01-roadmap": 2, "01-roadmap-pending": 2, "01-roadmap-reopen": 2,
    "02-gather-materials": 3,
    "03-extracting": 4, "00-quality-screen": 4,
    "04-synthesizing": 5, "04-synthesizing-done": 5, "04-post-synthesis": 5,
    "05-critic-review": 6,
    "done": 7,
}

# stage 串 → 读者向 label（精确到 stage，比大阶段名更具体；前端按 state 配色，不在此塞 emoji）
_STAGE_DISPLAY_LABEL = {
    "00-init": "未开工",
    "01-roadmap": "规划中", "01-roadmap-pending": "规划中", "01-roadmap-reopen": "规划补缺",
    "02-gather-materials": "收料中",
    "03-extracting": "抽取中", "00-quality-screen": "质量筛查",
    "04-synthesizing": "合成中", "04-synthesizing-done": "合成中", "04-post-synthesis": "合成收尾",
    "05-critic-review": "评审中",
    "done": "已完成", "quarantined": "已隔离",
}

# 未知 stage 兜底：按数字前缀尽力猜大阶段（猜不到=0）
_STAGE_PREFIX_GUESS = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 9: 6}


def stage_progress(stage: str | None) -> dict:
    """把 topic.stage 收敛成读者向进度。单一事实源，供 web 三处展示共用、纯函数、不抛。

    返回 {label, phase_index, total, state}：
      - label       读者向阶段名（如 '合成中' / '已完成'；emoji 由前端按 state 加）
      - phase_index 1..7 大阶段序号；空/未知=0
      - total       总大阶段数（=7）
      - state       'done' | 'in_progress' | 'not_started' | 'quarantined' | 'unknown'

    未知 stage 优雅降级：label=原 stage 串、state='unknown'、phase_index 按数字前缀尽力猜。
    """
    total = len(STAGE_PHASE_NAMES)
    s = (stage or "").strip()
    if not s:
        return {"label": "未开工", "phase_index": 0, "total": total, "state": "not_started"}
    if s == "quarantined":
        return {"label": "已隔离", "phase_index": 0, "total": total, "state": "quarantined"}
    if s == "done":
        return {"label": "已完成", "phase_index": total, "total": total, "state": "done"}
    if s == "00-init":
        return {"label": "未开工", "phase_index": 1, "total": total, "state": "not_started"}
    label = _STAGE_DISPLAY_LABEL.get(s)
    idx = _STAGE_PHASE_INDEX.get(s)
    if label is not None and idx is not None:
        return {"label": label, "phase_index": idx, "total": total, "state": "in_progress"}
    # 未知 stage：原串兜底 + 前缀猜阶段
    head = s.split("-", 1)[0]
    guess = _STAGE_PREFIX_GUESS.get(int(head), 0) if head.isdigit() else 0
    return {"label": s, "phase_index": guess, "total": total, "state": "unknown"}


def _topics_dir() -> Path:
    return PRISM_ROOT / "topics"


def _topic_path(slug: str, variant: str) -> Path:
    if not variant:
        raise ValueError("必须显式指定 variant，例如 'sonnet' 或 'qwen3.6-plus'")
    return _topics_dir() / slug / variant / "topic.yaml"


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_SEARCH_TERM_MAX_CHARS = 15
_SHORT_NAME_MAX_CHARS = 12
_LONG_QUESTION_THRESHOLD = 25


def _validate_search_terms(search_terms: list) -> None:
    """H3: search_terms 校验 — list[str]，每项 ≤15 字，至少非空 1 项。"""
    if not isinstance(search_terms, list):
        raise ValueError(f"search_terms 必须是 list[str]，得到: {search_terms!r}")
    cleaned = [s for s in search_terms if isinstance(s, str) and s.strip()]
    if not cleaned:
        raise ValueError(f"search_terms 不能全空，得到: {search_terms!r}")
    for s in cleaned:
        if len(s) > _SEARCH_TERM_MAX_CHARS:
            raise ValueError(
                f"search_terms 每项 ≤{_SEARCH_TERM_MAX_CHARS} 字（避免拼出来又超长），得到: {s!r} ({len(s)} 字)"
            )


def create_topic(
    slug: str,
    display_name: str,
    topic_type: str,
    question: str,
    geo: str,
    depth: str,
    variant: str,
    ticker: str | None = None,
    extra_tickers: list[str] | None = None,
    short_name: str | None = None,
    search_terms: list[str] | None = None,
    parent_topic: str | None = None,
    concepts: list[str] | None = None,
    monitoring_tier: str = "dormant",
) -> Path:
    """创建 topic.yaml。

    H1: company 类型必须传 ticker，否则 raise ValueError —— 避免 build_search_queries
        的 company-event 覆盖槽静默不生成。
    M1: extra_tickers 用于 AH 双重上市 / 多市场（如 [SSE_688331, HKEX_09995] 的 H 股部分；
        或 [HKEX_09988, US_BABA, NASDAQ_BABAF] 的 ADR 多重上市）。每项格式同 ticker。
        写入 scope.extra_tickers + scope.extra_markets（并行 list[str]，长度一致）。
    H3 (v2): display_name 用于 UI 展示（可长，含 ticker/英文名），short_name 用于
        WebSearch 查询（≤12 字，纯主体名）。company 类型必须传 short_name。
        例：display_name='荣昌生物 (RemeGen, SSE 688331)' / short_name='荣昌生物'
    H3 (v2): question >25 字时必须传 search_terms。脚本不做关键词提取
        （切到非关键名词反而误导）—— 让 LLM 在创建时显式提炼。
        例：question='荣昌生物 ADC+自免双管线 商业化兑现 BD 回流' → search_terms=
        ['ADC 商业化', 'BD 海外授权', 'IgAN 管线']
    """
    # 变体名归一：仅在创建新目录这一处做（绝不在 _topic_path 里做——会让读历史
    # opus4.8 目录全 FileNotFoundError）。映射发生则提示原→规范；未登记模型提示加表。
    _orig_variant = variant
    variant = model_registry.canonical(variant)
    if variant != _orig_variant:
        print(f"ℹ 变体名归一: {_orig_variant!r} → {variant!r}（model_registry 别名）",
              file=sys.stderr)
    elif not model_registry.is_known(variant):
        print(f"ℹ 变体 {variant!r} 未登记于 model_registry，建议加入以便父引用兜底"
              f"（命名参照表中已登记规范名，如 'opus4.8' / 'claude-opus-4-7'）", file=sys.stderr)
    if topic_type == "company" and not ticker:
        raise ValueError(
            "topic_type='company' 必须传 ticker (格式: '{EXCHANGE}_{CODE}'，如 'SSE_688331' / 'HKEX_09995' / 'US_AAPL'). "
            "后续 build_search_queries 的 company-event 覆盖槽依赖 ticker，漏传会静默缺失。"
        )
    if topic_type == "company" and not short_name:
        raise ValueError(
            "topic_type='company' 必须传 short_name (≤12 字，纯主体名，搜索查询用). "
            f"display_name={display_name!r} 含 ticker/英文名常超长，不能直接用于 WebSearch。"
            f"例：display_name='荣昌生物 (RemeGen, SSE 688331)' → short_name='荣昌生物'"
        )
    if ticker:
        _validate_ticker(ticker, field="ticker")
    if extra_tickers is not None:
        if not isinstance(extra_tickers, list):
            raise ValueError(f"extra_tickers 必须是 list[str]，得到: {extra_tickers!r}")
        for t in extra_tickers:
            _validate_ticker(t, field="extra_tickers item")
        if ticker and ticker in extra_tickers:
            raise ValueError(
                f"extra_tickers 不能包含主 ticker {ticker!r}（已在 scope.ticker），请去重"
            )
        if len(extra_tickers) != len(set(extra_tickers)):
            raise ValueError(f"extra_tickers 内部不能重复，得到: {extra_tickers!r}")
    if short_name is not None:
        if not isinstance(short_name, str) or not short_name.strip():
            raise ValueError(f"short_name 必须是非空 str，得到: {short_name!r}")
        if len(short_name) > _SHORT_NAME_MAX_CHARS:
            raise ValueError(
                f"short_name ≤{_SHORT_NAME_MAX_CHARS} 字（搜索友好），得到: {short_name!r} ({len(short_name)} 字)"
            )
    # 长 question 的 hard gate：脚本不做关键词提取
    if (question or "") and len((question or "").strip()) > _LONG_QUESTION_THRESHOLD and not search_terms:
        raise ValueError(
            f"scope.question 超 {_LONG_QUESTION_THRESHOLD} 字（{len(question)} 字）但 search_terms 未给。"
            f"脚本不会自动提炼关键词（切到非核心名词反而误导）。"
            f"请主 agent 从 question 中挑 2-4 个核心名词作 search_terms（每项 ≤{_SEARCH_TERM_MAX_CHARS} 字），"
            f"例：question='荣昌生物 ADC+自免双管线 商业化兑现 BD 回流' → search_terms=['ADC 商业化', 'BD 海外授权', 'IgAN 管线']"
        )
    if search_terms is not None and search_terms != []:
        _validate_search_terms(search_terms)

    path = _topic_path(slug, variant)
    if path.exists():
        raise FileExistsError(f"Topic already exists: {slug}/{variant}")
    # 下游兜底（[skill-routing]）：slug 已存在其他变体而本变体是新建时，打印 stderr
    # 提示——挡"跳过 00 Step 3 直奔 create_topic"时的盲建。不 raise（同 slug 新变体
    # 是合法复用路径），只把"这是个分叉点 + 有复用机会"从沉默变可见。
    existing_variants = list_variants(slug)
    if existing_variants:
        print(
            f"⚠ slug={slug!r} 已存在变体 {existing_variants}，你正在创建新变体 {variant!r}。"
            f"\n  确认不是想推进旧变体? 推进走 workflow（读 topic.yaml 判 stage），勿盲建空变体。"
            f"\n  若确为换模型/换架构重研：复用旧料按 00 Step 3 新变体分支（复用 materials 机械层、findings 本变体重抽、set_parent_materials 引父级），可隔离变量对比。",
            file=sys.stderr,
        )
    scope = {
        "geo": geo,
        "question": question,
        "depth": depth,
    }
    if ticker:
        scope["ticker"] = ticker
        scope["market"] = _infer_market(ticker, geo)
    if extra_tickers:
        scope["extra_tickers"] = list(extra_tickers)
        scope["extra_markets"] = [_infer_market(t, geo) for t in extra_tickers]
    if short_name:
        scope["short_name"] = short_name.strip()
    if search_terms:
        scope["search_terms"] = [s.strip() for s in search_terms if isinstance(s, str) and s.strip()]
    # 首个 variant 自动标 canonical（dashboard 默认展示用，避免靠迭代顺序赌）。
    # 已有其他 variant 时不抢——保持现 canonical 不动，新建的非 canonical 直到用户在
    # /prism/{slug} 页显式 set_canonical 才切换。
    is_first_variant = not existing_variants
    data = {
        "slug": slug,
        "display_name": display_name,
        "type": topic_type,
        "created": _now_iso(),
        "status": "active",
        "stage": "00-init",
        "canonical": is_first_variant,
        "parent_topic": parent_topic,
        "monitoring_tier": monitoring_tier,
        "concepts": concepts or [],
        "scope": scope,
        # file-first：建 topic 时不预置任何产出槽（空 {}）。产出落地时由
        # set_output_status / set_output_referenced_mats 的 setdefault 惰性注册，
        # 保证「有文件才有 outputs_state 条目」（消除"未开工却显示 pending"的死 slot）。
        # 首次合成"该产哪些"的枚举改由 list_affected_outputs 用 _outputs_for_type(type)
        # 补出 canonical 集——故 outputs_state 空 ≠ 无产出计划。
        "outputs_state": {},
        "parent_materials": [],
        "next_actions": ["运行 workflow 01-build-roadmap"],
        "user_todos": [],
        "monitoring": {"enabled": False, "cadence": "daily"},
    }
    _write_yaml(path, data)
    (path.parent / "outputs").mkdir(exist_ok=True)
    (path.parent.parent / "inbox").mkdir(exist_ok=True)
    return path


def read_topic(slug: str, variant: str) -> dict:
    path = _topic_path(slug, variant)
    if not path.exists():
        raise FileNotFoundError(f"Topic not found: {slug}/{variant}")
    data = _read_yaml(path)
    data.setdefault("parent_topic", None)
    data.setdefault("monitoring_tier", "dormant")
    data.setdefault("concepts", [])
    # 修 7: critic-review verdict 状态。set_critic_verdict 写入，next_stage 决定不依赖此字段
    # （verdict-驱动的跳转在 workflow 05 里用 set_stage 显式做）。
    data.setdefault("critic", None)
    # 命门拆解（B 层，镜像 thesis 结构）。旧 topic 无之 → 缺省空壳，graceful。
    data.setdefault("decomposition", {"current_version": None, "last_updated": None, "history": []})
    if "outputs_state" in data:
        for key, state in data["outputs_state"].items():
            state.setdefault("data_freshness", None)
            state.setdefault("referenced_mat_ids", None)
            state.setdefault("last_error", None)
    if "user_todos" in data and data["user_todos"]:
        try:
            data["user_todos"] = [_normalize_todo(t) for t in data["user_todos"]]
        except Exception:
            pass
    return data


def update_topic(slug: str, variant: str, **fields) -> None:
    data = read_topic(slug, variant)
    data.update(fields)
    _write_yaml(_topic_path(slug, variant), data)


def set_stage(slug: str, stage: str, variant: str) -> None:
    """切换 stage，并维护平行 stage_history（B1 承重墙，spec observability.md §4.1）。

    每次切换：① 回填上一条 history 的 exited_at；② append 新条目，盖 entered_at
    + 进入瞬间的 detect_gaps 精简快照。同 stage 幂等（不重复 append）。快照失败返回空
    不抛。向后兼容：旧 topic 无 stage_history → 视为空 list 起步，现有 `stage` str 不动。
    """
    from datetime import datetime, timezone
    data = read_topic(slug, variant)
    prev = data.get("stage")
    if prev == stage:
        update_topic(slug, variant, stage=stage)  # 同 stage：不动 history
        return
    hist = data.get("stage_history")
    if not isinstance(hist, list):
        hist = []
    now = datetime.now(timezone.utc).isoformat()
    if hist and hist[-1].get("exited_at") is None:
        hist[-1]["exited_at"] = now          # 回填上一条退出
    # 延迟 import 防循环（gap_detector imports topic）
    from prism.scripts.gap_detector import snapshot_gaps
    hist.append({
        "stage": stage,
        "entered_at": now,
        "exited_at": None,
        "gap_snapshot": snapshot_gaps(slug, variant),
    })
    update_topic(slug, variant, stage=stage, stage_history=hist)


def set_canonical(slug: str, variant: str) -> None:
    """把 slug 下指定 variant 标为 canonical，同 slug 其他 variant 自动清掉。

    dashboard / monitor 通过 _canonical_variant 读这个字段决定展示哪个 variant 的结论。
    每个 slug 必须恰好有一个 canonical（_canonical_variant 兜底逻辑能容忍 0 个，
    但显式标定是主路径）。
    """
    if not _topic_path(slug, variant).exists():
        raise FileNotFoundError(f"Topic not found: {slug}/{variant}")
    for v in list_variants(slug):
        data = _read_yaml(_topic_path(slug, v))
        new_val = (v == variant)
        if data.get("canonical") != new_val:
            data["canonical"] = new_val
            _write_yaml(_topic_path(slug, v), data)


# F17: primer 深度软门禁阈值。depth=deep 的正文字数下限——参照级 primer ~9000+ 字，
# from-zero 赶进度跑出的 outline ~1800 字。取 6000 作保守地板，挡 outline 假冒 deep。
_PRIMER_DEEP_MIN_CHARS = 6000


def primer_quality_gate(slug: str, variant: str) -> dict:
    """机械检查 00_primer 是否真够 depth=deep（零 LLM，修 F17）。

    检查项：depth（frontmatter 自报）/ char_count（正文字数）/ has_controversy（争议节）
    / has_selfcheck（自检节）/ critic_passed（机械 flag，由 set_output_critic_passed 置位）。
    ok 规则：depth=deep → 四项全过才 ok；depth=shallow / 无 → ok=True（诚实标浅不设地板）。
    供 set_output_status('00_primer','fresh') 软门禁用：deep 但 ok=False → 降级 'draft'。
    """
    primer = PRISM_ROOT / "topics" / slug / variant / "outputs" / "00_primer.md"
    out = {"depth": None, "char_count": 0, "has_controversy": False,
           "has_selfcheck": False, "critic_passed": False, "ok": True, "warnings": []}
    if not primer.exists():
        out["ok"] = False
        out["warnings"].append("00_primer.md 不存在")
        return out
    raw = primer.read_text(encoding="utf-8")
    body = raw
    depth = None
    if raw.startswith("---"):
        end = raw.find("---", 3)
        if end > 0:
            try:
                depth = (yaml.safe_load(raw[3:end]) or {}).get("depth")
            except Exception:
                depth = None
            body = raw[end + 3:]
    out["depth"] = depth
    out["char_count"] = len(body)
    out["has_controversy"] = "争议" in body
    out["has_selfcheck"] = ("自检" in body) or ("自测" in body)
    try:
        st = (read_topic(slug, variant).get("outputs_state") or {}).get("00_primer") or {}
        out["critic_passed"] = bool(st.get("critic_passed"))
    except Exception:
        out["critic_passed"] = False
    if depth == "deep":
        if out["char_count"] < _PRIMER_DEEP_MIN_CHARS:
            out["warnings"].append(
                f"正文 {out['char_count']} 字 < deep 地板 {_PRIMER_DEEP_MIN_CHARS}")
        if not out["has_controversy"]:
            out["warnings"].append("缺争议节（写作硬规约要求 5-7 条根本争议）")
        if not out["has_selfcheck"]:
            out["warnings"].append("缺自检清单节")
        if not out["critic_passed"]:
            out["warnings"].append("未过 critic（set_output_critic_passed 未置位）")
        out["ok"] = not out["warnings"]
    return out


def set_output_critic_passed(slug: str, variant: str, output_key: str) -> None:
    """机械标记某 output 已过独立 critic（修 F17）。primer Step 3 critic 收敛后**先调本函数**，
    再调 set_output_status(fresh)——否则 depth=deep 的 primer 会被门禁降级 draft。"""
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["critic_passed"] = True
    entry["last_updated"] = _now_iso()
    _write_yaml(_topic_path(slug, variant), data)


def set_output_status(slug: str, output_key: str, status: str, variant: str, version: int | None = None) -> None:
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["status"] = status
    entry["last_updated"] = _now_iso()
    if version is not None:
        entry["version"] = version
    # F17 软门禁：仅 00_primer 标 fresh 时，自报 depth=deep 但机械检查不过 → 降级 'draft'
    # + 记 primer_gate 摘要。其余 output_key / status 路径字节不变（零回归）。
    if output_key == "00_primer" and status == "fresh":
        gate = primer_quality_gate(slug, variant)
        if gate.get("depth") == "deep" and not gate.get("ok"):
            entry["status"] = "draft"
            entry["primer_gate"] = {
                "downgraded_from": "fresh",
                "checked_at": _now_iso(),
                "warnings": gate["warnings"],
            }
    _write_yaml(_topic_path(slug, variant), data)


def set_output_referenced_mats(slug: str, output_key: str, mat_ids: list[str], variant: str) -> None:
    """记录某 output 本次合成所引用的 manifest mat_ids（去重排序）。
    04-synthesize 写完一份 output 后调用，让下次跑 list_affected_outputs 能判定增量。
    成功调用会清空 last_error——再跑一遍即抹掉之前的失败记录。
    同时把 status 从 'stale' 抹回 'fresh'——闭环 critic verdict='request-rewrite'
    路径（修 H1：避免 critic 标 stale 后即使 04 已重写，list_affected_outputs
    仍报 critic-stale 死循环）。
    """
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["referenced_mat_ids"] = sorted(set(mat_ids))
    entry["last_updated"] = _now_iso()
    entry["last_error"] = None
    if entry.get("status") == "stale":
        entry["status"] = "fresh"
    _write_yaml(_topic_path(slug, variant), data)
    _trigger_dashboard(slug, variant, f"output={output_key}")


def set_output_error(slug: str, output_key: str, message: str, variant: str) -> None:
    """标记某 output 本次合成失败。04-synthesize 单份产出 except 时调用，
    让其余 10 份继续跑（修 9: workflow resume）。下次再跑该 output 成功后
    set_output_referenced_mats 会清空此字段。
    """
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["last_error"] = {"at": _now_iso(), "message": str(message)[:500]}
    _write_yaml(_topic_path(slug, variant), data)


def list_failed_outputs(slug: str, variant: str) -> list[dict]:
    """返回所有有 last_error 的 output（用于"哪些产出需要重跑"）。"""
    data = read_topic(slug, variant)
    out = []
    for key, state in (data.get("outputs_state") or {}).items():
        err = state.get("last_error")
        if err:
            out.append({"output_key": key, "last_error": err})
    return out


_VALID_CRITIC_VERDICTS = ("approve", "request-rewrite", "request-more")


def _trigger_dashboard(slug: str, variant: str, reason: str) -> None:
    """关键节点后异步重建 dashboard（修 S5）—— fire-and-forget subprocess。

    挂载点（仅这几处，避免每个 set_stage 都触发）：
      - set_critic_verdict（任何 verdict）
      - set_thesis（升版）
      - set_output_referenced_mats（每份产出收尾，覆盖 04/09/10）

    用 subprocess + start_new_session 真正脱离主进程——dashboard 跑 ~25s 行情拉取
    不能让 set_critic_verdict 阻塞主对话。失败仅 stderr 留痕，不阻塞、不写 todo
    （fire-and-forget 模式下无法捕获 exit code）。
    """
    import os
    import subprocess
    import sys

    log_dir = PRISM_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "dashboard_auto.log"
    try:
        with open(log_path, "ab") as fout:
            fout.write(f"\n--- {_now_iso()} triggered by {reason} ({slug}/{variant}) ---\n".encode())
            subprocess.Popen(
                [sys.executable, "-m", "prism.scripts.dashboard"],
                stdout=fout, stderr=subprocess.STDOUT,
                cwd=str(PRISM_ROOT.parent),
                start_new_session=True,
                close_fds=True,
                env={**os.environ, "PRISM_DASHBOARD_AUTO": "1"},
            )
    except Exception:
        # 真不能再 raise——主流程不应被 dashboard 触发逻辑搞挂
        pass


def set_critic_verdict(
    slug: str,
    variant: str,
    verdict: str,
    summary: str = "",
    thesis_version: int | None = None,
    rewrite_keys: list[str] | None = None,
) -> dict:
    """workflow 05-critic-review Step 7 调用。记录评审结论 + 自动按 verdict 跳转 stage
    + 写默认 next_actions（修 S4：原 workflow 05 Step 7 大段模板化脚本下沉到此函数）。

    verdict:
      - 'approve'         → set_stage('done')      研究完结，可进 06-daily-monitor
      - 'request-rewrite' → set_stage('04-synthesizing')  04 部分 output 需要重写
                            额外 rewrite_keys（list[str]）会被同步 set_output_status('stale')
      - 'request-more'    → set_stage('02-gather-materials')  缺 material，回 02

    summary 会被嵌入 next_actions 作为可读理由。主 agent 仍可在本函数返回后再 append todo。
    返回写入的 critic dict（含 next_stage 字段供主 agent 汇报）。
    """
    if verdict not in _VALID_CRITIC_VERDICTS:
        raise ValueError(
            f"Invalid verdict: {verdict!r}. Must be one of {_VALID_CRITIC_VERDICTS}"
        )
    data = read_topic(slug, variant)
    critic = {
        "verdict": verdict,
        "summary": summary,
        "at": _now_iso(),
        "thesis_version": thesis_version,
    }
    next_st = {
        "approve": "done",
        "request-rewrite": "04-synthesizing",
        "request-more": "02-gather-materials",
    }[verdict]
    critic["next_stage"] = next_st
    data["critic"] = critic
    data["stage"] = next_st

    summary_line = f"critic 评审：{summary}" if summary else "critic 评审完成"
    if verdict == "approve":
        ver_tag = f"thesis_v{thesis_version} 已通过 critic-review" if thesis_version is not None else "thesis 已通过 critic-review"
        data["next_actions"] = [
            "研究主题已闭环，下一步「监控 {slug}」启动 06-daily-monitor".replace("{slug}", slug),
            ver_tag,
            summary_line,
        ]
    elif verdict == "request-rewrite":
        keys_str = ", ".join(rewrite_keys or []) or "（主 agent 未提供 rewrite_keys）"
        data["next_actions"] = [
            f"critic 标 stale: {keys_str}",
            "主 agent 即将在本对话续跑 04（见 workflow 05 Step 7.5）",
            summary_line,
        ]
        # 同步把 rewrite_keys 标 stale，让 04 _shared.md 走 critic-stale 路径
        for ok in rewrite_keys or []:
            entry = data["outputs_state"].setdefault(ok, dict(_DEFAULT_OUTPUT_STATE))
            entry["status"] = "stale"
            entry["last_updated"] = _now_iso()
    else:  # request-more
        data["next_actions"] = [
            f"说「prism 推进 {slug}」回到 02-gather-materials，先跑 web-search prescan",
            summary_line,
        ]

    _write_yaml(_topic_path(slug, variant), data)
    _trigger_dashboard(slug, variant, f"critic-verdict={verdict}")
    return critic


def get_critic_verdict(slug: str, variant: str) -> dict | None:
    """返回当前 critic 状态；未评审过返回 None。"""
    return read_topic(slug, variant).get("critic")


def set_next_actions(
    slug: str,
    actions: list[str],
    variant: str,
    prescan_status: str | None = None,
    prescan_failure_reason: str | None = None,
) -> None:
    """更新 next_actions。

    ISSUE-001：当 prescan_status='failed' 时，自动 prepend 一条警示 action，
    迫使主 agent 在推进下一步前显式决策"补 prescan 还是接受 failed"。
    其余 prescan_status（None / 'full' / 'partial'）行为不变（不修改 actions）。
    """
    final_actions = list(actions)
    if prescan_status == "failed":
        reason = prescan_failure_reason or "未知（疑似 WebSearch 限流或区域阻断）"
        warning = (
            f"⚠️  prescan FAILED (reason: {reason}) — 推进 workflow 01 前必须二选一: "
            f"(a) 手工 prescan：用户另设备搜索 baseline 第五节优先 query 并粘贴结果给主 agent 入库；"
            f"(b) 接受 failed prescan：thesis 中 time_sensitivity=快变 的 fact 全部降级 uncertain，"
            f"K# 攻打 todo 优先级 P0 升级；workflow 05 critic-review 必须 block 04-synthesize 至用户复决"
        )
        if not final_actions or not final_actions[0].startswith("⚠️  prescan FAILED"):
            final_actions = [warning] + final_actions
    update_topic(slug, variant, next_actions=final_actions)


_VALID_INFO_TIERS = ("public", "half_public", "hard")
_VALID_PRIORITIES = ("P0", "P1", "P2")
_VALID_TODO_STATUSES = ("pending", "in_progress", "done")

# 自动获取覆盖规约（auto-fetch 规约）状态位：
#  - fetch_status：机械层"尝试的真实结果"。unattempted=从没试过（默认，R3 消费前必须先试）；
#    fetched=抓到材料已入库；empty=有效尝试过但公开确实没有（触发用户决策，不静默跳过）；
#    error=工具/网络/限流失败（必须重试，永不据此降级为 user_todo）。
#  - disposition：仅 fetch_status='empty' 时有意义，记录用户对"公开抓不到"的处置。
#    undecided=尚未决定（默认，硬闸门：阻塞合成）；waived=用户选跳过（合成写诚实缺口）；
#    will_collect=用户选我来收（合成写待补料显式缺口，材料到位后 auto_resolve 翻 fetched）。
_VALID_FETCH_STATUSES = ("unattempted", "fetched", "empty", "error")
_VALID_DISPOSITIONS = ("undecided", "waived", "will_collect")

# address 格式: 裸 'K1' 或带事件锚 'K1@2026Q2-earnings'。事件锚解决 K# 粒度过粗问题
# （参 feedback_addresses_granularity）。匹配规则：
#  - todo address 裸 'K1' → 任何同 key 的 mat address 都覆盖（向后兼容）
#  - todo address 'K1@evt' → mat address 必须也是 'K1@evt' 才覆盖（严格事件匹配）
#  - mat  address 'K1@evt' 仅覆盖同事件的 todo；裸 K1 todo 仍接受（视为通配）
_ADDR_RE = re.compile(r"^[KQ]\d+(@[A-Za-z0-9_\-]+)?$")


def _addr_key(addr: str) -> str:
    """提取 address 的 K#/Q# 部分（去掉 @event 后缀）。"""
    return addr.split("@", 1)[0] if isinstance(addr, str) else ""


def _addr_event(addr: str) -> str | None:
    """提取 address 的 @event 部分；裸 K# 返回 None。"""
    if isinstance(addr, str) and "@" in addr:
        return addr.split("@", 1)[1]
    return None


def addresses_match(todo_addrs: list[str], mat_addrs: list[str]) -> bool:
    """判定 mat 是否覆盖 todo 的某个 address。规则见 _ADDR_RE 注释。

    返回 True 当且仅当存在 (t, m) ∈ todo×mat 满足：
      key(t) == key(m) 且 (event(t) is None 或 event(t) == event(m))
    """
    for t in todo_addrs or []:
        tk, te = _addr_key(t), _addr_event(t)
        if not tk:
            continue
        for m in mat_addrs or []:
            mk, me = _addr_key(m), _addr_event(m)
            if tk != mk:
                continue
            if te is None or te == me:
                return True
    return False


def addresses_match_event_anchored(todo_addrs: list[str], mat_addrs: list[str]) -> bool:
    """强命中：todo 带 @event 锚且 mat 同 key 同 event 才 True。

    裸 K# todo（无事件锚）一律 False。用于 hard/half_public 深料 todo 的闭环判定——
    堵"任一 K# web 命中假闭环深料"（专家访谈/镜鉴/地缘）的假阳性（修 F9）。
    """
    for t in todo_addrs or []:
        tk, te = _addr_key(t), _addr_event(t)
        if not tk or te is None:
            continue
        for m in mat_addrs or []:
            if tk == _addr_key(m) and te == _addr_event(m):
                return True
    return False


def _normalize_todo(item) -> dict:
    """接受 str 或 dict，规范化为统一 schema。

    str → {task: str, info_tier: 'public', priority: 'P1', addresses: [], status: 'pending'}
    dict → 校验字段，缺省值补全
    可选扩展字段：covered_by (list[mat_id])、coverage_note (str)
    """
    if isinstance(item, str):
        return {
            "task": item,
            "priority": "P1",
            "info_tier": "public",
            "addresses": [],
            "source_hint": "",
            "status": "pending",
            "fetch_status": "unattempted",
            "fetch_attempts": 0,
            "disposition": "undecided",
        }
    if not isinstance(item, dict) or "task" not in item:
        raise ValueError(f"todo 必须是 str 或含 task 字段的 dict，得到: {item!r}")
    tier = item.get("info_tier", "public")
    if tier not in _VALID_INFO_TIERS:
        raise ValueError(f"info_tier 必须是 {_VALID_INFO_TIERS}，得到: {tier!r}")
    priority = item.get("priority", "P1")
    if priority not in _VALID_PRIORITIES:
        raise ValueError(f"priority 必须是 {_VALID_PRIORITIES}，得到: {priority!r}")
    status = item.get("status", "pending")
    if status not in _VALID_TODO_STATUSES:
        raise ValueError(f"status 必须是 {_VALID_TODO_STATUSES}，得到: {status!r}")
    fetch_status = item.get("fetch_status", "unattempted")
    if fetch_status not in _VALID_FETCH_STATUSES:
        raise ValueError(f"fetch_status 必须是 {_VALID_FETCH_STATUSES}，得到: {fetch_status!r}")
    fetch_attempts = item.get("fetch_attempts", 0)
    if not isinstance(fetch_attempts, int) or fetch_attempts < 0:
        raise ValueError(f"fetch_attempts 必须是非负 int，得到: {fetch_attempts!r}")
    disposition = item.get("disposition", "undecided")
    if disposition not in _VALID_DISPOSITIONS:
        raise ValueError(f"disposition 必须是 {_VALID_DISPOSITIONS}，得到: {disposition!r}")
    addresses = item.get("addresses", [])
    if not isinstance(addresses, list):
        raise ValueError(f"addresses 必须是 list，得到: {addresses!r}")
    for a in addresses:
        if not isinstance(a, str) or not _ADDR_RE.match(a):
            raise ValueError(
                f"address 格式必须是 'K#' / 'Q#' 或 'K#@event-slug'（event-slug ∈ [A-Za-z0-9_-]），得到: {a!r}"
            )
    out = {
        "task": item["task"],
        "priority": priority,
        "info_tier": tier,
        "addresses": addresses,
        "source_hint": item.get("source_hint", ""),
        "status": status,
        "fetch_status": fetch_status,
        "fetch_attempts": fetch_attempts,
        "disposition": disposition,
    }
    covered_by = item.get("covered_by")
    if covered_by:
        if not isinstance(covered_by, list):
            raise ValueError(f"covered_by 必须是 list[str]，得到: {covered_by!r}")
        out["covered_by"] = list(covered_by)
    coverage_note = item.get("coverage_note")
    if coverage_note:
        out["coverage_note"] = str(coverage_note)
    archive_candidate = item.get("archive_candidate")
    if archive_candidate:
        out["archive_candidate"] = str(archive_candidate)
    last_fetch_note = item.get("last_fetch_note")
    if last_fetch_note:
        out["last_fetch_note"] = str(last_fetch_note)
    disposition_note = item.get("disposition_note")
    if disposition_note:
        out["disposition_note"] = str(disposition_note)
    return out


def _resolve_todos_against_materials(slug: str, variant: str, todos: list[dict]) -> bool:
    """对 todos 列表中的 pending 项，检查 manifest 已有 materials 是否覆盖。

    闭环逻辑与 web_prescan.auto_resolve_todos 一致（修 F9）：
      - public：K# 命中即 status=done
      - hard/half_public：仅事件锚强命中才 done，裸 K# 命中只标 in_progress

    就地修改 todos 列表（不创建副本）。返回 True 如果有修改。
    """
    from prism.scripts.manifest import read_manifest

    try:
        manifest = read_manifest(slug, variant)
    except (FileNotFoundError, Exception):
        return False

    # 建 mat_id → addresses 映射
    mat_addr_map: dict[str, list[str]] = {}
    for m in manifest.get("materials") or []:
        addrs = m.get("addresses") or []
        if addrs:
            mat_addr_map[m["id"]] = addrs

    if not mat_addr_map:
        return False

    dirty = False
    for todo in todos:
        if not isinstance(todo, dict):
            continue
        if todo.get("status") in ("done", "in_progress"):
            continue
        if "reverse-check" in (todo.get("source_hint") or ""):
            continue
        todo_addrs = todo.get("addresses") or []
        if not todo_addrs:
            continue

        matched = [
            mid for mid, addrs in mat_addr_map.items()
            if addresses_match(todo_addrs, addrs)
        ]
        if not matched:
            continue

        existing = set(todo.get("covered_by") or [])
        todo["covered_by"] = sorted(existing | set(matched))
        dirty = True

        tier = todo.get("info_tier", "public")
        strong = tier == "public" or any(
            addresses_match_event_anchored(todo_addrs, mat_addr_map[mid])
            for mid in matched
        )
        # 材料命中即视为抓取义务已了（auto-fetch 规约）：R3 不再重抓此 todo
        todo["fetch_status"] = "fetched"
        if strong:
            todo["status"] = "done"
            todo["coverage_note"] = f"已由 materials {', '.join(matched[:3])} 覆盖"
        else:
            todo["status"] = "in_progress"
            todo["coverage_note"] = (
                f"materials {', '.join(matched[:3])} 命中 K# 但无事件锚；"
                f"{tier} 深料需事件锚或同 source_type 材料才闭环"
            )

    return dirty


def set_user_todos(slug: str, todos: list, variant: str, *, _skip_resolve: bool = False) -> None:
    """全量覆写 user_todos。接受 list[str | dict]，每项规范化为统一 schema 后写入。

    保护（修 H2）：若 yaml 现有 todos 里**有**任何 addresses 非空的结构化项，
    且本次传入的 todos 全部 addresses 为空（包括 str），raise ValueError——
    强迫调用方走 `append_user_todos`（增量追加）或显式传完整 dict 列表。
    这条规则不影响 00/01 初始化（yaml 里无结构化 todos 时不触发）。

    _skip_resolve：内部参数，auto_resolve_todos 调用时传 True 避免重复 resolve。
    """
    normalized = [_normalize_todo(t) for t in todos]
    try:
        existing = read_topic(slug, variant).get("user_todos", []) or []
    except FileNotFoundError:
        existing = []
    existing_has_structured = any(
        isinstance(t, dict) and t.get("addresses") for t in existing
    )
    new_has_structured = any(t.get("addresses") for t in normalized)
    if existing_has_structured and not new_has_structured:
        raise ValueError(
            "set_user_todos 拒绝全量覆写：yaml 现有结构化 todos（含 addresses），"
            "但本次传入项 addresses 全空。请改用 append_user_todos(slug, todos, variant) "
            "增量追加，或传完整 dict 列表保留 addresses。"
        )

    # 写入前自动 resolve：新 todo 匹配已有 materials 则标 done（修：todo 后建导致假 pending）
    if not _skip_resolve:
        _resolve_todos_against_materials(slug, variant, normalized)

    update_topic(slug, variant, user_todos=normalized)


def append_user_todos(slug: str, todos: list, variant: str) -> None:
    """追加 user_todos（按 task 字符串去重），不覆写老 todos。

    新增项可以是 str（无 addresses 占位）或 dict（结构化）。
    若 task 与现有 todo 重复，跳过该项（保留老的）。
    用于 03/04/05 等"中间 stage"想加一条提示但不能动 01/02 结构化字段的场景。

    写入前自动 resolve：新 todo 匹配已有 materials 则标 done（修：todo 后建导致假 pending）。
    """
    try:
        existing = read_topic(slug, variant).get("user_todos", []) or []
    except FileNotFoundError:
        existing = []
    existing_tasks = {t["task"] for t in existing if isinstance(t, dict) and "task" in t}
    new_normalized = [_normalize_todo(t) for t in todos]
    fresh = [t for t in new_normalized if t["task"] not in existing_tasks]
    if not fresh:
        return

    # 写入前自动 resolve：新 todo 匹配已有 materials 则标 done（修：todo 后建导致假 pending）
    _resolve_todos_against_materials(slug, variant, fresh)

    update_topic(slug, variant, user_todos=existing + fresh)


def thesis_coverage(slug: str, variant: str, expected_keys: list[str]) -> dict:
    """对给定的一组期望 keys（如 K1..K5），统计每个 key 被多少 todo 攻打。

    返回：{
        'by_key': {'K1': [todo, ...], 'K2': [], ...},  # 每个 key 对应的 todo 列表（按出现顺序）
        'uncovered': ['K3', 'K5'],                      # 没有任何 todo 引用的 key
        'covered': ['K1', 'K2', 'K4'],
        'coverage_pct': 60,
    }
    """
    data = read_topic(slug, variant)
    todos = data.get("user_todos", []) or []
    by_key: dict[str, list] = {k: [] for k in expected_keys}
    for t in todos:
        if not isinstance(t, dict):
            continue
        # 支持 K1 和 K1@event 两种格式：都映射回 K1 桶
        for addr in t.get("addresses", []) or []:
            k = _addr_key(addr)
            if k in by_key:
                by_key[k].append(t)
    uncovered = [k for k in expected_keys if not by_key[k]]
    covered = [k for k in expected_keys if by_key[k]]
    pct = round(100 * len(covered) / len(expected_keys)) if expected_keys else 0
    return {
        "by_key": by_key,
        "uncovered": uncovered,
        "covered": covered,
        "coverage_pct": pct,
    }


def update_user_todo_status(
    slug: str,
    variant: str,
    task_substring: str,
    status: str,
    covered_by: list[str] | None = None,
    coverage_note: str | None = None,
) -> None:
    """根据 task 字段子串匹配，更新对应 todo 的 status。

    可选参数：
      covered_by: 追加到 todo.covered_by 的 material id 列表（去重合并）
      coverage_note: 覆盖原 coverage_note；常用于 web-search 自动覆盖说明
    """
    if status not in _VALID_TODO_STATUSES:
        raise ValueError(f"status 必须是 {_VALID_TODO_STATUSES}")
    data = read_topic(slug, variant)
    todos = data.get("user_todos", [])
    hit = False
    for t in todos:
        if isinstance(t, dict) and task_substring in t.get("task", ""):
            t["status"] = status
            if covered_by:
                existing = set(t.get("covered_by") or [])
                t["covered_by"] = sorted(existing | set(covered_by))
            if coverage_note:
                t["coverage_note"] = coverage_note
            hit = True
    if not hit:
        raise ValueError(f"未找到包含 {task_substring!r} 的 todo")
    update_topic(slug, variant, user_todos=todos)


def mark_todo_fetch(
    slug: str,
    variant: str,
    task_substring: str,
    fetch_status: str,
    note: str | None = None,
    increment_attempts: bool = True,
) -> None:
    """auto-fetch 规约：盖一条 todo 的尝试结果（fetch_status）。子串匹配 task。

    fetch_status ∈ _VALID_FETCH_STATUSES：
      fetched=抓到入库 / empty=有效尝试但公开无源 / error=工具网络失败需重试 / unattempted=回退。
    increment_attempts=True 时 fetch_attempts+1（仅在确实又跑了一次尝试时传 True）。
    note 写入 last_fetch_note。无匹配 raise。
    """
    if fetch_status not in _VALID_FETCH_STATUSES:
        raise ValueError(f"fetch_status 必须是 {_VALID_FETCH_STATUSES}，得到: {fetch_status!r}")
    data = read_topic(slug, variant)
    todos = data.get("user_todos", [])
    hit = False
    for t in todos:
        if isinstance(t, dict) and task_substring in t.get("task", ""):
            t["fetch_status"] = fetch_status
            if increment_attempts:
                t["fetch_attempts"] = int(t.get("fetch_attempts", 0) or 0) + 1
            if note:
                t["last_fetch_note"] = note
            hit = True
    if not hit:
        raise ValueError(f"未找到包含 {task_substring!r} 的 todo")
    update_topic(slug, variant, user_todos=todos)


def set_todo_disposition(
    slug: str,
    variant: str,
    task_substring: str,
    disposition: str,
    note: str | None = None,
) -> None:
    """auto-fetch 规约：记录用户对 empty todo 的处置。empty 硬闸门 AskUserQuestion 后调用。

    disposition ∈ _VALID_DISPOSITIONS：
      waived=用户选跳过（合成写诚实缺口）/ will_collect=我来收（合成写待补料显式缺口）。
    note 写入 disposition_note（理由）。无匹配 raise。
    """
    if disposition not in _VALID_DISPOSITIONS:
        raise ValueError(f"disposition 必须是 {_VALID_DISPOSITIONS}，得到: {disposition!r}")
    data = read_topic(slug, variant)
    todos = data.get("user_todos", [])
    hit = False
    for t in todos:
        if isinstance(t, dict) and task_substring in t.get("task", ""):
            t["disposition"] = disposition
            if note:
                t["disposition_note"] = note
            hit = True
    if not hit:
        raise ValueError(f"未找到包含 {task_substring!r} 的 todo")
    update_topic(slug, variant, user_todos=todos)


def pending_unfetched_todos(slug: str, variant: str) -> list[dict]:
    """auto-fetch 规约 R3：返回仍欠一次有效尝试的 active todo。

    条件：status∈{pending,in_progress} 且 fetch_status∈{unattempted,error}；
    排除 reverse-check（'补 roadmap' 语义、非可抓缺口，与 _resolve 一致）。
    01/02/03/04 统一调用此清单决定"还要抓什么 / 重试什么"。
    """
    try:
        todos = read_topic(slug, variant).get("user_todos", []) or []
    except FileNotFoundError:
        return []
    out = []
    for t in todos:
        if not isinstance(t, dict):
            continue
        if t.get("status") not in ("pending", "in_progress"):
            continue
        if "reverse-check" in (t.get("source_hint") or ""):
            continue
        if t.get("fetch_status", "unattempted") in ("unattempted", "error"):
            out.append(t)
    return out


def empty_undecided_todos(slug: str, variant: str) -> list[dict]:
    """auto-fetch 规约 empty 硬闸门：返回自动抓已确认公开无源、但用户尚未处置的 todo。

    条件：status∈{pending,in_progress} 且 fetch_status='empty' 且 disposition='undecided'。
    合成前与逐环 R3 都查它——非空必须 AskUserQuestion 让用户逐条选 waived/will_collect，
    否则不得进决策链、不得写缺口（反静默核心）。
    """
    try:
        todos = read_topic(slug, variant).get("user_todos", []) or []
    except FileNotFoundError:
        return []
    out = []
    for t in todos:
        if not isinstance(t, dict):
            continue
        if t.get("status") not in ("pending", "in_progress"):
            continue
        if t.get("fetch_status") == "empty" and t.get("disposition", "undecided") == "undecided":
            out.append(t)
    return out


def set_concepts(slug: str, concepts: list[str], variant: str) -> None:
    update_topic(slug, variant, concepts=concepts)


def set_monitoring_tier(slug: str, tier: str, variant: str) -> None:
    """设 monitoring_tier，并联动 monitoring.enabled（tier!=dormant ⇒ enabled=True）。

    历史上 monitoring_tier（顶层）与 monitoring.enabled（嵌套）各写各的，
    daily-monitor 接线后两者必须一致——否则 tier=deep 但 enabled=false 会让
    调度逻辑与展示打架。这里一次写齐。
    """
    if tier not in ("deep", "watch", "dormant"):
        raise ValueError(f"Invalid tier: {tier}, must be deep/watch/dormant")
    data = read_topic(slug, variant)
    monitoring = data.get("monitoring") or {}
    monitoring["enabled"] = tier != "dormant"
    update_topic(slug, variant, monitoring_tier=tier, monitoring=monitoring)


def set_monitoring_reviewed(slug: str, variant: str, ts: str | None = None) -> None:
    """记录 monitoring.last_reviewed=巡检时间戳。零 LLM。

    industry/arena 的 upgrade_triggers/monitor_metrics 无具体日期，靠"距上次巡检
    >= recency"做周期重扫；本字段就是那个"上次"。ts 省略则取当前 UTC。
    """
    data = read_topic(slug, variant)
    monitoring = data.get("monitoring") or {}
    monitoring["last_reviewed"] = ts or _now_iso()
    update_topic(slug, variant, monitoring=monitoring)


def set_pending_thesis_review(
    slug: str,
    variant: str,
    *,
    reason: str,
    proposal_id: str | None = None,
    locator: str | None = None,
    since: str | None = None,
) -> dict:
    """盖戳:本 topic 有一条已确认的重大监控翻牌(kill 触发 / signpost 翻 bear)
    尚未经 04/05 消化。零 LLM。由 monitor.confirm_flip 在 requires_thesis_review
    的 proposal 确认后调用。

    多次破位覆盖式更新 since(取最新确认时间)——一次 04/05 评审能消化截至其
    时间戳的全部破位。是否"已消化"不在这里判,靠 get_pending_thesis_review 渲染时
    比对 critic.at / thesis.last_updated 自动判定,故横幅会在跑过 04/05 后自动消失。
    """
    marker = {
        "since": since or _now_iso(),
        "reason": reason,
        "proposal_id": proposal_id,
        "locator": locator,
    }
    update_topic(slug, variant, pending_thesis_review=marker)
    return marker


def pending_review_unresolved(topic_data: dict) -> dict | None:
    """纯函数:给一份 topic.yaml dict,返回未消化的重大变更戳;若破位确认后已跑过
    04(thesis.last_updated 更新)或 05(critic.at 更新)则视为已消化,返回 None。

    无 I/O——供 get_pending_thesis_review(按 slug 读盘后调)和 web 各 chip 渲染共用
    (列表/树/变体页已持有完整 topic.yaml dict,免再读盘)。时间戳均 topic._now_iso()
    同格式 ISO-8601,可直接字典序比较。
    """
    marker = (topic_data or {}).get("pending_thesis_review")
    if not marker or not marker.get("since"):
        return None
    since = marker["since"]
    critic_at = (topic_data.get("critic") or {}).get("at")
    thesis_updated = (topic_data.get("thesis") or {}).get("last_updated")
    for ts in (critic_at, thesis_updated):
        if ts and ts > since:
            return None  # 破位确认后已有一次 04/05 → 已消化
    return marker


def get_pending_thesis_review(slug: str, variant: str) -> dict | None:
    """返回未消化的重大变更戳(按 slug/variant 读盘 → pending_review_unresolved)。
    纯读判定不写盘——横幅/chip 自动消失,无需手动 dismiss。
    """
    return pending_review_unresolved(read_topic(slug, variant))


def clear_pending_thesis_review(slug: str, variant: str) -> None:
    """显式清戳(可选;正常靠 get_pending_thesis_review 自动判定消失)。"""
    if read_topic(slug, variant).get("pending_thesis_review") is not None:
        update_topic(slug, variant, pending_thesis_review=None)


_VALID_PRESCAN_STATUSES = ("full", "partial", "failed")


def set_thesis(
    slug: str,
    variant: str,
    version: int,
    summary: str,
    stage_set_at: str,
    prescan_status: str | None = None,
    prescan_failure_reason: str | None = None,
    force_failed: bool = False,
) -> dict | None:
    """记录 LLM 在特定阶段的 thesis 表态。完整 markdown 写到 thesis_v{N}.md。

    summary: 一句话核心 thesis（≤120 字），用于 yaml/web 列表展示
    stage_set_at: thesis 表态时的研究阶段（如 01-roadmap-pending、04-synthesizing）

    ISSUE-001：prescan_status 三态（'full' / 'partial' / 'failed' / None）
      - None      : 向后兼容，行为不变（不写 prescan_status）
      - 'full'    : prescan 命中 100%，正常推进
      - 'partial' : 命中 [WEB_SEARCH_FAIL_THRESHOLD, 1.0)，标 partial 但允许写入
      - 'failed'  : 命中 <WEB_SEARCH_FAIL_THRESHOLD，**必须** force_failed=True + prescan_failure_reason
                    否则 raise ValueError——强制主 agent 显式确认"接受 failed prescan 状态"
        建议在 set_thesis 前调 check_prescan_health() 取 status / failure_reason

    H5 修订（顶层污染消除）：prescan_status 只写到 `history[N]`，**不再写 thesis 顶层**。
      读"当前 thesis 写时 prescan 状态"用 `get_current_prescan_status(slug, variant)`。
      后续轮次（workflow 01/02/06）的 prescan 走独立 `set_prescan_log()`，不调本函数。

    副作用：升版后自动跑 reverse-check（version>=1 且 roadmap 存在时）：
      若 thesis 的 K# 在 roadmap.L4/material 中未闭环，自动写 "roadmap 需补 Kx" todo，
      并把 stage 翻成 '01-roadmap-reopen'。返回 reverse-check 结果（含 newly_added_todos）。
      version=0 或 roadmap 未建时跳过。
    """
    if prescan_status is not None and prescan_status not in _VALID_PRESCAN_STATUSES:
        raise ValueError(
            f"prescan_status={prescan_status!r} 非法，必须为 "
            f"{_VALID_PRESCAN_STATUSES} 之一或 None"
        )
    if prescan_status == "failed":
        if not force_failed:
            raise ValueError(
                "prescan_status='failed' 但未传 force_failed=True — "
                "主 agent 必须显式确认接受 failed prescan 状态（thesis 是训练知识赌注）。"
                "建议先尝试串行重试 baseline 优先 query，仍失败再重调本函数时传 force_failed=True"
            )
        if not (prescan_failure_reason and prescan_failure_reason.strip()):
            raise ValueError(
                "prescan_status='failed' 必须同时传 prescan_failure_reason "
                "（如 'WebSearch 限流静默返空' / 'API 区域阻断' / '主 agent 跳过 Step 4.5a'）"
            )

    data = read_topic(slug, variant)
    thesis = data.setdefault("thesis", {"current_version": None, "last_updated": None, "history": []})
    thesis["current_version"] = version
    thesis["last_updated"] = _now_iso()
    history_entry = {
        "version": version,
        "stage_set_at": stage_set_at,
        "set_at": _now_iso(),
        "summary": summary,
    }
    if prescan_status is not None:
        history_entry["prescan_status"] = prescan_status
        if prescan_failure_reason:
            history_entry["prescan_failure_reason"] = prescan_failure_reason
        # H5 修订：不再写 thesis 顶层。后续轮次 prescan 失败如果回写顶层会污染该
        # thesis 版本写时的 prescan 状态。读"当前写时 prescan 状态"用
        # get_current_prescan_status() 从 history 取当前版本即可。
    # H5 清理：旧 yaml 残留的顶层字段在本次 set_thesis 时一次性移除（迁移）
    thesis.pop("prescan_status", None)
    thesis.pop("prescan_failure_reason", None)
    thesis["history"].append(history_entry)
    _write_yaml(_topic_path(slug, variant), data)

    if version >= 1:
        # 先做 K# 回收（标记上版有本版无的 K#），再做 reverse-check（标记本版缺的 K#）
        archived = mark_outdated_ks(slug, variant, version)
        rev = reverse_check_roadmap_coverage(slug, variant, version)
        if isinstance(rev, dict):
            rev["outdated_ks_marked"] = archived
        _trigger_dashboard(slug, variant, f"thesis_v{version}")
        return rev
    _trigger_dashboard(slug, variant, f"thesis_v{version}")
    return None


_VALID_CONVERGENCE_STATUSES = ("open", "converged", "capped")


def set_decomposition(
    slug: str,
    variant: str,
    version: int,
    summary: str,
    stage_set_at: str,
    convergence_status: str | None = None,
    changelog: str | None = None,
) -> None:
    """记录命门拆解（B 层）的版本表态。完整 markdown 写到 decomposition_v{N}.md。

    镜像 `set_thesis` 的版本化结构（current_version / last_updated / history），但拆解
    **不做 prescan / reverse-check** —— 它是合成活动的前移产物，可靠性闸门在 04 写作期的
    有界 delta 重拆，不在此（见 plan §关键设计原理 3/4/5）。

    summary: 一句话命门概览（≤120 字，如 "命门1=固态电解质量产良率; 命门2=车厂认证节奏"）。
    stage_set_at: 拆解表态时的阶段（v0 在 '00-research-pending'；v1+ 在 '04-synthesizing'）。
    convergence_status:
      - None / 'open' : 仍可能再拆（v0 默认，或 delta 非空待第二趟）
      - 'converged'   : delta 空 + gap 双轴绿 + critic 无重大
      - 'capped'      : 撞 2 轮硬顶，残留命门进诚实缺口清单 / 踢 07-drilldown
    changelog: v1+ 必带 —— 一句话 delta（命门 added/dropped/re-ranked + 为什么），防震荡用。
    """
    if convergence_status is not None and convergence_status not in _VALID_CONVERGENCE_STATUSES:
        raise ValueError(
            f"convergence_status={convergence_status!r} 非法，必须为 "
            f"{_VALID_CONVERGENCE_STATUSES} 之一或 None"
        )

    data = read_topic(slug, variant)
    decomp = data.setdefault(
        "decomposition", {"current_version": None, "last_updated": None, "history": []}
    )
    decomp["current_version"] = version
    decomp["last_updated"] = _now_iso()
    history_entry = {
        "version": version,
        "stage_set_at": stage_set_at,
        "set_at": _now_iso(),
        "summary": summary,
    }
    if convergence_status is not None:
        history_entry["convergence_status"] = convergence_status
    if changelog:
        history_entry["changelog"] = changelog
    decomp["history"].append(history_entry)
    _write_yaml(_topic_path(slug, variant), data)
    _trigger_dashboard(slug, variant, f"decomposition_v{version}")


# ---------------------------------------------------------------------------
# H5: prescan 状态读写分离 — thesis 写时 vs 后续轮次
# ---------------------------------------------------------------------------

def get_current_prescan_status(slug: str, variant: str) -> dict:
    """读"当前 thesis 写时的 prescan 状态"（从 history[current_version] 取，不读顶层）。

    返回 {'status': str|None, 'failure_reason': str|None, 'version': int|None}
      - 无 thesis 或 thesis.history 空 → 全 None
      - history 当前版本没有 prescan_status → status=None（向后兼容旧 thesis）

    H5 修订前：调用方读 thesis.prescan_status 顶层；该顶层会被后续轮次 prescan
    污染。H5 后顶层不再写，调用方一律走本 helper。
    """
    data = read_topic(slug, variant)
    thesis = data.get("thesis") or {}
    cur = thesis.get("current_version")
    history = thesis.get("history") or []
    if cur is None or not history:
        return {"status": None, "failure_reason": None, "version": cur}
    entry = next((h for h in history if h.get("version") == cur), None)
    if not entry:
        # current_version 指向不存在的版本（异常态），退化到最新 entry
        entry = history[-1] if history else {}
    return {
        "status": entry.get("prescan_status"),
        "failure_reason": entry.get("prescan_failure_reason"),
        "version": cur,
    }


def set_prescan_log(
    slug: str,
    variant: str,
    status: str,
    triggered_by: str,
    hit_rate: float | None = None,
    queries_run: int | None = None,
    queries_with_hits: int | None = None,
    failure_reason: str | None = None,
) -> dict:
    """记录后续轮次 prescan 健康度，独立于 thesis 状态。

    用于 workflow 01 Step 8 / 02 Step 0 / 06 Step 1b 等"非写 thesis"轮次的 prescan。
    H5 修订前这些调用方按文档建议调 set_thesis(prescan_status=...) 回写顶层，
    会污染 thesis 写时状态；H5 后这些调用走本函数，写到 topic.prescan_log 数组。

    status: 'full' / 'partial' / 'failed'
    triggered_by: 来源标识（如 '01-prescan', '02-step0', '06-daily-monitor'）
    返回 append 的 log entry。
    """
    if status not in _VALID_PRESCAN_STATUSES:
        raise ValueError(
            f"status={status!r} 非法，必须为 {_VALID_PRESCAN_STATUSES} 之一"
        )
    if status == "failed" and not (failure_reason and failure_reason.strip()):
        raise ValueError(
            "status='failed' 必须同时传 failure_reason（如 'WebSearch 限流静默返空'）"
        )

    data = read_topic(slug, variant)
    log_list = data.setdefault("prescan_log", [])
    entry = {
        "round_at": _now_iso(),
        "status": status,
        "triggered_by": triggered_by,
    }
    if hit_rate is not None:
        entry["hit_rate"] = round(hit_rate, 3)
    if queries_run is not None:
        entry["queries_run"] = queries_run
    if queries_with_hits is not None:
        entry["queries_with_hits"] = queries_with_hits
    if failure_reason:
        entry["failure_reason"] = failure_reason
    log_list.append(entry)
    _write_yaml(_topic_path(slug, variant), data)
    return entry


def mark_outdated_ks(slug: str, variant: str, version: int) -> list[str]:
    """对比 thesis_v{version} 与 thesis_v{version-1} 的 K#，找出上版有本版无的（被 thesis 收回）。
    给 active user_todos（addresses 含该 K#）加 archive_candidate 标记，让用户/UI 知道这条已过时。

    返回被标记的 outdated K# 列表（即便没有匹配 todo 也返回，便于诊断）。
    finding / roadmap entry 暂不自动改（避免覆盖手动编辑）；后续考虑加 lint 提醒。
    """
    if version < 1:
        return []
    from . import outputs as outputs_io
    curr_ks = set(outputs_io.extract_killer_questions(slug, variant, version))
    prev_ks = set(outputs_io.extract_killer_questions(slug, variant, version - 1))
    outdated = sorted(prev_ks - curr_ks, key=lambda k: int(k[1:]) if k[1:].isdigit() else 999)
    if not outdated:
        return []
    data = read_topic(slug, variant)
    todos = data.get("user_todos") or []
    note = f"thesis v{version} 已移除该 K#（上版 K# 集合：{sorted(prev_ks)}，本版：{sorted(curr_ks)}）"
    touched = False
    for t in todos:
        if not isinstance(t, dict) or t.get("status") == "done":
            continue
        addrs_keys = {_addr_key(a) for a in (t.get("addresses") or [])}
        if addrs_keys & set(outdated):
            t["archive_candidate"] = note
            touched = True
    if touched:
        update_topic(slug, variant, user_todos=todos)
    return outdated


def reverse_check_roadmap_coverage(slug: str, variant: str, version: int) -> dict:
    """对 thesis_v{version} 跑 roadmap 覆盖反查；缺口写 todo + 翻 stage。

    返回：{
        'triggered': bool,                    # 是否真的执行了反查（roadmap 存在且有 K#）
        'ok': bool,                            # 全部闭环
        'uncovered_in_l4': [...],
        'uncovered_in_material': [...],
        'newly_added_todos': [task, ...],     # 本次新增的 todo task 字符串
        'stage_flipped_to': str | None,        # 若翻了 stage 则记录目标
    }
    """
    from . import outputs as outputs_io  # 延迟引入避免循环
    cov = outputs_io.validate_roadmap_thesis_coverage(slug, variant, version)
    if not cov.get("roadmap_exists") or not cov.get("thesis_ks"):
        return {
            "triggered": False, "ok": cov.get("ok", False),
            "uncovered_in_l4": cov.get("uncovered_in_l4", []),
            "uncovered_in_material": cov.get("uncovered_in_material", []),
            "newly_added_todos": [], "stage_flipped_to": None,
        }
    if cov["ok"]:
        return {
            "triggered": True, "ok": True,
            "uncovered_in_l4": [], "uncovered_in_material": [],
            "newly_added_todos": [], "stage_flipped_to": None,
        }

    uncovered = sorted(
        set(cov["uncovered_in_l4"]) | set(cov["uncovered_in_material"]),
        key=lambda k: int(k[1:]) if k[1:].isdigit() else 999,
    )
    data = read_topic(slug, variant)
    todos = list(data.get("user_todos") or [])

    # 已存在的 active reverse-check todo（pending/in_progress）按 K# key 去重（忽略 @event）；
    # status=done 视为真闭环，若该 K# 后续又缺，下次允许重新写新 todo 再提醒。
    existing_reopen = set()
    for t in todos:
        if not isinstance(t, dict):
            continue
        hint = (t.get("source_hint") or "")
        if "reverse-check" in hint and t.get("status") != "done":
            for a in (t.get("addresses") or []):
                existing_reopen.add(_addr_key(a))

    added: list[str] = []
    for k in uncovered:
        if k in existing_reopen:
            continue
        in_l4 = k in cov["uncovered_in_l4"]
        in_mat = k in cov["uncovered_in_material"]
        miss_parts = []
        if in_l4:
            miss_parts.append("L4-hunting")
        if in_mat:
            miss_parts.append("tier-material")
        miss_str = " + ".join(miss_parts)
        task = f"roadmap 需补 {k}：thesis v{version} 升版后 {k} 在 {miss_str} 中未闭环"
        todos.append({
            "task": task,
            "priority": "P1",
            "info_tier": "public",
            "addresses": [k],
            "source_hint": f"auto-generated by set_thesis reverse-check (v{version})",
            "status": "pending",
        })
        added.append(task)

    if added:
        update_topic(slug, variant, user_todos=todos)

    stage_flipped = None
    # 仅当当前 stage 已过 01-roadmap（说明确实是后期升版漏补）才翻
    current_stage = data.get("stage", "")
    if current_stage not in ("00-init", "01-roadmap", "01-roadmap-reopen", "quarantined"):
        set_stage(slug, "01-roadmap-reopen", variant)
        stage_flipped = "01-roadmap-reopen"

    return {
        "triggered": True, "ok": False,
        "uncovered_in_l4": cov["uncovered_in_l4"],
        "uncovered_in_material": cov["uncovered_in_material"],
        "newly_added_todos": added,
        "stage_flipped_to": stage_flipped,
    }


def set_data_freshness(slug: str, output_key: str, freshness: str, variant: str) -> None:
    data = read_topic(slug, variant)
    entry = data["outputs_state"].setdefault(output_key, dict(_DEFAULT_OUTPUT_STATE))
    entry["data_freshness"] = freshness
    entry["last_updated"] = _now_iso()
    _write_yaml(_topic_path(slug, variant), data)


def list_variants(slug: str) -> list[str]:
    """List all model variant names under a topic slug."""
    slug_dir = _topics_dir() / slug
    if not slug_dir.is_dir():
        return []
    variants = []
    for sub in slug_dir.iterdir():
        if sub.is_dir() and (sub / "topic.yaml").is_file():
            variants.append(sub.name)
    return sorted(variants)


def list_topics(variant: str | None = None) -> list[dict]:
    """List all topics.

    Without variant: list all variants from all topics.
    With variant: only scan that variant under each topic slug.
    """
    root = _topics_dir()
    if not root.exists():
        return []
    results = []
    for slug_dir in root.iterdir():
        if not slug_dir.is_dir():
            continue
        if variant:
            path = slug_dir / variant / "topic.yaml"
            if path.is_file():
                try:
                    topic = _read_yaml(path)
                    topic["variant"] = variant
                    results.append(topic)
                except Exception:
                    pass
        else:
            for sub in slug_dir.iterdir():
                if sub.is_dir() and (sub / "topic.yaml").is_file():
                    try:
                        topic = _read_yaml(sub / "topic.yaml")
                        topic["variant"] = sub.name
                        results.append(topic)
                    except Exception:
                        pass
    results.sort(key=lambda t: t.get("created", ""), reverse=True)
    return results


def get_parent_materials_dir(slug: str, variant: str) -> Path | None:
    """If this topic has a parent_topic, return the parent's shared materials directory."""
    try:
        topic = read_topic(slug, variant)
        parent = topic.get("parent_topic")
        if parent:
            return _topics_dir() / parent / "materials"
    except Exception:
        pass
    return None


def list_parent_materials(slug: str, variant: str) -> list[str]:
    """List material filenames from the parent topic's materials directory."""
    parent_dir = get_parent_materials_dir(slug, variant)
    if parent_dir and parent_dir.is_dir():
        return sorted([p.name for p in parent_dir.iterdir() if p.is_file()])
    return []


def _resolved_parent_variant(parent_slug: str, child_variant: str, explicit: str | None) -> str:
    """父引用落盘时定父变体：显式给了直接用；否则按 model_registry 兜底——
    同模型/唯一/全登记取最优（confident），拿不准（多个异模型且含未登记）则 **raise**
    列候选（"不确定才问"的强制点：脚本拒绝瞎猜，主 agent 去问用户再显式传）。
    父尚无任何变体目录时退回子变体名（非破坏，读时安全网再兜）。
    """
    if explicit:
        return explicit
    pvs = list_variants(parent_slug)
    if not pvs:
        return child_variant
    res = model_registry.resolve_parent_variant(child_variant, pvs)
    if res["chosen"] and res["confident"]:
        return res["chosen"]
    raise ValueError(
        f"无法确定父 {parent_slug!r} 的复用变体（child={child_variant!r}, "
        f"候选={res['candidates']}, 原因={res['reason']}）。"
        f"请主 agent 问用户后，显式传 parent_variant。"
    )


def set_parent_materials(slug: str, variant: str, items: list[dict]) -> None:
    """Set parent_materials field on topic.

    Each item: {parent_slug, parent_variant (optional → model_registry 兜底解析),
    mat_id, addresses (list[str], optional), note (optional)}.
    Idempotent: full replacement.
    """
    path = _topic_path(slug, variant)
    data = _read_yaml(path)
    cleaned = []
    for it in items:
        entry = {
            "parent_slug": it["parent_slug"],
            "parent_variant": _resolved_parent_variant(
                it["parent_slug"], variant, it.get("parent_variant")),
            "mat_id": it["mat_id"],
        }
        if it.get("addresses"):
            entry["addresses"] = list(it["addresses"])
        if it.get("note"):
            entry["note"] = it["note"]
        cleaned.append(entry)
    data["parent_materials"] = cleaned
    _write_yaml(path, data)


def add_parent_material(
    slug: str,
    variant: str,
    parent_slug: str,
    mat_id: str,
    addresses: list[str] | None = None,
    note: str | None = None,
    parent_variant: str | None = None,
) -> None:
    """Append a single parent material reference (idempotent on mat_id)."""
    path = _topic_path(slug, variant)
    data = _read_yaml(path)
    items = data.get("parent_materials") or []
    items = [x for x in items if x.get("mat_id") != mat_id]
    entry = {
        "parent_slug": parent_slug,
        "parent_variant": _resolved_parent_variant(parent_slug, variant, parent_variant),
        "mat_id": mat_id,
    }
    if addresses:
        entry["addresses"] = list(addresses)
    if note:
        entry["note"] = note
    items.append(entry)
    data["parent_materials"] = items
    _write_yaml(path, data)


def find_child_topics(parent_slug: str, variant: str | None = None) -> list[dict]:
    """Find all topics whose parent_topic matches parent_slug."""
    children = []
    for t in list_topics(variant=variant):
        if t.get("parent_topic") == parent_slug:
            children.append(t)
    return children


# ---------------------------------------------------------------------------
# Workstream 2 — topic 图谱 / 跨层复用（set_parent / get_relative_outputs /
# suggest_relatives）。全部零 LLM：脚本只列文件路径 + 出机械候选，
# "谁是父" 与 "借哪段" 的判断一律由对话里的 LLM 做。
#
# 跨层复用受 §1.3 护栏约束（见 04-synthesize/_*_funnel.md）：亲属成稿产出仅作
# 输入/参照，质量校验永远按本 topic 自己的 K# + findings + critic 跑。
# get_relative_outputs 故意只返路径不读内容——借用 ≠ 结论注入。
# ---------------------------------------------------------------------------

# type tier 严格递增：company < arena < industry。父 tier 必须 > 子 tier。
_TYPE_TIER = {"company": 0, "arena": 1, "industry": 2}

# 按 type 映射成稿 case 文件名（决策链路径产出）
_CASE_BY_TYPE = {
    "company": "c_investment_case",
    "industry": "i_industry_case",
    "arena": "a_arena_case",
}
# 按 type 映射 dashboard sidecar（机器消费）
_SIDECAR_BY_TYPE = {
    "company": "07_decision_kit.yaml",
    "industry": "industry_to_arenas.yaml",
    "arena": "peer_matrix.yaml",
}


def set_parent(slug: str, variant: str, parent_slug: str | None) -> None:
    """设/改/解 topic 父级（创建后）。parent_slug=None 解链。零 LLM。

    校验（机械，非 LLM 判断）：
      - 不能自指
      - parent 必须存在（list_variants 非空）
      - type tier 严格递增：company(0) < arena(1) < industry(2)，
        父 tier 必须 > 子 tier，否则 raise ValueError
    """
    data = read_topic(slug, variant)
    if parent_slug is None:
        data["parent_topic"] = None
        _write_yaml(_topic_path(slug, variant), data)
        return
    if parent_slug == slug:
        raise ValueError(f"parent_topic 不能自指: {slug!r}")
    parent_variants = list_variants(parent_slug)
    if not parent_variants:
        raise ValueError(f"父 topic 不存在: {parent_slug!r}（无任何 variant）")
    # 选父变体读 type：confident-or-best（同模型/唯一/全登记最优），拿不准则退回旧行为
    # （读路径非破坏，不 raise）。
    _res = model_registry.resolve_parent_variant(variant, parent_variants)
    pv = _res["chosen"] or (variant if variant in parent_variants else parent_variants[0])
    parent_type = read_topic(parent_slug, pv).get("type", "")
    child_type = data.get("type", "")
    ct = _TYPE_TIER.get(child_type)
    pt = _TYPE_TIER.get(parent_type)
    if ct is not None and pt is not None and pt <= ct:
        raise ValueError(
            f"type tier 必须严格递增（company<arena<industry）：本 topic type={child_type!r}"
            f"(tier {ct}) 的父必须更高层，但 {parent_slug!r} type={parent_type!r}(tier {pt})。"
        )
    data["parent_topic"] = parent_slug
    _write_yaml(_topic_path(slug, variant), data)


def _relative_output_paths(slug: str, variant: str) -> dict:
    """收集一个 topic 的成稿产出路径（只列磁盘存在的文件）。内部 helper，零 LLM。

    返回 {primer, thesis, decomposition, case, sidecar} 的子集——键仅在对应文件存在时出现。
    """
    from . import outputs as outputs_io  # 延迟引入避免循环

    base = _topic_path(slug, variant).parent
    out_dir = base / "outputs"
    try:
        topic_type = read_topic(slug, variant).get("type", "")
    except Exception:
        topic_type = ""
    paths: dict[str, str] = {}
    primer = out_dir / "00_primer.md"
    if primer.is_file():
        paths["primer"] = str(primer)
    try:
        versions = outputs_io.list_thesis_files(slug, variant)
    except Exception:
        versions = []
    if versions:
        tp = base / f"thesis_v{versions[-1]}.md"
        if tp.is_file():
            paths["thesis"] = str(tp)
    try:
        dversions = outputs_io.list_decomposition_files(slug, variant)
    except Exception:
        dversions = []
    if dversions:
        dp = base / f"decomposition_v{dversions[-1]}.md"
        if dp.is_file():
            paths["decomposition"] = str(dp)
    case_key = _CASE_BY_TYPE.get(topic_type)
    if case_key:
        cp = out_dir / f"{case_key}.md"
        if cp.is_file():
            paths["case"] = str(cp)
    sidecar = _SIDECAR_BY_TYPE.get(topic_type)
    if sidecar:
        sp = out_dir / sidecar
        if sp.is_file():
            paths["sidecar"] = str(sp)
    return paths


def get_relative_outputs(slug: str, variant: str) -> dict:
    """返回本 topic 的父+子成稿产出路径清单，供 04-synthesize Step 1 亲属 hook 复用。

    脚本**只返文件路径、绝不读内容、不做任何判断**——借用永远是输入/参照，
    受 §1.3 跨层复用护栏约束（借来必标来源、质量按本维度自跑、冲突时本 topic 赢）。

    返回：{
        'parent':   {slug, variant, type, display_name, outputs:{primer?,thesis?,decomposition?,case?,sidecar?}} | None,
        'children': [ {同结构}, ... ],   # 经 find_child_topics（同 variant scope）
    }
    无亲属 → parent=None, children=[] → 调用方退化独立合成，零特判。
    """
    data = read_topic(slug, variant)
    result: dict = {"parent": None, "children": []}

    parent_slug = data.get("parent_topic")
    if parent_slug:
        pvs = list_variants(parent_slug)
        if pvs:
            _res = model_registry.resolve_parent_variant(variant, pvs)
            pv = _res["chosen"] or (variant if variant in pvs else pvs[0])
            try:
                pdata = read_topic(parent_slug, pv)
                result["parent"] = {
                    "slug": parent_slug,
                    "variant": pv,
                    "type": pdata.get("type", ""),
                    "display_name": pdata.get("display_name", parent_slug),
                    "outputs": _relative_output_paths(parent_slug, pv),
                }
            except Exception:
                pass

    for child in find_child_topics(slug, variant=variant):
        cslug = child.get("slug")
        if not cslug:
            continue
        cvar = child.get("variant", variant)
        result["children"].append({
            "slug": cslug,
            "variant": cvar,
            "type": child.get("type", ""),
            "display_name": child.get("display_name", cslug),
            "outputs": _relative_output_paths(cslug, cvar),
        })
    return result


# slug token 匹配时剔除的非语义前缀（geo 标记）——避免 "cn-*" 互相误命中
_SLUG_STOP_TOKENS = {"cn", "us", "global", "eu", "jp", "kr", "hk", "uk", "tw", "in"}


def _slug_semantic_tokens(s: str) -> set:
    """slug 按 '-' 切后剔除 geo 前缀 + 纯数字段（ticker 码），留语义 token。
    'cn-ganfeng-lithium-002460' → {'ganfeng','lithium'}。"""
    return {
        tok for tok in s.split("-")
        if tok and tok not in _SLUG_STOP_TOKENS and not tok.isdigit()
    }


def _norm_ticker(t: str | None) -> str:
    """归一化 ticker 作跨 sidecar 比对：剥交易所前缀取代码段，大写。
    SZSE_002460 → 002460；裸 SES → SES。"""
    if not t:
        return ""
    return str(t).split("_")[-1].upper()


def _sidecar_tags_and_tickers(slug: str, variant: str) -> tuple[set, set]:
    """读一个 topic 的 sidecar，取 cluster_tags 与 companies[].ticker（归一化）。
    sidecar 不存在 / 无对应字段 → 返空集。容错不抛（stub 期常无 sidecar）。"""
    tags: set = set()
    tickers: set = set()
    try:
        topic_type = read_topic(slug, variant).get("type", "")
    except Exception:
        return tags, tickers
    sidecar = _SIDECAR_BY_TYPE.get(topic_type)
    if not sidecar:
        return tags, tickers
    sp = _topic_path(slug, variant).parent / "outputs" / sidecar
    if not sp.is_file():
        return tags, tickers
    try:
        doc = yaml.safe_load(sp.read_text(encoding="utf-8")) or {}
        tags = {str(t) for t in (doc.get("cluster_tags") or [])}
        for c in (doc.get("companies") or []):
            tk = c.get("ticker")
            if tk:
                tickers.add(_norm_ticker(tk))
    except Exception:
        pass
    return tags, tickers


def suggest_relatives(slug: str, variant: str) -> dict:
    """relink 机械候选发现器：纯字符串/集合匹配，**不写盘、零 LLM**。

    扫同 variant 所有 topic，按机械信号**加权**打分，返回父/子候选供对话里 LLM 判读后调
    set_parent 确认。双向、顺序无关——同时给父候选+子候选，在父端或子端跑都给一致集合。

    信号权重（structural 强信号压过 geo 噪声）：
      - ticker 跨 sidecar : 3   本 ticker ∈ 对方 peer matrix / 对方 ticker ∈ 本 peer matrix
                                （company↔arena 最强信号）
      - cluster_tags      : 2   双方 sidecar cluster_tags 交集（concepts 实测全空，不用）
      - search_terms      : 2   scope.search_terms 交集
      - slug-token        : 1   slug 按 '-' 切后 token 交集（**剔 geo 前缀 + 纯数字 ticker 码**）
      - geo               : 1   scope.geo 相等（弱信号，同 geo topic 太多）
    type tier 不兼容（同 tier / 未知）直接排除。只返 score≥1，按 score 降序；signals 记录命中项。

    返回 {'parent_candidates': [...], 'child_candidates': [...]}，
    每项 {slug, variant, type, signals:[...], score}。
    """
    me = read_topic(slug, variant)
    my_type = me.get("type", "")
    my_tier = _TYPE_TIER.get(my_type)
    my_scope = me.get("scope") or {}
    my_geo = (my_scope.get("geo") or "").strip().upper()  # 大小写无关（实测 global vs GLOBAL 混用）
    my_ticker_norm = _norm_ticker(my_scope.get("ticker"))
    my_terms = {str(t) for t in (my_scope.get("search_terms") or [])}
    my_slug_tokens = _slug_semantic_tokens(slug)
    my_tags, my_matrix_tickers = _sidecar_tags_and_tickers(slug, variant)

    parent_candidates: list[dict] = []
    child_candidates: list[dict] = []

    for other in list_topics(variant=variant):
        oslug = other.get("slug")
        if not oslug or oslug == slug:
            continue
        otier = _TYPE_TIER.get(other.get("type", ""))
        # tier 方向必须明确（父>我 或 子<我），同 tier / 未知直接排除
        if my_tier is None or otier is None or otier == my_tier:
            continue
        ovar = other.get("variant", variant)
        oscope = other.get("scope") or {}
        signals: list[str] = []
        score = 0

        otags, oticks = _sidecar_tags_and_tickers(oslug, ovar)
        if my_ticker_norm and my_ticker_norm in oticks:
            signals.append("ticker-in-their-matrix"); score += 3
        if my_matrix_tickers and _norm_ticker(oscope.get("ticker")) in my_matrix_tickers:
            signals.append("their-ticker-in-our-matrix"); score += 3
        if my_tags and (my_tags & otags):
            signals.append("cluster_tags"); score += 2
        if my_terms and (my_terms & {str(t) for t in (oscope.get("search_terms") or [])}):
            signals.append("search_terms"); score += 2
        if my_slug_tokens & _slug_semantic_tokens(oslug):
            signals.append("slug-token"); score += 1
        if my_geo and (oscope.get("geo") or "").strip().upper() == my_geo:
            signals.append("geo"); score += 1

        if not signals:
            continue
        entry = {
            "slug": oslug,
            "variant": ovar,
            "type": other.get("type", ""),
            "signals": signals,
            "score": score,
        }
        if otier > my_tier:
            parent_candidates.append(entry)
        else:  # otier < my_tier
            child_candidates.append(entry)

    parent_candidates.sort(key=lambda e: e["score"], reverse=True)
    child_candidates.sort(key=lambda e: e["score"], reverse=True)
    return {"parent_candidates": parent_candidates, "child_candidates": child_candidates}


def baseline_knowledge_path(slug: str, variant: str) -> Path:
    return _topic_path(slug, variant).parent / "baseline_knowledge.md"


def read_baseline_knowledge(slug: str, variant: str) -> str | None:
    """Return the baseline knowledge markdown content, or None if not written yet."""
    p = baseline_knowledge_path(slug, variant)
    if not p.is_file():
        return None
    return p.read_text(encoding="utf-8")


def has_baseline_knowledge(slug: str, variant: str) -> bool:
    return baseline_knowledge_path(slug, variant).is_file()