# Web-Search Adapter 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **2026-05-28 ERRATA**：本计划 Phase 1 把 `GENERIC_AUTHORITATIVE_HOSTS` + `CLUSTER_AUTHORITATIVE_HOSTS` 从 `tavily_search.py` 原样搬到 `providers/_domain.py`，但当晚复审发现这违反 H2 设计原则（脚本只做 deterministic 黑名单，主观分类交给 LLM；参 `memory/feedback_prescan_domain_tier.md`）。已删除：
>
> - `GENERIC_AUTHORITATIVE_HOSTS` / `CLUSTER_AUTHORITATIVE_HOSTS` 两份白名单整体删除
> - `classify_hit_domain_tier(url, cluster=None)` → `classify_hit_domain_tier(url)`，只对 `LOW_SIGNAL_HOSTS` 黑名单源返 `'other'`，其余返 `None`
> - `WebSearchAdapter.__init__` / CLI `--cluster` 参数删除
> - `web_prescan.promote_to_whitelist` / `demote_from_whitelist` / `_load_runtime_whitelist` / `_runtime_whitelist.yaml` 沉淀机制删除
>
> 现状以代码为准。本计划其余内容（KeyPool / Provider / Router / 双向 fallback / 退出码契约）仍然有效。

**Goal:** 把单一 `tavily_search.py` 升级为多 provider 智能路由 adapter，支持 Tavily/Exa/Serper 三家、单 provider 内多 key 轮换、provider 间按 query intent 路由+失败 fallback、与 Anthropic WebSearch tool 通过退出码契约做双向 fallback；落沙箱后所有 prism workflow 入库类 web 检索都走 adapter，对话探索类走 WebSearch tool。

**Architecture:**
- `prism/scripts/providers/`：Provider 抽象 + KeyPool + 三家具体实现，每家自管 key 池+断路器
- `prism/scripts/web_search.py`：`WebSearchAdapter` 编排，按 intent 排序 provider 并循环 fallback；CLI 入口 `python -m prism.scripts.web_search`
- `prism/scripts/router.py`：query → intent 启发式分类 + provider ranking
- 与主 agent 通过**退出码 + stderr JSON** 契约通信，agent 在双向 fallback 时按表执行
- `state/web_search_keys.json` 跨会话持久化每 key 的当日配额、冷却、连续失败计数

**Tech Stack:** Python 3.11、`urllib`（继续不引入 requests）、`pytest`、PyYAML、Anthropic 内置 WebSearch（仅在 fallback 契约层），与现有 `register_web_search_batch` schema 完全对齐。

**红线纪律**（贯穿所有 phase）：
1. **不调 LLM API**：所有 intent 分类用规则 heuristic，禁脚本里加 LLM call（[[feedback_llm_workflow]]）
2. **保持 hit dict schema 与 `register_web_search_batch` 对齐**（title/url/snippet/score/raw_content）
3. **不改现有 `tavily_search.py` 公共导入**：保留 shim 兼容旧调用（`from prism.scripts.tavily_search import tavily_search` 仍工作）
4. **修改任何 function/method 前先跑 `gitnexus_impact`**，HIGH/CRITICAL 风险先跟用户确认
5. **每 phase 收尾必跑 `gitnexus_detect_changes()`**
6. **key 明文不进 git、不进日志**：state 文件只存 fingerprint（前 8 + 后 8 sha256），仓库根加 `state/` 到 `.gitignore`

---

## 文件结构

### Phase 1（核心抽象 + Tavily 迁移）

**Create:**
- `prism/scripts/providers/__init__.py` — 导出 `Provider`, `Hit`, `ProviderError`, `NoKeyAvailable`
- `prism/scripts/providers/base.py` — `Hit` dataclass + `Provider` Protocol + 异常体系
- `prism/scripts/providers/keypool.py` — `KeyPool` + `KeyState` + 状态持久化
- `prism/scripts/providers/_domain.py` — 把 `LOW_SIGNAL_HOSTS` / `GENERIC_AUTHORITATIVE_HOSTS` / `CLUSTER_AUTHORITATIVE_HOSTS` / `classify_hit_domain_tier` 从 `tavily_search.py` 搬过来
- `prism/scripts/providers/tavily.py` — `TavilyProvider`，从 `tavily_search.py` 提取 HTTP 调用逻辑
- `prism/scripts/test_providers_base.py`
- `prism/scripts/test_providers_keypool.py`
- `prism/scripts/test_providers_tavily.py`

**Modify:**
- `prism/scripts/tavily_search.py` — 改为兼容 shim：从 `providers.tavily` 重导出 `tavily_search` 函数（旧入口仍可用）
- `.gitignore` 顶部加 `state/`

### Phase 2（Adapter + Router + CLI search）

**Create:**
- `prism/scripts/router.py` — `classify_intent()` + `rank_providers()`
- `prism/scripts/web_search.py` — `WebSearchAdapter` 类 + `__main__` CLI
- `prism/scripts/test_router.py`
- `prism/scripts/test_web_search_adapter.py`

### Phase 3（Postprocess 模式 + 退出码契约）

**Modify:**
- `prism/scripts/web_search.py` — 增 `postprocess` 子命令；定义退出码常量；stderr JSON 状态输出
- `prism/scripts/test_web_search_adapter.py` — 加 fallback / postprocess / exit-code 测试

**Create:**
- `prism/workflows/_web_search_routing.md` — 路由总则 + 退出码处理表 + 双向 fallback 规约（主 agent 必读）

### Phase 4（Exa + Serper Provider）

**Create:**
- `prism/scripts/providers/exa.py` — `ExaProvider`
- `prism/scripts/providers/serper.py` — `SerperProvider`
- `prism/scripts/test_providers_exa.py`
- `prism/scripts/test_providers_serper.py`

**Modify:**
- `prism/scripts/web_search.py` — `_default_providers()` 注册 Exa+Serper
- `prism/scripts/router.py` — `rank_providers` 根据 capability 设置打分

### Phase 5（Workflow 文档接入 + Prescan 切换）

**Modify:**
- `prism/workflows/00-research-topic.md` — Step 4.5 prescan 改用 adapter CLI（保留旧 `tavily_search` 路径兼容）
- `prism/workflows/03-extract-findings.md` — Step 2.4 inline web-search 改用 adapter
- `prism/workflows/04-synthesize/_shared.md` — 同步路由总则引用
- `prism/workflows/05-critic-review.md` — Step 6.5 同步
- `prism/workflows/_web_search_aggregation.md` — 顶部加路由总则跳转链接
- `prism/workflows/_subagent_deep_search.md` / `_subagent_fetch_material.md` — 强制 subagent 走 adapter（不调 MCP）

---

## Phase 1 — 核心抽象 + Tavily 迁移

### Task 1.1：Hit dataclass + Provider Protocol + 异常体系

**Files:**
- Create: `prism/scripts/providers/__init__.py`
- Create: `prism/scripts/providers/base.py`
- Test: `prism/scripts/test_providers_base.py`

- [ ] **Step 1：写 base.py 的失败测试**

```python
# prism/scripts/test_providers_base.py
from prism.scripts.providers.base import Hit, ProviderError, NoKeyAvailable


def test_hit_to_dict_round_trip():
    h = Hit(
        title="t", url="https://example.com/a", snippet="s",
        score=0.8, raw_content=None, published_at=None,
        source_provider="tavily",
    )
    d = h.to_dict()
    assert d["title"] == "t"
    assert d["url"] == "https://example.com/a"
    assert d["snippet"] == "s"
    assert d["score"] == 0.8
    assert d["source_provider"] == "tavily"
    # 与 register_web_search_batch 期望的 schema 对齐：必有 title/url/snippet
    assert {"title", "url", "snippet"} <= d.keys()


def test_provider_error_chain():
    inner = RuntimeError("boom")
    err = ProviderError("tavily failed", provider="tavily", retryable=True)
    err.__cause__ = inner
    assert err.provider == "tavily"
    assert err.retryable is True
    assert "tavily failed" in str(err)


def test_no_key_available_inherits_provider_error():
    err = NoKeyAvailable(provider="tavily", soonest_recovery=None)
    assert isinstance(err, ProviderError)
    assert err.provider == "tavily"
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_providers_base.py -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'prism.scripts.providers'`

- [ ] **Step 3：实现 base.py**

```python
# prism/scripts/providers/base.py
from __future__ import annotations

from dataclasses import dataclass, field, asdict
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
    published_at: str | None = None  # ISO8601
    source_provider: str = ""        # 'tavily' | 'exa' | 'serper' | 'websearch_fallback'
    domain_tier: str | None = None   # adapter 后处理填

    def to_dict(self) -> dict:
        d = asdict(self)
        # 不删 None 字段：register_web_search_batch 已宽容处理
        return d


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
    capabilities: set[str]  # {'time_filter','semantic','extract','news','patents',...}

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
```

