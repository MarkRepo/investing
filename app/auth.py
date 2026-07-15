"""简单 cookie token 鉴权。

只保护触发 LLM 的 endpoint。token 存 .env PRISM_AUTH_TOKEN，
客户端首次通过 POST /prism/auth 验证后写 30 天 cookie。
"""
from __future__ import annotations

import os
from fastapi import Cookie, HTTPException

_TOKEN = os.environ.get("PRISM_AUTH_TOKEN", "")


def require_auth(prism_auth: str | None = Cookie(default=None)) -> None:
    """FastAPI Depends — cookie 不存在或 token 不匹配时返回 401。"""
    if not _TOKEN:
        return  # 未配置 token 时放行（降级兼容）
    if prism_auth != _TOKEN:
        raise HTTPException(status_code=401, detail="unauthorized")
