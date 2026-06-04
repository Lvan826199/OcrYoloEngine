"""OpenCV 模板匹配识别器:多尺度 + 阈值 + NMS 去重。"""

from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection
from ocr_yolo_engine.templates.store import TemplateSpec

Box = tuple[float, float, float, float, float]  # x1,y1,x2,y2,score


class _StoreLike(Protocol):
    def get_image(self, name: str) -> np.ndarray: ...
    def spec(self, name: str) -> TemplateSpec: ...


def _iou(a: Box, b: Box) -> float:
    ax1, ay1, ax2, ay2, _ = a
    bx1, by1, bx2, by2, _ = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


def non_max_suppression(boxes: list[Box], iou_threshold: float) -> list[Box]:
    ordered = sorted(boxes, key=lambda b: b[4], reverse=True)
    kept: list[Box] = []
    for box in ordered:
        if all(_iou(box, k) < iou_threshold for k in kept):
            kept.append(box)
    return kept


class TemplateRecognizer:
    def __init__(
        self,
        store: _StoreLike,
        scales: tuple[float, ...] = (0.8, 0.9, 1.0, 1.1, 1.2),
        iou_threshold: float = 0.4,
    ) -> None:
        self._store = store
        self._scales = scales
        self._iou = iou_threshold

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        scene = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        results: list[RawDetection] = []
        for name in ctx.templates:
            spec = self._store.spec(name)
            threshold = float(spec.params.get("threshold", ctx.conf_threshold))
            tmpl = cv2.cvtColor(self._store.get_image(name), cv2.COLOR_BGR2GRAY)
            boxes: list[Box] = []
            for scale in self._scales:
                th, tw = int(tmpl.shape[0] * scale), int(tmpl.shape[1] * scale)
                if th < 4 or tw < 4 or th > scene.shape[0] or tw > scene.shape[1]:
                    continue
                resized = cv2.resize(tmpl, (tw, th))
                # 用平方差(TM_SQDIFF)并按最大可能差值归一为置信度:
                # 1.0 表示逐像素完全一致,0.0 表示最大差异。
                # 相比 TM_CCOEFF_NORMED,对常量(纯色)模板不会退化。
                diff = cv2.matchTemplate(scene, resized, cv2.TM_SQDIFF)
                max_diff = (255.0**2) * resized.size
                res = 1.0 - diff / max_diff
                ys, xs = np.where(res >= threshold)
                for x, y in zip(xs.tolist(), ys.tolist(), strict=True):
                    score = float(res[y, x])
                    boxes.append((float(x), float(y), float(x + tw), float(y + th), score))
            for x1, y1, x2, y2, score in non_max_suppression(boxes, self._iou):
                results.append(
                    RawDetection(
                        source="template",
                        label=name,
                        text=None,
                        confidence=score,
                        bbox=[x1, y1, x2, y2],
                    )
                )
        return results
