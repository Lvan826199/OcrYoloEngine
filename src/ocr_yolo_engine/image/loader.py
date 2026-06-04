"""图片来源加载与解码:base64 / 本地路径(白名单) / 原始字节。"""

from __future__ import annotations

import base64
import binascii
import os

import cv2
import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode


def decode_image_bytes(data: bytes) -> np.ndarray:
    """把图片字节解码为 BGR ndarray;失败抛 INVALID_IMAGE。"""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise EngineError(ErrorCode.INVALID_IMAGE, "无法解码为图片")
    return img


def load_from_base64(b64: str) -> np.ndarray:
    payload = b64.split(",", 1)[1] if b64.startswith("data:") else b64
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EngineError(ErrorCode.INVALID_IMAGE, "base64 解码失败") from exc
    return decode_image_bytes(data)


def load_from_path(path: str, allowed_roots: list[str]) -> np.ndarray:
    real = os.path.realpath(path)
    roots = [os.path.realpath(r) for r in allowed_roots]
    if not any(real == r or real.startswith(r + os.sep) for r in roots):
        raise EngineError(
            ErrorCode.PATH_NOT_ALLOWED,
            "路径不在允许的根目录白名单内",
            details={"path": path},
        )
    if not os.path.isfile(real):
        raise EngineError(ErrorCode.INVALID_IMAGE, "文件不存在", details={"path": path})
    with open(real, "rb") as fh:
        return decode_image_bytes(fh.read())
