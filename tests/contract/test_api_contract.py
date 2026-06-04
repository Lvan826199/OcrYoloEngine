from ocr_yolo_engine.recognizers.base import RawDetection
from tests.conftest import make_client


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ocr_with_detections(png_b64):
    c = make_client(ocr_canned=[RawDetection("ocr", None, "登录", 0.9, [10, 20, 30, 40])])
    r = c.post("/v1/ocr", json={"base64": png_b64})
    assert r.status_code == 200
    body = r.json()
    assert body["image_size"] == [100, 80]
    dets = body["method_results"]["ocr"]["detections"]
    assert dets[0]["text"] == "登录"
    assert dets[0]["bbox"] == [10, 20, 30, 40]


def test_ocr_empty_is_200_not_error(client, png_b64):
    r = client.post("/v1/ocr", json={"base64": png_b64})
    assert r.status_code == 200
    assert r.json()["method_results"]["ocr"]["detections"] == []


def test_invalid_base64_returns_400_error_code(client):
    r = client.post("/v1/ocr", json={"base64": "@@notbase64@@"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "INVALID_IMAGE"


def test_detect_requires_model_422(client, png_b64):
    r = client.post("/v1/detect", json={"image": {"base64": png_b64}, "methods": ["yolo"]})
    assert r.status_code == 422


def test_models_listing(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    assert r.json()["models"] == [{"name": "game", "version": "v1"}]


def test_auth_rejects_when_enabled(png_b64):
    from ocr_yolo_engine.settings import Settings

    c = make_client(settings=Settings(api_keys=["secret"], allowed_path_roots=[]))
    r = c.post("/v1/ocr", json={"base64": png_b64})
    assert r.status_code == 401
    r2 = c.post("/v1/ocr", json={"base64": png_b64}, headers={"X-API-Key": "secret"})
    assert r2.status_code == 200
