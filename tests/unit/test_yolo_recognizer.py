import numpy as np

from ocr_yolo_engine.models.registry import ModelSpec
from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.yolo import YoloRecognizer


class FakeBoxes:
    def __init__(self):
        self.xyxy = np.array([[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]])
        self.conf = np.array([0.9, 0.6])
        self.cls = np.array([0, 1])


class FakeResult:
    def __init__(self):
        self.boxes = FakeBoxes()


class FakeModel:
    def __init__(self):
        self.last_conf = None

    def predict(self, image, conf, verbose=False):
        self.last_conf = conf
        return [FakeResult()]


class FakeRegistry:
    def __init__(self, model):
        self._model = model
        self._spec = ModelSpec(
            name="game", path="x.pt", version="v2", classes={0: "boss", 1: "coin"}
        )

    def get(self, name):
        return self._model

    def spec(self, name):
        return self._spec


def test_yolo_maps_classes_and_passes_threshold():
    model = FakeModel()
    rec = YoloRecognizer(registry=FakeRegistry(model))
    out = rec.infer(
        np.zeros((100, 100, 3), dtype=np.uint8),
        InferContext(conf_threshold=0.5, model="game"),
    )
    assert model.last_conf == 0.5
    assert len(out) == 2
    assert out[0].source == "yolo"
    assert out[0].label == "boss"
    assert out[0].confidence == 0.9
    assert out[0].bbox == [10.0, 20.0, 30.0, 40.0]
    assert out[1].label == "coin"


def test_yolo_unknown_class_falls_back_to_index_string():
    model = FakeModel()
    reg = FakeRegistry(model)
    reg._spec = ModelSpec(name="game", path="x.pt", version="v2", classes={})
    rec = YoloRecognizer(registry=reg)
    out = rec.infer(
        np.zeros((100, 100, 3), dtype=np.uint8),
        InferContext(conf_threshold=0.0, model="game"),
    )
    assert out[0].label == "0"