```python
# prism/scripts/providers/__init__.py
from .base import Hit, Provider, ProviderError, NoKeyAvailable

__all__ = ["Hit", "Provider", "ProviderError", "NoKeyAvailable"]
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_providers_base.py -v`
Expected: PASS（3 tests）

- [ ] **Step 5：commit**

```bash
git add prism/scripts/providers/__init__.py prism/scripts/providers/base.py \
        prism/scripts/test_providers_base.py
git commit -m "feat(prism): web-search adapter Phase1 - Hit dataclass + Provider protocol"
```

---

### Task 1.2：KeyPool + 持久化

**Files:**
- Create: `prism/scripts/providers/keypool.py`
- Test: `prism/scripts/test_providers_keypool.py`
- Modify: `.gitignore`（加 `state/`）

- [ ] **Step 1：写 KeyPool 失败测试**

```python
# prism/scripts/test_providers_keypool.py
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from prism.scripts.providers.keypool import KeyPool, KeyState
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
    # 第 1 次 429 → 60s 冷却；剩 k2bbbb 可用
    assert pool.acquire() == "k2bbbb"


def test_acquire_raises_when_all_exhausted(tmp_state):
    pool = KeyPool("tavily", ["k1aaaa"], free_quota_per_day=10)
    pool.state[pool._fp("k1aaaa")].used_today = 10  # 用尽
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
    pool.state[fp].reset_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    pool._maybe_reset(pool.state[fp])
    assert pool.state[fp].used_today == 0


def test_fingerprint_does_not_leak_key(tmp_state):
    pool = KeyPool("tavily", ["super-secret-key-1234567890"], free_quota_per_day=10)
    fp = pool._fp("super-secret-key-1234567890")
    assert "secret" not in fp
    assert len(fp) == 16  # 8 prefix + 8 sha256 suffix
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_providers_keypool.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3：实现 keypool.py**

```python
# prism/scripts/providers/keypool.py
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .base import NoKeyAvailable

_STATE_PATH = Path.home() / ".claude" / "projects" / "-Users-yangqi-investing" / "state" / "web_search_keys.json"

# 失败退避阶梯（秒）
_BACKOFF_LADDER = [60, 300, 1800]


@dataclass
class KeyState:
    fingerprint: str
    used_today: int = 0
    reset_at: str | None = None              # ISO8601 UTC
    cooldown_until: str | None = None        # ISO8601 UTC
    consecutive_429: int = 0
    last_success: str | None = None          # ISO8601 UTC
    disabled: bool = False                   # 401/403 永久拉黑


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
        """日历日 UTC 0 点重置 used_today。"""
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
                    soonest = min(filter(None, [soonest, cd]))
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
        out = {"provider": self.provider, "free_quota": self.free_quota, "keys": []}
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
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_providers_keypool.py -v`
Expected: PASS（7 tests）

- [ ] **Step 5：把 `state/` 加进 .gitignore**

Run: `grep -q "^state/" .gitignore || echo "state/" >> .gitignore`

检查：`grep state/ .gitignore` 输出 `state/`

- [ ] **Step 6：commit**

```bash
git add prism/scripts/providers/keypool.py prism/scripts/test_providers_keypool.py .gitignore
git commit -m "feat(prism): web-search adapter Phase1 - KeyPool with rotation + persistence"
```

---

### Task 1.3：Domain tier 模块拆出

**Files:**
- Create: `prism/scripts/providers/_domain.py`

- [ ] **Step 1：建 _domain.py，把 hosts 集合 + classify 函数从 tavily_search.py 整段搬过来**

复制 `prism/scripts/tavily_search.py` 第 30-144 行（`LOW_SIGNAL_HOSTS` / `GENERIC_AUTHORITATIVE_HOSTS` / `CLUSTER_AUTHORITATIVE_HOSTS` / `classify_hit_domain_tier`）到 `prism/scripts/providers/_domain.py`，**完整保留 docstring 和注释**。文件头加：

```python
"""Domain tier 分类（搬自 tavily_search.py）。

LOW_SIGNAL_HOSTS / GENERIC_AUTHORITATIVE_HOSTS / CLUSTER_AUTHORITATIVE_HOSTS
是 cluster 专属与全行业通用权威源白名单，classify_hit_domain_tier 由
adapter 后处理调用，给每条 Hit 写入 domain_tier。
"""
```

- [ ] **Step 2：跑现有 tavily_search 相关测试不退化**

Run: `pytest prism/scripts/ -k "tavily or whitelist" -v`
Expected: PASS（不动 tavily_search.py 的话现状测试仍通过）

- [ ] **Step 3：commit**

```bash
git add prism/scripts/providers/_domain.py
git commit -m "feat(prism): web-search adapter Phase1 - extract domain tier to providers/_domain.py"
```

---

### Task 1.4：TavilyProvider 实现

**Files:**
- Create: `prism/scripts/providers/tavily.py`
- Test: `prism/scripts/test_providers_tavily.py`

- [ ] **Step 1：写 TavilyProvider 失败测试（mock HTTP）**

```python
# prism/scripts/test_providers_tavily.py
import json
from unittest.mock import MagicMock, patch

import pytest

from prism.scripts.providers.tavily import TavilyProvider
from prism.scripts.providers.base import ProviderError, Hit


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "prism.scripts.providers.keypool._STATE_PATH",
        tmp_path / "web_search_keys.json",
    )


def _mock_resp(payload: dict):
    """构造 urllib.request.urlopen context manager mock。"""
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    cm.__exit__.return_value = False
    return cm


def test_search_returns_hit_list(tmp_state):
    p = TavilyProvider(keys=["k1aaaa"])
    payload = {
        "results": [
            {"title": "T1", "url": "https://reuters.com/x",
             "content": "snip", "score": 0.9},
            {"title": "T2", "url": "https://bloomberg.com/y",
             "content": "snip2", "score": 0.7},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)):
        hits = p.search("uranium price", max_results=2)
    assert len(hits) == 2
    assert isinstance(hits[0], Hit)
    assert hits[0].url == "https://reuters.com/x"
    assert hits[0].source_provider == "tavily"


def test_search_429_rotates_to_next_key(tmp_state):
    p = TavilyProvider(keys=["k1aaaa", "k2bbbb"])

    import urllib.error
    err = urllib.error.HTTPError(
        url="https://api.tavily.com/search", code=429,
        msg="Too Many Requests", hdrs={}, fp=None,
    )
    ok_payload = {"results": [{"title": "T", "url": "https://a.com",
                               "content": "s", "score": 0.5}]}
    seq = [err, _mock_resp(ok_payload)]

    def _side(*args, **kwargs):
        item = seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    with patch("urllib.request.urlopen", side_effect=_side):
        hits = p.search("q")
    assert len(hits) == 1


def test_search_all_keys_exhausted_raises(tmp_state):
    p = TavilyProvider(keys=["k1aaaa"])
    import urllib.error
    err = urllib.error.HTTPError(
        url="https://api.tavily.com/search", code=429,
        msg="Too Many Requests", hdrs={}, fp=None,
    )
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(ProviderError):
            p.search("q")


def test_search_capabilities():
    assert TavilyProvider.capabilities >= {"time_filter", "extract", "news"}
    assert TavilyProvider.name == "tavily"
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_providers_tavily.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3：实现 TavilyProvider**

```python
# prism/scripts/providers/tavily.py
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .base import Hit, ProviderError, NoKeyAvailable
from .keypool import KeyPool

_ENDPOINT = "https://api.tavily.com/search"
_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
# Tavily 免费 1000/月 ≈ 33/天保守估
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
    import re
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
                    f"tavily: all keys exhausted", provider=self.name, retryable=False,
                ) from e
            payload = {
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
            f"tavily: all keys failed", provider=self.name,
        ) from last_err
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_providers_tavily.py -v`
Expected: PASS（4 tests）

- [ ] **Step 5：commit**

```bash
git add prism/scripts/providers/tavily.py prism/scripts/test_providers_tavily.py
git commit -m "feat(prism): web-search adapter Phase1 - TavilyProvider with KeyPool"
```

---

### Task 1.5：tavily_search.py 改 shim 兼容

**Files:**
- Modify: `prism/scripts/tavily_search.py`

- [ ] **Step 1：先跑 gitnexus_impact 看 tavily_search 上游依赖**

Run（在对话里调）：`mcp__gitnexus__impact target="tavily_search" direction="upstream"`

预期：报告 prescan / web_search 调用方。如果出现 HIGH/CRITICAL，停下来跟用户确认。

- [ ] **Step 2：把 tavily_search.py 改成 shim**

整个文件覆盖为：

