"""结果缓存单元测试:真实 LruResultCache(get/set/LRU 淘汰/clear/ttl 过期)
与 compute_cache_key 的稳定性/区分性。全部真实数据,无 mock。
"""

from __future__ import annotations

import base64
import time

import cv2
import numpy as np

from ocr_yolo_engine.cache import (
    CachedResult,
    LruResultCache,
    NullResultCache,
    compute_cache_key,
)
from ocr_yolo_engine.schemas import ImageInput, MethodResult, RecognizeRequest


def _make_result(n: int = 1) -> CachedResult:
    return CachedResult(
        method_results={"template": MethodResult(elapsed_ms=float(n))},
        image_size=[n, n],
    )


def test_null_cache_is_noop():
    c = NullResultCache()
    c.set("k", _make_result())
    assert c.get("k") is None
    c.clear()  # 不应抛错


def test_lru_get_set_and_miss():
    c = LruResultCache(maxsize=4)
    assert c.get("缺失") is None
    v = _make_result(3)
    c.set("a", v)
    got = c.get("a")
    assert got is not None
    assert got.image_size == [3, 3]


def test_lru_eviction_by_maxsize():
    c = LruResultCache(maxsize=2)
    c.set("a", _make_result(1))
    c.set("b", _make_result(2))
    # 访问 a 使其变为最近使用,接着插 c 应淘汰最久未用的 b。
    assert c.get("a") is not None
    c.set("c", _make_result(3))
    assert c.get("a") is not None
    assert c.get("c") is not None
    assert c.get("b") is None


def test_lru_clear():
    c = LruResultCache(maxsize=2)
    c.set("a", _make_result())
    c.set("b", _make_result())
    c.clear()
    assert c.get("a") is None
    assert c.get("b") is None


def test_lru_ttl_expiry():
    # 极小 ttl + 真实 sleep:存入后睡过期窗口,命中视为 miss。
    c = LruResultCache(maxsize=4, ttl_s=1)
    c.set("a", _make_result())
    assert c.get("a") is not None  # 立即取仍在
    time.sleep(1.05)
    assert c.get("a") is None  # 已过期


def _decode(b64: str) -> np.ndarray:
    raw = base64.b64decode(b64)
    return cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)


def _b64_of(img: np.ndarray) -> str:
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return base64.b64encode(buf.tobytes()).decode()


def test_cache_key_stable_for_same_image_and_params():
    img = np.full((20, 20, 3), 128, dtype=np.uint8)
    b64 = _b64_of(img)
    bgr = _decode(b64)
    req = RecognizeRequest(image=ImageInput(base64=b64), methods=["template"], templates=["patch"])
    k1 = compute_cache_key(bgr, req)
    k2 = compute_cache_key(bgr, req)
    assert k1 == k2


def test_cache_key_differs_for_different_params():
    img = np.full((20, 20, 3), 128, dtype=np.uint8)
    b64 = _b64_of(img)
    bgr = _decode(b64)
    req_a = RecognizeRequest(
        image=ImageInput(base64=b64), methods=["template"], templates=["patch"]
    )
    req_b = RecognizeRequest(
        image=ImageInput(base64=b64), methods=["template"], templates=["other"]
    )
    assert compute_cache_key(bgr, req_a) != compute_cache_key(bgr, req_b)


def test_cache_key_differs_for_different_image():
    b64_a = _b64_of(np.full((20, 20, 3), 100, dtype=np.uint8))
    b64_b = _b64_of(np.full((20, 20, 3), 200, dtype=np.uint8))
    req_a = RecognizeRequest(
        image=ImageInput(base64=b64_a), methods=["template"], templates=["patch"]
    )
    req_b = RecognizeRequest(
        image=ImageInput(base64=b64_b), methods=["template"], templates=["patch"]
    )
    assert compute_cache_key(_decode(b64_a), req_a) != compute_cache_key(_decode(b64_b), req_b)


def test_cache_key_ignores_cache_mode():
    # cache 模式不应影响键(它决定读写策略,不决定结果)。
    img = np.full((20, 20, 3), 128, dtype=np.uint8)
    b64 = _b64_of(img)
    bgr = _decode(b64)
    req_auto = RecognizeRequest(
        image=ImageInput(base64=b64), methods=["template"], templates=["patch"], cache="auto"
    )
    req_refresh = RecognizeRequest(
        image=ImageInput(base64=b64), methods=["template"], templates=["patch"], cache="refresh"
    )
    assert compute_cache_key(bgr, req_auto) == compute_cache_key(bgr, req_refresh)
