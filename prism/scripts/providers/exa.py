from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from .base import Hit, ProviderError, NoKeyAvailable
from .keypool import KeyPool

_ENDPOINT = "https://api.exa.ai/search"
_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
_FREE_QUOTA_PER_DAY = 30


def _load_keys() -> list[str]:
    raw = os.environ.get("EXA_API_KEY")
    if not raw and _SETTINGS_PATH.exists():
        data = json.loads(_SETTINGS_PATH.read_text())
        raw = data.get("env", {}).get("EXA_API_KEY")
    if not raw:
        raise RuntimeError("EXA_API_KEY 未配置")
    if isinstance(raw, list):
        return [k.strip() for k in raw if k and k.strip()]
    return [k.strip() for k in re.split(r"[,\n]", raw) if k.strip()]


_INTENT_TO_CATEGORY = {
    "vertical:scholar": "research paper",
    "vertical:patent":  "research paper",
}


class ExaProvider:
    name = "exa"
    capabilities = {"semantic", "scholar", "general"}

    def __init__(self, keys: list[str] | None = None, timeout_s: int = 30):
        self.pool = KeyPool(self.name, keys or _load_keys(), _FREE_QUOTA_PER_DAY)
        self.timeout_s = timeout_s

    def healthy(self) -> bool:
        try:
            self.pool.acquire()
            return True
        except NoKeyAvailable:
            return False

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        days: int | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        need_extract: bool = False,
        intent: str | None = None,
    ) -> list[Hit]:
        last_err: Exception | None = None
        for _ in range(len(self.pool.keys)):
            try:
                key = self.pool.acquire()
            except NoKeyAvailable as e:
                raise ProviderError("exa: all keys exhausted",
                                    provider=self.name, retryable=False) from e

            payload: dict = {
                "query": query,
                "numResults": max_results,
                "useAutoprompt": True,
                "contents": {"text": True} if need_extract else {"highlights": True},
            }
            if intent and intent in _INTENT_TO_CATEGORY:
                payload["category"] = _INTENT_TO_CATEGORY[intent]
            if include_domains:
                payload["includeDomains"] = include_domains
            if exclude_domains:
                payload["excludeDomains"] = exclude_domains
            if days is not None:
                from datetime import datetime, timedelta, timezone
                start = (datetime.now(timezone.utc) -
                         timedelta(days=days)).date().isoformat()
                payload["startPublishedDate"] = start

            req = urllib.request.Request(
                _ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": key,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    self.pool.record_429(key)
                    last_err = e
                    continue
                if e.code in (401, 403):
                    self.pool.record_403(key)
                    last_err = e
                    continue
                raise ProviderError(f"exa: HTTP {e.code}",
                                    provider=self.name) from e
            except urllib.error.URLError as e:
                last_err = e
                continue
            else:
                self.pool.record_success(key)
                return [
                    Hit(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=(r.get("text") or
                                 " ".join(r.get("highlights", [])) or "")[:500],
                        score=r.get("score"),
                        raw_content=r.get("text"),
                        published_at=r.get("publishedDate"),
                        source_provider=self.name,
                    )
                    for r in data.get("results", [])
                ]
        raise ProviderError("exa: all keys failed",
                            provider=self.name) from last_err
