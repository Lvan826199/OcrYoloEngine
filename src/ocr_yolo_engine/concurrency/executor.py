"""有界工作池 + 每模型锁 + 背压:推理在线程池跑,过载 503,超时 504。"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import TypeVar

from ocr_yolo_engine.errors import EngineError, ErrorCode

T = TypeVar("T")


class InferenceExecutor:
    """有界工作池:限制并发与排队总量,按模型串行化,超时与过载分别上报 504/503。"""

    def __init__(self, max_workers: int, max_queue: int, timeout_s: float) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._slots = threading.Semaphore(max_queue + max_workers)
        self._timeout = timeout_s
        self._model_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _model_lock(self, key: str) -> threading.Lock:
        with self._locks_guard:
            if key not in self._model_locks:
                self._model_locks[key] = threading.Lock()
            return self._model_locks[key]

    def submit(self, model_key: str, fn: Callable[[], T]) -> T:
        if not self._slots.acquire(blocking=False):
            raise EngineError(
                ErrorCode.OVERLOADED, "服务繁忙,请稍后重试", details={"retry_after": 1}
            )
        try:
            lock = self._model_lock(model_key)

            def guarded() -> T:
                with lock:
                    return fn()

            future = self._pool.submit(guarded)
            try:
                return future.result(timeout=self._timeout)
            except FutureTimeout as exc:
                future.cancel()
                raise EngineError(
                    ErrorCode.TIMEOUT, "推理超时", details={"timeout_s": self._timeout}
                ) from exc
        finally:
            self._slots.release()

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
