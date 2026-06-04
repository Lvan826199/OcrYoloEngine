"""调试标注:在图像副本上画检测框与简短文字,用于 debug=true 返回。"""

from __future__ import annotations

import cv2
import numpy as np

from ocr_yolo_engine.schemas import Detection

# 标注样式:绿色框 + 绿色文字,粗细与字号在小图上也清晰可辨。
_BOX_COLOR = (0, 255, 0)
_TEXT_COLOR = (0, 255, 0)
_THICKNESS = 1
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.4


def draw_detections(image_bgr: np.ndarray, detections: list[Detection]) -> np.ndarray:
    """在输入 BGR 图的副本上逐个画检测框与简短标注文字,返回画好的图。

    - bbox 为全图像素坐标 [x1, y1, x2, y2],取整后用 cv2.rectangle 画框。
    - 文字优先用 label,否则用 text,末尾追加置信度,如 "patch 0.97"。
    - 不修改原图(在副本上作业)。
    """
    canvas = image_bgr.copy()
    for det in detections:
        x1, y1, x2, y2 = (int(round(v)) for v in det.bbox)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), _BOX_COLOR, _THICKNESS)
        base = det.label or det.text or ""
        caption = f"{base} {det.confidence:.2f}".strip()
        # 文字基线放在框上方一点;若贴近上边界则改放框内,避免被裁掉。
        text_y = y1 - 3 if y1 - 3 >= 8 else y1 + 12
        cv2.putText(
            canvas,
            caption,
            (x1, text_y),
            _FONT,
            _FONT_SCALE,
            _TEXT_COLOR,
            _THICKNESS,
            cv2.LINE_AA,
        )
    return canvas
