"""daily-monitor 编排:watchlist(成本闸)+ scan(到期检测)+ queue(待确认翻牌)。零 LLM。

闭环里脚本只负责的三件机械事:
  1. **watchlist**(`prism/watchlist.yaml`):用户在 web 勾选的关注清单。成本由它而非
     topic 总数决定——不在清单的 event 永不触发昂贵自动搜。两级粒度:
       - scope='topic':跟该 topic 全部 event(所有 signpost/kill + 价格)
       - scope='event':只跟某一条(kind=signpost/kill/price + locator)
  2. **scan**(`scan_due_events`,只读):遍历 watchlist→按 type 读 sidecar→挑出到期项,
     分桶返回。signpost/kill 只是"候选",真正判读由 headless claude 做;price 是零 LLM,
     可直接成 proposal(`propose_price_breaches`)。
  3. **queue**(`prism/monitor_queue.yaml`):staging,非决策真相源。proposal 由 headless
     判读(signpost/kill)或本模块(price)写入;用户 web 端 confirm 后机械回写 sidecar +
     追加 living_feed。confirm 永远零 LLM。

canonical variant 与 dashboard 对齐(`dashboard.canonical_variant`),避免翻错 variant 的牌。
"""
from __future__ import annotations

import hashlib
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from prism.scripts import macro_registry
from prism.scripts import sidecar_edit
from prism.scripts.dashboard import (
    _parse_signpost_date,
    canonical_variant,
)

PRISM_ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = PRISM_ROOT / "watchlist.yaml"
QUEUE_PATH = PRISM_ROOT / "monitor_queue.yaml"

_VALID_SCOPE = ("topic", "event")
_VALID_KIND = ("signpost", "kill", "price")
# 买入区间(price breach 触发):跨入这两档即"破位进买入框"
_BUY_ZONES = ("strong_buy", "accumulate")


# ── yaml io ────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


# ── watchlist ────────────────────────────────────────────────────────────────

def load_watchlist() -> list[dict]:
    return _read_yaml(WATCHLIST_PATH).get("watches") or []


def _save_watchlist(watches: list[dict]) -> None:
    _write_yaml(WATCHLIST_PATH, {"watches": watches})


def _watch_key(w: dict) -> tuple:
    """唯一键:同 slug+scope+kind+locator 视为同一条关注(去重/删除用)。"""
    return (w.get("slug"), w.get("scope"), w.get("kind"), w.get("locator"))


def add_watch(
    slug: str,
    scope: str = "topic",
    kind: str | None = None,
    locator: str | None = None,
    variant: str | None = None,
) -> dict:
    """加一条关注。variant 省略则用 dashboard canonical（与翻牌对齐）。

    scope='topic' 跟全部 event;scope='event' 必须带 kind(+signpost/kill 还要 locator)。
    重复 add(同 key)幂等 no-op。返回新增的 watch 条目（或既存条目）。
    """
    if scope not in _VALID_SCOPE:
        raise ValueError(f"scope 必须 ∈ {_VALID_SCOPE}，得到 {scope!r}")
    if scope == "event":
        if kind not in _VALID_KIND:
            raise ValueError(f"scope=event 时 kind 必须 ∈ {_VALID_KIND}，得到 {kind!r}")
        if kind in ("signpost", "kill") and not locator:
            raise ValueError(f"scope=event kind={kind} 必须带 locator")
    else:
        kind = None
        locator = None
    if not variant:
        variant = canonical_variant(slug)
        if not variant:
            raise ValueError(f"slug {slug!r} 无任何 topic variant，无法关注")
    entry = {
        "slug": slug,
        "variant": variant,
        "scope": scope,
        "kind": kind,
        "locator": locator,
        "added_at": _now_iso(),
    }
    watches = load_watchlist()
    for w in watches:
        if _watch_key(w) == _watch_key(entry):
            return w  # 幂等
    watches.append(entry)
    _save_watchlist(watches)
    return entry


def remove_watch(
    slug: str,
    scope: str | None = None,
    kind: str | None = None,
    locator: str | None = None,
) -> int:
    """删关注。只给 slug → 删该 slug 全部条目;带 scope/kind/locator → 精确删。

    返回删除条数。
    """
    watches = load_watchlist()
    before = len(watches)

    def _match(w: dict) -> bool:
        if w.get("slug") != slug:
            return False
        if scope is not None and w.get("scope") != scope:
            return False
        if kind is not None and w.get("kind") != kind:
            return False
        if locator is not None and w.get("locator") != locator:
            return False
        return True

    watches = [w for w in watches if not _match(w)]
    _save_watchlist(watches)
    return before - len(watches)


