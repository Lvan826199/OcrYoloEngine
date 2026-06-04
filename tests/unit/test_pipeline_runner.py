"""管线测试:真实 TemplateRecognizer + 真实模板图 + 真实场景图,验证真实行为。"""

from __future__ import annotations

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.models.registry import ModelRegistry
from ocr_yolo_engine.pipeline_runner import run_recognition
from ocr_yolo_engine.recognizers.template import TemplateRecognizer
from ocr_yolo_engine.recognizers.yolo import load_yolo_model
from ocr_yolo_engine.schemas import ImageInput, RecognizeRequest
from ocr_yolo_engine.service.deps import AppContext
from ocr_yolo_engine.settings import Settings
from tests.conftest import (
    SCENE_H,
    SCENE_W,
    TEMPLATE_NAME,
    TEMPLATE_VERSION,
    build_template_store,
)
from tests.fixtures.factory import make_scene_with_patch, scene_b64


def _ctx(store) -> AppContext:
    settings = Settings(api_keys=[], allowed_path_roots=[])
    return AppContext(
        settings=settings,
        registry=ModelRegistry({}, loader_fn=load_yolo_model, cache_size=1),
        template_store=store,
        executor=InferenceExecutor(max_workers=2, max_queue=8, timeout_s=5),
        recognizers={"template": TemplateRecognizer(store=store)},
    )


def test_run_template_returns_finalized_detection():
    """全图无 ROI:bbox 为全图像素坐标,且带 center / 归一化坐标。"""
    store = build_template_store()
    ctx = _ctx(store)
    img = make_scene_with_patch(SCENE_W, SCENE_H, (30, 40, 12, 12))
    req = RecognizeRequest(
        image=ImageInput(base64=scene_b64(img)),
        methods=["template"],
        templates=[TEMPLATE_NAME],
    )
    resp = run_recognition(ctx, req)
    assert resp.image_size == [SCENE_W, SCENE_H]
    dets = resp.method_results["template"].detections
    assert dets
    d = dets[0]
    assert d.source == "template"
    assert d.label == TEMPLATE_NAME
    # bbox 左上角接近黑块真实位置(±3)。
    assert abs(d.bbox[0] - 30) <= 3
    assert abs(d.bbox[1] - 40) <= 3
    # center 与归一化坐标真实计算。
    assert abs(d.center[0] - 36) <= 3
    assert d.bbox_norm[0] == d.bbox[0] / SCENE_W
    assert d.center_norm[1] == d.center[1] / SCENE_H
    ctx.executor.shutdown()


def test_run_applies_roi_offset():
    """ROI 裁剪后识别器返回的是裁剪图局部坐标,finalize 须加回偏移到全图坐标。"""
    store = build_template_store()
    ctx = _ctx(store)
    # 黑块放在 (50, 30),ROI 框住 (40, 20, 40, 40) 这块区域。
    img = make_scene_with_patch(SCENE_W, SCENE_H, (50, 30, 12, 12))
    req = RecognizeRequest(
        image=ImageInput(base64=scene_b64(img)),
        methods=["template"],
        templates=[TEMPLATE_NAME],
        roi={"x": 40, "y": 20, "w": 40, "h": 40},
    )
    resp = run_recognition(ctx, req)
    dets = resp.method_results["template"].detections
    assert dets
    d = dets[0]
    # bbox 已加回偏移,接近全图真实坐标 (50, 30)。
    assert abs(d.bbox[0] - 50) <= 3
    assert abs(d.bbox[1] - 30) <= 3
    ctx.executor.shutdown()


def test_template_versions_in_response():
    """响应里携带真实模板版本号。"""
    store = build_template_store()
    ctx = _ctx(store)
    img = make_scene_with_patch(SCENE_W, SCENE_H, (30, 40, 12, 12))
    req = RecognizeRequest(
        image=ImageInput(base64=scene_b64(img)),
        methods=["template"],
        templates=[TEMPLATE_NAME],
    )
    resp = run_recognition(ctx, req)
    assert resp.method_results["template"].template_versions == {TEMPLATE_NAME: TEMPLATE_VERSION}
    ctx.executor.shutdown()


def test_conf_threshold_gates_matches():
    """阈值透传的真实行为:高阈值无匹配,低阈值有匹配。

    用浅灰块,使其与纯黑模板的相似度处于中间区间,从而被阈值区分。
    """
    store = build_template_store()
    ctx = _ctx(store)
    # 深灰块(非纯黑):与纯黑模板有中等差异,落在阈值可区分区间。
    img = make_scene_with_patch(SCENE_W, SCENE_H, (30, 40, 12, 12), patch_color=(70, 70, 70))

    high = RecognizeRequest(
        image=ImageInput(base64=scene_b64(img)),
        methods=["template"],
        templates=[TEMPLATE_NAME],
        conf_threshold=0.99,
    )
    low = RecognizeRequest(
        image=ImageInput(base64=scene_b64(img)),
        methods=["template"],
        templates=[TEMPLATE_NAME],
        conf_threshold=0.1,
    )
    # 注:spec.params 里的 threshold 优先于 ctx.conf_threshold;此用例验证识别器
    # 真实阈值门控行为,故临时清空模板自带 threshold,让请求 conf 生效。
    store.spec(TEMPLATE_NAME).params.pop("threshold", None)

    resp_high = run_recognition(ctx, high)
    resp_low = run_recognition(ctx, low)
    assert resp_high.method_results["template"].detections == []
    assert resp_low.method_results["template"].detections
    ctx.executor.shutdown()
