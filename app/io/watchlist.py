"""Watchlist (observation pool) markdown table I/O.

Three stages: ``prefilter`` / ``researching`` / ``price-triggers``. Each stage
is a markdown file with a single GitHub-flavored table. Columns are
stage-specific.

Discipline (DESIGN §3.9):
- ``source_type`` in prefilter must be one of ``SOURCE_TYPES`` — forbids
  "news / friend recommendation / hot list" from entering the pool.
- Moving prefilter → researching requires ``date_added + STALE_DAYS ≤ today``
  AND three-question gate answered (gate_*` fields).
"""
from datetime import date as date_cls
from pathlib import Path

from app import config as cfg

STAGES = ("prefilter", "researching", "price-triggers")

SOURCE_TYPES = ("quant_screen", "qual_radar", "product_experience")
STALE_DAYS = 7
RESEARCHING_MAX = 2  # DESIGN §8 坑 8: 同时最多 2 家 researching

GATE_QUESTIONS = (
    ("gate_competence", "这家公司大致在我的能力圈里吗？（或我愿意投入时间学）"),
    ("gate_mispricing", "当前价格有没有明显的错误定价信号？（估值分位极端 / 市场认知偏差）"),
    ("gate_genuine_interest", "我对它真的有兴趣吗？（不是 FOMO，不是『应该研究』）"),
)

COLUMNS: dict[str, tuple[str, ...]] = {
    "prefilter": ("date_added", "ticker", "source_type", "source", "notes"),
    "researching": ("started", "ticker", "gap_focus", "target_finish", "gate_notes"),
    "price-triggers": ("set_on", "ticker", "first_entry_price", "add1_price", "add2_price", "v0_link"),
}


def _watchlist_path(stage: str, base: Path | None) -> Path:
    if stage not in STAGES:
        raise ValueError(f"unknown stage {stage!r}; valid: {STAGES}")
    root = Path(base) / "watchlist" if base else cfg.WATCHLIST_DIR
    return root / f"{stage}.md"


def _parse_table(text: str, columns: tuple[str, ...]) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or not s.endswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        # skip header + separator rows
        if cells == list(columns):
            continue
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        if len(cells) != len(columns):
            continue
        rows.append(dict(zip(columns, cells)))
    return rows


