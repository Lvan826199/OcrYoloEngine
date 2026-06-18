"""/v1 路由:单方法 + 合并 + 上传 + 资产列表 + 健康检查。"""

from __future__ import annotations

import base64
from typing import Any, cast

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from ocr_yolo_engine.image.loader import decode_image_bytes
from ocr_yolo_engine.observability import metrics
from ocr_yolo_engine.pipeline_runner import run_recognition
from ocr_yolo_engine.preprocessing.pipeline import enforce_byte_limit
from ocr_yolo_engine.schemas import (
    DetectRequest,
    ImageInput,
    MatchRequest,
    Method,
    RecognizeRequest,
    RecognizeResponse,
)
from ocr_yolo_engine.service.auth import require_api_key
from ocr_yolo_engine.service.deps import AppContext

router = APIRouter()

# 各受保护路由共用的鉴权依赖
_AUTH = [Depends(require_api_key)]


def _ctx(request: Request) -> AppContext:
    return cast(AppContext, request.app.state.ctx)


def _run(
    request: Request,
    req: RecognizeRequest,
    response: Response,
    preloaded: tuple[bytes, Any] | None = None,
) -> RecognizeResponse:
    ctx = _ctx(request)
    result = run_recognition(ctx, req, preloaded=preloaded)
    # X-Cache 头:缓存关闭或本次 off → BYPASS;命中 → HIT;算了且缓存开 → MISS。
    if ctx.settings.result_cache_size == 0 or req.cache == "off":
        response.headers["X-Cache"] = "BYPASS"
    elif result.from_cache:
        response.headers["X-Cache"] = "HIT"
    else:
        response.headers["X-Cache"] = "MISS"
    return result


@router.post(
    "/v1/ocr",
    response_model=RecognizeResponse,
    dependencies=_AUTH,
    tags=["识别"],
    summary="文字识别（OCR）",
    description="传入截图，识别图中所有文字，返回每段文字的内容、坐标和置信度。"
    "不需要提前准备模型，内置模型首次使用时自动下载。"
    '\n\n**请求体直接传图片**（`{"base64": "..."}`），不需要套 `image` 字段。',
)
def ocr(request: Request, body: ImageInput, response: Response) -> RecognizeResponse:
    return _run(request, RecognizeRequest(image=body, methods=["ocr"]), response)


@router.post(
    "/v1/detect",
    response_model=RecognizeResponse,
    dependencies=_AUTH,
    tags=["识别"],
    summary="目标检测（YOLO）",
    description="传入截图和模型名，检测图中的目标物体，返回每个目标的类别、坐标和置信度。"
    "\n\n需要在 `configs/models.yaml` 里登记模型。"
    "仓库自带通用模型 `yolov8n`（能识别人、车、动物等 80 类）。",
)
def detect(request: Request, body: DetectRequest, response: Response) -> RecognizeResponse:
    return _run(request, body.to_recognize_request(), response)


@router.post(
    "/v1/match",
    response_model=RecognizeResponse,
    dependencies=_AUTH,
    tags=["识别"],
    summary="模板匹配",
    description="传入截图和模板名，在图中查找与模板相似的区域，返回匹配位置的坐标和置信度。"
    "\n\n需要在 `configs/templates.yaml` 里登记模板。"
    "仓库自带示例模板 `demo_block`，安装后即可体验。",
)
def match(request: Request, body: MatchRequest, response: Response) -> RecognizeResponse:
    return _run(request, body.to_recognize_request(), response)


@router.post(
    "/v1/recognize",
    response_model=RecognizeResponse,
    dependencies=_AUTH,
    tags=["识别"],
    summary="多方式混合识别",
    description="一次请求同时使用多种识别方式（OCR / YOLO / 模板匹配），各方式结果分组返回。"
    "\n\n支持 4 种合并策略（`merge` 字段）："
    "\n- `none`（默认）：各方式结果分开"
    "\n- `priority`：按顺序试，有结果就停"
    "\n- `dedup`：合并后去除重叠的重复项"
    "\n- `concat`：全部合在一起按置信度排序",
)
def recognize(request: Request, body: RecognizeRequest, response: Response) -> RecognizeResponse:
    return _run(request, body, response)


