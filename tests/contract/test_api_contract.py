"""契约测试:全部真实数据、真实 TemplateRecognizer 端到端,不引用任何 fake。"""

from __future__ import annotations

from ocr_yolo_engine.settings import Settings
from tests.conftest import (
    PATCH_CENTER,
    TEMPLATE_NAME,
    TEMPLATE_THRESHOLD,
    TEMPLATE_VERSION,
    make_client,
)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_match_with_target_returns_detection(client, scene_with_target_b64):
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": scene_with_target_b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    assert r.status_code == 200
    dets = r.json()["method_results"]["template"]["detections"]
    assert dets, "含目标场景应至少检出一个模板匹配"
    d = dets[0]
    # 首个 bbox 中心应接近黑块真实中心(±3 容差)。
    cx, cy = d["center"]
    assert abs(cx - PATCH_CENTER[0]) <= 3
    assert abs(cy - PATCH_CENTER[1]) <= 3
    assert d["confidence"] >= TEMPLATE_THRESHOLD


def test_match_without_target_returns_empty(client, scene_without_target_b64):
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": scene_without_target_b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    # 成功但无目标:200 + 空数组。
    assert r.status_code == 200
    assert r.json()["method_results"]["template"]["detections"] == []


def test_invalid_base64_returns_400(client):
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": "@@notbase64@@"},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    assert r.status_code == 400
    assert r.json()["error_code"] == "INVALID_IMAGE"


def test_detect_requires_model_422(client, scene_with_target_b64):
    r = client.post(
        "/v1/detect",
        json={"image": {"base64": scene_with_target_b64}, "methods": ["yolo"]},
    )
    assert r.status_code == 422


def test_models_listing(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    assert r.json()["models"] == [{"name": "game", "version": "v1"}]


def test_templates_listing(client):
    r = client.get("/v1/templates")
    assert r.status_code == 200
    assert r.json()["templates"] == [{"name": TEMPLATE_NAME, "version": TEMPLATE_VERSION}]


def test_ready_lists_models(client):
    r = client.get("/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert "game" in body["models"]


def test_auth_rejects_without_key_and_accepts_with_key(scene_with_target_b64):
    c = make_client(settings=Settings(api_keys=["secret"], allowed_path_roots=[]))
    body = {
        "image": {"base64": scene_with_target_b64},
        "methods": ["template"],
        "templates": [TEMPLATE_NAME],
    }
    r = c.post("/v1/match", json=body)
    assert r.status_code == 401
    r2 = c.post("/v1/match", json=body, headers={"X-API-Key": "secret"})
    assert r2.status_code == 200
