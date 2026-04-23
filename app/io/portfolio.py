"""Portfolio (positions) markdown table I/O.

positions.md columns:
``ticker | market | entry_date | avg_cost | shares | position_pct | v0_link``

``upsert_position`` side-effect (from DESIGN §7 q4): when a new position is
added and the target V0 has ``status: draft``, flip it to ``active`` and
backfill entry_date + position_size_pct. Already-active V0s are not rewritten.
"""
from datetime import date
from pathlib import Path

from app import config as cfg
from app.io import v0 as v0io

COLUMNS = (
    "ticker",
    "market",
    "entry_date",
    "avg_cost",
    "shares",
    "position_pct",
    "v0_link",
)

_PREAMBLE = "# 当前持仓\n\n"


def _positions_path(base: Path | None) -> Path:
    root = Path(base) / "portfolio" if base else cfg.PORTFOLIO_DIR
    return root / "positions.md"


def _parse_table(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if cells == list(COLUMNS):
            continue
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        if len(cells) != len(COLUMNS):
            continue
        rows.append(dict(zip(COLUMNS, cells)))
    return rows


def _emit(rows: list[dict]) -> str:
    header = "| " + " | ".join(COLUMNS) + " |"
    sep = "|" + "|".join(["---"] * len(COLUMNS)) + "|"
    out = [header, sep]
    for r in rows:
        out.append("| " + " | ".join(str(r.get(c, "")) for c in COLUMNS) + " |")
    return _PREAMBLE + "\n".join(out) + "\n"


def read_positions(base: Path | None = None) -> list[dict]:
    path = _positions_path(base)
    if not path.exists():
        return []
    return _parse_table(path.read_text(encoding="utf-8"))


def _write_positions(rows: list[dict], base: Path | None) -> Path:
    path = _positions_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_emit(rows), encoding="utf-8")
    return path


def total_position_pct(rows: list[dict]) -> float:
    total = 0.0
    for r in rows:
        try:
            total += float(r.get("position_pct") or 0)
        except (TypeError, ValueError):
            pass
    return total


def _maybe_activate_v0(entry: dict, base: Path | None) -> None:
    """If V0 is draft and this is an active buy, promote + backfill."""
    ticker = entry["ticker"]
    market = entry["market"]
    try:
        doc = v0io.read_v0(ticker, market, base=base)
    except FileNotFoundError:
        return
    fm = dict(doc["frontmatter"])
    if fm.get("status") != "draft":
        return

    fm["status"] = "active"
    fm["entry_date"] = entry.get("entry_date") or date.today().isoformat()
    try:
        fm["position_size_pct"] = float(entry.get("position_pct") or 0)
    except (TypeError, ValueError):
        fm["position_size_pct"] = 0
    fm["last_reviewed"] = date.today().isoformat()

    v0io.write_v0(ticker, market, fm, doc["body"], base=base)


def upsert_position(entry: dict, base: Path | None = None) -> Path:
    """Insert or update a position keyed by (market, ticker).

    Triggers ``_maybe_activate_v0`` on every upsert so the V0 status stays
    coherent with the portfolio even if the user adds via CLI later.
    """
    if "ticker" not in entry or "market" not in entry:
        raise ValueError("entry must include ticker and market")

    normalized = {c: str(entry.get(c, "")) for c in COLUMNS}
    rows = read_positions(base)
    key = (normalized["market"], normalized["ticker"])
    replaced = False
    for i, r in enumerate(rows):
        if (r["market"], r["ticker"]) == key:
            rows[i] = normalized
            replaced = True
            break
    if not replaced:
        rows.append(normalized)

    path = _write_positions(rows, base)
    _maybe_activate_v0(normalized, base)
    return path