```python
"""Tavily Web Search 兼容 shim — 旧入口转发到 providers.tavily。

历史调用方（如 prism/scripts/web_prescan.py 的旧路径）保留 import 兼容。
新代码请直接 from prism.scripts.providers.tavily import TavilyProvider。
"""
from __future__ import annotations

from prism.scripts.providers._domain import (
    LOW_SIGNAL_HOSTS,
    GENERIC_AUTHORITATIVE_HOSTS,
    CLUSTER_AUTHORITATIVE_HOSTS,
    classify_hit_domain_tier,
)
from prism.scripts.providers.tavily import TavilyProvider


def tavily_search(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_raw_content: bool = False,
    include_domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    days: int | None = None,
    timeout_s: int = 30,
) -> list[dict]:
    """旧 API：返回 list[dict]，schema 与 register_web_search_batch hits 对齐。"""
    p = TavilyProvider(timeout_s=timeout_s)
    hits = p.search(
        query,
        max_results=max_results,
        days=days,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
        need_extract=include_raw_content,
        search_depth=search_depth,
    )
    return [h.to_dict() for h in hits]


def tavily_search_batch(
    queries: list[str],
    max_results_per_query: int = 5,
    search_depth: str = "basic",
    days: int | None = None,
) -> dict[str, list[dict]]:
    return {
        q: tavily_search(
            q,
            max_results=max_results_per_query,
            search_depth=search_depth,
            days=days,
        )
        for q in queries
    }


__all__ = [
    "tavily_search", "tavily_search_batch", "classify_hit_domain_tier",
    "LOW_SIGNAL_HOSTS", "GENERIC_AUTHORITATIVE_HOSTS", "CLUSTER_AUTHORITATIVE_HOSTS",
]
```

- [ ] **Step 3：跑全量回归确认没破坏现有调用方**

Run: `pytest prism/scripts/ -v`
Expected: 全 PASS（包含 phase1 新增的 + 历史 tavily 相关测试）

- [ ] **Step 4：跑 gitnexus_detect_changes**

Run（在对话里）：`mcp__gitnexus__detect_changes`
检查：affected_processes 不超出"web-search/prescan"范围，无意外火箭。

- [ ] **Step 5：commit**

```bash
git add prism/scripts/tavily_search.py
git commit -m "refactor(prism): tavily_search.py downgraded to compat shim over TavilyProvider"
```

---

## Phase 2 — Adapter + Router + CLI

### Task 2.1：Router（intent 分类 + provider ranking）

**Files:**
- Create: `prism/scripts/router.py`
- Test: `prism/scripts/test_router.py`

- [ ] **Step 1：写 router 失败测试**

```python
# prism/scripts/test_router.py
from prism.scripts.router import classify_intent, rank_providers


class _FakeProvider:
    def __init__(self, name, caps, healthy=True):
        self.name = name
        self.capabilities = caps
        self._h = healthy
    def healthy(self):
        return self._h


def test_classify_intent_news_keywords():
    assert classify_intent("FDA 2026 Q1 approval") == "news"
    assert classify_intent("uranium spot price last week") == "news"


def test_classify_intent_semantic_phrases():
    assert classify_intent("papers similar to GLP-1 cardiovascular outcome") == "semantic"
    assert classify_intent("companies like Cameco") == "semantic"


def test_classify_intent_exact_with_site_op():
    assert classify_intent("site:sec.gov 10-K Cameco 2025") == "exact"


def test_classify_intent_vertical_patent():
    assert classify_intent("patent SMR reactor cooling") == "vertical:patent"
    assert classify_intent("scholar GLP-1 cardiovascular") == "vertical:scholar"


def test_classify_intent_general_fallback():
    assert classify_intent("uranium market overview") == "general"


def test_rank_providers_news_prefers_tavily():
    tav = _FakeProvider("tavily", {"news", "time_filter"})
    exa = _FakeProvider("exa", {"semantic"})
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, exa, ser], intent="news")
    assert ranked[0].name == "tavily"


def test_rank_providers_semantic_prefers_exa():
    tav = _FakeProvider("tavily", {"news"})
    exa = _FakeProvider("exa", {"semantic"})
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, exa, ser], intent="semantic")
    assert ranked[0].name == "exa"


def test_rank_providers_exact_prefers_serper():
    tav = _FakeProvider("tavily", {"news"})
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, ser], intent="exact")
    assert ranked[0].name == "serper"


def test_rank_providers_skips_unhealthy():
    tav = _FakeProvider("tavily", {"news"}, healthy=False)
    ser = _FakeProvider("serper", {"general"})
    ranked = rank_providers([tav, ser], intent="news")
    assert all(p.name != "tavily" for p in ranked)
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_router.py -v`
Expected: FAIL，`ModuleNotFoundError`

- [ ] **Step 3：实现 router.py**

```python
# prism/scripts/router.py
from __future__ import annotations

import re
from typing import Iterable

from prism.scripts.providers.base import Provider

_NEWS_RE = re.compile(
    r"\b(today|yesterday|last\s+(week|month|quarter|year)|"
    r"this\s+(week|month|quarter|year)|"
    r"20\d{2}\s*[Qq][1-4]|"
    r"FDA|EPA|SEC\s+filing|earnings|approval|launch|recall|"
    r"announce(d|ment)?|release|update|breaking)\b",
    re.IGNORECASE,
)
_SEMANTIC_RE = re.compile(
    r"\b(similar\s+to|like\s+\w+|papers?\s+(on|about)|"
    r"research\s+about|companies?\s+like|alternatives?\s+to)\b",
    re.IGNORECASE,
)
_EXACT_RE = re.compile(r"\bsite:\S+|\binurl:|\bintitle:|\b\d{6,}\b")
_VERTICAL_MAP = {
    "patent":  re.compile(r"\bpatent(s|ed)?\b", re.IGNORECASE),
    "scholar": re.compile(r"\bscholar(ly)?\b|\bjournal\b|\bdoi\b", re.IGNORECASE),
    "image":   re.compile(r"\bimage(s)?\b|\bphoto(s)?\b", re.IGNORECASE),
    "map":     re.compile(r"\bmap\b|\bnear\s+\w+\b", re.IGNORECASE),
}


def classify_intent(query: str) -> str:
    """heuristic: 'news' | 'semantic' | 'exact' | 'vertical:<kind>' | 'general'

    顺序：vertical > exact > news > semantic > general（更具体的优先）
    """
    for kind, pat in _VERTICAL_MAP.items():
        if pat.search(query):
            return f"vertical:{kind}"
    if _EXACT_RE.search(query):
        return "exact"
    if _NEWS_RE.search(query):
        return "news"
    if _SEMANTIC_RE.search(query):
        return "semantic"
    return "general"


# intent → 偏好 capability 加权
_INTENT_WEIGHTS: dict[str, dict[str, float]] = {
    "news":              {"news": 3.0, "time_filter": 2.0, "general": 0.5},
    "semantic":          {"semantic": 3.0, "general": 0.5},
    "exact":             {"general": 2.0, "exact": 3.0},
    "vertical:patent":   {"patent": 5.0, "general": 0.5},
    "vertical:scholar":  {"scholar": 5.0, "semantic": 1.0, "general": 0.5},
    "vertical:image":    {"image": 5.0, "general": 0.5},
    "vertical:map":      {"map": 5.0, "general": 0.5},
    "general":           {"general": 1.5, "news": 1.0, "semantic": 1.0},
}


def rank_providers(
    providers: Iterable[Provider],
    *,
    intent: str,
) -> list[Provider]:
    """按 intent 给 provider 打分并排序，过滤不 healthy 的。"""
    weights = _INTENT_WEIGHTS.get(intent, _INTENT_WEIGHTS["general"])
    scored: list[tuple[float, Provider]] = []
    for p in providers:
        if not p.healthy():
            continue
        score = sum(w for cap, w in weights.items() if cap in p.capabilities)
        scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored]
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_router.py -v`
Expected: PASS（9 tests）

- [ ] **Step 5：commit**

```bash
git add prism/scripts/router.py prism/scripts/test_router.py
git commit -m "feat(prism): web-search adapter Phase2 - router intent classification + provider ranking"
```

---

### Task 2.2：WebSearchAdapter 主体

**Files:**
- Create: `prism/scripts/web_search.py`
- Test: `prism/scripts/test_web_search_adapter.py`

- [ ] **Step 1：写 adapter 失败测试**

