import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode


def test_engine_error_carries_code_and_status():
    err = EngineError(ErrorCode.MODEL_NOT_FOUND, "模型 abc 不存在", details={"model": "abc"})
    assert err.code is ErrorCode.MODEL_NOT_FOUND
    assert err.http_status == 404
    assert err.details == {"model": "abc"}
    assert "abc" in str(err)


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (ErrorCode.INVALID_IMAGE, 400),
        (ErrorCode.IMAGE_TOO_LARGE, 413),
        (ErrorCode.PATH_NOT_ALLOWED, 403),
        (ErrorCode.MODEL_NOT_FOUND, 404),
        (ErrorCode.TEMPLATE_NOT_FOUND, 404),
        (ErrorCode.OVERLOADED, 503),
        (ErrorCode.TIMEOUT, 504),
        (ErrorCode.INTERNAL, 500),
    ],
)
def test_status_mapping(code, status):
    assert EngineError(code, "x").http_status == status


def test_to_response_body():
    body = EngineError(ErrorCode.INVALID_IMAGE, "坏图", details={"k": 1}).to_body("req-1")
    assert body == {
        "request_id": "req-1",
        "error_code": "INVALID_IMAGE",
        "message": "坏图",
        "details": {"k": 1},
    }
