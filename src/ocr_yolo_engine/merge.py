"""/recognize 多方法合并策略(可插拔):none/concat/dedup。

设计要点:
- none:返回 None(各方法分开返回,保持现状)。
- concat:汇总所有方法的全部 detections,按 confidence 降序拼接。
- dedup:汇总后按置信度降序做跨方法 NMS,丢弃与已保留框 IoU >= 阈值的低分框。
- priority:不在本模块实现——它需要在 runner 里短路控制"跑几个方法",见 pipeline_runner。
"""

from __future__ import annotations

from ocr_yolo_engine.schemas import Detection, Method, MethodResult

# 跨方法 dedup 的 IoU 阈值:>= 该值视为同一目标,只保留高置信度者。
DEDUP_IOU_THRESHOLD = 0.5


def iou(a: list[float], b: list[float]) -> float:
    """两个 bbox [x1,y1,x2,y2] 的交并比;无重叠或退化框返回 0.0。"""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def _flatten(method_results: dict[Method, MethodResult]) -> list[Detection]:
    """汇总所有方法的全部 detections 为一个扁平列表。"""
    out: list[Detection] = []
    for result in method_results.values():
        out.extend(result.detections)
    return out


def merge_detections(
    strategy: str, method_results: dict[Method, MethodResult]
) -> list[Detection] | None:
    """按策略合并多方法检测结果。priority 由 runner 短路处理,不会传入此处。"""
    if strategy == "none":
        return None
    if strategy == "concat":
        return sorted(_flatten(method_results), key=lambda d: d.confidence, reverse=True)
    if strategy == "dedup":
        ordered = sorted(_flatten(method_results), key=lambda d: d.confidence, reverse=True)
        kept: list[Detection] = []
        for det in ordered:
            if all(iou(det.bbox, k.bbox) < DEDUP_IOU_THRESHOLD for k in kept):
                kept.append(det)
        return kept
    raise ValueError(f"未知的合并策略:{strategy}")
