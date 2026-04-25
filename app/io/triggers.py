"""Price triggers CRUD + evaluation (DESIGN §3.7 price_triggers table).

A trigger fires when a ticker's latest close crosses the trigger price in the
action's direction:

  buy-direction  (close ≤ trigger_price):  first_entry, add_1, add_2
  sell-direction (close ≥ trigger_price):  trim, exit
  stop-direction (close ≤ trigger_price):  stop_loss

Once ``triggered_at`` is set, the trigger is "fired" and no longer actionable
by the user. Delete or recreate to reset. We do this so waking up once to
"HIMS below $15" and then ignoring it doesn't retrigger every day forever.
"""
from __future__ import annotations

import sqlite3
from datetime import date as date_cls
from pathlib import Path
from typing import Any

from app.io import financials as fin_io

BUY_ACTIONS = ("first_entry", "add_1", "add_2")
SELL_ACTIONS = ("trim", "exit")
STOP_ACTIONS = ("stop_loss",)
ALL_ACTIONS = BUY_ACTIONS + SELL_ACTIONS + STOP_ACTIONS


def direction(action: str) -> str:
    if action in BUY_ACTIONS or action in STOP_ACTIONS:
        return "below"  # triggers when close ≤ trigger_price
    if action in SELL_ACTIONS:
        return "above"  # triggers when close ≥ trigger_price
    raise ValueError(f"unknown action {action!r}; valid: {ALL_ACTIONS}")


def create(
    ticker: str,
    trigger_price: float,
    action: str,
    v0_snapshot_path: str = "",
    created_at: date_cls | None = None,
    base: Path | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Insert a new trigger. Returns the rowid."""
    if action not in ALL_ACTIONS:
        raise ValueError(f"action must be one of {ALL_ACTIONS}")
    if trigger_price <= 0:
        raise ValueError("trigger_price must be > 0")

    ticker = ticker.strip().upper()
    created = (created_at or date_cls.today()).isoformat()
    owns = conn is None
    conn = conn or fin_io.connect(base=base)
    try:
        cur = conn.execute(
            """
            INSERT INTO price_triggers
                (ticker, trigger_price, action, v0_snapshot_path, created_at, triggered_at)
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (ticker, trigger_price, action, v0_snapshot_path or None, created),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        if owns:
            conn.close()


def delete(trigger_rowid: int, base: Path | None = None) -> None:
    conn = fin_io.connect(base=base)
    try:
        conn.execute("DELETE FROM price_triggers WHERE rowid = ?", (trigger_rowid,))
        conn.commit()
    finally:
        conn.close()


def list_for_ticker(
    ticker: str, base: Path | None = None, conn: sqlite3.Connection | None = None
) -> list[dict[str, Any]]:
    owns = conn is None
    conn = conn or fin_io.connect(base=base)
    try:
        rows = conn.execute(
            """
            SELECT rowid AS id, ticker, trigger_price, action,
                   v0_snapshot_path, created_at, triggered_at
            FROM price_triggers
            WHERE ticker = ?
            ORDER BY triggered_at IS NOT NULL, trigger_price
            """,
            (ticker.strip().upper(),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        if owns:
            conn.close()


def list_all(base: Path | None = None) -> list[dict[str, Any]]:
    conn = fin_io.connect(base=base)
    try:
        rows = conn.execute(
            """
            SELECT rowid AS id, ticker, trigger_price, action,
                   v0_snapshot_path, created_at, triggered_at
            FROM price_triggers
            ORDER BY ticker, trigger_price
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _is_crossed(action: str, close: float, trigger_price: float) -> bool:
    if direction(action) == "below":
        return close <= trigger_price
    return close >= trigger_price


def evaluate(
    prices: dict[str, tuple[str, float]],
    today: date_cls | None = None,
    base: Path | None = None,
) -> dict[str, list[dict]]:
    """Mark crossed-but-not-yet-triggered rows as triggered.

    ``prices``: ``{ticker: (date_iso, close)}`` map from ``quotes.latest_prices_map()``.
    Returns ``{"new": [...], "already": [...], "armed": [...]}`` — the
    "new" list are rows triggered by *this* call.
    """
    today = today or date_cls.today()
    conn = fin_io.connect(base=base)
    new: list[dict] = []
    already: list[dict] = []
    armed: list[dict] = []
    try:
        rows = conn.execute(
            """SELECT rowid AS id, ticker, trigger_price, action, triggered_at
               FROM price_triggers"""
        ).fetchall()
        for r in rows:
            record = dict(r)
            latest = prices.get(r["ticker"])
            if not latest:
                armed.append(record)
                continue
            _, close = latest
            crossed = _is_crossed(r["action"], close, r["trigger_price"])
            record["latest_price"] = close
            if r["triggered_at"]:
                already.append(record)
                continue
            if crossed:
                conn.execute(
                    "UPDATE price_triggers SET triggered_at = ? WHERE rowid = ?",
                    (today.isoformat(), r["id"]),
                )
                record["triggered_at"] = today.isoformat()
                new.append(record)
            else:
                armed.append(record)
        conn.commit()
    finally:
        conn.close()
    return {"new": new, "already": already, "armed": armed}


def reset(trigger_rowid: int, base: Path | None = None) -> None:
    """Clear ``triggered_at`` so the trigger can fire again."""
    conn = fin_io.connect(base=base)
    try:
        conn.execute(
            "UPDATE price_triggers SET triggered_at = NULL WHERE rowid = ?",
            (trigger_rowid,),
        )
        conn.commit()
    finally:
        conn.close()