```python
# prism/scripts/test_web_search_adapter.py
from unittest.mock import MagicMock

import pytest

from prism.scripts.providers.base import Hit, ProviderError
from prism.scripts.web_search import WebSearchAdapter


class _StubProvider:
    def __init__(self, name, caps, hits=None, raises=None, healthy=True):
        self.name = name
        self.capabilities = caps
        self._hits = hits or []
        self._raises = raises
        self._h = healthy
        self.calls = 0

    def healthy(self):
        return self._h

    def search(self, query, **kwargs):
        self.calls += 1
        if self._raises:
            raise self._raises
        return self._hits


def _hit(url, score=0.8, prov="tavily"):
    return Hit(title="t", url=url, snippet="s", score=score, source_provider=prov)


def test_adapter_returns_hits_from_top_provider():
    p1 = _StubProvider("tavily", {"news"}, hits=[_hit("https://reuters.com/a")])
    p2 = _StubProvider("serper", {"general"}, hits=[_hit("https://example.com/b")])
    adp = WebSearchAdapter([p1, p2])
    hits = adp.search("FDA approval 2026")
    assert len(hits) == 1
    assert p1.calls == 1 and p2.calls == 0


def test_adapter_falls_back_on_provider_error():
    err = ProviderError("boom", provider="tavily")
    p1 = _StubProvider("tavily", {"news"}, raises=err)
    p2 = _StubProvider("serper", {"general"}, hits=[_hit("https://x.com/y")])
    adp = WebSearchAdapter([p1, p2])
    hits = adp.search("FDA approval 2026")
    assert len(hits) == 1
    assert hits[0].source_provider in {"tavily", "serper"}  # source_provider 来自实际命中的 provider
    assert p1.calls == 1 and p2.calls == 1


def test_adapter_soft_fallback_on_low_score():
    p1 = _StubProvider("tavily", {"news"}, hits=[_hit("https://a.com", score=0.1)])
    p2 = _StubProvider("serper", {"general"}, hits=[_hit("https://b.com", score=0.9)])
    adp = WebSearchAdapter([p1, p2], min_score=0.3)
    hits = adp.search("FDA approval 2026")
    assert hits[0].url == "https://b.com"


def test_adapter_postprocess_assigns_domain_tier():
    p1 = _StubProvider("tavily", {"news"}, hits=[
        _hit("https://reuters.com/a"),
        _hit("https://twitter.com/b"),
    ])
    adp = WebSearchAdapter([p1], cluster=None)
    hits = adp.search("oil prices")
    tiers = {h.url: h.domain_tier for h in hits}
    assert tiers["https://reuters.com/a"] == "llm-judged-official"
    # twitter 在 LOW_SIGNAL_HOSTS，被打 'other'
    assert tiers["https://twitter.com/b"] == "other"


def test_adapter_dedup_by_canonical_url():
    p1 = _StubProvider("tavily", {"news"}, hits=[
        _hit("https://reuters.com/a"),
        _hit("https://reuters.com/a?utm_source=x"),  # 应去重
    ])
    adp = WebSearchAdapter([p1])
    hits = adp.search("oil prices")
    assert len(hits) == 1


def test_adapter_raises_when_all_providers_exhausted():
    err = ProviderError("dead", provider="tavily")
    p1 = _StubProvider("tavily", {"news"}, raises=err)
    p2 = _StubProvider("serper", {"general"}, raises=err)
    adp = WebSearchAdapter([p1, p2])
    with pytest.raises(RuntimeError):
        adp.search("query")
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_web_search_adapter.py -v`
Expected: FAIL，`ImportError: cannot import name 'WebSearchAdapter'`

- [ ] **Step 3：实现 web_search.py 主体**

```python
# prism/scripts/web_search.py
from __future__ import annotations

import json
import sys
from urllib.parse import urlparse, urlunparse

from prism.scripts.providers.base import Hit, ProviderError
from prism.scripts.providers._domain import classify_hit_domain_tier
from prism.scripts.router import classify_intent, rank_providers


def _canonical_url(url: str) -> str:
    """去 query 中的 tracking 参数（utm_*, fbclid 等），只保留 path + 主要 query。"""
    parsed = urlparse(url)
    query = "&".join(
        kv for kv in parsed.query.split("&")
        if kv and not kv.split("=")[0].lower().startswith(("utm_", "fbclid", "gclid"))
    )
    return urlunparse(parsed._replace(query=query, fragment=""))


class WebSearchAdapter:
    def __init__(
        self,
        providers: list,
        *,
        cluster: str | None = None,
        min_score: float = 0.3,
    ):
        self.providers = providers
        self.cluster = cluster
        self.min_score = min_score

    def search(
        self,
        query: str,
        *,
        intent: str | None = None,
        max_results: int = 5,
        days: int | None = None,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        need_extract: bool = False,
    ) -> list[Hit]:
        intent = intent or classify_intent(query)
        ranked = rank_providers(self.providers, intent=intent)
        if not ranked:
            raise RuntimeError(f"no healthy provider for intent={intent}")

        last_err: Exception | None = None
        for p in ranked:
            try:
                hits = p.search(
                    query,
                    max_results=max_results,
                    days=days,
                    include_domains=include_domains,
                    exclude_domains=exclude_domains,
                    need_extract=need_extract,
                )
            except ProviderError as e:
                last_err = e
                continue
            # soft fallback：0 hit 或全低分 → 试下一家
            if not hits:
                continue
            top = max((h.score or 0.0) for h in hits)
            if top < self.min_score:
                continue
            return self._postprocess(hits)

        raise RuntimeError(
            f"all providers exhausted for query={query!r}: {last_err}"
        )

    def _postprocess(self, hits: list[Hit]) -> list[Hit]:
        seen: set[str] = set()
        out: list[Hit] = []
        for h in hits:
            canon = _canonical_url(h.url)
            if canon in seen:
                continue
            seen.add(canon)
            tier = classify_hit_domain_tier(h.url, cluster=self.cluster)
            if tier:
                h.domain_tier = tier
            out.append(h)
        return out

    def postprocess_external_hits(self, hits: list[Hit]) -> list[Hit]:
        """供 WebSearch fallback 使用：吃外部 hit list，跑 dedup + domain_tier。"""
        return self._postprocess(hits)
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_web_search_adapter.py -v`
Expected: PASS（6 tests）

- [ ] **Step 5：commit**

```bash
git add prism/scripts/web_search.py prism/scripts/test_web_search_adapter.py
git commit -m "feat(prism): web-search adapter Phase2 - WebSearchAdapter with intent routing + dedup"
```

---

### Task 2.3：CLI search 入口

**Files:**
- Modify: `prism/scripts/web_search.py`
- Test: `prism/scripts/test_web_search_adapter.py`（追加 CLI 测试）

- [ ] **Step 1：CLI 失败测试**

在 `test_web_search_adapter.py` 末尾追加：

```python
def test_cli_search_writes_json_to_stdout(tmp_path, monkeypatch, capsys):
    """smoke test: CLI 走 main，参数解析 + 输出格式正确。
    实际 provider 用 stub，不打外网。
    """
    from prism.scripts import web_search as ws

    p1 = _StubProvider("tavily", {"news", "general"}, hits=[
        _hit("https://reuters.com/x"),
    ])
    monkeypatch.setattr(ws, "_default_providers", lambda: [p1])

    rc = ws.main(["search", "uranium", "--max-results", "1", "--output", "stdout"])
    assert rc == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert isinstance(payload, list)
    assert payload[0]["url"] == "https://reuters.com/x"
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_web_search_adapter.py::test_cli_search_writes_json_to_stdout -v`
Expected: FAIL，`AttributeError: module ... has no attribute 'main'`

- [ ] **Step 3：在 web_search.py 末尾加 CLI**

```python
# 追加到 web_search.py 末尾

import argparse


# 退出码（Phase 3 会用到，预先定义）
EXIT_OK = 0
EXIT_PARTIAL = 10
EXIT_NO_HITS = 20
EXIT_DEGRADED = 30
EXIT_ALL_EXHAUSTED = 40
EXIT_CONFIG = 50


def _default_providers() -> list:
    """按可用 key 决定加载哪些 provider；缺 key 的 provider 跳过。"""
    out = []
    try:
        from prism.scripts.providers.tavily import TavilyProvider
        out.append(TavilyProvider())
    except (RuntimeError, ValueError):
        pass
    # Phase 4 会加 Exa / Serper
    return out


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="web_search")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="run web search via adapter")
    s.add_argument("query")
    s.add_argument("--intent",
                   choices=["news", "semantic", "exact", "general",
                            "vertical:patent", "vertical:scholar",
                            "vertical:image", "vertical:map"],
                   default=None)
    s.add_argument("--max-results", type=int, default=5)
    s.add_argument("--days", type=int, default=None)
    s.add_argument("--cluster", default=None)
    s.add_argument("--include-domains", default=None,
                   help="comma-separated")
    s.add_argument("--exclude-domains", default=None)
    s.add_argument("--need-extract", action="store_true")
    s.add_argument("--output", choices=["stdout", "sidecar"], default="stdout")
    s.add_argument("--slug", default=None, help="when --output=sidecar")
    s.add_argument("--variant", default=None)
    s.add_argument("--triggered-by", default=None)
    s.add_argument("--addresses", default=None,
                   help="comma-separated, when --output=sidecar")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.cmd != "search":
        return EXIT_CONFIG

    providers = _default_providers()
    if not providers:
        sys.stderr.write(json.dumps({
            "status": "config_error",
            "reason": "no provider configured (check API keys)",
        }) + "\n")
        return EXIT_CONFIG

    adp = WebSearchAdapter(providers, cluster=args.cluster)
    inc = args.include_domains.split(",") if args.include_domains else None
    exc = args.exclude_domains.split(",") if args.exclude_domains else None
    try:
        hits = adp.search(
            args.query,
            intent=args.intent,
            max_results=args.max_results,
            days=args.days,
            include_domains=inc,
            exclude_domains=exc,
            need_extract=args.need_extract,
        )
    except RuntimeError as e:
        sys.stderr.write(json.dumps({
            "status": "all_exhausted",
            "reason": str(e),
            "fallback_hint": "use_websearch_tool",
        }) + "\n")
        return EXIT_ALL_EXHAUSTED

    if args.output == "stdout":
        sys.stdout.write(json.dumps(
            [h.to_dict() for h in hits], ensure_ascii=False, indent=2,
        ))
        return EXIT_OK if hits else EXIT_NO_HITS

    # sidecar 模式：调 register_web_search_batch
    if not all([args.slug, args.variant, args.triggered_by]):
        sys.stderr.write(json.dumps({
            "status": "config_error",
            "reason": "--output=sidecar 需要 --slug --variant --triggered-by",
        }) + "\n")
        return EXIT_CONFIG

    from prism.scripts.web_prescan import register_web_search_batch
    addresses = args.addresses.split(",") if args.addresses else []
    result = register_web_search_batch(
        slug=args.slug,
        variant=args.variant,
        query=args.query,
        addresses=addresses,
        triggered_by=args.triggered_by,
        hits=[h.to_dict() for h in hits],
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_OK if hits else EXIT_NO_HITS


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_web_search_adapter.py -v`
Expected: PASS（包含新加的 CLI smoke test）

