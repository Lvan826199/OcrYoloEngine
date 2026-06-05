"""FastAPI 应用装配:DI 容器、异常处理、路由。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse

from ocr_yolo_engine.errors import EngineError
from ocr_yolo_engine.observability.logging import current_request_id, setup_logging
from ocr_yolo_engine.service.deps import AppContext, build_context
from ocr_yolo_engine.service.routes import router
from ocr_yolo_engine.settings import Settings


def create_app(ctx: AppContext | None = None, settings: Settings | None = None) -> FastAPI:
    setup_logging()
    app = FastAPI(
        title="OcrYoloEngine",
        version="0.1.0",
        description="面向自动化测试的视觉识别服务——截图发过来，返回文字和目标的坐标。",
        openapi_tags=[
            {"name": "识别", "description": "核心识别接口：文字识别、目标检测、模板匹配"},
            {"name": "文件上传", "description": "用文件上传方式（而非 base64）发送图片"},
            {"name": "资产管理", "description": "查看和管理已登记的模型与模板"},
            {"name": "运维", "description": "健康检查、就绪检查、运行指标"},
        ],
    )
    app.state.ctx = ctx or build_context(settings)

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
