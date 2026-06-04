import base64

import cv2
import numpy as np

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.models.registry import ModelRegistry
from ocr_yolo_engine.pipeline_runner import run_recognition
from ocr_yolo_engine.recognizers.base import RawDetection
from ocr_yolo_engine.schemas import ImageInput, RecognizeRequest
from ocr_yolo_engine.service.deps import AppContext
from ocr_yolo_engine.settings import Settings
from ocr_yolo_engine.templates.store import TemplateStore
from tests.fakes.recognizers import FakeRecognizer


def _b64_image(w=100, h=80):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode()


def _ctx(recognizers, settings=None):
    settings = settings or Settings(api_keys=[], allowed_path_roots=[])
    return AppContext(
        settings=settings,
        registry=ModelRegistry({}, loader_fn=lambda s: None, cache_size=1),
        template_store=TemplateStore({}),
        executor=InferenceExecutor(max_workers=2, max_queue=8, timeout_s=5),
        recognizers=recognizers,
    )


def test_run_ocr_returns_finalized_detections():
    fake = FakeRecognizer(
        [RawDetection(source="ocr", label=None, text="hi", confidence=0.9, bbox=[10, 20, 30, 40])]
    )
    ctx = _ctx({"ocr": fake})
    req = RecognizeRequest(image=ImageInput(base64=_b64_image()), methods=["ocr"])
    resp = run_recognition(ctx, req)
    assert resp.image_size == [100, 80]
    det = resp.method_results["ocr"].detections[0]
    assert det.text == "hi"
    assert det.bbox == [10, 20, 30, 40]
    assert det.center == [20, 30]
    assert det.bbox_norm[0] == 10 / 100
    ctx.executor.shutdown()


def test_run_applies_roi_offset():
    fake = FakeRecognizer(
        [RawDetection(source="template", label="x", text=None, confidence=1.0, bbox=[0, 0, 5, 5])]
    )
    ctx = _ctx({"template": fake})
    req = RecognizeRequest(
        image=ImageInput(base64=_b64_image()),
        methods=["template"],
        templates=["x"],
        roi={"x": 10, "y": 10, "w": 40, "h": 40},
    )
    resp = run_recognition(ctx, req)
    det = resp.method_results["template"].detections[0]
    assert det.bbox == [10, 10, 15, 15]
    ctx.executor.shutdown()


def test_conf_threshold_passed_to_recognizer():
    fake = FakeRecognizer([])
    ctx = _ctx({"ocr": fake})
    req = RecognizeRequest(
        image=ImageInput(base64=_b64_image()), methods=["ocr"], conf_threshold=0.7
    )
    run_recognition(ctx, req)
    assert fake.calls[0].conf_threshold == 0.7
    ctx.executor.shutdown()