def _emit_table(columns: tuple[str, ...], rows: list[dict]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "|" + "|".join(["---"] * len(columns)) + "|"
    out_lines = [header, sep]
    for r in rows:
        cells = [str(r.get(c, "")) for c in columns]
        out_lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(out_lines) + "\n"


_HEADER_MARKERS = {
    "prefilter": "# 观察池 · 预筛段",
    "researching": "# 观察池 · 正在研究段",
    "price-triggers": "# 观察池 · 价格触发段",
}


def _preamble_for(stage: str) -> str:
    """Return the fixed preamble (title + blockquote note) for a stage file."""
    if stage == "prefilter":
        return (
            "# 观察池 · 预筛段\n\n"
            "> 新候选入池的第一站。必须先在这里静置至少 1 周再走预筛三问。\n"
            "> 禁止快速路径（看新闻当天进研究、朋友强推直接研究、涨幅榜追热点）。\n\n"
        )
    if stage == "researching":
        return (
            "# 观察池 · 正在研究段\n\n"
            "> 预筛三问全过 → 从 prefilter 进入此段。\n"
            "> 上限：同时最多 2 家（防止过度研究，DESIGN §8 坑 8）。\n\n"
        )
    return (
        "# 观察池 · 价格触发段\n\n"
        "> 研究完成、V0 已写，等价格到区间。\n"
        "> 此段公司**不主动研究**——已经研究过了，等价格。\n\n"
    )


def read_watchlist(stage: str, base: Path | None = None) -> list[dict]:
    path = _watchlist_path(stage, base)
    if not path.exists():
        return []
    return _parse_table(path.read_text(encoding="utf-8"), COLUMNS[stage])


def _write_stage(stage: str, rows: list[dict], base: Path | None) -> Path:
    path = _watchlist_path(stage, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _preamble_for(stage) + _emit_table(COLUMNS[stage], rows)
    path.write_text(text, encoding="utf-8")
    return path


def append_watchlist(stage: str, entry: dict, base: Path | None = None) -> Path:
    """Append a row to ``stage``. Validates prefilter ``source_type`` if set."""
    if stage == "prefilter":
        st = str(entry.get("source_type", "")).strip()
        if st and st not in SOURCE_TYPES:
            raise ValueError(
                f"source_type must be one of {SOURCE_TYPES}, got {st!r}. "
                "News / hot-list / friend recommendations are not valid sources (DESIGN §3.9)."
            )
    rows = read_watchlist(stage, base)
    normalized = {c: str(entry.get(c, "")) for c in COLUMNS[stage]}
    rows.append(normalized)
    return _write_stage(stage, rows, base)


def _parse_date(s: str) -> date_cls | None:
    try:
        return date_cls.fromisoformat(s.strip())
    except (ValueError, AttributeError):
        return None


def move_watchlist(
    ticker: str,
    from_stage: str,
    to_stage: str,
    extra: dict | None = None,
    base: Path | None = None,
    today: date_cls | None = None,
    gate_answers: dict[str, str] | None = None,
    gate_reasons: dict[str, str] | None = None,
) -> None:
    """Remove ``ticker`` from ``from_stage`` and insert into ``to_stage``.

    ``extra`` provides columns needed by the destination stage that the
    source row doesn't have (e.g. ``started`` when moving into researching).

    Discipline on prefilter → researching (DESIGN §3.9):
    - row's ``date_added`` + STALE_DAYS must be ≤ today
    - all three GATE_QUESTIONS must be answered ``yes`` with reason ≥ 30 chars
    """
    if from_stage == to_stage:
        raise ValueError("from_stage and to_stage must differ")

    src_rows = read_watchlist(from_stage, base)
    source_row = next((r for r in src_rows if r["ticker"] == ticker), None)
    if source_row is None:
        raise LookupError(f"{ticker} not in {from_stage}")

    if from_stage == "prefilter" and to_stage == "researching":
        current_researching = read_watchlist("researching", base)
        if len(current_researching) >= RESEARCHING_MAX:
            current_tickers = [r.get("ticker", "") for r in current_researching]
            raise ValueError(
                f"researching already has {len(current_researching)} names "
                f"({', '.join(current_tickers)}); cap is {RESEARCHING_MAX} "
                "(DESIGN §8 坑 8 — 过度研究观察池). Finish one first."
            )
        t = today or date_cls.today()
        d = _parse_date(source_row.get("date_added", ""))
        if d is None:
            raise ValueError(
                f"{ticker}: date_added missing/invalid; cannot confirm 7-day seasoning."
            )
        delta = (t - d).days
        if delta < STALE_DAYS:
            raise ValueError(
                f"{ticker}: only {delta} day(s) since date_added={d.isoformat()}; "
                f"must wait {STALE_DAYS} days before moving to researching (DESIGN §3.9)."
            )
        gate_answers = gate_answers or {}
        gate_reasons = gate_reasons or {}
        missing: list[str] = []
        for qid, _ in GATE_QUESTIONS:
            if gate_answers.get(qid, "").lower() != "yes":
                missing.append(f"{qid}=not_yes")
                continue
            if len(gate_reasons.get(qid, "").strip()) < 30:
                missing.append(f"{qid}=reason<30")
        if missing:
            raise ValueError(
                "three-question gate not satisfied: " + ", ".join(missing)
                + " (each answer must be yes + reason ≥ 30 chars)."
            )
        # Store the gate record in the researching row for audit.
        # Use " ; " separator (not "|") since rows are pipe-delimited in markdown.
        gate_summary = " ; ".join(
            f"{qid}: {gate_reasons.get(qid, '').strip()}" for qid, _ in GATE_QUESTIONS
        )
        extra = {**(extra or {}), "gate_notes": gate_summary}

    src_rows = [r for r in src_rows if r["ticker"] != ticker]
    _write_stage(from_stage, src_rows, base)

    merged = {**source_row, **(extra or {})}
    append_watchlist(to_stage, merged, base)


def researching_status(
    row: dict, today: date_cls | None = None
) -> str:
    """Return one of ``on_track`` / ``due`` / ``overdue`` / ``unset``.

    - ``on_track``: today ≤ target_finish
    - ``due``: target_finish < today ≤ target_finish + 7
    - ``overdue``: today > target_finish + 7
    - ``unset``: target_finish missing/invalid
    """
    t = today or date_cls.today()
    target = _parse_date(row.get("target_finish", ""))
    if target is None:
        return "unset"
    if t <= target:
        return "on_track"
    if (t - target).days <= 7:
        return "due"
    return "overdue"
