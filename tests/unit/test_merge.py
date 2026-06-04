"""merge 模块单元测试:真实 Detection 列表、确定性断言,无 mock。"""

from __future__ import annotations

from typing import cast

from ocr_yolo_engine.merge import iou, merge_detections
from ocr_yolo_engine.schemas import Detection, Method, MethodResult


def _det(source: Method, conf: float, bbox: list[float]) -> Detection:
    """用真实坐标构造一个 Detection;center/norm 取占位真实值,不影响合并逻辑。"""
    x1, y1, x2, y2 = bbox
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    return Detection(
        source=source,
        label=None,
        text=None,
        confidence=conf,
        bbox=bbox,
        center=[cx, cy],
        bbox_norm=[0.0, 0.0, 0.0, 0.0],
        center_norm=[0.0, 0.0],
    )


def _results(**kw: list[Detection]) -> dict[Method, MethodResult]:
    return {cast(Method, k): MethodResult(detections=v) for k, v in kw.items()}


def test_iou_full_overlap() -> None:
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_iou_no_overlap() -> None:
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_iou_partial_overlap() -> None:
    # 两个 10x10 框,重叠区 5x5=25,并集 100+100-25=175。
    assert abs(iou([0, 0, 10, 10], [5, 5, 15, 15]) - 25 / 175) < 1e-9


def test_iou_degenerate_box_returns_zero() -> None:
    assert iou([0, 0, 0, 0], [0, 0, 10, 10]) == 0.0


def test_none_returns_none() -> None:
    results = _results(template=[_det("template", 0.9, [0, 0, 10, 10])])
    assert merge_detections("none", results) is None


def test_concat_sorts_by_confidence_desc() -> None:
    results = _results(
        template=[_det("template", 0.5, [0, 0, 10, 10]), _det("template", 0.9, [20, 0, 30, 10])],
        ocr=[_det("ocr", 0.7, [40, 0, 50, 10])],
    )
    merged = merge_detections("concat", results)
    assert merged is not None
    assert [d.confidence for d in merged] == [0.9, 0.7, 0.5]
    # 全部检测都在(2 + 1)。
    assert len(merged) == 3


def test_dedup_drops_high_iou_keeps_higher_conf() -> None:
    # 两个高 IoU 框来自不同方法 → 只保留高置信度;另一低 IoU 框独立保留。
    a = _det("template", 0.95, [0, 0, 10, 10])
    b = _det("ocr", 0.60, [1, 1, 11, 11])  # 与 a IoU 很高(>=0.5)
    c = _det("ocr", 0.80, [50, 50, 60, 60])  # 与前两者不重叠
    merged = merge_detections("dedup", _results(template=[a], ocr=[b, c]))
    assert merged is not None
    confs = [d.confidence for d in merged]
    # 保留 a(0.95)与 c(0.80),丢弃 b(0.60);降序。
    assert confs == [0.95, 0.80]
    assert all(abs(d.confidence - 0.60) > 1e-9 for d in merged)


def test_dedup_keeps_low_iou_boxes() -> None:
    a = _det("template", 0.9, [0, 0, 10, 10])
    b = _det("ocr", 0.8, [100, 100, 110, 110])
    merged = merge_detections("dedup", _results(template=[a], ocr=[b]))
    assert merged is not None
    assert len(merged) == 2
