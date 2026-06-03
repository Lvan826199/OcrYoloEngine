import pytest
from pydantic import ValidationError

from ocr_yolo_engine.schemas import (
    Detection,
    ImageInput,
    RecognizeRequest,
    RecognizeResponse,
    ROI,
)


def test_image_input_requires_exactly_one_source():
    ImageInput(base64="abc")
    ImageInput(path="/a/b.png")
    with pytest.raises(ValidationError):
        ImageInput()
    with pytest.raises(ValidationError):
        ImageInput(base64="abc", path="/a/b.png")


def test_recognize_request_yolo_requires_model():
    with pytest.raises(ValidationError):
        RecognizeRequest(image=ImageInput(base64="x"), methods=["yolo"])
    req = RecognizeRequest(image=ImageInput(base64="x"), methods=["yolo"], model="game_a")
    assert req.model == "game_a"


def test_recognize_request_template_requires_templates():
    with pytest.raises(ValidationError):
        RecognizeRequest(image=ImageInput(base64="x"), methods=["template"])
    req = RecognizeRequest(
        image=ImageInput(base64="x"), methods=["template"], templates=["settings_icon"]
    )
    assert req.templates == ["settings_icon"]


def test_roi_validation():
    ROI(x=0, y=0, w=10, h=10)
    with pytest.raises(ValidationError):
        ROI(x=0, y=0, w=0, h=10)


def test_detection_roundtrip():
    d = Detection(
        source="yolo",
        label="cat",
        text=None,
        confidence=0.9,
        bbox=[1, 2, 3, 4],
        center=[2, 3],
        bbox_norm=[0.1, 0.2, 0.3, 0.4],
        center_norm=[0.2, 0.3],
    )
    assert d.model_dump()["source"] == "yolo"


def test_response_builds():
    resp = RecognizeResponse(
        request_id="r1", image_size=[100, 200], method_results={}, debug_image=None
    )
    assert resp.image_size == [100, 200]
