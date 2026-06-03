import cv2
import numpy as np
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore


def _write_png(path, w=6, h=6):
    cv2.imwrite(str(path), np.zeros((h, w, 3), dtype=np.uint8))


def test_get_loads_and_caches(tmp_path):
    p = tmp_path / "icon.png"
    _write_png(p)
    specs = {
        "icon": TemplateSpec(name="icon", path=str(p), version="v1", params={"threshold": 0.8})
    }
    store = TemplateStore(specs)
    img1 = store.get_image("icon")
    img2 = store.get_image("icon")
    assert img1 is img2
    assert img1.shape == (6, 6, 3)


def test_get_unknown_raises(tmp_path):
    store = TemplateStore({})
    with pytest.raises(EngineError) as ei:
        store.get_image("nope")
    assert ei.value.code is ErrorCode.TEMPLATE_NOT_FOUND


def test_spec_and_versions(tmp_path):
    p = tmp_path / "icon.png"
    _write_png(p)
    specs = {"icon": TemplateSpec(name="icon", path=str(p), version="v3", params={})}
    store = TemplateStore(specs)
    assert store.spec("icon").version == "v3"
    assert store.versions(["icon"]) == {"icon": "v3"}
    assert store.list_templates() == ["icon"]