# ── scan ─────────────────────────────────────────────────────────────────────

def _topic_type(slug: str, variant: str) -> str:
    from prism.scripts.topic import read_topic
    try:
        return read_topic(slug, variant).get("type", "")
    except Exception:
        return ""


def _load_company_sidecar(slug: str, variant: str) -> dict | None:
    path = PRISM_ROOT / "topics" / slug / variant / "outputs" / "07_decision_kit.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None  # 损坏 sidecar 不抛，让 scan 继续扫其余 topic


def _within(d: date | None, today: date, within_days: int) -> bool:
    """到期(含逾期):date<=today+window。逾期(date<today)也算到期，必须包含。"""
    if d is None:
        return False
    return (d - today).days <= within_days


def scan_due_events(within_days: int = 14) -> dict:
    """只读:遍历 watchlist，挑出到期 event 分桶返回。绝不写任何文件。

    返回 {
      due_signposts, due_kills,   # 候选——交 headless claude 判读
      price_breach,               # 零 LLM——可直接 propose
      recurring_review,           # industry/arena 无日期触发器，按周期重扫
      unparseable,                # 日期解析失败的 signpost/kill（写错=永不触发，必须曝光）
                                  # macro 的 unparseable 项额外带 {slug, variant,
                                  # field:"macro_input", locator} 字段。
      price_unavailable,          # 停牌/缺数/币种错配——不误报破位
      skipped_no_sidecar,         # 关注了但还没 sidecar（macro 无登记表时 reason="no_macro_registry"）
      macro_due,                  # macro topic 事件/描述到期项，带 slug/variant + 登记表字段
      macro_alert,                # macro topic 行情型 alert_series 越带项
    }
    每个 due 项带 slug/variant/locator，足够 headless 定位与判读。
    """
    today = date.today()
    out = {
        "due_signposts": [], "due_kills": [], "price_breach": [],
        "recurring_review": [], "unparseable": [],
        "price_unavailable": [], "skipped_no_sidecar": [],
        "macro_due": [], "macro_alert": [],
    }
    for w in load_watchlist():
        slug = w.get("slug")
        variant = w.get("variant") or canonical_variant(slug)
        if not variant:
            continue
        scope = w.get("scope", "topic")
        wkind = w.get("kind")
        wloc = w.get("locator")
        ttype = _topic_type(slug, variant)

        # macro：无 07 sidecar，读 macro_inputs 登记表分桶（事件/描述到期 + 行情越带）
        if ttype == "macro":
            try:
                reg = macro_registry.read_registry(slug, variant)
            except FileNotFoundError:
                out["skipped_no_sidecar"].append(
                    {"slug": slug, "variant": variant, "reason": "no_macro_registry"})
                continue
            # macro 到期为"已过期"语义（overdue-only，见 scan_macro_inputs）：
            # 仅在发布点已过才提示取新值，不做 within_days 前瞻（与 proposal 文案一致）。
            mscan = macro_registry.scan_macro_inputs(reg, today=today)
            for x in mscan["due_event"] + mscan["due_policy"]:
                out["macro_due"].append({"slug": slug, "variant": variant, **x})
            for x in mscan["alert_series"]:
                out["macro_alert"].append({"slug": slug, "variant": variant, **x})
            for u in mscan["unparseable"]:
                out["unparseable"].append({"slug": slug, "variant": variant,
                                           "field": "macro_input", "locator": u.get("name")})
            continue

        # industry/arena:无 dated signpost，走周期重扫
        if ttype in ("industry", "arena"):
            out["recurring_review"].append({
                "slug": slug, "variant": variant, "type": ttype,
                "last_reviewed": _last_reviewed(slug, variant),
            })
            continue

        sidecar = _load_company_sidecar(slug, variant)
        if sidecar is None:
            out["skipped_no_sidecar"].append({"slug": slug, "variant": variant})
            continue

        # signposts
        if scope == "topic" or wkind == "signpost":
            for sp in sidecar.get("signposts") or []:
                loc = sidecar_edit.signpost_locator(sp.get("date"), sp.get("event", ""))
                if scope == "event" and wkind == "signpost" and loc != wloc:
                    continue
                if sp.get("triggered") is not None:
                    continue  # 已翻牌
                d = _parse_signpost_date(sp.get("date"))
                item = {
                    "slug": slug, "variant": variant, "locator": loc,
                    "date": str(sp.get("date")), "event": sp.get("event"),
                    "bull_signal": sp.get("bull_signal"),
                    "bear_signal": sp.get("bear_signal"),
                    "current_triggered": sp.get("triggered"),
                }
                if d is None:
                    out["unparseable"].append({**item, "field": "signpost"})
                elif _within(d, today, within_days):
                    out["due_signposts"].append(item)

        # kills
        if scope == "topic" or wkind == "kill":
            for k in sidecar.get("kill_criteria") or []:
                kid = k.get("id")
                if scope == "event" and wkind == "kill" and kid != wloc:
                    continue
                if k.get("status") != "pending":
                    continue
                d = _parse_signpost_date(k.get("check_at"))
                item = {
                    "slug": slug, "variant": variant, "locator": kid,
                    "check_at": str(k.get("check_at")),
                    "description": k.get("description"),
                    "current_status": k.get("status"),
                }
                if d is None:
                    out["unparseable"].append({**item, "field": "kill"})
                elif _within(d, today, within_days):
                    out["due_kills"].append(item)

        # price breach（零 LLM）
        if scope == "topic" or wkind == "price":
            breach = _check_price_breach(slug, variant, sidecar)
            if breach is None:
                out["price_unavailable"].append({"slug": slug, "variant": variant})
            elif breach.get("in_buy_zone"):
                out["price_breach"].append(breach)

    return out


