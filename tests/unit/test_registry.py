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


def test_spec_version_lookup():
    reg = ModelRegistry(_specs(), loader_fn=lambda s: s.name, cache_size=3)
    assert reg.spec("a").version == "v1"
    assert reg.list_models() == ["a", "b", "c"]
