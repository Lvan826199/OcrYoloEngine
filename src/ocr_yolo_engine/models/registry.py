"""模型注册表:从配置读规格,懒加载 + LRU 缓存 + 卸载/重载,线程安全。"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ocr_yolo_engine.errors import EngineError, ErrorCode


@dataclass
class ModelSpec:
    name: str
    path: str
    version: str
    classes: dict[int, str] = field(default_factory=dict)


class ModelRegistry:
    def __init__(
        self,
        specs: dict[str, ModelSpec],
        loader_fn: Callable[[ModelSpec], Any],
        cache_size: int,
    ) -> None:
        self._specs = specs
        self._loader = loader_fn
        self._cache_size = cache_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()

    def spec(self, name: str) -> ModelSpec:
        if name not in self._specs:
            raise EngineError(
                ErrorCode.MODEL_NOT_FOUND, f"模型 {name} 未注册", details={"model": name}
            )
        return self._specs[name]

    def list_models(self) -> list[str]:
        return list(self._specs.keys())

    def loaded_names(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())

    def get(self, name: str) -> Any:
        spec = self.spec(name)
        with self._lock:
            if name in self._cache:
                self._cache.move_to_end(name)
                return self._cache[name]
            obj = self._loader(spec)
            self._cache[name] = obj
            self._cache.move_to_end(name)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
            return obj

    def unload(self, name: str) -> None:
        with self._lock:
            self._cache.pop(name, None)

    def reload(self, name: str) -> Any:
        self.unload(name)
        return self.get(name)
