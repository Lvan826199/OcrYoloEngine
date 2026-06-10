"""FastAPI 应用装配:DI 容器、异常处理、路由。"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from ocr_yolo_engine.errors import EngineError
from ocr_yolo_engine.observability.logging import (
    bind_request_id,
    current_request_id,
    new_request_id,
    setup_logging,
)
from ocr_yolo_engine.service.deps import AppContext, build_context
from ocr_yolo_engine.service.routes import router
from ocr_yolo_engine.settings import Settings

_access_logger = logging.getLogger("ocr_yolo_engine.access")


def create_app(ctx: AppContext | None = None, settings: Settings | None = None) -> FastAPI:
    setup_logging()

    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        # 服务停止时关停推理线程池,不留孤儿线程。
        app.state.ctx.executor.shutdown()

    app = FastAPI(
        lifespan=_lifespan,
        title="OcrYoloEngine",
        version="0.2.1",
        description="面向自动化测试的视觉识别服务——截图发过来，返回文字和目标的坐标。",
        openapi_tags=[
            {"name": "识别", "description": "核心识别接口：文字识别、目标检测、模板匹配"},
            {"name": "文件上传", "description": "用文件上传方式（而非 base64）发送图片"},
            {"name": "资产管理", "description": "查看和管理已登记的模型与模板"},
            {"name": "运维", "description": "健康检查、就绪检查、运行指标"},
        ],
    )
    app.state.ctx = ctx or build_context(settings)

    # request_id 必须在 async 中间件里绑定:同步路由跑在线程池,
    # 线程内对 contextvar 的修改传不回事件循环,异常处理器会取到占位 "-"。
    # 同一中间件顺带:给所有响应(含错误)加 X-Request-ID 头 + 记结构化访问日志。
    @app.middleware("http")
    async def _request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = new_request_id()
        bind_request_id(request_id)
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        _access_logger.info(
            "access",
            extra={
                "extra_fields": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "elapsed_ms": round(elapsed_ms, 2),
                }
            },
        )
        return response

    @app.exception_handler(EngineError)
    async def _engine_error_handler(request: Request, exc: EngineError) -> JSONResponse:
        headers = {}
        if exc.code.value == "OVERLOADED":
            headers["Retry-After"] = str(exc.details.get("retry_after", 1))
        return JSONResponse(
            status_code=exc.http_status, content=exc.to_body(current_request_id()), headers=headers
        )

    @app.get("/", include_in_schema=False)
    async def _root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    app.include_router(router)
    return app