def _last_reviewed(slug: str, variant: str) -> str | None:
    from prism.scripts.topic import read_topic
    try:
        return (read_topic(slug, variant).get("monitoring") or {}).get("last_reviewed")
    except Exception:
        return None


def _check_price_breach(slug: str, variant: str, sidecar: dict) -> dict | None:
    """比当前价与 buy_box。零 LLM。

    返回 None = 价格不可用(停牌/缺数/无 ticker)——不误报破位。
    否则返回 {slug,variant,close,zone,in_buy_zone,buy_box}。
    """
    from prism.scripts import market_data
    from prism.scripts.dashboard import _locate_zone
    buy_box = sidecar.get("buy_box") or {}
    if not buy_box:
        return None
    try:
        q = market_data.get_quote(slug, variant)
    except Exception:
        return None
    if q.get("error") or q.get("close") is None:
        return None
    close = q["close"]
    zone = _locate_zone(close, buy_box)
    return {
        "slug": slug, "variant": variant,
        "close": close, "zone": zone,
        "in_buy_zone": zone in _BUY_ZONES,
        "buy_box": buy_box,
        "price_date": q.get("date"),
    }


# ── queue / proposals ──────────────────────────────────────────────────────────

def load_queue() -> list[dict]:
    return _read_yaml(QUEUE_PATH).get("pending") or []


def _save_queue(pending: list[dict]) -> None:
    _write_yaml(QUEUE_PATH, {"pending": pending})


def make_proposal_id(slug: str, variant: str, kind: str, locator: str) -> str:
    raw = f"{slug}|{variant}|{kind}|{locator}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def propose_flips(proposals: list[dict]) -> dict:
    """把 proposal 列表 upsert 进 queue。同 proposal_id 覆盖(幂等)。

    每个 proposal 必带:slug, variant, kind('signpost'|'kill'|'price'), locator,
    proposed_value。可选:expected_current, evidence(完整 hits,confirm 时注册进
    web_search 库), evidence_urls(裸链接,展示/回退用), living_feed_entry,
    rationale, requires_thesis_review。
    已 confirmed 的同 id 不被覆盖(防重写已落盘的翻牌)。
    返回 {added, updated, skipped_confirmed}。
    """
    pending = load_queue()
    by_id = {p["proposal_id"]: p for p in pending}
    added = updated = skipped = 0
    for raw in proposals:
        slug = raw["slug"]
        variant = raw["variant"]
        kind = raw["kind"]
        locator = raw.get("locator") or ("buy_box" if kind == "price" else "")
        pid = make_proposal_id(slug, variant, kind, locator)
        existing = by_id.get(pid)
        if existing and existing.get("status") == "confirmed":
            skipped += 1
            continue
        entry = {
            "proposal_id": pid,
            "slug": slug, "variant": variant, "kind": kind, "locator": locator,
            "proposed_value": raw.get("proposed_value"),
            "expected_current": raw.get("expected_current"),
            # evidence: 完整 hits(title/url/snippet[/domain_tier]),confirm 时注册进
            # web_search 库喂 05;evidence_urls 仅供 web 端展示 + evidence 缺失时回退合成。
            "evidence": raw.get("evidence") or [],
            "evidence_urls": raw.get("evidence_urls") or [],
            "living_feed_entry": raw.get("living_feed_entry") or "",
            "rationale": raw.get("rationale") or "",
            "requires_thesis_review": bool(raw.get("requires_thesis_review")),
            "status": "awaiting_confirm",
            "created_at": _now_iso(),
            "confirmed_at": None,
            "writeback_done": False,
            "living_feed_appended": False,
        }
        by_id[pid] = entry
        if existing:
            updated += 1
        else:
            added += 1
    _save_queue(list(by_id.values()))
    return {"added": added, "updated": updated, "skipped_confirmed": skipped}


