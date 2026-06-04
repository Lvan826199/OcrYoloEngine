"""draw_detections 单元测试:真实造图 + 真实 Detection,断言真实画框行为。"""

from __future__ import annotations

import numpy as np

from ocr_yolo_engine.preprocessing.annotate import draw_detections
from ocr_yolo_engine.schemas import Detection


def _det(bbox: list[float], *, label: str | None, text: str | None, conf: float) -> Detection:
    x1, y1, x2, y2 = bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return Detection(
        source="template",
        label=label,
        text=text,
        confidence=conf,
        bbox=bbox,
        center=[cx, cy],
        bbox_norm=[0.0, 0.0, 0.0, 0.0],
        center_norm=[0.0, 0.0],
    )


def test_draw_detections_keeps_size_and_changes_pixels():
    """画框后图尺寸不变,且像素与原图不全等(确实画了东西),原图不被修改。"""
    img = np.full((80, 100, 3), 255, dtype=np.uint8)
    original = img.copy()
    dets = [
        _det([30.0, 40.0, 42.0, 52.0], label="patch", text=None, conf=0.97),
        _det([10.0, 10.0, 25.0, 25.0], label=None, text="abc", conf=0.55),
    ]

    out = draw_detections(img, dets)

    # 尺寸与输入一致。
    assert out.shape == img.shape
    # 确实画了东西:输出与原图不全等。
    assert not np.array_equal(out, img)
    # 原图未被修改(在副本上作业)。
    assert np.array_equal(img, original)


def test_draw_detections_empty_is_copy():
    """无检测时返回与原图等价的副本,但非同一对象。"""
    img = np.full((40, 40, 3), 128, dtype=np.uint8)
    out = draw_detections(img, [])
    assert np.array_equal(out, img)
    assert out is not img


def test_draw_detections_uses_text_when_no_label():
    """label 缺失时用 text 作为标注前缀,不报错且改变像素。"""
    img = np.full((60, 60, 3), 255, dtype=np.uint8)
    dets = [_det([5.0, 5.0, 30.0, 30.0], label=None, text="hello", conf=0.8)]
    out = draw_detections(img, dets)
    assert not np.array_equal(out, img)