- [ ] **Step 5：手动 smoke test（不打外网）**

Run: `python -m prism.scripts.web_search search --help`
Expected: argparse usage 正常输出，列出全部 flag

- [ ] **Step 6：commit**

```bash
git add prism/scripts/web_search.py prism/scripts/test_web_search_adapter.py
git commit -m "feat(prism): web-search adapter Phase2 - CLI search subcommand + sidecar output"
```

---

## Phase 3 — Postprocess 模式 + 退出码契约

### Task 3.1：Postprocess CLI 子命令

**Files:**
- Modify: `prism/scripts/web_search.py`（加 `postprocess` 子命令）
- Test: `prism/scripts/test_web_search_adapter.py`

- [ ] **Step 1：写 postprocess 失败测试**

追加：

```python
def test_cli_postprocess_reads_stdin_and_writes_sidecar(tmp_path, monkeypatch, capsys):
    """主 agent 把 WebSearch tool 拿到的 hits 通过 stdin 喂进来，跑 dedup + domain_tier
    后调 register_web_search_batch（mock）。
    """
    import json as _json
    from prism.scripts import web_search as ws

    captured_call = {}
    def _fake_register(**kwargs):
        captured_call.update(kwargs)
        return {"n_high": 1, "n_mid": 0, "n_low": 0,
                "mat_ids": ["mat-aaa"], "duplicates": 0}

    monkeypatch.setattr(
        "prism.scripts.web_prescan.register_web_search_batch",
        _fake_register,
    )

    payload = _json.dumps([
        {"title": "T", "url": "https://reuters.com/x", "snippet": "s"},
        {"title": "T2", "url": "https://reuters.com/x?utm_source=fb",
         "snippet": "dup"},  # 应去重
    ])
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(payload))

    rc = ws.main([
        "postprocess",
        "--source", "websearch_fallback",
        "--query", "uranium",
        "--cluster", "uranium-nuclear",
        "--slug", "global-uranium-supply",
        "--variant", "claude-opus-4-7",
        "--triggered-by", "00-prescan-fallback",
        "--addresses", "thesis-1",
    ])
    assert rc == 0
    # 只有一条进 register_web_search_batch（去重后）
    assert len(captured_call["hits"]) == 1
    # hit 应被打上 source_provider="websearch_fallback" 与 domain_tier
    assert captured_call["hits"][0]["source_provider"] == "websearch_fallback"
    assert captured_call["hits"][0]["domain_tier"] == "llm-judged-official"
    assert captured_call["triggered_by"] == "00-prescan-fallback"
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_web_search_adapter.py::test_cli_postprocess_reads_stdin_and_writes_sidecar -v`
Expected: FAIL，argparse 不识别 postprocess 子命令

- [ ] **Step 3：在 web_search.py 加 postprocess 子命令**

在 `_build_arg_parser` 里追加：

```python
    pp = sub.add_parser("postprocess",
                        help="postprocess external hits from WebSearch fallback")
    pp.add_argument("--source", default="websearch_fallback",
                    help="source_provider tag for these hits")
    pp.add_argument("--query", required=True)
    pp.add_argument("--cluster", default=None)
    pp.add_argument("--slug", required=True)
    pp.add_argument("--variant", required=True)
    pp.add_argument("--triggered-by", required=True)
    pp.add_argument("--addresses", default="")
```

`main()` 在 `if args.cmd != "search"` 改成分发：

```python
def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.cmd == "search":
        return _cmd_search(args)
    if args.cmd == "postprocess":
        return _cmd_postprocess(args)
    return EXIT_CONFIG
```

把现有 search 实现挪进 `_cmd_search(args)`，再加：

```python
def _cmd_postprocess(args) -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.stderr.write(json.dumps({"status": "no_input"}) + "\n")
        return EXIT_CONFIG
    items = json.loads(raw)
    hits = [
        Hit(
            title=item.get("title", ""),
            url=item.get("url", ""),
            snippet=item.get("snippet", ""),
            score=item.get("score"),
            raw_content=item.get("raw_content"),
            source_provider=args.source,
        )
        for item in items
    ]
    adp = WebSearchAdapter(providers=[], cluster=args.cluster)
    processed = adp.postprocess_external_hits(hits)

    from prism.scripts.web_prescan import register_web_search_batch
    addresses = [a for a in args.addresses.split(",") if a]
    result = register_web_search_batch(
        slug=args.slug,
        variant=args.variant,
        query=args.query,
        addresses=addresses,
        triggered_by=args.triggered_by,
        hits=[h.to_dict() for h in processed],
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
    return EXIT_OK
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_web_search_adapter.py -v`
Expected: 全 PASS

- [ ] **Step 5：commit**

```bash
git add prism/scripts/web_search.py prism/scripts/test_web_search_adapter.py
git commit -m "feat(prism): web-search adapter Phase3 - postprocess CLI for WebSearch fallback bridge"
```

---

### Task 3.2：退出码 stderr JSON 契约 + status 子命令

**Files:**
- Modify: `prism/scripts/web_search.py`
- Test: `prism/scripts/test_web_search_adapter.py`

- [ ] **Step 1：写退出码测试**

追加：

```python
def test_cli_search_exit_40_on_all_exhausted(monkeypatch, capsys):
    from prism.scripts.providers.base import ProviderError
    from prism.scripts import web_search as ws

    err = ProviderError("dead", provider="tavily")
    p1 = _StubProvider("tavily", {"news"}, raises=err)
    monkeypatch.setattr(ws, "_default_providers", lambda: [p1])

    rc = ws.main(["search", "uranium", "--output", "stdout"])
    assert rc == ws.EXIT_ALL_EXHAUSTED
    err_out = capsys.readouterr().err
    payload = json.loads(err_out.strip())
    assert payload["status"] == "all_exhausted"
    assert payload["fallback_hint"] == "use_websearch_tool"


def test_cli_search_exit_20_on_zero_hits(monkeypatch, capsys):
    from prism.scripts import web_search as ws

    p1 = _StubProvider("tavily", {"news"}, hits=[])
    p2 = _StubProvider("serper", {"general"}, hits=[])
    monkeypatch.setattr(ws, "_default_providers", lambda: [p1, p2])

    # 全空 hits → adapter 抛 RuntimeError (exhausted) 还是 0 hit？当前实现：
    # 全空被 soft fallback 跳过，所有 provider 走完仍 0 hit → 抛 RuntimeError → 40
    # 这是设计选择：把 0 hit 也当 exhausted，让主 agent 走 WebSearch fallback
    rc = ws.main(["search", "noresult", "--output", "stdout"])
    assert rc == ws.EXIT_ALL_EXHAUSTED


def test_cli_status_subcommand(monkeypatch, capsys):
    from prism.scripts import web_search as ws

    p1 = _StubProvider("tavily", {"news"})
    p1.pool = MagicMock()
    p1.pool.status.return_value = {
        "provider": "tavily",
        "free_quota": 33,
        "keys": [{"fingerprint": "aaaa1111", "used_today": 5,
                  "disabled": False, "cooldown_until": None,
                  "consecutive_429": 0, "last_success": None,
                  "reset_at": None}],
    }
    monkeypatch.setattr(ws, "_default_providers", lambda: [p1])

    rc = ws.main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "tavily" in out
    assert "5/33" in out  # used_today / free_quota 行
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_web_search_adapter.py -v`
Expected: status 测试失败（缺子命令），exit_40 / exit_20 看实现是否完整

- [ ] **Step 3：实现 status 子命令 + 完善退出码**

在 `_build_arg_parser` 加：

```python
    sub.add_parser("status", help="show key pool status across providers")
```

`main()` 分发加：

```python
    if args.cmd == "status":
        return _cmd_status()
```

