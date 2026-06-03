import numpy as np
import pytest

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection, Recognizer


def test_rawdetection_fields():
    r = RawDetection(source="ocr", label=None, text="hi", confidence=0.7, bbox=[0, 0, 5, 5])
    assert r.source == "ocr"
    assert r.text == "hi"
    assert r.bbox == [0, 0, 5, 5]


def test_recognizer_is_abstract():
    with pytest.raises(TypeError):
        Recognizer()


def test_concrete_recognizer_runs():
    class Echo(Recognizer):
        def infer(self, image, ctx):
            return [
                RawDetection(source="ocr", label=None, text="x", confidence=1.0, bbox=[0, 0, 1, 1])
            ]

    out = Echo().infer(np.zeros((2, 2, 3), dtype=np.uint8), InferContext(conf_threshold=0.25))
    assert out[0].text == "x"
