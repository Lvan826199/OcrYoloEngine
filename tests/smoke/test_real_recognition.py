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
