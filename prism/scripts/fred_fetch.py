"""FRED 自动抓取（第二期）。零 LLM：读登记表里 fetch_method==fred-api 的输入，
拉最新观测，调 macro_registry.record_observation 落 observed。单测 mock httpx。"""
from __future__ import annotations

import os

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"


def get_fred_api_key() -> str:
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise RuntimeError("FRED_API_KEY 未设置（见 .env.example）")
    return key
