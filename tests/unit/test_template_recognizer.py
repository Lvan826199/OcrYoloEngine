"""模板识别器单测:NMS 用真实数据;匹配用真实 TemplateStore + 真实模板 PNG。"""

from __future__ import annotations

import os
import tempfile

import cv2
import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.template import TemplateRecognizer, non_max_suppression
from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore


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


def _store_with_black_template(name: str = "blk") -> TemplateStore:
    """在临时目录真实写出 10x10 黑块模板 PNG 并注册。"""
    tmp_dir = tempfile.mkdtemp(prefix="ocr_yolo_tmpl_test_")
    path = os.path.join(tmp_dir, f"{name}.png")
    cv2.imwrite(path, np.zeros((10, 10, 3), dtype=np.uint8))
    return TemplateStore(
        {name: TemplateSpec(name=name, path=path, version="v1", params={"threshold": 0.8})}
    )


def test_recognizer_finds_template_in_scene():
    scene = np.full((100, 100, 3), 255, dtype=np.uint8)
    scene[40:50, 30:40] = 0
    store = _store_with_black_template("blk")

    rec = TemplateRecognizer(store=store, scales=(1.0,))
    out = rec.infer(scene, InferContext(conf_threshold=0.8, templates=["blk"]))
    assert len(out) == 1
    d = out[0]
    assert d.source == "template"
    assert d.label == "blk"
    assert abs(d.bbox[0] - 30) <= 2 and abs(d.bbox[1] - 40) <= 2
    assert d.confidence >= 0.8