def propose_price_breaches(within_days: int = 14) -> dict:
    """零 LLM 路径:scan + 把 price_breach 直接成 proposal 写进 queue。

    main.py 巡检循环直接调(不经 headless)。living_feed 文案机械生成。
    """
    scan = scan_due_events(within_days=within_days)
    proposals = []
    for b in scan["price_breach"]:
        bb = b["buy_box"]
        entry = (
            f"## {date.today().isoformat()} 价格破位:跌入买入框\n"
            f"**来源**:market_data 自动行情\n"
            f"**关键信息**:现价 {b['close']}（{b.get('price_date') or '—'}）"
            f"落入 **{b['zone']}** 区间"
            f"（强买≤{bb.get('strong_buy_max')} / 可建仓 {bb.get('accumulate_min')}-{bb.get('accumulate_max')}）\n"
            f"**对已有判断的影响**:触及预设买入区,需按 position_framework 复核建仓\n"
            f"**当前判断更新**:维持原判断,价格信号待人工确认"
        )
        proposals.append({
            "slug": b["slug"], "variant": b["variant"], "kind": "price",
            "locator": "buy_box", "proposed_value": b["zone"],
            "evidence_urls": [], "living_feed_entry": entry,
            "rationale": f"现价 {b['close']} 落入 {b['zone']}（零 LLM 价格判定）",
            "requires_thesis_review": False,
        })
    result = propose_flips(proposals)
    result["scanned_breaches"] = len(scan["price_breach"])
    return result


def propose_macro_updates(within_days: int = 14) -> dict:
    """零 LLM 路径：scan macro 桶 → 写 kind='macro_input' proposal 进 queue。

    macro proposal 是信息型——confirm 只追加 living_feed + 盖"建议重判"戳，
    绝不自动改 regime_read（判断永远人在 web 端触发）。
    importance=load_bearing 或越带 alert → requires_thesis_review=True。
    """
    scan = scan_due_events(within_days=within_days)
    proposals = []
    today_str = date.today().isoformat()
    for item in scan["macro_due"]:
        name = item.get("name", "")
        imp = item.get("importance")
        entry = (
            f"## {today_str} 宏观输入到期：{name}\n"
            f"**来源**：{item.get('source', '—')}（{item.get('cadence_type')}）\n"
            f"**关键信息**：该输入已到发布/排期点，待取新值与旧读数对比\n"
            f"**对已有判断的影响**：{item.get('causal_sentence') or '（见登记表机制句）'}\n"
            f"**当前判断更新**：维持，等用户在 web 端决定是否重判"
        )
        proposals.append({
            "slug": item["slug"], "variant": item["variant"], "kind": "macro_input",
            "locator": name, "proposed_value": "due",
            "living_feed_entry": entry,
            "rationale": f"{name} 到期（{item.get('cadence_type')}）",
            "requires_thesis_review": imp == "load_bearing",
        })
    for item in scan["macro_alert"]:
        name = item.get("name", "")
        obs = item.get("observed") or {}
        entry = (
            f"## {today_str} 宏观承重序列越带：{name}\n"
            f"**来源**：{item.get('source', '—')}（行情型 alert_series）\n"
            f"**关键信息**：最新 {obs.get('value', obs.get('z', '—'))} / 上次 {obs.get('prev_value', '—')}，越预设报警带\n"
            f"**对已有判断的影响**：{item.get('causal_sentence') or '承重序列突变，可能预示体制切换'}\n"
            f"**当前判断更新**：维持，强烈建议用户重判"
        )
        proposals.append({
            "slug": item["slug"], "variant": item["variant"], "kind": "macro_input",
            "locator": name, "proposed_value": "alert",
            "living_feed_entry": entry,
            "rationale": f"{name} 越报警带",
            "requires_thesis_review": True,
        })
    result = propose_flips(proposals)
    result["scanned_macro"] = len(scan["macro_due"]) + len(scan["macro_alert"])
    return result


