"""ultralytics YOLO 识别器:从注册表取模型,输出类别+框+置信度;重依赖懒加载。"""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.models.registry import ModelSpec
from ocr_yolo_engine.recognizers.base import InferContext, RawDetection, Recognizer


class _RegistryLike(Protocol):
    def get(self, name: str) -> Any: ...
    def spec(self, name: str) -> ModelSpec: ...


class YoloRecognizer(Recognizer):
    def __init__(self, registry: _RegistryLike) -> None:
        self._registry = registry

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        if not ctx.model:
            raise EngineError(ErrorCode.MODEL_NOT_FOUND, "yolo 推理缺少 model 参数")
        model = self._registry.get(ctx.model)
        classes = self._registry.spec(ctx.model).classes
        results = model.predict(image, conf=ctx.conf_threshold, verbose=False)
        out: list[RawDetection] = []
        for res in results:
            boxes = res.boxes
            xyxy = np.asarray(boxes.xyxy)
            conf = np.asarray(boxes.conf)
            cls = np.asarray(boxes.cls)
            for i in range(len(xyxy)):
                cls_idx = int(cls[i])
                label = classes.get(cls_idx, str(cls_idx))
                x1, y1, x2, y2 = (float(v) for v in xyxy[i])
                out.append(
                    RawDetection(
                        source="yolo",
                        label=label,
                        text=None,
                        confidence=float(conf[i]),
                        bbox=[x1, y1, x2, y2],
                    )
                )
        return out


def load_yolo_model(spec: ModelSpec) -> Any:
    """生产用 loader_fn:懒加载 ultralytics 模型。注入到 ModelRegistry。"""
    # 懒加载,避免顶层导入 torch;ultralytics 未显式 re-export YOLO。
    # 装了 ultralytics 的环境会报 attr-defined,未装的环境则该 ignore 多余,
    # 故同时容忍 unused-ignore,使两类 mypy 环境均通过。
    from ultralytics import YOLO  # type: ignore[attr-defined, unused-ignore]

    return YOLO(spec.path)
