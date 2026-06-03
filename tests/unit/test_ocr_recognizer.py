import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.ocr import OcrRecognizer


class FakePaddle:
    def ocr(self, img, cls=True):
        return [
            [
                [[[10, 20], [60, 20], [60, 40], [10, 40]], ("登录", 0.95)],
                [[[10, 50], [40, 50], [40, 70], [10, 70]], ("OK", 0.80)],
            ]
        ]


def test_ocr_wraps_results_with_bounding_box():
    rec = OcrRecognizer(engine=FakePaddle())
    out = rec.infer(np.zeros((100, 100, 3), dtype=np.uint8), InferContext(conf_threshold=0.0))
    assert len(out) == 2
    first = out[0]
    assert first.source == "ocr"
    assert first.label is None
    assert first.text == "登录"
    assert first.confidence == 0.95
    assert first.bbox == [10, 20, 60, 40]


def test_ocr_filters_by_confidence():
    rec = OcrRecognizer(engine=FakePaddle())
    out = rec.infer(np.zeros((100, 100, 3), dtype=np.uint8), InferContext(conf_threshold=0.9))
    assert [d.text for d in out] == ["登录"]


def test_ocr_handles_empty_page():
    class EmptyPaddle:
        def ocr(self, img, cls=True):
            return [None]

    rec = OcrRecognizer(engine=EmptyPaddle())
    out = rec.infer(np.zeros((10, 10, 3), dtype=np.uint8), InferContext(conf_threshold=0.0))
    assert out == []
