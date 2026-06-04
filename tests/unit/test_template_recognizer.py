import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.template import TemplateRecognizer, non_max_suppression


def test_nms_keeps_highest_and_drops_overlap():
    boxes = [
        (10, 10, 50, 50, 0.9),
        (12, 12, 52, 52, 0.7),
        (200, 200, 240, 240, 0.8),
    ]
    kept = non_max_suppression(boxes, iou_threshold=0.4)
    assert len(kept) == 2
    assert kept[0][4] == 0.9
    assert kept[1][4] == 0.8


def test_nms_empty():
    assert non_max_suppression([], iou_threshold=0.4) == []


def test_recognizer_finds_template_in_scene():
    scene = np.full((100, 100, 3), 255, dtype=np.uint8)
    scene[40:50, 30:40] = 0
    template = np.zeros((10, 10, 3), dtype=np.uint8)

    class StubStore:
        def get_image(self, name):
            return template

        def spec(self, name):
            from ocr_yolo_engine.templates.store import TemplateSpec

            return TemplateSpec(name=name, path="x", version="v1", params={"threshold": 0.8})

    rec = TemplateRecognizer(store=StubStore(), scales=(1.0,))
    out = rec.infer(scene, InferContext(conf_threshold=0.8, templates=["blk"]))
    assert len(out) == 1
    d = out[0]
    assert d.source == "template"
    assert d.label == "blk"
    assert abs(d.bbox[0] - 30) <= 2 and abs(d.bbox[1] - 40) <= 2
    assert d.confidence >= 0.8
