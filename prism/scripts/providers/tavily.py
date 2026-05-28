from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from .base import Hit, ProviderError, NoKeyAvailable
from .keypool import KeyPool

_ENDPOINT = "https://api.tavily.com/search"
_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
_FREE_QUOTA_PER_DAY = 33


def _load_keys() -> list[str]:
    """env 优先，未加载从 ~/.claude/settings.json env 读，逗号/换行分多 key。"""
    raw = os.environ.get("TAVILY_API_KEY")
    if not raw and _SETTINGS_PATH.exists():
        data = json.loads(_SETTINGS_PATH.read_text())
        raw = data.get("env", {}).get("TAVILY_API_KEY")
    if not raw:
        raise RuntimeError("TAVILY_API_KEY 未配置")
    if isinstance(raw, list):
        return [k.strip() for k in raw if k and k.strip()]
    return [k.strip() for k in re.split(r"[,\n]", raw) if k.strip()]


class TavilyProvider:
    name = "tavily"
    capabilities = {"time_filter", "extract", "news", "general"}

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
        search_depth: str | None = None,
    ) -> list[Hit]:
        depth = search_depth or ("advanced" if need_extract else "basic")
        last_err: Exception | None = None
        for _ in range(len(self.pool.keys)):
            try:
                key = self.pool.acquire()
            except NoKeyAvailable as e:
                raise ProviderError(
                    "tavily: all keys exhausted", provider=self.name, retryable=False,
                ) from e
            payload: dict = {
                "api_key": key,
                "query": query,
                "max_results": max_results,
                "search_depth": depth,
                "include_raw_content": need_extract,
            }
            if days is not None:
                payload["days"] = days
            if include_domains:
                payload["include_domains"] = include_domains
            if exclude_domains:
                payload["exclude_domains"] = exclude_domains

            req = urllib.request.Request(
                _ENDPOINT,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    retry_after = e.headers.get("Retry-After") if e.headers else None
                    self.pool.record_429(key, int(retry_after) if retry_after else None)
                    last_err = e
                    continue
                if e.code in (401, 403):
                    self.pool.record_403(key)
                    last_err = e
                    continue
                raise ProviderError(
                    f"tavily: HTTP {e.code}", provider=self.name,
                ) from e
            except urllib.error.URLError as e:
                last_err = e
                continue
            else:
                self.pool.record_success(key)
                return [
                    Hit(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        score=r.get("score"),
                        raw_content=r.get("raw_content"),
                        published_at=r.get("published_date"),
                        source_provider=self.name,
                    )
                    for r in data.get("results", [])
                ]
        raise ProviderError(
            "tavily: all keys failed", provider=self.name,
        ) from last_err
