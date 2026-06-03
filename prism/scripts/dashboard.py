"""Generate prism/dashboard.md — investment decision dashboard.

Usage:
    python -m prism.scripts.dashboard
    python -c "from prism.scripts.dashboard import build; build()"
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import yaml

PRISM_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_PATH = PRISM_ROOT / "dashboard.md"


# ── helpers ──────────────────────────────────────────────────────────────────

def _load_sidecar(slug: str, variant: str) -> dict | None:
    path = PRISM_ROOT / "topics" / slug / variant / "outputs" / "07_decision_kit.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None


def _load_industry_sidecar(slug: str, variant: str) -> dict | None:
    path = PRISM_ROOT / "topics" / slug / variant / "outputs" / "09_industry_to_arenas.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None


def _load_arena_sidecar(slug: str, variant: str) -> dict | None:
    path = PRISM_ROOT / "topics" / slug / variant / "outputs" / "10_peer_matrix.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None


def _load_monitor_queue() -> list[dict]:
    """Read pending proposals from monitor_queue.yaml (daily-monitor staging).

    Read directly (not via monitor.py) to avoid a circular import — monitor.py
    imports dashboard.canonical_variant. Returns only awaiting_confirm proposals.
    """
    path = PRISM_ROOT / "monitor_queue.yaml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    pending = data.get("pending") or []
    return [p for p in pending if p.get("status") == "awaiting_confirm"]


def _fetch_price(ticker: str) -> dict:
    """Fetch current price via the existing market_data machinery."""
    if not ticker:
        return {}
    market, code = ("", ticker)
    if "_" in ticker:
        market, code = ticker.split("_", 1)
    try:
        from scripts.fetch_quotes_eod import run_for_ticker
        run_for_ticker(code, market)
    except Exception:
        pass
    try:
        from app.io import quotes as quotes_io
        latest = quotes_io.latest_for(code)
        if latest:
            return {
                "close": latest.get("close"),
                "date": str(latest.get("date", "")),
                "pe_ttm": latest.get("pe_ttm"),
            }
    except Exception:
        pass
    return {}


def _locate_zone(price: float, buy_box: dict) -> str:
    """Return buy zone label for a given price."""
    if not price or not buy_box:
        return "unknown"
    strong_max = buy_box.get("strong_buy_max")
    acc_max = buy_box.get("accumulate_max")
    hold_max = buy_box.get("hold_max")
    if strong_max and price <= strong_max:
        return "strong_buy"
    if acc_max and price <= acc_max:
        return "accumulate"
    if hold_max and price <= hold_max:
        return "hold"
    return "above_hold"


def _zone_emoji(zone: str) -> str:
    return {
        "strong_buy": "🟢 强力买入",
        "accumulate": "🔵 可建仓",
        "hold": "🟡 观望",
        "above_hold": "🔴 高于观望区",
        "unknown": "⚪ 未知",
    }.get(zone, zone)


def _gap_to_buy(price: float, buy_box: dict) -> str | None:
    """Distance from current price to the top of strong_buy zone."""
    if not price or not buy_box:
        return None
    strong_max = buy_box.get("strong_buy_max")
    if not strong_max:
        return None
    pct = (price - strong_max) / strong_max * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.0f}%"


def _days_stale(generated_str: str | None) -> int | None:
    if not generated_str:
        return None
    try:
        if isinstance(generated_str, datetime):
            dt = generated_str
        else:
            dt = datetime.fromisoformat(str(generated_str).replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return max(0, delta.days)
    except Exception:
        return None


def _freshness_emoji(days: int | None) -> str:
    if days is None:
        return "⚪"
    if days <= 14:
        return "🟢"
    if days <= 45:
        return "🟡"
    return "🔴"


def _fmt_freshness(r: dict) -> str:
    days = r.get("freshness_days")
    emoji = r.get("freshness_emoji", "⚪")
    return f"{emoji} {'?d' if days is None else f'{days}d'}"


def _parse_signpost_date(date_str: Any) -> date | None:
    """Parse a signpost date string → date, or None on failure.

    Handles "2026-Q2" (quarter→month start), "2026" (year), "2026-08" (month),
    and ISO "2026-08-01". Shared by dashboard display (silently skips None) and
    monitor.scan (surfaces the None ones into an `unparseable` bucket — a mistyped
    date means the signpost would NEVER trigger, which is exactly what must be seen).
    """
    s = str(date_str or "").strip()
    if not s:
        return None
    try:
        if "Q" in s:
            year, q = s.split("-Q")
            month = (int(q) - 1) * 3 + 1
            return date(int(year), month, 1)
        if len(s) == 4:
            return date(int(s), 1, 1)
        if len(s) == 7:
            year, month = s.split("-")
            return date(int(year), int(month), 1)
        return date.fromisoformat(s)
    except Exception:
        return None


def _upcoming_signposts(signposts: list[dict], within_days: int = 60) -> list[dict]:
    """Filter signposts expected within `within_days` from today."""
    today = date.today()
    result = []
    for sp in signposts:
        if sp.get("triggered") is not None:
            continue  # already resolved
        sp_date = _parse_signpost_date(sp.get("date"))
        if sp_date is None:
            continue  # unparseable — dashboard skips; monitor.scan reports it
        if (sp_date - today).days <= within_days:
            result.append(sp)
    return result


def _kill_triggered(kill_criteria: list[dict]) -> list[dict]:
    return [k for k in kill_criteria if k.get("status") == "triggered_bull"
            or k.get("status") == "triggered_bear"]


# ── canonical variant (shared by dashboard + monitor) ─────────────────────────

def _sidecar_loader_for(topic_type: str):
    """Pick the sidecar loader matching a topic type (07 company / 09 / 10)."""
    if topic_type == "industry":
        return _load_industry_sidecar
    if topic_type == "arena":
        return _load_arena_sidecar
    return _load_sidecar


def _canonical_variant(topics: list[dict]) -> dict:
    """Pick the canonical variant dict for a slug's topics.

    Order: variant whose type-matched sidecar exists → deepseek-v4-pro → first.
    Single source of truth so dashboard cards and monitor flips never land on
    different variants of the same slug.
    """
    if not topics:
        raise ValueError("topics 不能为空")
    loader = _sidecar_loader_for(topics[0].get("type", ""))
    for t in topics:
        if loader(t["slug"], t.get("variant", "")):
            return t
    for t in topics:
        if t.get("variant") == "deepseek-v4-pro":
            return t
    return topics[0]


def canonical_variant(slug: str) -> str | None:
    """Public: resolve a slug's canonical variant string. None if no topics.

    Used by monitor/watchlist to lock onto the same variant the dashboard renders.
    """
    from prism.scripts.topic import list_topics
    topics = [t for t in list_topics() if t.get("slug") == slug]
    if not topics:
        return None
    return _canonical_variant(topics).get("variant", "")


# ── topic collection ─────────────────────────────────────────────────────────

def _collect_company_rows() -> list[dict]:
    from prism.scripts.topic import list_topics
    rows = []

    slug_variants: dict[str, list[dict]] = {}
    for topic in list_topics():
        if topic.get("type") != "company":
            continue
        slug_variants.setdefault(topic["slug"], []).append(topic)

    for slug, topics in slug_variants.items():
        topic = _canonical_variant(topics)
        variant = topic.get("variant", "")
        sidecar = _load_sidecar(slug, variant)
        if not sidecar:
            rows.append({
                "slug": slug,
                "variant": variant,
                "display_name": topic.get("display_name", slug),
                "ticker": "",
                "missing_sidecar": True,
            })
            continue

        ticker = sidecar.get("ticker", "")
        price_data = _fetch_price(ticker)
        price = price_data.get("close") or sidecar.get("buy_box", {}).get("current_price")
        price_date = price_data.get("date") or sidecar.get("buy_box", {}).get("price_as_of", "")
        buy_box = sidecar.get("buy_box", {})
        zone = _locate_zone(price, buy_box) if price else "unknown"
        gap = _gap_to_buy(price, buy_box) if price else None
        days = _days_stale(sidecar.get("generated"))
        upcoming = _upcoming_signposts(sidecar.get("signposts", []))
        kills = _kill_triggered(sidecar.get("kill_criteria", []))
        models = sidecar.get("valuation_models", [])

        rows.append({
            "slug": slug,
            "variant": variant,
            "display_name": sidecar.get("display_name", topic.get("display_name", slug)),
            "ticker": ticker,
            "price": price,
            "price_date": price_date,
            "pe_ttm": price_data.get("pe_ttm"),
            "buy_box": buy_box,
            "zone": zone,
            "zone_label": _zone_emoji(zone),
            "gap_to_buy": gap,
            "position_initial_max": sidecar.get("position_framework", {}).get("initial_max_pct"),
            "position_full_max": sidecar.get("position_framework", {}).get("full_max_pct"),
            "position_tier": sidecar.get("position_framework", {}).get("position_tier"),
            "valuation_models": models,
            "kill_triggered": kills,
            "upcoming_signposts": upcoming,
            "freshness_days": days,
            "freshness_emoji": _freshness_emoji(days),
            "cluster_tags": sidecar.get("cluster_tags", []),
            "missing_sidecar": False,
        })
    return rows


def _collect_non_company_rows() -> list[dict]:
    """Summarise arena/industry topics enriched with 09/10 sidecar data.

    De-duplicates by slug: for slugs with multiple variants, picks the variant
    that has the richest sidecar (09 or 10), falling back to deepseek-v4-pro.
    """
    from prism.scripts.topic import list_topics

    # Group topics by slug, keeping all variants
    slug_variants: dict[str, list[dict]] = {}
    for topic in list_topics():
        if topic.get("type") == "company":
            continue
        slug_variants.setdefault(topic["slug"], []).append(topic)

    rows = []
    for slug, topics in slug_variants.items():
        topic = _canonical_variant(topics)
        slug = topic["slug"]
        variant = topic.get("variant", "")
        topic_type = topic.get("type", "")

        # 07 sidecar (kill/signposts — may not exist for non-company)
        sidecar = _load_sidecar(slug, variant)
        days = _days_stale((sidecar or {}).get("generated"))
        upcoming = _upcoming_signposts((sidecar or {}).get("signposts", []))
        cluster_tags = (sidecar or {}).get("cluster_tags", [])

        row: dict = {
            "slug": slug,
            "variant": variant,
            "display_name": topic.get("display_name", slug),
            "type": topic_type,
            "upcoming_signposts": upcoming,
            "freshness_days": days,
            "freshness_emoji": _freshness_emoji(days),
            "cluster_tags": cluster_tags,
        }

        if topic_type == "industry":
            ind = _load_industry_sidecar(slug, variant)
            if ind:
                row["industry_data"] = ind
                # override freshness from 09 sidecar if 07 absent
                if not days:
                    days09 = _days_stale(ind.get("generated"))
                    row["freshness_days"] = days09
                    row["freshness_emoji"] = _freshness_emoji(days09)
                if not cluster_tags:
                    row["cluster_tags"] = ind.get("cluster_tags", [])
        elif topic_type == "arena":
            arena = _load_arena_sidecar(slug, variant)
            if arena:
                row["arena_data"] = arena
                if not days:
                    days10 = _days_stale(arena.get("generated"))
                    row["freshness_days"] = days10
                    row["freshness_emoji"] = _freshness_emoji(days10)
                if not cluster_tags:
                    row["cluster_tags"] = arena.get("cluster_tags", [])

        rows.append(row)
    return rows


# ── markdown rendering ────────────────────────────────────────────────────────

def _render_valuation_table(models: list[dict]) -> str:
    if not models:
        return ""
    lines = [
        "| 估值模型 | Bull 公允值 | Base 公允值 | Bear 公允值 |",
        "|---------|----------|----------|----------|",
    ]
    for m in models:
        def fmt(v):
            if v is None:
                return "—"
            if isinstance(v, list):
                lo, hi = v
                if lo is None:
                    return f"<{hi}"
                if hi is None:
                    return f">{lo}"
                return f"{lo}–{hi}"
            return str(v)
        lines.append(
            f"| {m.get('label', m.get('name', ''))} "
            f"| {fmt(m.get('bull_fair_value'))} "
            f"| {fmt(m.get('base_fair_value'))} "
            f"| {fmt(m.get('bear_fair_value'))} |"
        )
    return "\n".join(lines)


def _render_dashboard(company_rows: list[dict], other_rows: list[dict]) -> str:
    today_str = date.today().isoformat()
    lines: list[str] = []

    n_industry = sum(1 for r in other_rows if r["type"] == "industry")
    n_arena = sum(1 for r in other_rows if r["type"] == "arena")
    lines += [
        f"# 投资仪表盘",
        f"",
        (f"> 生成：{today_str}　　公司：{len(company_rows)} 个　　"
         f"行业：{n_industry} 个　　竞技场：{n_arena} 个"),
        f"",
    ]

    # ── Section 1: Company decision table ────────────────────────────────────
    lines += [
        "## 公司层：决策清单",
        "",
        "| 公司 | 当前价 | 当前区间 | 距 Buy 区间 | 仓位上限 | Kill | 近期路标 | 数据新鲜度 |",
        "|------|--------|---------|-----------|---------|------|---------|----------|",
    ]
    for r in company_rows:
        if r.get("missing_sidecar"):
            lines.append(
                f"| [{r['display_name']}](/prism/{r['slug']}/{r['variant']}) "
                f"| — | ⚪ 缺 sidecar | — | — | — | — | — |"
            )
            continue
        price_str = f"{r['price']:.2f}" if r.get("price") is not None else "—"
        kill_str = "🚨" if r["kill_triggered"] else "✅"
        signpost_str = f"{len(r['upcoming_signposts'])} 个" if r["upcoming_signposts"] else "—"
        # #5: 优先展示仓位档位（试探/标准/重仓）；initial_max_pct 为档位的可选人工落点
        _init, _tier, _full = r.get("position_initial_max"), r.get("position_tier"), r.get("position_full_max")
        if _tier:
            pos_str = _tier + (f" (≤{_init}%)" if _init else "") + f" / {_full or '—'}%"
        else:
            pos_str = f"{_init or '—'}% / {_full or '—'}%"
        lines.append(
            f"| [{r['display_name']}](/prism/{r['slug']}/{r['variant']}) ({r['ticker']}) "
            f"| {price_str} "
            f"| {r['zone_label']} "
            f"| {r.get('gap_to_buy') or '—'} "
            f"| {pos_str} "
            f"| {kill_str} "
            f"| {signpost_str} "
            f"| {_fmt_freshness(r)} |"
        )

    lines.append("")

    # ── Section 2: Company detail cards ─────────────────────────────────────
    lines += ["## 公司详情", ""]
    for r in company_rows:
        if r.get("missing_sidecar"):
            continue
        lines += [
            f"### {r['display_name']} ({r['ticker']})",
            f"",
        ]

        # Buy box summary
        bb = r["buy_box"]
        price_str_detail = f"{r['price']:.2f}" if r.get("price") is not None else "—"
        lines += [
            "**买入框**",
            "",
            f"| 区间 | 价格 |",
            f"|------|------|",
            f"| 🟢 强力买入 | ≤ {bb.get('strong_buy_max') or '—'} |",
            f"| 🔵 可建仓 | {bb.get('accumulate_min') or '—'} – {bb.get('accumulate_max') or '—'} |",
            f"| 🟡 观望 | {bb.get('hold_min') or '—'} – {bb.get('hold_max') or '—'} |",
            f"| 🔴 高于观望 | > {bb.get('hold_max') or '—'} |",
            f"| **当前** | **{price_str_detail}**（{r.get('price_date') or '—'}）→ {r['zone_label']} |",
            "",
        ]

        # Valuation matrix
        vm = r.get("valuation_models", [])
        if vm:
            lines += ["**估值矩阵**", ""]
            lines.append(_render_valuation_table(vm))
            lines.append("")

        # Kill criteria
        kills = r.get("kill_triggered", [])
        if kills:
            lines += ["**🚨 Kill 已触发**", ""]
            for k in kills:
                lines.append(f"- **{k['id']}**: {k['description']}")
            lines.append("")

        # Upcoming signposts
        upcoming = r.get("upcoming_signposts", [])
        if upcoming:
            lines += ["**近期路标（60天内）**", ""]
            for sp in upcoming:
                event = sp.get('event') or sp.get('signal') or '—'
                lines.append(
                    f"- **{sp['date']}** {event}  "
                    f"（多：{sp.get('bull_signal', '—')} / 空：{sp.get('bear_signal', '—')}）"
                )
            lines.append("")

        lines.append("---")
        lines.append("")

    # ── Section 3: Kill alerts (all companies) ────────────────────────────────
    all_kills = [r for r in company_rows if not r.get("missing_sidecar") and r["kill_triggered"]]
    lines += ["## 🚨 Kill 触发警报", ""]
    if all_kills:
        for r in all_kills:
            for k in r["kill_triggered"]:
                lines.append(f"- **{r['display_name']}** — {k['description']}")
    else:
        lines.append("*当前无 Kill 触发。*")
    lines.append("")

    # ── Section 4: Signpost calendar (all topics) ────────────────────────────
    lines += ["## ⏰ 路标日历（60 天内）", ""]
    all_sp: list[tuple[str, str, dict]] = []
    for r in company_rows:
        if not r.get("missing_sidecar"):
            for sp in r.get("upcoming_signposts", []):
                all_sp.append((sp["date"], r["display_name"], sp))
    for r in other_rows:
        for sp in r.get("upcoming_signposts", []):
            all_sp.append((sp["date"], r["display_name"], sp))
    all_sp.sort(key=lambda x: str(x[0]))
    if all_sp:
        for date_str, name, sp in all_sp:
            event = sp.get('event') or sp.get('signal') or '—'
            lines.append(f"- **{date_str}** [{name}] {event}")
    else:
        lines.append("*60 天内无路标。*")
    lines.append("")

    # ── Section 4b: Pending monitor flips (daily-monitor staging) ─────────────
    queue = _load_monitor_queue()
    lines += ["## 🔔 待确认监控翻牌", ""]
    if queue:
        lines.append("> 由 daily-monitor 自动判读产出，**需在 web 端点确认后才回写**。")
        lines.append("")
        lines += [
            "| 标的 | 类型 | 建议翻牌 | 依据 | 证据 | 需重评 thesis |",
            "|------|------|---------|------|------|--------------|",
        ]
        thesis_review_slugs: list[str] = []
        for p in queue:
            kind = p.get("kind", "")
            target = p.get("locator", "") if kind != "price" else "buy_box"
            val = p.get("proposed_value", "—")
            rationale = (str(p.get("rationale") or "—")).replace("|", "\\|")[:50]
            ev = p.get("evidence_urls") or []
            ev_str = f"{len(ev)} 条" if ev else "⚠️ 无"
            needs = "🔺" if p.get("requires_thesis_review") else "—"
            if p.get("requires_thesis_review"):
                thesis_review_slugs.append(p.get("slug", ""))
            lines.append(
                f"| {p.get('slug', '')} | {kind} ({target}) | {val} "
                f"| {rationale} | {ev_str} | {needs} |"
            )
        lines.append("")
        review = sorted(set(s for s in thesis_review_slugs if s))
        if review:
            lines.append(
                "**🔺 建议重评 thesis**（kill/重大 signpost 触发，请在对话里发起交互式 "
                f"05-critic-review / 重新合成）：{', '.join(review)}"
            )
            lines.append("")
    else:
        lines.append("*当前无待确认翻牌。*")
        lines.append("")

    # ── Section 5: Industry layer ─────────────────────────────────────────────
    industry_rows = [r for r in other_rows if r["type"] == "industry"]
    lines += ["## 行业层：竞技场选择", ""]
    if not industry_rows:
        lines.append("*暂无行业 topic。*\n")
    for r in industry_rows:
        ind = r.get("industry_data")
        days_str = _fmt_freshness(r)
        lines += [
            f"### {r['display_name']} [{days_str}]",
            "",
        ]
        if ind:
            arenas = ind.get("arenas", [])
            deep = [a for a in arenas if a.get("tier") == "deep"]
            watch = [a for a in arenas if a.get("tier") == "watch"]
            elim = [a for a in arenas if a.get("tier") == "eliminated"]

            if deep:
                lines.append("**深度研究竞技场（Deep）**\n")
                lines += [
                    "| 竞技场 | 综合评分 | 已建 topic | 核心逻辑 |",
                    "|--------|---------|-----------|---------|",
                ]
                for a in deep:
                    scores = a.get("scores", {})
                    composite = scores.get("composite", "—")
                    topic_link = (
                        f"[✓](/prism/{a['topic_slug']}/deepseek-v4-pro)"
                        if a.get("topic_created") else "—"
                    )
                    reason = (a.get("tier_reason") or "").replace("|", "\\|")[:60]
                    lines.append(
                        f"| {a['name']} | {composite} | {topic_link} | {reason} |"
                    )
                lines.append("")

            if watch:
                lines.append("**观察竞技场（Watch）**\n")
                lines += [
                    "| 竞技场 | 综合评分 | 升级触发器 |",
                    "|--------|---------|----------|",
                ]
                for a in watch:
                    scores = a.get("scores", {})
                    composite = scores.get("composite", "—")
                    triggers = "; ".join(a.get("upgrade_triggers", []))[:60] or "—"
                    lines.append(f"| {a['name']} | {composite} | {triggers} |")
                lines.append("")

            if elim:
                elim_names = ", ".join(a["name"] for a in elim)
                lines.append(f"**淘汰（Eliminated）**：{elim_names}\n")
        else:
            lines.append("*暂无 09 sidecar，请运行 workflow 09。*\n")
        lines.append("---\n")

    # ── Section 6: Arena layer ────────────────────────────────────────────────
    arena_rows = [r for r in other_rows if r["type"] == "arena"]
    lines += ["## 竞技场层：公司排名", ""]
    if not arena_rows:
        lines.append("*暂无竞技场 topic。*\n")
    for r in arena_rows:
        arena = r.get("arena_data")
        days_str = _fmt_freshness(r)
        lines += [
            f"### {r['display_name']} [{days_str}]",
            "",
        ]
        if arena:
            companies = arena.get("companies", [])
            shortlist = [c for c in companies if c.get("tier") == "shortlist"]
            watch_co = [c for c in companies if c.get("tier") == "watch"]
            elim_co = [c for c in companies if c.get("tier") == "eliminated"]

            if shortlist:
                lines.append("**入围（Shortlist）**\n")
                lines += [
                    "| 公司 | 代码 | 评分 | 已建 topic | 一句话逻辑 |",
                    "|------|------|------|-----------|-----------|",
                ]
                for c in shortlist:
                    topic_link = (
                        f"[✓](/prism/{c['topic_slug']}/deepseek-v4-pro)"
                        if c.get("topic_created") else "—"
                    )
                    thesis = (c.get("thesis_one_liner") or "—").replace("|", "\\|")[:70]
                    lines.append(
                        f"| {c['name']} | {c.get('ticker') or '—'} "
                        f"| {c.get('score', '—')} | {topic_link} | {thesis} |"
                    )
                lines.append("")

            if watch_co:
                lines.append("**观察（Watch）**\n")
                lines += [
                    "| 公司 | 代码 | 评分 | 升级触发器 |",
                    "|------|------|------|----------|",
                ]
                for c in watch_co:
                    triggers = "; ".join(c.get("upgrade_triggers", []))[:60] or "—"
                    lines.append(
                        f"| {c['name']} | {c.get('ticker') or '—'} "
                        f"| {c.get('score', '—')} | {triggers} |"
                    )
                lines.append("")

            if elim_co:
                elim_names = ", ".join(
                    f"{'~~' if c.get('quarantine') else ''}{c['name']}{'~~' if c.get('quarantine') else ''}"
                    for c in elim_co
                )
                lines.append(f"**淘汰（Eliminated）**：{elim_names}\n")
        else:
            lines.append("*暂无 10 sidecar，请运行 workflow 10。*\n")
        lines.append("---\n")

    # ── Section 7: Cross-layer cluster view ──────────────────────────────────
    lines += ["## 跨层主题聚合（Cluster Tags）", ""]
    tag_map: dict[str, list[str]] = {}
    for r in company_rows + other_rows:
        for tag in r.get("cluster_tags", []):
            if not isinstance(tag, str):
                continue  # industry-schema sidecars store cluster dicts here; skip
            tag_map.setdefault(tag, []).append(r["display_name"])
    if tag_map:
        lines += [
            "| 主题标签 | 涉及研究 | 数量 |",
            "|---------|---------|------|",
        ]
        for tag, names in sorted(tag_map.items(), key=lambda x: -len(x[1])):
            names_str = ", ".join(names)[:80]
            lines.append(f"| `{tag}` | {names_str} | {len(names)} |")
    else:
        lines.append("*暂无 cluster tags。*")
    lines.append("")

    # ── Section 8: Data staleness alert ──────────────────────────────────────
    stale = [r for r in (company_rows + other_rows)
             if not r.get("missing_sidecar") and (r.get("freshness_days") or 0) > 45]
    lines += ["## 🟡 数据过期提醒（>45 天）", ""]
    if stale:
        for r in stale:
            lines.append(f"- **{r['display_name']}**：上次更新 {r['freshness_days']} 天前，建议重新生成产出")
    else:
        lines.append("*所有 topic 数据均在 45 天内。*")
    lines.append("")

    return "\n".join(lines)


# ── entry point ───────────────────────────────────────────────────────────────

def build() -> Path:
    """Build dashboard.md and return its path."""
    company_rows = _collect_company_rows()
    other_rows = _collect_non_company_rows()
    content = _render_dashboard(company_rows, other_rows)
    DASHBOARD_PATH.write_text(content, encoding="utf-8")
    print(f"✅ dashboard.md 已生成 → {DASHBOARD_PATH}")
    print(f"   公司：{len(company_rows)} 个，行业/竞技场：{len(other_rows)} 个")
    return DASHBOARD_PATH


if __name__ == "__main__":
    build()
