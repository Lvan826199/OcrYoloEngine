"""FastAPI 应用装配:DI 容器、异常处理、路由。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ocr_yolo_engine.errors import EngineError
from ocr_yolo_engine.observability.logging import current_request_id, setup_logging
from ocr_yolo_engine.service.deps import AppContext, build_context
from ocr_yolo_engine.service.routes import router
from ocr_yolo_engine.settings import Settings


def create_app(ctx: AppContext | None = None, settings: Settings | None = None) -> FastAPI:
    setup_logging()
    app = FastAPI(title="OcrYoloEngine", version="0.1.0")
    app.state.ctx = ctx or build_context(settings)

    @app.exception_handler(EngineError)
    async def _engine_error_handler(request: Request, exc: EngineError) -> JSONResponse:
        headers = {}
        if exc.code.value == "OVERLOADED":
            headers["Retry-After"] = str(exc.details.get("retry_after", 1))
        return JSONResponse(
            status_code=exc.http_status, content=exc.to_body(current_request_id()), headers=headers
        )

    app.include_router(router)
    return app
