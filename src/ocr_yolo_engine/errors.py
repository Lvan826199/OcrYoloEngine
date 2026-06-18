"""统一错误码、异常与 HTTP 映射。"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_IMAGE = "INVALID_IMAGE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    TEMPLATE_NOT_FOUND = "TEMPLATE_NOT_FOUND"
    OVERLOADED = "OVERLOADED"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


_STATUS: dict[ErrorCode, int] = {
    ErrorCode.INVALID_IMAGE: 400,
    ErrorCode.IMAGE_TOO_LARGE: 413,
    ErrorCode.PATH_NOT_ALLOWED: 403,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.MODEL_NOT_FOUND: 404,
    ErrorCode.TEMPLATE_NOT_FOUND: 404,
    ErrorCode.OVERLOADED: 503,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.INTERNAL: 500,
}


class EngineError(Exception):
    """业务异常:携带错误码、可读信息与结构化细节。"""

    def __init__(
        self, code: ErrorCode, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    @property
    def http_status(self) -> int:
        return _STATUS[self.code]

    def to_body(self, request_id: str) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
        }