def _append_living_feed(slug: str, variant: str, entry_md: str) -> None:
    """把一段 markdown 追加到 08_living_feed.md 末尾,并 bump output 状态。零 LLM。"""
    if not entry_md.strip():
        return
    out_dir = PRISM_ROOT / "topics" / slug / variant / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "08_living_feed.md"
    block = "\n\n---\n\n" + entry_md.strip() + "\n"
    if path.exists():
        path.write_text(path.read_text(encoding="utf-8") + block, encoding="utf-8")
    else:
        path.write_text(
            f"# 信息流时间线:{slug}\n\n> daily-monitor 追加式日志。\n" + block,
            encoding="utf-8",
        )
    try:
        from prism.scripts.topic import read_topic, set_output_status
        cur = (read_topic(slug, variant).get("outputs_state") or {}).get("08_living_feed") or {}
        set_output_status(slug, "08_living_feed", "fresh", variant,
                          version=(cur.get("version") or 0) + 1)
    except Exception:
        pass  # status bump 失败不该让翻牌回滚


def _anchor_for(slug: str, variant: str, kind: str, locator: str) -> str:
    """从 sidecar 取该 event 的语义锚点,作 register_web_search 的 addresses。

    signpost → 'signpost:{event}｜bear:{bear_signal}'；kill → 'kill:{description}'。
    锚点是 free-text(非 K#),故注册时不会进任何 K# todo 的覆盖候选
    (todo 闭环本就按文档身份、不按 K#,见 feedback_todo_closure_key)。取不到回退到 '{kind}:{locator}'。
    """
    sidecar = _load_company_sidecar(slug, variant) or {}
    if kind == "signpost":
        for sp in sidecar.get("signposts") or []:
            if sidecar_edit.signpost_locator(sp.get("date"), sp.get("event", "")) == locator:
                ev = (sp.get("event") or "").strip()
                bear = (sp.get("bear_signal") or "").strip()
                anchor = f"signpost:{ev}"
                return f"{anchor}｜bear:{bear}" if bear else anchor
    elif kind == "kill":
        for k in sidecar.get("kill_criteria") or []:
            if k.get("id") == locator:
                return f"kill:{(k.get('description') or locator)}"
    return f"{kind}:{locator}"


def _register_proposal_evidence(slug: str, variant: str, target: dict, anchor: str):
    """把 proposal 的证据 hits 注册进 web_search 库,addressed 到 signpost/kill 锚点,
    triggered_by='06-daily-monitor'。让 05 的 gap_detector 数得到这批新证据、独立反方
    拿得到。URL 去重幂等(register_web_search_result 内 find_by_url 合并)。零 LLM。

    优先用 proposal['evidence'](完整 hits: title/url/snippet);退化到 evidence_urls
    时合成最小 hit(title/snippet 取 rationale),靠 domain_tier 过 funnel(whitelist 域
    仍进高 band,低 tier 裸 url 会被 funnel 丢——这是预期,弱证据本就不该污染证据库)。
    返回 register_web_search_batch 的结果 dict,无证据返回 None。
    """
    hits = [h for h in (target.get("evidence") or []) if h.get("url")]
    if not hits:
        urls = target.get("evidence_urls") or []
        snippet = target.get("rationale") or ""
        hits = [{"title": u, "url": u, "snippet": snippet} for u in urls if u]
    if not hits:
        return None
    from prism.scripts.web_prescan import register_web_search_batch
    return register_web_search_batch(
        slug, variant,
        query=f"[daily-monitor] {anchor}",
        addresses=[anchor],
        triggered_by="06-daily-monitor",
        hits=hits,
    )


