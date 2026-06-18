import pytest
from pydantic import ValidationError

from ocr_yolo_engine.settings import Settings


def test_defaults_match_spec():
    s = Settings()
    assert s.device == "auto"
    assert s.default_conf_threshold == 0.25
    assert s.model_cache_size == 3
    assert s.max_workers == 4
    assert s.max_queue == 32
    assert s.request_timeout_s == 30
    assert s.max_image_bytes == 10 * 1024 * 1024
    assert s.max_image_pixels == 4096 * 4096
    assert s.allowed_path_roots == []
    assert s.api_keys == []


def test_env_override(monkeypatch):
    monkeypatch.setenv("OYE_DEVICE", "cpu")
    monkeypatch.setenv("OYE_MAX_WORKERS", "8")
    monkeypatch.setenv("OYE_API_KEYS", '["k1","k2"]')
    s = Settings()
    assert s.device == "cpu"
    assert s.max_workers == 8
    assert s.api_keys == ["k1", "k2"]


def test_auth_enabled_flag():
    assert Settings(api_keys=[]).auth_enabled is False
    assert Settings(api_keys=["k1"]).auth_enabled is True


@pytest.mark.parametrize(
    "kwargs",
    [
        {"default_conf_threshold": 1.5},
        {"model_cache_size": 0},
        {"result_cache_size": -1},
        {"result_cache_ttl_s": -1},
        {"max_workers": 0},
        {"max_queue": -1},
        {"request_timeout_s": 0},
        {"max_image_bytes": 0},
        {"max_image_pixels": 0},
    ],
)
def test_invalid_runtime_limits_rejected(kwargs):
    with pytest.raises(ValidationError):
        Settings(**kwargs)
