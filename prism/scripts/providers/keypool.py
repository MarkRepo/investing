from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .base import NoKeyAvailable

_STATE_PATH = Path.home() / ".claude" / "projects" / "-Users-yangqi-investing" / "state" / "web_search_keys.json"

_BACKOFF_LADDER = [60, 300, 1800]


@dataclass
class KeyState:
    fingerprint: str
    used_today: int = 0
    reset_at: str | None = None
    cooldown_until: str | None = None
    consecutive_429: int = 0
    last_success: str | None = None
    disabled: bool = False


class KeyPool:
    def __init__(self, provider: str, keys: list[str], free_quota_per_day: int):
        self.provider = provider
        self.keys = [k for k in keys if k]
        if not self.keys:
            raise ValueError(f"{provider}: empty key list")
        self.free_quota = free_quota_per_day
        self.state: dict[str, KeyState] = {}
        self._load_state()

    @staticmethod
    def _fp(key: str) -> str:
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return f"{h[:8]}{h[-8:]}"

    def _ensure(self, key: str) -> KeyState:
        fp = self._fp(key)
        if fp not in self.state:
            self.state[fp] = KeyState(fingerprint=fp)
        return self.state[fp]

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _maybe_reset(self, st: KeyState) -> None:
        if st.reset_at is None:
            tomorrow = (self._now() + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            st.reset_at = tomorrow.isoformat()
            return
        reset = datetime.fromisoformat(st.reset_at)
        if self._now() >= reset:
            st.used_today = 0
            tomorrow = (self._now() + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0)
            st.reset_at = tomorrow.isoformat()

    def acquire(self) -> str:
        now = self._now()
        candidates: list[tuple[int, str]] = []
        soonest: datetime | None = None

        for key in self.keys:
            st = self._ensure(key)
            self._maybe_reset(st)
            if st.disabled:
                continue
            if st.cooldown_until is not None:
                cd = datetime.fromisoformat(st.cooldown_until)
                if cd > now:
                    soonest = cd if soonest is None else min(soonest, cd)
                    continue
                st.cooldown_until = None
            if st.used_today >= self.free_quota:
                continue
            candidates.append((st.used_today, key))

        if not candidates:
            self._persist()
            raise NoKeyAvailable(provider=self.provider, soonest_recovery=soonest)

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    def record_success(self, key: str) -> None:
        st = self._ensure(key)
        st.used_today += 1
        st.last_success = self._now().isoformat()
        st.consecutive_429 = 0
        st.cooldown_until = None
        self._persist()

    def record_429(self, key: str, retry_after: int | None = None) -> None:
        st = self._ensure(key)
        st.consecutive_429 += 1
        idx = min(st.consecutive_429 - 1, len(_BACKOFF_LADDER) - 1)
        backoff = retry_after if retry_after is not None else _BACKOFF_LADDER[idx]
        st.cooldown_until = (self._now() + timedelta(seconds=backoff)).isoformat()
        self._persist()

    def record_403(self, key: str) -> None:
        st = self._ensure(key)
        st.disabled = True
        self._persist()

    def status(self) -> dict:
        out: dict = {"provider": self.provider, "free_quota": self.free_quota, "keys": []}
        for key in self.keys:
            st = self._ensure(key)
            out["keys"].append(asdict(st))
        return out

    def _load_state(self) -> None:
        if not _STATE_PATH.exists():
            for k in self.keys:
                self._ensure(k)
            return
        raw = json.loads(_STATE_PATH.read_text())
        for fp, data in raw.get(self.provider, {}).items():
            self.state[fp] = KeyState(**data)
        for k in self.keys:
            self._ensure(k)

    def _persist(self) -> None:
        _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if _STATE_PATH.exists():
            raw = json.loads(_STATE_PATH.read_text())
        else:
            raw = {}
        raw[self.provider] = {fp: asdict(st) for fp, st in self.state.items()}
        _STATE_PATH.write_text(json.dumps(raw, indent=2, ensure_ascii=False))
