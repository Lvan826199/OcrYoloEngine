"""预处理:通道统一、输入上限校验、ROI 裁剪与坐标回映射。"""

from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.schemas import ROI, Detection, Method


class _RawLike(Protocol):
    source: Method
    label: str | None
    text: str | None
    confidence: float
    bbox: list[float]


def to_rgb(bgr: np.ndarray) -> np.ndarray:
    """BGR → RGB,内部统一以 RGB 流转。"""
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def enforce_limits(raw_bytes: bytes, image: np.ndarray, *, max_bytes: int, max_pixels: int) -> None:
    """校验字节数与分辨率不超过上限;超过时抛 IMAGE_TOO_LARGE。"""
    if len(raw_bytes) > max_bytes:
        raise EngineError(
            ErrorCode.IMAGE_TOO_LARGE,
            "图片字节数超过上限",
            details={"bytes": len(raw_bytes), "max_bytes": max_bytes},
        )
    h, w = image.shape[:2]
    if w * h > max_pixels:
        raise EngineError(
            ErrorCode.IMAGE_TOO_LARGE,
            "图片分辨率超过上限",
            details={"pixels": w * h, "max_pixels": max_pixels},
        )


def crop_roi(image: np.ndarray, roi: ROI | None) -> tuple[np.ndarray, tuple[int, int]]:
    """按 ROI 裁剪;返回(裁剪图, (offset_x, offset_y))。roi 为 None 返回全图。"""
    if roi is None:
        return image, (0, 0)
    h, w = image.shape[:2]
    if roi.x + roi.w > w or roi.y + roi.h > h:
        raise EngineError(
            ErrorCode.INVALID_IMAGE,
            "ROI 超出图片边界",
            details={"roi": roi.model_dump(), "image": [w, h]},
        )
    cropped = image[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]
    return cropped, (roi.x, roi.y)


def finalize_detections(
    raws: list[_RawLike], *, offset: tuple[int, int], full_w: int, full_h: int
) -> list[Detection]:
    """把识别器原始结果加偏移回映射到全图,并计算归一化坐标。"""
    ox, oy = offset
    out: list[Detection] = []
    for r in raws:
        x1, y1, x2, y2 = r.bbox
        x1 += ox
        y1 += oy
        x2 += ox
        y2 += oy
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        out.append(
            Detection(
                source=r.source,
                label=r.label,
                text=r.text,
                confidence=r.confidence,
                bbox=[x1, y1, x2, y2],
                center=[cx, cy],
                bbox_norm=[x1 / full_w, y1 / full_h, x2 / full_w, y2 / full_h],
                center_norm=[cx / full_w, cy / full_h],
            )
        )
    return out
