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
