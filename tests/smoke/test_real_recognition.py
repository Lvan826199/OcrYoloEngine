"""真实端到端冒烟测试:真实模型(PaddleOCR / YOLO)+ 真实模板 HTTP 链路。

运行:uv run pytest -m smoke
重依赖缺失时由 importorskip 优雅跳过;模型下载需联网,失败时 skip 并注明原因。
"""

from __future__ import annotations

import numpy as np
import pytest

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection

pytestmark = pytest.mark.smoke


def test_ocr_real_inference():
    """真实 PaddleOCR:在白底图上写 "HELLO",断言识别到非空文字(内容带容差)。"""
    pytest.importorskip("paddleocr")
    import cv2

    from ocr_yolo_engine.recognizers.ocr import OcrRecognizer

    img = np.full((120, 400, 3), 255, dtype=np.uint8)
    cv2.putText(img, "HELLO", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 4)

    rec = OcrRecognizer()  # engine=None → 懒加载真实 PaddleOCR
    try:
        out = rec.infer(img, InferContext(conf_threshold=0.0))
    except Exception as exc:  # noqa: BLE001 - 模型下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 PaddleOCR 模型:{exc}")

    assert isinstance(out, list)
    assert all(isinstance(d, RawDetection) for d in out)
    assert any((d.text or "").strip() for d in out), "应识别到至少一段非空文字"


def test_yolo_real_inference():
    """真实 YOLO:加载 yolov8n.pt,对真实图推理,断言返回规整 RawDetection 列表。"""
    pytest.importorskip("ultralytics")

    from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
    from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model

    registry = ModelRegistry(
        {"yolov8n": ModelSpec(name="yolov8n", path="yolov8n.pt", version="v8n", classes={})},
        loader_fn=load_yolo_model,
        cache_size=1,
    )
    rec = YoloRecognizer(registry=registry)
    img = np.zeros((640, 640, 3), dtype=np.uint8)

    try:
        out = rec.infer(img, InferContext(conf_threshold=0.25, model="yolov8n"))
    except Exception as exc:  # noqa: BLE001 - 权重下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 yolov8n 权重:{exc}")

    assert isinstance(out, list)
    for d in out:
        assert isinstance(d, RawDetection)
        assert len(d.bbox) == 4
        assert all(isinstance(v, float) for v in d.bbox)


def test_reload_real_model_http():
    """真实 TestClient + 真实可加载 registry:POST reload 真实加载 yolov8n 权重。"""
    pytest.importorskip("ultralytics")

    from fastapi.testclient import TestClient

    from ocr_yolo_engine.concurrency.executor import InferenceExecutor
    from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
    from ocr_yolo_engine.recognizers.ocr import OcrRecognizer
    from ocr_yolo_engine.recognizers.template import TemplateRecognizer
    from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model
    from ocr_yolo_engine.service.app import create_app
    from ocr_yolo_engine.service.deps import AppContext
    from ocr_yolo_engine.settings import Settings
    from tests.conftest import build_template_store

    settings = Settings(api_keys=[], allowed_path_roots=[])
    # 真实可加载 registry:reload 会触发 load_yolo_model 真实下载/加载权重。
    registry = ModelRegistry(
        {"yolov8n": ModelSpec(name="yolov8n", path="yolov8n.pt", version="v8n", classes={})},
        loader_fn=load_yolo_model,
        cache_size=1,
    )
    store = build_template_store()
    ctx = AppContext(
        settings=settings,
        registry=registry,
        template_store=store,
        executor=InferenceExecutor(max_workers=2, max_queue=8, timeout_s=30),
        recognizers={
            "ocr": OcrRecognizer(settings=settings),
            "yolo": YoloRecognizer(registry=registry),
            "template": TemplateRecognizer(store=store),
        },
    )
    client = TestClient(create_app(ctx=ctx))

    try:
        r = client.post("/v1/models/yolov8n/reload")
    except Exception as exc:  # noqa: BLE001 - 权重下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 yolov8n 权重:{exc}")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "reloaded"
    assert body["version"] == "v8n"
    # 真实加载成功后,缓存里应含 yolov8n。
    assert "yolov8n" in registry.loaded_names()


def test_recognize_multi_method_merge_concat_real():
    """真实多方法 /v1/recognize:场景含文字 + 黑块,template+ocr,merge=concat。

    断言 merged 同时含模板与 OCR 的检测,且按置信度降序有序。
    """
    pytest.importorskip("paddleocr")

    import cv2

    from tests.conftest import TEMPLATE_NAME, make_client
    from tests.fixtures.factory import make_scene_with_patch, scene_b64

    # 真实场景:白底 + 文字 "HELLO"(供 OCR)+ 12x12 黑块(供模板匹配)。
    img = make_scene_with_patch(400, 160, (300, 120, 12, 12))
    cv2.putText(img, "HELLO", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 4)

    client = make_client()
    try:
        r = client.post(
            "/v1/recognize",
            json={
                "image": {"base64": scene_b64(img)},
                "methods": ["template", "ocr"],
                "templates": [TEMPLATE_NAME],
                "merge": "concat",
            },
        )
    except Exception as exc:  # noqa: BLE001 - 模型下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 PaddleOCR 模型:{exc}")

    assert r.status_code == 200, r.text
    body = r.json()
    tmpl = body["method_results"]["template"]["detections"]
    ocr = body["method_results"]["ocr"]["detections"]
    assert tmpl, "应检出模板黑块"
    assert ocr, "应识别到文字"
    merged = body["merged"]
    assert merged is not None
    # 合并后应同时包含模板与 OCR 来源的检测。
    sources = {d["source"] for d in merged}
    assert {"template", "ocr"} <= sources
    assert len(merged) == len(tmpl) + len(ocr)
    # 按置信度降序有序。
    confs = [d["confidence"] for d in merged]
    assert confs == sorted(confs, reverse=True)


def test_template_real_http_e2e():
    """真实 TestClient + 真实模板:无重依赖,完整 HTTP 跑通模板匹配。"""
    from tests.conftest import PATCH_CENTER, SCENE_H, SCENE_W, TEMPLATE_NAME, make_client
    from tests.fixtures.factory import make_scene_with_patch, scene_b64

    client = make_client()
    b64 = scene_b64(make_scene_with_patch(SCENE_W, SCENE_H, (30, 40, 12, 12)))
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    assert r.status_code == 200
    dets = r.json()["method_results"]["template"]["detections"]
    assert dets
    cx, cy = dets[0]["center"]
    assert abs(cx - PATCH_CENTER[0]) <= 3
    assert abs(cy - PATCH_CENTER[1]) <= 3