def confirm_flip(proposal_id: str) -> dict:
    """确认一条 proposal → 机械回写 sidecar(signpost/kill) + 追加 living_feed。零 LLM。

    幂等:已 confirmed 的重复 confirm 为 no-op。sidecar 被 04/05 重排/删 →
    sidecar_edit 抛 StaleProposal,这里标 status='stale' 不盲写。
    """
    pending = load_queue()
    target = next((p for p in pending if p["proposal_id"] == proposal_id), None)
    if target is None:
        raise ValueError(f"proposal {proposal_id!r} 不存在")
    if target.get("status") == "confirmed":
        return {"proposal_id": proposal_id, "status": "confirmed", "noop": True}

    slug, variant = target["slug"], target["variant"]
    kind = target["kind"]
    try:
        if kind == "signpost" and not target.get("writeback_done"):
            sidecar_edit.set_signpost_triggered(
                slug, variant, target["locator"],
                target["proposed_value"],
                expected_current=target.get("expected_current"),
            )
        elif kind == "kill" and not target.get("writeback_done"):
            sidecar_edit.set_kill_status(
                slug, variant, target["locator"],
                target["proposed_value"],
                expected_current=target.get("expected_current"),
            )
        # kind == 'price':无 sidecar 翻牌，仅追加 living_feed
    except sidecar_edit.StaleProposal as e:
        target["status"] = "stale"
        target["stale_reason"] = str(e)
        _save_queue(pending)
        return {"proposal_id": proposal_id, "status": "stale", "reason": str(e)}

    target["writeback_done"] = True
    if not target.get("living_feed_appended") and target.get("living_feed_entry"):
        _append_living_feed(slug, variant, target["living_feed_entry"])
        target["living_feed_appended"] = True
    # 把巡检证据注册进 web_search 库(addressed 到 signpost/kill 锚点),让 05 gap 体检
    # 数得到、独立反方拿得到——否则巡检搜的料只躺在 living_feed 散文里,重评得重搜。
    # URL 去重幂等;失败不回滚翻牌但在 proposal 上留痕(evidence_register_error)。零 LLM。
    if kind in ("signpost", "kill") and not target.get("evidence_registered"):
        try:
            anchor = _anchor_for(slug, variant, kind, target.get("locator"))
            res = _register_proposal_evidence(slug, variant, target, anchor)
            if res is not None:
                target["registered_mat_ids"] = [m for m in res.get("mat_ids") or [] if m]
                target["evidence_anchor"] = anchor
                target["evidence_registered"] = True
                target.pop("evidence_register_error", None)
        except Exception as e:  # 缺 manifest / 占位 URL 等 → 留痕,不阻断翻牌
            target["evidence_register_error"] = str(e)

    target["status"] = "confirmed"
    target["confirmed_at"] = _now_iso()
    _save_queue(pending)

    # 重大变更(kill 触发 / signpost 翻 bear)→ 盖"待重评 thesis"戳,详情页常驻横幅,
    # 跑过 04/05 后由 get_pending_thesis_review 自动判消。盖戳失败不回滚翻牌。
    if target.get("requires_thesis_review"):
        try:
            from prism.scripts.topic import set_pending_thesis_review
            set_pending_thesis_review(
                slug, variant,
                reason=target.get("rationale") or f"{kind} 触发({target.get('proposed_value')})",
                proposal_id=proposal_id,
                locator=target.get("locator"),
            )
        except Exception:
            pass  # 盖戳失败仅丢横幅,不影响已落盘的翻牌

    return {"proposal_id": proposal_id, "status": "confirmed", "noop": False,
            "requires_thesis_review": target.get("requires_thesis_review", False),
            "registered_mat_ids": target.get("registered_mat_ids") or [],
            "evidence_register_error": target.get("evidence_register_error")}


def confirm_all() -> dict:
    """确认所有 awaiting_confirm proposal。返回逐条结果。"""
    results = []
    for p in load_queue():
        if p.get("status") == "awaiting_confirm":
            results.append(confirm_flip(p["proposal_id"]))
    return {"confirmed": results, "count": len(results)}


def discard_flip(proposal_id: str) -> dict:
    """丢弃一条 proposal(标 discarded,不回写)。"""
    pending = load_queue()
    target = next((p for p in pending if p["proposal_id"] == proposal_id), None)
    if target is None:
        raise ValueError(f"proposal {proposal_id!r} 不存在")
    target["status"] = "discarded"
    _save_queue(pending)
    return {"proposal_id": proposal_id, "status": "discarded"}


# ── CLI(供 headless claude 读 scan 结果)─────────────────────────────────────

def _print_scan(within_days: int) -> None:
    import json
    scan = scan_due_events(within_days=within_days)
    print(json.dumps(scan, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    within = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    if cmd == "scan":
        _print_scan(within)
    elif cmd == "price":
        import json
        print(json.dumps(propose_price_breaches(within), ensure_ascii=False, indent=2))
    elif cmd == "macro":
        import json
        print(json.dumps(propose_macro_updates(within), ensure_ascii=False, indent=2))
    else:
        print(f"unknown command: {cmd}（支持 scan / price / macro）", file=sys.stderr)
        sys.exit(1)
