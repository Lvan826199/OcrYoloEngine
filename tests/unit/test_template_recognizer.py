"""模板识别器单测:NMS 用真实数据;匹配用真实 TemplateStore + 真实模板 PNG。"""

from __future__ import annotations

import os
import tempfile
import time

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


def _store_with_black_template(name: str = "blk", params: dict | None = None) -> TemplateStore:
    """在临时目录真实写出 10x10 黑块模板 PNG 并注册。"""
    tmp_dir = tempfile.mkdtemp(prefix="ocr_yolo_tmpl_test_")
    path = os.path.join(tmp_dir, f"{name}.png")
    cv2.imwrite(path, np.zeros((10, 10, 3), dtype=np.uint8))
    if params is None:
        params = {"threshold": 0.8}
    return TemplateStore({name: TemplateSpec(name=name, path=path, version="v1", params=params)})


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


def test_fallback_threshold_has_floor():
    """模板未配 threshold 时,过低的请求阈值要被抬到下限,防止全图逐像素命中。

    真实数据:200 灰度纯色场景 vs 黑色模板,逐像素得分约 0.385——
    高于请求的 0.1、低于下限 0.5,旧实现会全图命中,新实现应一无所获。
    """
    scene = np.full((100, 100, 3), 200, dtype=np.uint8)
    store = _store_with_black_template("blk", params={})
    rec = TemplateRecognizer(store=store, scales=(1.0,))
    out = rec.infer(scene, InferContext(conf_threshold=0.1, templates=["blk"]))
    assert out == []


def test_candidate_count_is_bounded_per_scale():
    """得分普遍高于阈值时,每尺度候选数有 top-K 上限,封顶 NMS 的 O(n²) 开销。

    真实数据:100 灰度纯色场景 vs 黑色模板,逐像素得分约 0.846,
    全图 141x141 ≈ 2 万个候选;有上限后 NMS 输入有界,结果数 ≤ 上限。
    """
    scene = np.full((150, 150, 3), 100, dtype=np.uint8)
    store = _store_with_black_template("blk", params={})
    rec = TemplateRecognizer(store=store, scales=(1.0,))
    started = time.perf_counter()
    out = rec.infer(scene, InferContext(conf_threshold=0.5, templates=["blk"]))
    elapsed = time.perf_counter() - started
    assert len(out) <= 200, "NMS 后结果数不应超过每尺度候选上限"
    assert elapsed < 5, "候选受限后应远快于无界 NMS"