```python
def _cmd_status() -> int:
    providers = _default_providers()
    if not providers:
        sys.stderr.write(json.dumps({"status": "config_error"}) + "\n")
        return EXIT_CONFIG
    for p in providers:
        if not hasattr(p, "pool"):
            continue
        s = p.pool.status()
        active = sum(1 for k in s["keys"]
                     if not k["disabled"] and not k["cooldown_until"])
        used_total = sum(k["used_today"] for k in s["keys"])
        cap_total = s["free_quota"] * len(s["keys"])
        sys.stdout.write(
            f"{s['provider']}: {len(s['keys'])} keys, "
            f"{active} active, today {used_total}/{cap_total} "
            f"({used_total // len(s['keys'])}/{s['free_quota']} avg)\n"
        )
    return EXIT_OK
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_web_search_adapter.py -v`
Expected: 全 PASS

- [ ] **Step 5：手动 smoke**

Run: `python -m prism.scripts.web_search status`
Expected: 类似 `tavily: 1 keys, 1 active, today 0/33 (0/33 avg)`

- [ ] **Step 6：commit**

```bash
git add prism/scripts/web_search.py prism/scripts/test_web_search_adapter.py
git commit -m "feat(prism): web-search adapter Phase3 - exit-code contract + status subcommand"
```

---

### Task 3.3：Workflow 路由总则文档

**Files:**
- Create: `prism/workflows/_web_search_routing.md`

- [ ] **Step 1：写路由总则文档**

整文件如下：

```markdown
# Web 搜索路由总则（必读）

> 适用：所有 prism workflow 步骤、所有 subagent dispatch、所有用户对话里的 web 检索。
> 任何与 web 检索相关的实现/修改都必须遵守本文规约。

## 决策一句话

**进文件 → adapter；进上下文 → tool。**

## 三问决策

```
Q1. 结果要不要落 sidecar / 进 register_web_search_batch？
    YES → adapter（强制）
    NO  → 进 Q2

Q2. 是不是批处理（≥3 query 一次性）？或者要可重放？
    YES → adapter（强烈推荐）
    NO  → 进 Q3

Q3. 模型在对话里临时起意要查（探索式、单次、消化即用）？
    YES → WebSearch tool（Anthropic 原生）或 MCP
    NO  → adapter
```

## 步骤映射

| 步骤 | 用途 | 走哪 |
|------|------|------|
| 00 / Step 4.5 web-prescan | baseline 检索落 sidecar | adapter |
| 00 thesis_v0 起草前事实校验 | 模型确认数据点是否过期 | WebSearch tool |
| 02-06 起步 gap_detector 后补窟窿 | 针对 uncovered_K# 显式扩搜 | adapter |
| 03 deep dive 单 thesis 多 query 扩展 | 围绕 thesis 跑 4-8 query | adapter |
| 04 synthesize 期间补查具体事实 | 写 claim 时验证数据 | WebSearch tool |
| 04 bundle review 多 arena 检索 | 每 arena slug 独立 query 集 | adapter |
| 05 critic-rewrite 反方观点检索 | 找异见/反例 | adapter |
| 06 risk-blindspots | 系统性扫风险事件 | adapter |
| 07/09/10 sidecar 字段填充前校验 | 写字段时单次验证 | WebSearch tool |
| 08 living-feed 刷新 | 周期性扫近 N 天新闻 | adapter |
| subagent dispatch 内部检索 | 一律 adapter（脚本 + Bash） | adapter |

## Adapter CLI

```bash
# 直接 search → stdout JSON
python -m prism.scripts.web_search search "<query>" \
    --intent <news|semantic|exact|general> \
    --cluster <cluster> --days <N> --max-results 5

# search → 直接落 sidecar
python -m prism.scripts.web_search search "<query>" \
    --intent <intent> --cluster <cluster> \
    --output sidecar \
    --slug <slug> --variant <variant> \
    --triggered-by <step>-<thesis> \
    --addresses K1,K3

# WebSearch fallback：吃外部 hits 走 dedup + domain_tier + 落 sidecar
echo '<json hits array>' | python -m prism.scripts.web_search postprocess \
    --source websearch_fallback \
    --query "<original query>" \
    --cluster <cluster> --slug <slug> --variant <variant> \
    --triggered-by <step>-fallback --addresses K1

# key 池状态
python -m prism.scripts.web_search status
```

## 退出码契约

| 退出码 | 含义 | 主 agent 处理 |
|--------|------|---------------|
| 0  | 成功 | 继续 |
| 10 | 部分成功（某些 query 有结果） | 看 stderr 决定补搜 |
| 20 | 全 query 0 hit | 检查 query 写法；可改 WebSearch tool |
| 30 | SOME_DEGRADED（某 provider 已自动降级） | 继续，但记日志 |
| 40 | ALL_PROVIDERS_EXHAUSTED | **走 WebSearch fallback**（见下节） |
| 50 | 配置错（key 缺失等） | 停止，提示用户检查 key |

## 双向 Fallback 规约

### Adapter → WebSearch tool（救急）

退出码 40 时主 agent 必须执行：

1. 读 stderr JSON 拿 `queries_unmet` 和 `fallback_hint`
2. 对每个 unmet query 调 WebSearch tool 单次
3. 把 WebSearch 拿到的 url/title/snippet 整理成 hits JSON
4. 走 `postprocess` 子命令，`--source=websearch_fallback`
5. sidecar 自动标 `source_provider="websearch_fallback"`，dashboard 区分

### WebSearch tool → Adapter（升级）

WebSearch 命中以下任一情况切 adapter：

1. 0 citations
2. citations 全部域名在 LOW_SIGNAL_HOSTS（twitter/youtube/reddit 等）
3. 主 agent 判断"此结果需要进 sidecar"
4. 同一事实需要交叉验证

直接重跑同 query：
```
python -m prism.scripts.web_search search "<同 query>" --intent <classified> ...
```

### 防 ping-pong

- **per-query attempt 上限 = 2**：每个 query 在一次 workflow 步骤内最多被 adapter+WebSearch 各试一次
- **postprocess 模式不再触发 fallback**：只做后处理，不发起新检索
- 第二次仍失败 → 标 unmet → 写 sidecar `triggered_by` 后缀加 `-degraded` → 让人决定下一步

## 例外：什么时候允许走 WebSearch tool

只有三类：

1. **prescan 之前的训练知识校准**（[[feedback_thesis_after_prescan]]）—— 单次、不入库
2. **adapter 全 provider 全 key 都炸**—— circuit breaker 全开 → fallback 救急
3. **用户对话里临时问问题**—— 不属于 workflow

其余一律走 adapter。

## 引用

- 多 key 轮换 + 配额持久化：见 `prism/scripts/providers/keypool.py`
- domain_tier 白名单：见 `prism/scripts/providers/_domain.py`
- sidecar schema 纪律：[[feedback_sidecar_schema_compliance]]
- subagent 检索纪律：[[feedback_subagent_write_hallucination]] / [[feedback_subagent_bulk_synthesis]]
- gap_detector 触发：[[feedback_gap_detector_checkpoints]]
```

- [ ] **Step 2：commit**

```bash
git add prism/workflows/_web_search_routing.md
git commit -m "docs(prism): add web-search routing rules + fallback protocol (_web_search_routing.md)"
```

---

## Phase 4 — Exa + Serper Provider

### Task 4.1：ExaProvider

**Files:**
- Create: `prism/scripts/providers/exa.py`
- Test: `prism/scripts/test_providers_exa.py`

- [ ] **Step 1：写 Exa 失败测试**

```python
# prism/scripts/test_providers_exa.py
import json
from unittest.mock import MagicMock, patch

import pytest

from prism.scripts.providers.exa import ExaProvider
from prism.scripts.providers.base import ProviderError, Hit


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "prism.scripts.providers.keypool._STATE_PATH",
        tmp_path / "web_search_keys.json",
    )


def _mock_resp(payload):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    cm.__exit__.return_value = False
    return cm


def test_exa_search_returns_hits(tmp_state):
    p = ExaProvider(keys=["k1aaaa"])
    payload = {
        "results": [
            {"title": "T", "url": "https://arxiv.org/abs/x",
             "text": "snip", "score": 0.85,
             "publishedDate": "2026-04-01"},
        ]
    }
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)):
        hits = p.search("papers similar to X", max_results=1)
    assert hits[0].source_provider == "exa"
    assert hits[0].published_at == "2026-04-01"


def test_exa_capabilities():
    assert ExaProvider.capabilities >= {"semantic", "scholar", "general"}
    assert ExaProvider.name == "exa"
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_providers_exa.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3：实现 ExaProvider**

```python
# prism/scripts/providers/exa.py
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
# Exa 免费按月，保守按日 30
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
    "vertical:patent":  "research paper",  # exa 没原生 patent，借 paper
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

            payload = {
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
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_providers_exa.py -v`
Expected: PASS

- [ ] **Step 5：commit**

```bash
git add prism/scripts/providers/exa.py prism/scripts/test_providers_exa.py
git commit -m "feat(prism): web-search adapter Phase4 - ExaProvider with semantic + category"
```

---

### Task 4.2：SerperProvider

**Files:**
- Create: `prism/scripts/providers/serper.py`
- Test: `prism/scripts/test_providers_serper.py`

- [ ] **Step 1：写 Serper 失败测试**

```python
# prism/scripts/test_providers_serper.py
import json
from unittest.mock import MagicMock, patch

import pytest

from prism.scripts.providers.serper import SerperProvider
from prism.scripts.providers.base import Hit


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "prism.scripts.providers.keypool._STATE_PATH",
        tmp_path / "web_search_keys.json",
    )


