"""模板库:从配置读规格,按需加载模板图并缓存,带版本。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode


@dataclass
class TemplateSpec:
    name: str
    path: str
    version: str
    params: dict[str, Any] = field(default_factory=dict)


class TemplateStore:
    def __init__(self, specs: dict[str, TemplateSpec]) -> None:
        self._specs = specs
        self._cache: dict[str, np.ndarray] = {}
        self._lock = threading.RLock()

    def spec(self, name: str) -> TemplateSpec:
        if name not in self._specs:
            raise EngineError(
                ErrorCode.TEMPLATE_NOT_FOUND, f"模板 {name} 未注册", details={"template": name}
            )
        return self._specs[name]

    def list_templates(self) -> list[str]:
        return list(self._specs.keys())

    def versions(self, names: list[str]) -> dict[str, str]:
        return {n: self.spec(n).version for n in names}

    def get_image(self, name: str) -> np.ndarray:
        spec = self.spec(name)
        with self._lock:
            if name in self._cache:
                return self._cache[name]
            img = cv2.imread(spec.path, cv2.IMREAD_COLOR)
            if img is None:
                raise EngineError(
                    ErrorCode.TEMPLATE_NOT_FOUND,
                    f"模板图无法读取:{spec.path}",
                    details={"template": name},
                )
            self._cache[name] = img
            return img
