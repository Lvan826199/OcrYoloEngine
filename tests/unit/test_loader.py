import base64
import os

import cv2
import numpy as np
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.image.loader import decode_image_bytes, load_from_base64, load_from_path


def _png_bytes(w=4, h=3):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :, 2] = 255  # BGR 红
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_decode_valid_png_returns_bgr_ndarray():
    img = decode_image_bytes(_png_bytes())
    assert img.shape == (3, 4, 3)
    assert img.dtype == np.uint8


def test_decode_garbage_raises_invalid_image():
    with pytest.raises(EngineError) as ei:
        decode_image_bytes(b"not-an-image")
    assert ei.value.code is ErrorCode.INVALID_IMAGE


def test_load_from_base64():
    b64 = base64.b64encode(_png_bytes()).decode()
    img = load_from_base64(b64)
    assert img.shape == (3, 4, 3)


def test_load_from_base64_with_data_uri_prefix():
    b64 = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
    img = load_from_base64(b64)
    assert img.shape == (3, 4, 3)


def test_load_from_path_inside_whitelist(tmp_path):
    p = tmp_path / "a.png"
    png_data = _png_bytes()
    p.write_bytes(png_data)
    raw, img = load_from_path(str(p), allowed_roots=[str(tmp_path)])
    assert img.shape == (3, 4, 3)
    assert raw == png_data


def test_load_from_path_traversal_blocked(tmp_path):
    outside = tmp_path / "secret.png"
    outside.write_bytes(_png_bytes())
    root = tmp_path / "allowed"
    root.mkdir()
    sneaky = str(root / ".." / "secret.png")
    with pytest.raises(EngineError) as ei:
        load_from_path(sneaky, allowed_roots=[str(root)])
    assert ei.value.code is ErrorCode.PATH_NOT_ALLOWED


def test_load_from_path_empty_whitelist_blocks_all(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes())
    with pytest.raises(EngineError) as ei:
        load_from_path(str(p), allowed_roots=[])
    assert ei.value.code is ErrorCode.PATH_NOT_ALLOWED


@pytest.mark.skipif(os.name != "nt", reason="大小写不敏感路径白名单只在 Windows 上验证")
def test_load_from_path_windows_whitelist_is_case_insensitive(tmp_path):
    p = tmp_path / "a.png"
    png_data = _png_bytes()
    p.write_bytes(png_data)

    raw, img = load_from_path(str(p), allowed_roots=[str(tmp_path).upper()])

    assert raw == png_data
    assert img.shape == (3, 4, 3)