@router.post(
    "/v1/recognize/upload",
    response_model=RecognizeResponse,
    dependencies=_AUTH,
    tags=["文件上传"],
    summary="文件上传识别",
    description="用文件上传方式发送图片（不用 base64 编码），功能和 `/v1/recognize` 一样。"
    "\n\n`methods` 用逗号分隔，如 `ocr,template`；`templates` 同理。",
)
async def recognize_upload(
    request: Request,
    response: Response,
    file: UploadFile = File(description="要识别的图片文件"),
    methods: str = Form(description="识别方式，逗号分隔：ocr / yolo / template"),
    model: str | None = Form(default=None, description="YOLO 模型名（用 yolo 时必填）"),
    templates: str | None = Form(
        default=None, description="模板名，逗号分隔（用 template 时必填）"
    ),
    conf_threshold: float | None = Form(
        default=None, description="置信度门槛 0~1（可选，不填用默认值）"
    ),
) -> RecognizeResponse:
    data = await file.read()
    enforce_byte_limit(data, max_bytes=_ctx(request).settings.max_image_bytes)
    img = decode_image_bytes(data)  # 解码一次,失败抛 INVALID_IMAGE;结果直接传给管线复用
    b64 = base64.b64encode(data).decode()
    method_list: list[Method] = [m.strip() for m in methods.split(",") if m.strip()]  # type: ignore[misc]
    template_list = [t.strip() for t in templates.split(",")] if templates else None
    try:
        req = RecognizeRequest(
            image=ImageInput(base64=b64),
            methods=method_list,
            model=model,
            templates=template_list,
            conf_threshold=conf_threshold,
        )
    except ValidationError as exc:
        # 手工构造模型的校验失败不会被 FastAPI 自动接管,
        # 显式转成 RequestValidationError,与 JSON 接口一样返回 422。
        raise RequestValidationError(exc.errors()) from exc
    return _run(request, req, response, preloaded=(data, img))


@router.get(
    "/v1/models",
    dependencies=_AUTH,
    tags=["资产管理"],
    summary="查看已登记的模型",
    description="返回 `configs/models.yaml` 中登记的所有 YOLO 模型名称和版本。",
)
def list_models(request: Request) -> dict[str, Any]:
    reg = _ctx(request).registry
    return {"models": [{"name": n, "version": reg.spec(n).version} for n in reg.list_models()]}


@router.post(
    "/v1/models/{name}/unload",
    dependencies=_AUTH,
    tags=["资产管理"],
    summary="卸载模型（释放内存）",
    description="把指定模型从内存中卸载，释放内存/显存。模型名未登记返回 404。"
    "已登记但没有加载过的模型调了也不会报错。",
)
def unload_model(request: Request, name: str) -> dict[str, Any]:
    reg = _ctx(request).registry
    reg.spec(name)  # 未注册抛 MODEL_NOT_FOUND → 全局异常处理器转 404
    reg.unload(name)
    # 资产变更,旧缓存可能失效,整体清空(关闭态为 no-op)。
    _ctx(request).cache.clear()
    return {"name": name, "status": "unloaded", "loaded": reg.loaded_names()}


@router.post(
    "/v1/models/{name}/reload",
    dependencies=_AUTH,
    tags=["资产管理"],
    summary="重新加载模型",
    description="重新加载指定模型的权重文件。"
    "用法：更新了模型文件后调一次 reload，不用重启服务就能让新版本生效。",
)
def reload_model(request: Request, name: str) -> dict[str, Any]:
    reg = _ctx(request).registry
    reg.spec(name)  # 未注册抛 MODEL_NOT_FOUND → 全局异常处理器转 404
    reg.reload(name)
    # 资产变更,旧缓存作废,整体清空(关闭态为 no-op)。
    _ctx(request).cache.clear()
    return {"name": name, "version": reg.spec(name).version, "status": "reloaded"}


@router.get(
    "/v1/templates",
    dependencies=_AUTH,
    tags=["资产管理"],
    summary="查看已登记的模板",
    description="返回 `configs/templates.yaml` 中登记的所有模板名称和版本。",
)
def list_templates(request: Request) -> dict[str, Any]:
    store = _ctx(request).template_store
    return {
        "templates": [{"name": n, "version": store.spec(n).version} for n in store.list_templates()]
    }


@router.get(
    "/health",
    tags=["运维"],
    summary="健康检查",
    description='检查服务是否存活。返回 `{"status": "ok"}` 表示正常。不需要密钥。',
)
def health() -> dict[str, Any]:
    return {"status": "ok"}


@router.get(
    "/ready",
    tags=["运维"],
    summary="就绪检查",
    description="检查服务是否准备好接收请求。返回已配置的模型列表。不需要密钥。",
)
def ready(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    return {"status": "ready", "models": ctx.registry.list_models()}


@router.get(
    "/metrics",
    tags=["运维"],
    summary="运行指标",
    description="返回各识别方式的请求次数和累计耗时，Prometheus 文本格式。不需要密钥。",
)
def metrics_endpoint() -> Response:
    return Response(content=metrics.render(), media_type="text/plain; version=0.0.4; charset=utf-8")
