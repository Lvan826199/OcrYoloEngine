"""可插拔结果缓存:Null(关闭态)/ 线程安全有界 LRU(可选 TTL),以及缓存键计算。

设计原则:核心管线在 result_cache_size=0 时零开销——连缓存键(哈希)都不计算。
缓存键以"解码后的图像数组字节 + 规范化请求参数"算 sha256,兼容 base64/path 各来源。
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from ocr_yolo_engine.schemas import Method, MethodResult, RecognizeRequest


@dataclass
class CachedResult:
    """缓存条目:足以重建一个非 debug 的 RecognizeResponse(request_id 每次新生成)。"""

    method_results: dict[Method, MethodResult]
    image_size: list[int]


class ResultCache(Protocol):
    """结果缓存协议:实现需保证线程安全。"""

    def get(self, key: str) -> CachedResult | None: ...
    def set(self, key: str, value: CachedResult) -> None: ...
    def clear(self) -> None: ...


class NullResultCache:
    """关闭态缓存:get 恒 None、set/clear 为空操作。默认即此实现,核心零影响。"""

    def get(self, key: str) -> CachedResult | None:
        return None

    def set(self, key: str, value: CachedResult) -> None:
        return None

    def clear(self) -> None:
        return None


class LruResultCache:
    """线程安全有界 LRU 缓存,可选 TTL(基于单调时钟)。

    - maxsize:容量上限,超出按最久未用淘汰。
    - ttl_s:>0 时条目存活秒数;命中已过期条目视为 miss 并移除。
    """

    def __init__(self, maxsize: int, ttl_s: int = 0) -> None:
        if maxsize <= 0:
            raise ValueError("LruResultCache 的 maxsize 必须为正整数")
        self._maxsize = maxsize
        self._ttl_s = ttl_s
        # key -> (存入时刻(单调时钟), 值)
        self._store: OrderedDict[str, tuple[float, CachedResult]] = OrderedDict()
        self._lock = threading.Lock()

    def _expired(self, stored_at: float) -> bool:
        return self._ttl_s > 0 and (time.monotonic() - stored_at) >= self._ttl_s

    def get(self, key: str) -> CachedResult | None:
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            stored_at, value = item
            if self._expired(stored_at):
                # 过期即移除,视为 miss。
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return value

    def set(self, key: str, value: CachedResult) -> None:
        with self._lock:
            self._store[key] = (time.monotonic(), value)
            self._store.move_to_end(key)
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


def compute_cache_key(image_bgr: np.ndarray, req: RecognizeRequest) -> str:
    """以解码后的图像数组字节 + 规范化请求参数算 sha256,作为稳定缓存键。

    规范化:methods 排序、model、templates 排序、有效 conf_threshold(None 原样)、
    roi 的 model_dump、merge 字段(若 schema 含)。cache/debug 不参与键计算
    (它们决定是否读写缓存,而非结果本身)。
    """
    hasher = hashlib.sha256()
    hasher.update(image_bgr.tobytes())

    params: dict[str, object] = {
        "methods": sorted(req.methods),
        "model": req.model,
        "templates": sorted(req.templates) if req.templates else None,
        "conf_threshold": req.conf_threshold,
        "roi": req.roi.model_dump() if req.roi is not None else None,
    }
    # merge 字段若 schema 演进时新增,纳入键;当前 schema 无则跳过。
    merge = getattr(req, "merge", None)
    if merge is not None:
        params["merge"] = merge.model_dump() if hasattr(merge, "model_dump") else merge

    canonical = json.dumps(params, sort_keys=True, ensure_ascii=False, default=str)
    hasher.update(canonical.encode("utf-8"))
    return hasher.hexdigest()
