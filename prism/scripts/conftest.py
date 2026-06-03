"""Shared fixtures for monitor / sidecar_edit / watchlist tests.

Builds an isolated PRISM_ROOT in a tmpdir with one company topic + a sidecar
(07_decision_kit.yaml) crafted to exercise the tricky cases:
  - two signposts on the SAME date (2026-08-01) → locator must disambiguate
  - one overdue signpost, one far-future signpost
  - one signpost with a garbage date → unparseable bucket
  - one due kill (pending), one far-future kill
  - a buy_box for price-breach tests
market_data.get_quote is stubbed so scans never hit the network.
"""
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from prism.scripts import topic as topic_io

SLUG = "test-hood"
VARIANT = "claude-opus-4-7"

_SIDECAR = {
    "slug": SLUG,
    "variant": VARIANT,
    "topic_type": "company",
    "display_name": "Test HOOD",
    "ticker": "NASDAQ_HOOD",
    "generated": "2026-05-26T00:00:00Z",
    "buy_box": {
        "strong_buy_max": 55,
        "accumulate_min": 55,
        "accumulate_max": 65,
        "hold_min": 65,
        "hold_max": 80,
        "current_price": 73.64,
    },
    "kill_criteria": [
        {"id": "kill_due", "description": "due kill", "status": "pending",
         "check_at": "2026-05-01"},          # overdue → due
        {"id": "kill_future", "description": "future kill", "status": "pending",
         "check_at": "2027-12-31"},          # far future → not due
        {"id": "kill_baddate", "description": "bad date kill", "status": "pending",
         "check_at": "soon-ish"},            # unparseable
    ],
    "signposts": [
        {"date": "2026-05-01", "event": "overdue event",
         "bull_signal": "b", "bear_signal": "x", "triggered": None},   # due
        {"date": "2026-08-01", "event": "Rule 605",
         "bull_signal": "b", "bear_signal": "x", "triggered": None},   # dup date #1
        {"date": "2026-08-01", "event": "SCHW Q2",
         "bull_signal": "b", "bear_signal": "x", "triggered": None},   # dup date #2
        {"date": "2027-06-01", "event": "far future",
         "bull_signal": "b", "bear_signal": "x", "triggered": None},   # not due
        {"date": "garbage", "event": "bad date event",
         "bull_signal": "b", "bear_signal": "x", "triggered": None},   # unparseable
    ],
}


def _patch_roots(monkeypatch, tmpdir: Path) -> None:
    monkeypatch.setattr("prism.scripts.topic.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.manifest._PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.dashboard.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.sidecar_edit.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.monitor.PRISM_ROOT", tmpdir)
    monkeypatch.setattr("prism.scripts.monitor.WATCHLIST_PATH", tmpdir / "watchlist.yaml")
    monkeypatch.setattr("prism.scripts.monitor.QUEUE_PATH", tmpdir / "monitor_queue.yaml")
    # web_prescan 有自己的 PRISM_ROOT（confirm 注册证据写 inbox/web_search_log 走它）——
    # 不 patch 会让 register_web_search_batch 泄漏进真实仓库树。
    monkeypatch.setattr("prism.scripts.web_prescan.PRISM_ROOT", tmpdir)


def _write_sidecar(tmpdir: Path, slug: str, variant: str, sidecar: dict) -> None:
    out = tmpdir / "topics" / slug / variant / "outputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "07_decision_kit.yaml").write_text(
        yaml.dump(sidecar, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )


@pytest.fixture
def monitor_env(monkeypatch):
    """Isolated PRISM_ROOT + one company topic with the crafted sidecar.

    Yields (slug, variant, tmpdir). market_data.get_quote stubbed to a price
    in the HOLD zone (no breach) by default; tests can re-stub.
    """
    tmpdir = Path(tempfile.mkdtemp())
    _patch_roots(monkeypatch, tmpdir)
    (tmpdir / "topics" / SLUG / VARIANT).mkdir(parents=True)
    topic_io.create_topic(
        slug=SLUG, display_name="Test HOOD", topic_type="company",
        question="Q?", geo="US", depth="deep", variant=VARIANT,
        short_name="HOOD", ticker="NASDAQ_HOOD",
    )
    _write_sidecar(tmpdir, SLUG, VARIANT, _SIDECAR)

    # stub price → hold zone (73.64), no breach, no network
    def _fake_quote(slug, variant):
        return {"ticker": "HOOD", "market": "NASDAQ", "close": 73.64, "date": "2026-06-03"}
    monkeypatch.setattr("prism.scripts.market_data.get_quote", _fake_quote)

    yield SLUG, VARIANT, tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)
