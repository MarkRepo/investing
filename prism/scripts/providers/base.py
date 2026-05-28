from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Protocol


@dataclass
class Hit:
    """与 register_web_search_batch hits 参数对齐的 hit dataclass。"""
    title: str
    url: str
    snippet: str
    score: float | None = None
    raw_content: str | None = None
    published_at: str | None = None
    source_provider: str = ""
    domain_tier: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ProviderError(Exception):
    """provider 层错误。retryable=True 表示可换 key 或换 provider 重试。"""
    def __init__(self, msg: str, *, provider: str, retryable: bool = True):
        super().__init__(msg)
        self.provider = provider
        self.retryable = retryable


class NoKeyAvailable(ProviderError):
    """该 provider 所有 key 都不可用（耗尽/冷却/拉黑）。"""
    def __init__(self, *, provider: str, soonest_recovery: datetime | None):
        msg = f"{provider}: no key available"
        if soonest_recovery is not None:
            msg += f" (soonest recovery: {soonest_recovery.isoformat()})"
        super().__init__(msg, provider=provider, retryable=False)
        self.soonest_recovery = soonest_recovery


class Provider(Protocol):
    name: str
    capabilities: set[str]

    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        days: int | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        need_extract: bool = False,
    ) -> list[Hit]: ...

    def healthy(self) -> bool: ...
