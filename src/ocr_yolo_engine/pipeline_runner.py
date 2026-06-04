"""核心识别管线:与 HTTP 解耦,串起加载/预处理/并发/识别/回映射/组装。"""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.image.loader import load_from_base64, load_from_path
from ocr_yolo_engine.observability.logging import current_request_id
from ocr_yolo_engine.preprocessing.annotate import draw_detections
from ocr_yolo_engine.preprocessing.pipeline import (
    crop_roi,
    enforce_limits,
    finalize_detections,
    to_rgb,
)
from ocr_yolo_engine.recognizers.base import InferContext, RawDetection
from ocr_yolo_engine.schemas import (
    Detection,
    Method,
    MethodResult,
    RecognizeRequest,
    RecognizeResponse,
)
from ocr_yolo_engine.service.deps import AppContext


def _template_versions(ctx: AppContext, names: list[str]) -> dict[str, str]:
    """收集模板版本作为元数据;缺失模板不阻断主流程,跳过即可。"""
    versions: dict[str, str] = {}
    for name in names:
        try:
            versions[name] = ctx.template_store.spec(name).version
        except EngineError:
            continue
    return versions


def _load_bytes_and_image(ctx: AppContext, req: RecognizeRequest) -> tuple[bytes, np.ndarray]:
    """返回 (raw_bytes, bgr_image)。raw_bytes 仅用于大小上限校验。"""
    if req.image.base64 is not None:
        # 先走 loader 解码:非法 base64 / 非图片在此抛 INVALID_IMAGE
        img = load_from_base64(req.image.base64)
        payload = (
            req.image.base64.split(",", 1)[1]
            if req.image.base64.startswith("data:")
            else req.image.base64
        )
        # 解码到此处已通过校验,raw 仅供字节数上限判断
        raw = base64.b64decode(payload, validate=True)
        return raw, img
    assert req.image.path is not None
    img = load_from_path(req.image.path, ctx.settings.allowed_path_roots)
    return b"", img


def run_recognition(ctx: AppContext, req: RecognizeRequest) -> RecognizeResponse:
    request_id = current_request_id()
    raw_bytes, bgr = _load_bytes_and_image(ctx, req)
    enforce_limits(
        raw_bytes,
        bgr,
        max_bytes=ctx.settings.max_image_bytes,
        max_pixels=ctx.settings.max_image_pixels,
    )
    full_h, full_w = bgr.shape[:2]
    rgb = to_rgb(bgr)
    cropped, offset = crop_roi(rgb, req.roi)

    conf = (
        req.conf_threshold
        if req.conf_threshold is not None
        else ctx.settings.default_conf_threshold
    )
    infer_ctx = InferContext(conf_threshold=conf, model=req.model, templates=req.templates or [])

    method_results: dict[Method, MethodResult] = {}
    for method in req.methods:
        recognizer = ctx.recognizers[method]
        model_key = req.model if method == "yolo" and req.model else method
        started = time.perf_counter()

        def _infer(r: object = recognizer) -> list[RawDetection]:
            return r.infer(cropped, infer_ctx)  # type: ignore[attr-defined, no-any-return]

        raws = ctx.executor.submit(model_key, _infer)
        elapsed_ms = (time.perf_counter() - started) * 1000
        detections = finalize_detections(list(raws), offset=offset, full_w=full_w, full_h=full_h)

        model_version = (
            ctx.registry.spec(req.model).version if method == "yolo" and req.model else None
        )
        template_versions = (
            _template_versions(ctx, req.templates)
            if method == "template" and req.templates
            else None
        )
        method_results[method] = MethodResult(
            detections=detections,
            model_version=model_version,
            template_versions=template_versions,
            elapsed_ms=elapsed_ms,
        )

    debug_image = _build_debug_image(bgr, method_results) if req.debug else None

    return RecognizeResponse(
        request_id=request_id,
        image_size=[full_w, full_h],
        method_results=method_results,
        debug_image=debug_image,
    )


def _build_debug_image(bgr: np.ndarray, method_results: dict[Method, MethodResult]) -> str:
    """汇总所有方法的检测框,在原始全图 BGR 副本上画框,返回 base64 编码的 PNG。"""
    detections: list[Detection] = []
    for result in method_results.values():
        detections.extend(result.detections)
    annotated = draw_detections(bgr, detections)
    ok, buf = cv2.imencode(".png", annotated)
    if not ok:
        raise EngineError(ErrorCode.INTERNAL, "调试标注图 PNG 编码失败")
    return base64.b64encode(buf.tobytes()).decode()
