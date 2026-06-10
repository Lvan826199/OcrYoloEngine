import json
import logging

from ocr_yolo_engine.observability.logging import (
    JsonFormatter,
    bind_request_id,
    current_request_id,
    new_request_id,
)


def test_request_id_contextvar_roundtrip():
    bind_request_id("req-123")
    assert current_request_id() == "req-123"


def test_new_request_id_is_unique():
    a = new_request_id()
    b = new_request_id()
    assert a != b
    assert len(a) >= 8


def test_json_formatter_includes_request_id():
    bind_request_id("req-xyz")
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    line = JsonFormatter().format(record)
    payload = json.loads(line)
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "req-xyz"
    assert payload["level"] == "INFO"


def test_json_formatter_merges_extra_fields():
    """extra={"extra_fields": {...}} 的结构化字段应并入 JSON 输出顶层。"""
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "access", (), None)
    record.extra_fields = {"method": "POST", "path": "/v1/match", "status": 200}
    payload = json.loads(JsonFormatter().format(record))
    assert payload["method"] == "POST"
    assert payload["path"] == "/v1/match"
    assert payload["status"] == 200


def test_json_formatter_includes_utc_timestamp():
    """日志必须带时间戳(ISO8601 UTC),否则生产排查无法对时间线。"""
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hi", (), None)
    payload = json.loads(JsonFormatter().format(record))
    assert "time" in payload
    # ISO8601 且为 UTC(以 +00:00 结尾)。
    assert payload["time"].endswith("+00:00")
    assert payload["time"][:4].isdigit()
