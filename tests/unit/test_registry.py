import threading
import time

import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec


def _specs():
    return {
        "a": ModelSpec(name="a", path="a.pt", version="v1", classes={0: "cat"}),
        "b": ModelSpec(name="b", path="b.pt", version="v1", classes={0: "dog"}),
        "c": ModelSpec(name="c", path="c.pt", version="v1", classes={}),
    }


def test_get_lazy_loads_and_caches():
    calls = []
    reg = ModelRegistry(
        _specs(), loader_fn=lambda s: calls.append(s.name) or f"obj-{s.name}", cache_size=3
    )
    assert reg.get("a") == "obj-a"
    assert reg.get("a") == "obj-a"
    assert calls == ["a"]


def test_get_unknown_raises():
    reg = ModelRegistry(_specs(), loader_fn=lambda s: object(), cache_size=3)
    with pytest.raises(EngineError) as ei:
        reg.get("zzz")
    assert ei.value.code is ErrorCode.MODEL_NOT_FOUND


def test_lru_eviction():
    loaded = []
    reg = ModelRegistry(_specs(), loader_fn=lambda s: loaded.append(s.name) or s.name, cache_size=2)
    reg.get("a")
    reg.get("b")
    reg.get("a")
    reg.get("c")
    assert "b" not in reg.loaded_names()
    assert set(reg.loaded_names()) == {"a", "c"}


def test_unload_and_reload():
    loaded = []
    reg = ModelRegistry(_specs(), loader_fn=lambda s: loaded.append(s.name) or s.name, cache_size=3)
    reg.get("a")
    reg.unload("a")
    assert "a" not in reg.loaded_names()
    reg.get("a")
    assert loaded == ["a", "a"]


def test_slow_load_does_not_block_cached_get():
    """加载模型(可能数秒)不得持全局锁:并发取已缓存模型必须立即返回。"""

    def loader(s):
        if s.name == "a":
            time.sleep(0.3)  # 模拟慢加载
        return f"obj-{s.name}"

    reg = ModelRegistry(_specs(), loader_fn=loader, cache_size=3)
    reg.get("b")  # 预热 b(瞬时)

    slow_started = threading.Event()

    def load_slow():
        slow_started.set()
        reg.get("a")

    t = threading.Thread(target=load_slow)
    t.start()
    slow_started.wait()
    time.sleep(0.05)  # 确保慢加载已进入 loader
    begin = time.perf_counter()
    assert reg.get("b") == "obj-b"
    elapsed = time.perf_counter() - begin
    t.join()
    assert elapsed < 0.15, f"取缓存模型被慢加载阻塞了 {elapsed:.3f}s"


def test_concurrent_get_same_model_loads_once():
    """并发取同一未加载模型:loader 只执行一次(per-name 锁 + 双重检查)。"""
    calls = []
    lock = threading.Lock()

    def loader(s):
        with lock:
            calls.append(s.name)
        time.sleep(0.1)
        return f"obj-{s.name}"

    reg = ModelRegistry(_specs(), loader_fn=loader, cache_size=3)
    results = []
    threads = [threading.Thread(target=lambda: results.append(reg.get("a"))) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == ["obj-a"] * 4
    assert calls == ["a"]


def test_spec_version_lookup():
    reg = ModelRegistry(_specs(), loader_fn=lambda s: s.name, cache_size=3)
    assert reg.spec("a").version == "v1"
    assert reg.list_models() == ["a", "b", "c"]
