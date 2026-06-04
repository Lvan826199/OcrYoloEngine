"""golden 回归:加载已提交的真实样例图与模板,跑真实模板匹配,断言不回归。

样例图与模板均为确定性内容(已入库的 PNG),期望结果记录在
tests/fixtures/golden_scene.expected.json。用真实 TemplateRecognizer +
真实 TemplateStore 端到端验证,无任何 mock/fake。
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2

from ocr_yolo_engine.preprocessing.pipeline import finalize_detections, to_rgb
from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.template import TemplateRecognizer
from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_expected() -> dict:
    with (_FIXTURES / "golden_scene.expected.json").open(encoding="utf-8") as f:
        return json.load(f)


def test_golden_template_match_no_regression():
    """对已入库样例图跑真实模板匹配,bbox/center 在容差内、置信度达下限。"""
    expected = _load_expected()
    tmpl_name = expected["template"]["name"]
    tol = expected["tolerance_px"]
    min_conf = expected["min_confidence"]

    scene_bgr = cv2.imread(str(_FIXTURES / "golden_scene.png"), cv2.IMREAD_COLOR)
    assert scene_bgr is not None, "样例场景图应可读取"
    full_h, full_w = scene_bgr.shape[:2]
    assert [full_w, full_h] == expected["scene_size"]

    store = TemplateStore(
        {
            tmpl_name: TemplateSpec(
                name=tmpl_name,
                path=str(_FIXTURES / "golden_patch.png"),
                version="golden-v1",
                params={"threshold": min_conf},
            )
        }
    )
    # 纯黑块为常量区域,多尺度匹配会在块内任意子区得到同样满分,产生位置歧义;
    # golden 用单一原始尺度(1.0)做确定性、可复现的规范匹配,仍为真实匹配无 mock。
    recognizer = TemplateRecognizer(store=store, scales=(1.0,))

    # 与生产管线一致:识别器吃 RGB 图,坐标回映射交给 finalize_detections。
    rgb = to_rgb(scene_bgr)
    raws = recognizer.infer(rgb, InferContext(conf_threshold=min_conf, templates=[tmpl_name]))
    dets = finalize_detections(list(raws), offset=(0, 0), full_w=full_w, full_h=full_h)

    assert dets, "样例图应稳定检出黑块"
    best = max(dets, key=lambda d: d.confidence)

    ex_bbox = expected["bbox"]
    for got, want in zip(best.bbox, ex_bbox, strict=True):
        assert abs(got - want) <= tol, f"bbox {best.bbox} 偏离期望 {ex_bbox} 超过 {tol}px"

    ex_center = expected["center"]
    assert abs(best.center[0] - ex_center[0]) <= tol
    assert abs(best.center[1] - ex_center[1]) <= tol

    assert best.confidence >= min_conf
