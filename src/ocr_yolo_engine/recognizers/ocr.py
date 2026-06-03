"""PaddleOCR 识别器:仅文字识别;重依赖懒加载。"""

from __future__ import annotations

from typing import Any

import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection
from ocr_yolo_engine.settings import Settings, get_settings


class OcrRecognizer:
    def __init__(self, engine: Any | None = None, settings: Settings | None = None) -> None:
        self._engine = engine
        self._settings = settings or get_settings()

    def _ensure_engine(self) -> Any:
        if self._engine is None:
            from paddleocr import PaddleOCR  # 懒加载,避免顶层导入 paddle

            use_gpu = self._settings.device == "cuda"
            self._engine = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=use_gpu)
        return self._engine

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        engine = self._ensure_engine()
        pages = engine.ocr(image, cls=True)
        out: list[RawDetection] = []
        for page in pages:
            if not page:
                continue
            for box, (text, conf) in page:
                if conf < ctx.conf_threshold:
                    continue
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                out.append(
                    RawDetection(
                        source="ocr",
                        label=None,
                        text=text,
                        confidence=float(conf),
                        bbox=[float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))],
                    )
                )
        return out
