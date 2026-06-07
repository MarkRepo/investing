"""FRED 自动抓取（第二期）。零 LLM：读登记表里 fetch_method==fred-api 的输入，
拉最新观测，调 macro_registry.record_observation 落 observed。单测 mock httpx。"""
from __future__ import annotations

import os

import httpx

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def get_fred_api_key() -> str:
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY 未设置（见 .env.example）")
    return key


def fetch_latest_observation(series_id: str, *, client=None) -> tuple[float | None, str | None]:
    """拉某 FRED series 的最新一条观测。返回 (value, as_of)；缺测/无数据返回 (None, date|None)。
    client 可注入（测试 mock）；默认用 httpx。"""
    params = {
        "series_id": series_id,
        "api_key": get_fred_api_key(),
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1,
    }
    owns = client is None
    if owns:
        client = httpx.Client()
    try:
        resp = client.get(FRED_BASE, params=params, timeout=30)
        resp.raise_for_status()
        obs = resp.json().get("observations") or []
    finally:
        if owns:
            client.close()
    if not obs:
        return None, None
    rec = obs[0]
    raw = rec.get("value")
    as_of = rec.get("date")
    if raw in (None, "", "."):
        return None, as_of
    try:
        return float(raw), as_of
    except ValueError:
        return None, as_of
