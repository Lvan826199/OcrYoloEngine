import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.service.auth import verify_api_key
from ocr_yolo_engine.settings import Settings


def test_auth_disabled_allows_any():
    verify_api_key(None, Settings(api_keys=[]))


def test_auth_enabled_accepts_valid_key():
    verify_api_key("k1", Settings(api_keys=["k1", "k2"]))


def test_auth_enabled_rejects_missing_or_wrong():
    with pytest.raises(EngineError) as ei:
        verify_api_key(None, Settings(api_keys=["k1"]))
    assert ei.value.code is ErrorCode.UNAUTHORIZED
    assert ei.value.http_status == 401
    with pytest.raises(EngineError) as ei2:
        verify_api_key("bad", Settings(api_keys=["k1"]))
    assert ei2.value.code is ErrorCode.UNAUTHORIZED
    assert ei2.value.http_status == 401
