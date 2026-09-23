"""surf · 主题归一与载体资格（LLM 判定层）的读写。

本文件**不调用 LLM**——它只负责落盘格式、缓存与合并。判定由 Claude 在扫描流程
Step 2 中做（SKILL），输入只有「代码 + 名称 (+ 美股的 Morningstar 类别)」，
**不含任何行情数据**：给了涨跌幅，LLM 会按「涨得好的归一类」来分组，
等于从后门破掉铁律 2（DESIGN §6.1）。

数据流：
    scan_*.py fetch     → universe_{mkt}.csv（规则层 + 流动性筛完的幸存者）
    Claude 判定          → themes.json（本文件的 write_themes）
    scan_*.py finalize  → 读 themes.json，做 not_carrier 剔除与同主题折叠

缓存 `surf/theme_cache.json`：同一只 ETF 的主题基本不随时间变，只有新出现的代码
才需要判定，控制每期扫描的 token 开销。
"""
from __future__ import annotations

import json
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE_PATH = os.path.join(_ROOT, "theme_cache.json")

# themes.json / theme_cache.json 的单条记录字段
FIELDS = ("代码", "名称", "theme", "is_trend_carrier", "reason")


def load_cache() -> dict[str, dict]:
    """读全局主题缓存，key 为代码。文件不存在返回空字典。"""
    if not os.path.exists(CACHE_PATH):
        return {}
    with open(CACHE_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_cache(cache: dict[str, dict]) -> None:
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def pending(codes: list[str], names: dict[str, str]) -> list[dict]:
    """返回缓存里还没有的标的，即本期需要 LLM 判定的清单。

    输出**只带名称**，调用方不得往里加行情字段。
    """
    cache = load_cache()
    return [{"代码": c, "名称": names.get(c, "")} for c in codes if c not in cache]


def write_themes(scan_dir: str, records: list[dict]) -> str:
    """把本期用到的全部判定写入 scans/{date}/themes.json，并回写全局缓存。"""
    for r in records:
        missing = [k for k in FIELDS if k not in r]
        if missing:
            raise ValueError(f"themes 记录缺字段 {missing}: {r}")
    path = os.path.join(scan_dir, "themes.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    cache = load_cache()
    cache.update({r["代码"]: r for r in records})
    save_cache(cache)
    return path


def read_themes(scan_dir: str) -> dict[str, dict]:
    """读本期判定；本期文件缺的条目回落到全局缓存。"""
    out = dict(load_cache())
    path = os.path.join(scan_dir, "themes.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for r in json.load(f):
                out[r["代码"]] = r
    return out
