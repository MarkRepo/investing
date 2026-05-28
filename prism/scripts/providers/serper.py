from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from .base import Hit, ProviderError, NoKeyAvailable
from .keypool import KeyPool

_BASE = "https://google.serper.dev"
_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
_FREE_QUOTA_PER_DAY = 80


def _load_keys() -> list[str]:
    raw = os.environ.get("SERPER_API_KEY")
    if not raw and _SETTINGS_PATH.exists():
        data = json.loads(_SETTINGS_PATH.read_text())
        raw = data.get("env", {}).get("SERPER_API_KEY")
    if not raw:
        raise RuntimeError("SERPER_API_KEY 未配置")
    if isinstance(raw, list):
        return [k.strip() for k in raw if k and k.strip()]
    return [k.strip() for k in re.split(r"[,\n]", raw) if k.strip()]


_INTENT_TO_ENDPOINT = {
    "news":              "/news",
    "vertical:patent":   "/patents",
    "vertical:scholar":  "/scholar",
    "vertical:image":    "/images",
    "vertical:map":      "/maps",
}
_INTENT_TO_KEY = {
    "news":              "news",
    "vertical:patent":   "organic",
    "vertical:scholar":  "organic",
    "vertical:image":    "images",
    "vertical:map":      "places",
}


class SerperProvider:
    name = "serper"
    capabilities = {"general", "news", "exact", "patent", "scholar",
                    "image", "map"}

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
        endpoint = _INTENT_TO_ENDPOINT.get(intent, "/search")
        list_key = _INTENT_TO_KEY.get(intent, "organic")

        q = query
        if include_domains:
            q += " " + " OR ".join(f"site:{d}" for d in include_domains)
        if exclude_domains:
            q += " " + " ".join(f"-site:{d}" for d in exclude_domains)

        payload: dict = {"q": q, "num": max_results}
        if days is not None and intent == "news":
            payload["tbs"] = (
                "qdr:d" if days <= 1 else
                "qdr:w" if days <= 7 else
                "qdr:m" if days <= 31 else
                "qdr:y"
            )

        last_err: Exception | None = None
        for _ in range(len(self.pool.keys)):
            try:
                key = self.pool.acquire()
            except NoKeyAvailable as e:
                raise ProviderError("serper: all keys exhausted",
                                    provider=self.name, retryable=False) from e

            req = urllib.request.Request(
                _BASE + endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "X-API-KEY": key},
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
                raise ProviderError(f"serper: HTTP {e.code}",
                                    provider=self.name) from e
            except urllib.error.URLError as e:
                last_err = e
                continue
            else:
                self.pool.record_success(key)
                return [
                    Hit(
                        title=r.get("title", ""),
                        url=r.get("link", "") or r.get("imageUrl", ""),
                        snippet=r.get("snippet", "") or r.get("description", ""),
                        score=1.0 / r.get("position", 1),
                        published_at=r.get("date"),
                        source_provider=self.name,
                    )
                    for r in data.get(list_key, [])
                ]
        raise ProviderError("serper: all keys failed",
                            provider=self.name) from last_err
