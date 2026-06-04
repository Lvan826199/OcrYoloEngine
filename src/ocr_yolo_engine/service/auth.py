"""API Key 鉴权:api_keys 为空时关闭(本地友好)。"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request

from ocr_yolo_engine.settings import Settings, get_settings


def verify_api_key(provided: str | None, settings: Settings) -> None:
    if not settings.auth_enabled:
        return
    if provided is None or provided not in settings.api_keys:
        raise HTTPException(status_code=401, detail="无效或缺失的 API Key")


def _settings_for(request: Request) -> Settings:
    """优先使用注入到 app.state 的上下文配置,缺失时回退全局配置。"""
    ctx = getattr(request.app.state, "ctx", None)
    if ctx is not None:
        return ctx.settings  # type: ignore[no-any-return]
    return get_settings()


async def require_api_key(request: Request, x_api_key: str | None = Header(default=None)) -> None:
    verify_api_key(x_api_key, _settings_for(request))
