from types import SimpleNamespace

import numpy as np
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.preprocessing.pipeline import (
    crop_roi,
    enforce_limits,
    finalize_detections,
    to_rgb,
)
from ocr_yolo_engine.schemas import ROI


def test_to_rgb_swaps_channels():
    bgr = np.zeros((1, 1, 3), dtype=np.uint8)
    bgr[0, 0] = [10, 20, 30]  # B,G,R
    rgb = to_rgb(bgr)
    assert list(rgb[0, 0]) == [30, 20, 10]


def test_enforce_limits_bytes():
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    with pytest.raises(EngineError) as ei:
        enforce_limits(b"x" * 100, img, max_bytes=10, max_pixels=10_000)
    assert ei.value.code is ErrorCode.IMAGE_TOO_LARGE


def test_enforce_limits_pixels():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    with pytest.raises(EngineError) as ei:
        enforce_limits(b"x", img, max_bytes=10_000, max_pixels=100)
    assert ei.value.code is ErrorCode.IMAGE_TOO_LARGE


def test_enforce_limits_ok():
    img = np.zeros((5, 5, 3), dtype=np.uint8)
    enforce_limits(b"x" * 5, img, max_bytes=10, max_pixels=100)


def test_crop_roi_returns_cropped_and_offset():
    img = np.arange(100 * 100 * 3, dtype=np.uint8).reshape(100, 100, 3)
    roi = ROI(x=10, y=20, w=30, h=40)
    cropped, offset = crop_roi(img, roi)
    assert cropped.shape == (40, 30, 3)
    assert offset == (10, 20)


def test_crop_roi_out_of_bounds_raises():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    with pytest.raises(EngineError) as ei:
        crop_roi(img, ROI(x=40, y=40, w=20, h=20))
    assert ei.value.code is ErrorCode.INVALID_IMAGE


def test_crop_roi_none_returns_full_and_zero_offset():
    img = np.zeros((50, 60, 3), dtype=np.uint8)
    cropped, offset = crop_roi(img, None)
    assert cropped.shape == (50, 60, 3)
    assert offset == (0, 0)


def test_finalize_applies_offset_and_normalizes():
    raw = SimpleNamespace(
        source="yolo", label="cat", text=None, confidence=0.8, bbox=[10.0, 20.0, 30.0, 40.0]
    )
    dets = finalize_detections([raw], offset=(100, 200), full_w=400, full_h=400)
    d = dets[0]
    assert d.bbox == [110.0, 220.0, 130.0, 240.0]
    assert d.center == [120.0, 230.0]
    assert d.bbox_norm == [110 / 400, 220 / 400, 130 / 400, 240 / 400]
    assert d.center_norm == [120 / 400, 230 / 400]
    assert d.source == "yolo"
    assert d.label == "cat"