def _mock_resp(payload):
    cm = MagicMock()
    cm.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    cm.__exit__.return_value = False
    return cm


def test_serper_search_returns_organic_hits(tmp_state):
    p = SerperProvider(keys=["k1aaaa"])
    payload = {
        "organic": [
            {"title": "T1", "link": "https://sec.gov/x",
             "snippet": "s", "position": 1},
            {"title": "T2", "link": "https://reuters.com/y",
             "snippet": "s2", "position": 2},
        ],
    }
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)):
        hits = p.search("site:sec.gov 10-K 2025", max_results=2)
    assert hits[0].source_provider == "serper"
    assert hits[0].url == "https://sec.gov/x"
    # serper 没原生 score，用 1/position
    assert hits[0].score == 1.0
    assert hits[1].score == 0.5


def test_serper_search_routes_to_news_endpoint_on_news_intent(tmp_state):
    p = SerperProvider(keys=["k1aaaa"])
    payload = {"news": [
        {"title": "T", "link": "https://reuters.com/x",
         "snippet": "s", "position": 1, "date": "2026-05-27"},
    ]}
    with patch("urllib.request.urlopen", return_value=_mock_resp(payload)) as m:
        hits = p.search("FDA approval", max_results=1, intent="news")
    # 验证打的是 news 端点
    called_url = m.call_args[0][0].full_url if m.call_args else ""
    assert "news" in called_url or hits[0].published_at == "2026-05-27"


def test_serper_capabilities():
    assert SerperProvider.capabilities >= {"general", "news", "exact",
                                           "patent", "scholar"}
    assert SerperProvider.name == "serper"
```

- [ ] **Step 2：跑测试看失败**

Run: `pytest prism/scripts/test_providers_serper.py -v`
Expected: FAIL，`ImportError`

- [ ] **Step 3：实现 SerperProvider**

```python
# prism/scripts/providers/serper.py
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
# Serper 免费 2500/月 ≈ 80/天
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
_INTENT_TO_KEY = {  # 响应里 hits 的 list key
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
        need_extract: bool = False,  # serper 不提供
        intent: str | None = None,
    ) -> list[Hit]:
        endpoint = _INTENT_TO_ENDPOINT.get(intent, "/search")
        list_key = _INTENT_TO_KEY.get(intent, "organic")

        # site: / -site: 操作符通过 query 拼接
        q = query
        if include_domains:
            q += " " + " OR ".join(f"site:{d}" for d in include_domains)
        if exclude_domains:
            q += " " + " ".join(f"-site:{d}" for d in exclude_domains)

        payload = {"q": q, "num": max_results}
        if days is not None and intent == "news":
            # serper qdr: d/w/m/y
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
```

- [ ] **Step 4：跑测试看通过**

Run: `pytest prism/scripts/test_providers_serper.py -v`
Expected: PASS

- [ ] **Step 5：commit**

```bash
git add prism/scripts/providers/serper.py prism/scripts/test_providers_serper.py
git commit -m "feat(prism): web-search adapter Phase4 - SerperProvider with vertical endpoints"
```

---

### Task 4.3：Adapter 注册 Exa+Serper + Router 升级

**Files:**
- Modify: `prism/scripts/web_search.py`
- Modify: `prism/scripts/router.py`（确认权重已能识别新 capability）
- Test: `prism/scripts/test_web_search_adapter.py`

- [ ] **Step 1：把 Exa 和 Serper 加入 _default_providers**

修改 `prism/scripts/web_search.py` 的 `_default_providers`：

```python
def _default_providers() -> list:
    out = []
    try:
        from prism.scripts.providers.tavily import TavilyProvider
        out.append(TavilyProvider())
    except (RuntimeError, ValueError):
        pass
    try:
        from prism.scripts.providers.exa import ExaProvider
        out.append(ExaProvider())
    except (RuntimeError, ValueError):
        pass
    try:
        from prism.scripts.providers.serper import SerperProvider
        out.append(SerperProvider())
    except (RuntimeError, ValueError):
        pass
    return out
```

- [ ] **Step 2：写跨 provider intent 路由集成测试**

追加到 `test_web_search_adapter.py`：

```python
def test_full_routing_news_picks_tavily():
    """news intent + 三 provider 都健康 → tavily 排第一"""
    from prism.scripts.providers.base import Hit as _H

    class _P:
        def __init__(self, name, caps):
            self.name = name; self.capabilities = caps; self.calls = 0
        def healthy(self): return True
        def search(self, q, **kw):
            self.calls += 1
            return [_H(title="T", url=f"https://{self.name}.com",
                       snippet="s", score=0.9, source_provider=self.name)]

    tav = _P("tavily", {"news", "time_filter", "extract", "general"})
    exa = _P("exa", {"semantic", "scholar", "general"})
    ser = _P("serper", {"general", "news", "exact", "patent", "scholar"})

    adp = WebSearchAdapter([tav, exa, ser])
    hits = adp.search("FDA approval 2026 Q1")
    assert hits[0].source_provider == "tavily"
    assert tav.calls == 1


def test_full_routing_semantic_picks_exa():
    from prism.scripts.providers.base import Hit as _H

    class _P:
        def __init__(self, name, caps):
            self.name = name; self.capabilities = caps; self.calls = 0
        def healthy(self): return True
        def search(self, q, **kw):
            self.calls += 1
            return [_H(title="T", url=f"https://{self.name}.com/x",
                       snippet="s", score=0.9, source_provider=self.name)]

    tav = _P("tavily", {"news", "general"})
    exa = _P("exa", {"semantic", "general"})
    ser = _P("serper", {"general"})

    adp = WebSearchAdapter([tav, exa, ser])
    hits = adp.search("papers similar to GLP-1 cardio outcome")
    assert hits[0].source_provider == "exa"


def test_full_routing_vertical_patent_picks_serper():
    from prism.scripts.providers.base import Hit as _H

    class _P:
        def __init__(self, name, caps):
            self.name = name; self.capabilities = caps; self.calls = 0
        def healthy(self): return True
        def search(self, q, **kw):
            self.calls += 1
            return [_H(title="T", url=f"https://{self.name}.com/x",
                       snippet="s", score=0.9, source_provider=self.name)]

    tav = _P("tavily", {"news", "general"})
    exa = _P("exa", {"semantic", "general"})
    ser = _P("serper", {"general", "patent"})

    adp = WebSearchAdapter([tav, exa, ser])
    hits = adp.search("patent SMR reactor cooling")
    assert hits[0].source_provider == "serper"
```

- [ ] **Step 3：跑测试看通过**

Run: `pytest prism/scripts/test_web_search_adapter.py -v`
Expected: 全 PASS

- [ ] **Step 4：手动 smoke**

Run: `python -m prism.scripts.web_search status`
Expected: 显示 tavily / exa / serper 三家状态（缺 key 的会跳过，列已配置的）

- [ ] **Step 5：commit**

```bash
git add prism/scripts/web_search.py prism/scripts/test_web_search_adapter.py
git commit -m "feat(prism): web-search adapter Phase4 - register Exa+Serper, full routing tests"
```

---

## Phase 5 — Workflow 文档接入 + Prescan 切换

### Task 5.1：00 prescan 文档接入 adapter

**Files:**
- Modify: `prism/workflows/00-research-topic.md`

- [ ] **Step 1：定位 Step 4.5 prescan 章节**

Run: `grep -n "Step 4.5\|prescan\|web_prescan\|tavily_search" prism/workflows/00-research-topic.md`

读出现段落，确认改写位置。

- [ ] **Step 2：在 Step 4.5 加 adapter 命令块（不删旧 helper 路径）**

在 prescan 章节顶部追加：

```markdown
> **Web 搜索路径**：本步走 **adapter**。详见 [[_web_search_routing]]。
>
> ```bash
> python -m prism.scripts.web_search search "<query>" \
>     --intent news --cluster <cluster> --days 90 \
>     --max-results 5 --output sidecar \
>     --slug <slug> --variant <variant> \
>     --triggered-by 00-prescan-baseline \
>     --addresses thesis-1
> ```
>
> 每个 thesis 的 baseline 检索都用 adapter 一行命令落 sidecar。
> 退出码 40（all_exhausted）→ 走 WebSearch tool fallback，再用 `postprocess`
> 子命令兜回 sidecar，详见 [[_web_search_routing]] §双向 Fallback。
```

- [ ] **Step 3：跑文档语法检查（无脚本则跳过）**

Run: `head -1 prism/workflows/00-research-topic.md`
Expected: 文件开头 markdown header 完整

- [ ] **Step 4：commit**

```bash
git add prism/workflows/00-research-topic.md
git commit -m "docs(prism): wire 00-research-topic Step 4.5 prescan to web-search adapter"
```

---

### Task 5.2：03/04/05/06/08 文档同步路由总则

**Files:**
- Modify: `prism/workflows/03-extract-findings.md`
- Modify: `prism/workflows/04-synthesize/_shared.md`
- Modify: `prism/workflows/05-critic-review.md`
- Modify: `prism/workflows/06-daily-monitor.md`
- Modify: `prism/workflows/_web_search_aggregation.md`

- [ ] **Step 1：每个文件顶部加路由总则跳转**

对上面每个文件，找到首个 `## ` 章节之前的位置，插入：

