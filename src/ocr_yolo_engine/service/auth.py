"""API Key 鉴权:api_keys 为空时关闭(本地友好)。"""

from __future__ import annotations

from fastapi import Header, HTTPException

from ocr_yolo_engine.settings import Settings, get_settings


def verify_api_key(provided: str | None, settings: Settings) -> None:
    if not settings.auth_enabled:
        return
    if provided is None or provided not in settings.api_keys:
        raise HTTPException(status_code=401, detail="无效或缺失的 API Key")


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    verify_api_key(x_api_key, get_settings())
