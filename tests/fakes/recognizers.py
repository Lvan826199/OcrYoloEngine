"""测试用假识别器:不加载任何真实模型。"""

from __future__ import annotations

import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection


class FakeRecognizer:
    """返回预置 RawDetection,记录调用。"""

    def __init__(self, canned: list[RawDetection] | None = None) -> None:
        self.canned = canned or []
        self.calls: list[InferContext] = []

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        self.calls.append(ctx)
        return list(self.canned)
