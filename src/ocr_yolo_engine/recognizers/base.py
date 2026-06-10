"""识别器统一抽象与原始结果结构。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from ocr_yolo_engine.schemas import Method


@dataclass
class RawDetection:
    """识别器原始输出:bbox 基于传入识别器的那张图(可能是 ROI 裁剪图)。"""

    source: Method
    label: str | None
    text: str | None
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


@dataclass
class InferContext:
    """单次推理上下文。"""

    conf_threshold: float
    model: str | None = None
    templates: list[str] = field(default_factory=list)


class Recognizer(ABC):
    """所有识别器的统一契约:吃预处理图 + 上下文,吐 RawDetection。"""

    # 推理是否需要按 model_key 串行:底层引擎非线程安全(PaddleOCR/YOLO)时为 True;
    # 纯函数式计算(如 OpenCV 模板匹配)可置 False,由执行器跳过模型锁以提升吞吐。
    requires_serial_inference: bool = True

    @abstractmethod
    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        """坐标基于输入图,偏移与归一化由上层 finalize_detections 完成。"""
        raise NotImplementedError
