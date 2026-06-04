"""真实图像/模板构造工具:用 numpy/cv2 生成真实 BGR 图,供真实数据测试使用。"""

from __future__ import annotations

import base64

import cv2
import numpy as np


def make_scene_with_patch(
    w: int,
    h: int,
    patch_xywh: tuple[int, int, int, int],
    patch_color: tuple[int, int, int] = (0, 0, 0),
    bg_color: tuple[int, int, int] = (255, 255, 255),
) -> np.ndarray:
    """返回真实 BGR ndarray:在白底上指定位置画一个纯色块。

    patch_xywh 为 (x, y, w, h)。默认白底黑块,模板匹配可稳定定位。
    """
    img = np.full((h, w, 3), bg_color, dtype=np.uint8)
    x, y, pw, ph = patch_xywh
    img[y : y + ph, x : x + pw] = patch_color
    return img


def make_blank_scene(
    w: int, h: int, bg_color: tuple[int, int, int] = (255, 255, 255)
) -> np.ndarray:
    """返回真实 BGR ndarray:纯色背景、无任何目标块。"""
    return np.full((h, w, 3), bg_color, dtype=np.uint8)


def write_png(path: str, img: np.ndarray) -> None:
    """把 BGR 图真实写到磁盘 PNG。"""
    ok = cv2.imwrite(path, img)
    if not ok:
        raise RuntimeError(f"写入 PNG 失败:{path}")


def scene_b64(img: np.ndarray) -> str:
    """把 BGR 图编码为 PNG 并转 base64 字符串。"""
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("PNG 编码失败")
    return base64.b64encode(buf.tobytes()).decode()
