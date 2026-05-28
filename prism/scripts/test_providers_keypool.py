from datetime import datetime, timedelta, timezone

import pytest

from prism.scripts.providers.keypool import KeyPool
from prism.scripts.providers.base import NoKeyAvailable


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "prism.scripts.providers.keypool._STATE_PATH",
        tmp_path / "web_search_keys.json",
    )
    return tmp_path / "web_search_keys.json"


def test_acquire_picks_least_used(tmp_state):
    pool = KeyPool("tavily", ["k1aaaa", "k2bbbb", "k3cccc"], free_quota_per_day=10)
    pool.state[pool._fp("k1aaaa")].used_today = 5
    pool.state[pool._fp("k2bbbb")].used_today = 2
    pool.state[pool._fp("k3cccc")].used_today = 7
    assert pool.acquire() == "k2bbbb"


def test_record_429_cools_down_then_excludes(tmp_state):
    pool = KeyPool("tavily", ["k1aaaa", "k2bbbb"], free_quota_per_day=10)
    pool.record_429("k1aaaa")
    assert pool.acquire() == "k2bbbb"


def test_acquire_raises_when_all_exhausted(tmp_state):
    pool = KeyPool("tavily", ["k1aaaa"], free_quota_per_day=10)
    pool.state[pool._fp("k1aaaa")].used_today = 10
    with pytest.raises(NoKeyAvailable) as exc:
        pool.acquire()
    assert exc.value.provider == "tavily"


def test_record_403_disables_key_permanently(tmp_state):
    pool = KeyPool("tavily", ["k1aaaa", "k2bbbb"], free_quota_per_day=10)
    pool.record_403("k1aaaa")
    assert pool.state[pool._fp("k1aaaa")].disabled is True
    assert pool.acquire() == "k2bbbb"


def test_state_persists_across_instances(tmp_state):
    pool1 = KeyPool("tavily", ["k1aaaa"], free_quota_per_day=10)
    pool1.record_success("k1aaaa")
    pool1.record_success("k1aaaa")
    pool2 = KeyPool("tavily", ["k1aaaa"], free_quota_per_day=10)
    assert pool2.state[pool2._fp("k1aaaa")].used_today == 2


def test_quota_resets_at_utc_midnight(tmp_state):
    pool = KeyPool("tavily", ["k1aaaa"], free_quota_per_day=10)
    fp = pool._fp("k1aaaa")
    pool.state[fp].used_today = 10
    pool.state[fp].reset_at = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    pool._maybe_reset(pool.state[fp])
    assert pool.state[fp].used_today == 0


def test_fingerprint_does_not_leak_key(tmp_state):
    pool = KeyPool("tavily", ["super-secret-key-1234567890"], free_quota_per_day=10)
    fp = pool._fp("super-secret-key-1234567890")
    assert "secret" not in fp
    assert len(fp) == 16