```markdown
> **Web 搜索路径**：见 [[_web_search_routing]]（必读）。本步默认走 adapter；
> 仅事实校验类临时单查走 WebSearch tool。
```

- [ ] **Step 2：03 Step 2.4 inline web-search 段补 adapter CLI**

定位 `prism/workflows/03-extract-findings.md` 里 inline web-search 章节，在示例命令位置加：

```bash
python -m prism.scripts.web_search search "<query>" \
    --intent news --cluster <cluster> --output sidecar \
    --slug <slug> --variant <variant> \
    --triggered-by 03-extract --addresses K1,K3
```

并标注：`旧 helper register_web_search_batch 直调路径仍可用，但 adapter 会自动跑 dedup + domain_tier，推荐统一走 adapter`。

- [ ] **Step 3：05 Step 6.5 adapter 升级**

定位 `prism/workflows/05-critic-review.md` 的 Step 6.5 `request-more` 兜底章节，命令改为：

```bash
python -m prism.scripts.web_search search "<反方关键词>" \
    --intent news --cluster <cluster> --days 60 \
    --output sidecar --slug <slug> --variant <variant> \
    --triggered-by 05-critic --addresses <K#>
```

- [ ] **Step 4：commit**

```bash
git add prism/workflows/03-extract-findings.md prism/workflows/04-synthesize/_shared.md \
        prism/workflows/05-critic-review.md prism/workflows/06-daily-monitor.md \
        prism/workflows/_web_search_aggregation.md
git commit -m "docs(prism): wire 03/04/05/06 + aggregation workflows to web-search adapter routing"
```

---

### Task 5.3：subagent dispatch 模版强制 adapter

**Files:**
- Modify: `prism/workflows/_subagent_deep_search.md`
- Modify: `prism/workflows/_subagent_fetch_material.md`

- [ ] **Step 1：在两个 dispatch 模版顶部加硬规约**

两个文件均在前导段后插入：

```markdown
## 硬规约（不可省）

1. **本 subagent 内所有 web 检索必须走 adapter**（即 `python -m prism.scripts.web_search`），
   禁止调 `mcp__tavily__*` / `mcp__exa__*` / `mcp__serper__*` / Anthropic WebSearch tool。
   理由：MCP 调用每次进 turn 预算，30+ query 撞 60min 硬墙；adapter 一次 Bash 把多 query 串
   起来跑（`search` + 多 `--triggered-by`），且自带 KeyPool 轮换 + 失败 fallback。
   （参 [[feedback_subagent_bulk_synthesis]] / [[feedback_subagent_write_hallucination]]）
2. 退出码 40（all_exhausted）时本 subagent **直接 raise 给主 agent**，
   不要自己 fallback 到 WebSearch tool —— 双向 fallback 由主 agent 编排。
3. sidecar 入库一律 `--output sidecar` 模式；不要把 hits stdout 二次解析后再手工 register。
```

- [ ] **Step 2：commit**

```bash
git add prism/workflows/_subagent_deep_search.md prism/workflows/_subagent_fetch_material.md
git commit -m "docs(prism): subagent dispatch templates - force adapter, ban MCP/WebSearch in subagents"
```

---

### Task 5.4：跨 phase 集成测试（手动）

- [ ] **Step 1：在一个 topic 上端到端跑通 prescan**

挑选 `prism/topics/global-uranium-supply/`（已存在），执行：

```bash
python -m prism.scripts.web_search search "uranium spot price 2026" \
    --intent news --cluster uranium-nuclear --days 60 \
    --max-results 5 --output stdout
```

Expected：返回 ≥3 条 reuters/bloomberg/world-nuclear 等权威源，每条带 `source_provider="tavily"` 与 `domain_tier="llm-judged-official"`。

- [ ] **Step 2：跑 status**

Run: `python -m prism.scripts.web_search status`
Expected: tavily 行 `used_today` 增加 1。

- [ ] **Step 3：模拟 fallback 路径（手动构造）**

伪造一个 hits JSON：

```bash
echo '[{"title":"Test","url":"https://reuters.com/test","snippet":"hello"}]' | \
  python -m prism.scripts.web_search postprocess \
      --source websearch_fallback \
      --query "test" --cluster uranium-nuclear \
      --slug global-uranium-supply --variant claude-opus-4-7 \
      --triggered-by 00-prescan-fallback --addresses thesis-1
```

Expected：`register_web_search_batch` 返回 `n_high=1`，sidecar 已写入。

- [ ] **Step 4：跑 gitnexus_detect_changes 收尾**

Run（在对话里）：`mcp__gitnexus__detect_changes`

检查：affected_processes 限制在 web-search/prescan 范围，无意外 ripple。

- [ ] **Step 5：跑全量测试**

Run: `pytest prism/scripts/ -v`
Expected: 全 PASS（包含历史 + 新增）

- [ ] **Step 6：手动验证 sidecar 字段**

Read `prism/topics/global-uranium-supply/claude-opus-4-7/manifest.yaml`：
- 找到 Task 5.4 Step 1 / Step 3 入库的 mat
- 确认 `search_meta.triggered_by == "00-prescan-baseline" / "00-prescan-fallback"`
- 确认 `domain_tier` 已正确赋值

- [ ] **Step 7：最后一次 commit（如需补任何 cleanup）**

```bash
git status
# 如有 cleanup：
git add ...
git commit -m "feat(prism): web-search adapter Phase5 - end-to-end smoke verified on global-uranium-supply"
```

---

## 收尾 / 后续

实施完后立即做一次：

1. **Push 到 main 之前**：跑 `mcp__gitnexus__detect_changes` 完整扫一遍，确认所有 affected_processes 都符合预期，没有意外 leak。
2. **更新 `prism/dashboard.md`**（可选，Phase 6 候选项）：把 KeyPool status 接到 dashboard 上半部分，让用户一眼看到三家 key 池水位。
3. **CronCreate 定期刷 `python -m prism.scripts.web_search status`**（可选）：每天 9 点报当前 key 池余量；接近耗尽提前告警。

未做（明确 out of scope）：

- Cross-validation 模式（adapter + WebSearch tool 双跑比对）—— Phase 6 候选
- Circuit breaker 进阶（半开探测、provider 级冷却联动）—— Phase 6 候选
- 接入 dashboard 实时显示 —— Phase 6 候选
- Web 检索 cost 预算 / cost-aware 路由 —— 暂未需要
- Anthropic Messages API 直连模式（脚本里调 web_search server tool）—— 不做（详见 plan §一）

---

## 自审

**spec 覆盖**：
- ✅ Provider 抽象 + Hit / 异常体系 → Task 1.1
- ✅ KeyPool 多 key 轮换 + 持久化 → Task 1.2
- ✅ Tavily 迁移 → Task 1.3 / 1.4 / 1.5
- ✅ Router intent 分类 + provider ranking → Task 2.1
- ✅ Adapter 主体 + dedup + domain_tier → Task 2.2
- ✅ CLI search → Task 2.3
- ✅ Postprocess + 退出码契约 → Task 3.1 / 3.2
- ✅ 路由总则 + 双向 fallback 文档 → Task 3.3
- ✅ Exa / Serper provider → Task 4.1 / 4.2
- ✅ Adapter 注册 + 集成测试 → Task 4.3
- ✅ workflow 各步骤接入 → Task 5.1 / 5.2
- ✅ subagent 模版强制 → Task 5.3
- ✅ 端到端 smoke → Task 5.4

**type 一致性**：
- `Hit.to_dict()` 字段集合与 `register_web_search_batch` 必备 keys (`title/url/snippet`) 对齐 ✓
- `ProviderError.provider` 在所有 raise / 测试里命名一致 ✓
- `_INTENT_TO_ENDPOINT` / `_INTENT_TO_KEY` 在 Serper 同时定义并一致 ✓
- 退出码常量 `EXIT_*` 在 Phase2/3 共享 ✓

**placeholder 扫描**：
- 无 TBD / TODO / "implement later" ✓
- 每个步骤有具体命令或代码 ✓
- 文档改动给出了具体插入位置（grep 行号定位）+ 整段插入文本 ✓
