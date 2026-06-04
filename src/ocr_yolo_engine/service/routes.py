"""/v1 路由:单方法 + 合并 + 上传 + 资产列表 + 健康检查。"""

from __future__ import annotations

import base64
from typing import Any, cast

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ocr_yolo_engine.image.loader import decode_image_bytes
from ocr_yolo_engine.observability.logging import bind_request_id, new_request_id
from ocr_yolo_engine.pipeline_runner import run_recognition
from ocr_yolo_engine.schemas import ImageInput, Method, RecognizeRequest, RecognizeResponse
from ocr_yolo_engine.service.auth import require_api_key
from ocr_yolo_engine.service.deps import AppContext

router = APIRouter()

# 各受保护路由共用的鉴权依赖
_AUTH = [Depends(require_api_key)]


def _ctx(request: Request) -> AppContext:
    return cast(AppContext, request.app.state.ctx)


def _run(request: Request, req: RecognizeRequest) -> RecognizeResponse:
    bind_request_id(new_request_id())
    return run_recognition(_ctx(request), req)


@router.post("/v1/ocr", response_model=RecognizeResponse, dependencies=_AUTH)
def ocr(request: Request, body: ImageInput) -> RecognizeResponse:
    return _run(request, RecognizeRequest(image=body, methods=["ocr"]))


@router.post("/v1/detect", response_model=RecognizeResponse, dependencies=_AUTH)
def detect(request: Request, body: RecognizeRequest) -> RecognizeResponse:
    body.methods = ["yolo"]
    return _run(request, body)


@router.post("/v1/match", response_model=RecognizeResponse, dependencies=_AUTH)
def match(request: Request, body: RecognizeRequest) -> RecognizeResponse:
    body.methods = ["template"]
    return _run(request, body)


@router.post("/v1/recognize", response_model=RecognizeResponse, dependencies=_AUTH)
def recognize(request: Request, body: RecognizeRequest) -> RecognizeResponse:
    return _run(request, body)


@router.post("/v1/recognize/upload", response_model=RecognizeResponse, dependencies=_AUTH)
async def recognize_upload(
    request: Request,
    file: UploadFile = File(...),
    methods: str = Form(...),
    model: str | None = Form(default=None),
    templates: str | None = Form(default=None),
    conf_threshold: float | None = Form(default=None),
) -> RecognizeResponse:
    data = await file.read()
    decode_image_bytes(data)  # 校验可解码,失败抛 INVALID_IMAGE
    b64 = base64.b64encode(data).decode()
    method_list: list[Method] = [m.strip() for m in methods.split(",") if m.strip()]  # type: ignore[misc]
    template_list = [t.strip() for t in templates.split(",")] if templates else None
    req = RecognizeRequest(
        image=ImageInput(base64=b64),
        methods=method_list,
        model=model,
        templates=template_list,
        conf_threshold=conf_threshold,
    )
    return _run(request, req)


@router.get("/v1/models", dependencies=_AUTH)
def list_models(request: Request) -> dict[str, Any]:
    reg = _ctx(request).registry
    return {"models": [{"name": n, "version": reg.spec(n).version} for n in reg.list_models()]}


@router.post("/v1/models/{name}/unload", dependencies=_AUTH)
def unload_model(request: Request, name: str) -> dict[str, Any]:
    """卸载模型缓存(释放显存/内存)。name 未注册返回 404;已注册但未加载是 no-op。"""
    reg = _ctx(request).registry
    reg.spec(name)  # 未注册抛 MODEL_NOT_FOUND → 全局异常处理器转 404
    reg.unload(name)
    return {"name": name, "status": "unloaded", "loaded": reg.loaded_names()}


@router.post("/v1/models/{name}/reload", dependencies=_AUTH)
def reload_model(request: Request, name: str) -> dict[str, Any]:
    """重载模型(真实加载权重),用于不重启切换/刷新模型。name 未注册返回 404。"""
    reg = _ctx(request).registry
    reg.spec(name)  # 未注册抛 MODEL_NOT_FOUND → 全局异常处理器转 404
    reg.reload(name)
    return {"name": name, "version": reg.spec(name).version, "status": "reloaded"}


@router.get("/v1/templates", dependencies=_AUTH)
def list_templates(request: Request) -> dict[str, Any]:
    store = _ctx(request).template_store
    return {
        "templates": [{"name": n, "version": store.spec(n).version} for n in store.list_templates()]
    }


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    return {"status": "ready", "models": ctx.registry.list_models()}
