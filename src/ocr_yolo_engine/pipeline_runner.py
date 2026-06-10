"""核心识别管线:与 HTTP 解耦,串起加载/预处理/并发/识别/回映射/组装。"""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np

from ocr_yolo_engine.cache import CachedResult, compute_cache_key
from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.image.loader import decode_image_bytes, load_from_path
from ocr_yolo_engine.merge import merge_detections
from ocr_yolo_engine.observability import metrics
from ocr_yolo_engine.observability.logging import current_request_id
from ocr_yolo_engine.preprocessing.annotate import draw_detections
from ocr_yolo_engine.preprocessing.pipeline import (
    crop_roi,
    enforce_byte_limit,
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
    """返回 (raw_bytes, bgr_image)。字节上限在图像解码前校验,防解压炸弹先吃内存。"""
    max_bytes = ctx.settings.max_image_bytes
    if req.image.base64 is not None:
        import binascii

        payload = (
            req.image.base64.split(",", 1)[1]
            if req.image.base64.startswith("data:")
            else req.image.base64
        )
        try:
            raw = base64.b64decode(payload, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise EngineError(ErrorCode.INVALID_IMAGE, "base64 解码失败") from exc
        enforce_byte_limit(raw, max_bytes=max_bytes)
        img = decode_image_bytes(raw)
        return raw, img
    assert req.image.path is not None
    return load_from_path(req.image.path, ctx.settings.allowed_path_roots, max_bytes=max_bytes)


def run_recognition(
    ctx: AppContext,
    req: RecognizeRequest,
    preloaded: tuple[bytes, np.ndarray] | None = None,
) -> RecognizeResponse:
    """执行识别。preloaded=(原始字节, BGR 图) 时跳过加载解码(上传接口已解码,免重复)。"""
    request_id = current_request_id()
    raw_bytes, bgr = preloaded if preloaded is not None else _load_bytes_and_image(ctx, req)
    enforce_limits(
        raw_bytes,
        bgr,
        max_bytes=ctx.settings.max_image_bytes,
        max_pixels=ctx.settings.max_image_pixels,
    )
    full_h, full_w = bgr.shape[:2]

    # 结果缓存守卫(外挂,不改核心计算):仅在缓存开启且非 off、非 debug 时生效。
    cache_on = ctx.settings.result_cache_size > 0 and req.cache != "off" and not req.debug
    key = compute_cache_key(raw_bytes, req) if cache_on else None
    # 读:仅 auto 模式读缓存(refresh 强制重算)。
    if cache_on and key is not None and req.cache == "auto":
        hit = ctx.cache.get(key)
        if hit is not None:
            metrics.cache_event("hit")
            return RecognizeResponse(
                request_id=request_id,
                image_size=hit.image_size,
                method_results=hit.method_results,
                debug_image=None,
                from_cache=True,
                merged=hit.merged,
            )

    rgb = to_rgb(bgr)
    cropped, offset = crop_roi(rgb, req.roi)

    conf = (
        req.conf_threshold
        if req.conf_threshold is not None
        else ctx.settings.default_conf_threshold
    )
    infer_ctx = InferContext(conf_threshold=conf, model=req.model, templates=req.templates or [])

    method_results: dict[Method, MethodResult] = {}
    merged: list[Detection] | None = None

    if req.merge == "priority":
        # priority 短路:按 methods 顺序逐个跑,遇首个非空 detections 即停;
        # method_results 仅含已跑方法;merged = 命中方法的检测(全程无命中则 [])。
        merged = []
        for method in req.methods:
            result = _run_single_method(
                ctx, req, infer_ctx, cropped, offset, full_w, full_h, method
            )
            method_results[method] = result
            if result.detections:
                merged = list(result.detections)
                break
    else:
        # none/concat/dedup:维持"跑所有 methods"循环,算完后统一合并。
        for method in req.methods:
            method_results[method] = _run_single_method(
                ctx, req, infer_ctx, cropped, offset, full_w, full_h, method
            )
        merged = merge_detections(req.merge, method_results)

    debug_image = _build_debug_image(bgr, method_results) if req.debug else None

    # 写:auto/refresh 均在算完后写入(off 时 cache_on 为 False,完全绕过)。
    if cache_on and key is not None:
        metrics.cache_event("miss")
        ctx.cache.set(key, CachedResult(method_results, [full_w, full_h], merged))

    return RecognizeResponse(
        request_id=request_id,
        image_size=[full_w, full_h],
        method_results=method_results,
        debug_image=debug_image,
        from_cache=False,
        merged=merged,
    )


def _run_single_method(
    ctx: AppContext,
    req: RecognizeRequest,
    infer_ctx: InferContext,
    cropped: np.ndarray,
    offset: tuple[int, int],
    full_w: int,
    full_h: int,
    method: Method,
) -> MethodResult:
    """跑单个方法:并发提交推理、回映射、组装 MethodResult。供普通循环与 priority 短路共用。"""
    recognizer = ctx.recognizers[method]
    model_key = req.model if method == "yolo" and req.model else method
    started = time.perf_counter()

    def _infer() -> list[RawDetection]:
        return recognizer.infer(cropped, infer_ctx)

    try:
        raws = ctx.executor.submit(
            model_key, _infer, serialize=recognizer.requires_serial_inference
        )
    except Exception:
        # 失败(超时/过载/识别器异常)同样要进指标,否则 status="error" 永不出现。
        metrics.record(method, (time.perf_counter() - started) * 1000, ok=False)
        raise
    elapsed_ms = (time.perf_counter() - started) * 1000
    metrics.record(method, elapsed_ms, ok=True)
    detections = finalize_detections(list(raws), offset=offset, full_w=full_w, full_h=full_h)

    model_version = ctx.registry.spec(req.model).version if method == "yolo" and req.model else None
    template_versions = (
        _template_versions(ctx, req.templates) if method == "template" and req.templates else None
    )
    return MethodResult(
        detections=detections,
        model_version=model_version,
        template_versions=template_versions,
        elapsed_ms=elapsed_ms,
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
