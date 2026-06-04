"""契约测试:全部真实数据、真实 TemplateRecognizer 端到端,不引用任何 fake。"""

from __future__ import annotations

import base64

import cv2
import numpy as np

from ocr_yolo_engine.settings import Settings
from tests.conftest import (
    PATCH_CENTER,
    SCENE_H,
    SCENE_W,
    TEMPLATE_NAME,
    TEMPLATE_THRESHOLD,
    TEMPLATE_VERSION,
    make_client,
)
from tests.fixtures.factory import make_scene_with_patch, scene_b64


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


def test_match_debug_returns_decodable_annotated_image(client, scene_with_target_b64):
    """debug=true:响应 debug_image 非 None,base64 解码 + imdecode 得同尺寸图。"""
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": scene_with_target_b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
            "debug": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    # 含真实黑块,应检出目标,debug 标注图非 None。
    assert body["method_results"]["template"]["detections"], "应检出目标供标注"
    debug_image = body["debug_image"]
    assert debug_image is not None
    # base64 解码 + cv2.imdecode 得到真实图,尺寸与输入一致。
    raw = base64.b64decode(debug_image)
    decoded = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert decoded is not None
    h, w = decoded.shape[:2]
    assert (w, h) == (SCENE_W, SCENE_H)


def test_match_debug_false_returns_none(client, scene_with_target_b64):
    """未开启 debug:debug_image 仍为 None。"""
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": scene_with_target_b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    assert r.status_code == 200
    assert r.json()["debug_image"] is None


def test_match_roi_remaps_bbox_to_full_image(client):
    """ROI 裁剪后,返回 detection 的 bbox 应为全图坐标(已加回偏移)。"""
    # 场景 100x80;黑块放在全图 (60, 40),ROI 框住 (50, 30, 45, 45)(不越界)。
    patch_xywh = (60, 40, 12, 12)
    img = make_scene_with_patch(SCENE_W, SCENE_H, patch_xywh)
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": scene_b64(img)},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
            "roi": {"x": 50, "y": 30, "w": 45, "h": 45},
        },
    )
    assert r.status_code == 200
    dets = r.json()["method_results"]["template"]["detections"]
    assert dets, "ROI 内含目标,应检出"
    cx, cy = dets[0]["center"]
    # 全图坐标下黑块真实中心 (66, 46),±3 容差,证明偏移已正确回映射。
    expected_cx = patch_xywh[0] + patch_xywh[2] / 2
    expected_cy = patch_xywh[1] + patch_xywh[3] / 2
    assert abs(cx - expected_cx) <= 3
    assert abs(cy - expected_cy) <= 3


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


def test_unload_unknown_model_404(client):
    """卸载未注册模型:404 + MODEL_NOT_FOUND。"""
    r = client.post("/v1/models/不存在/unload")
    assert r.status_code == 404
    assert r.json()["error_code"] == "MODEL_NOT_FOUND"


def test_reload_unknown_model_404(client):
    """重载未注册模型:404 + MODEL_NOT_FOUND。"""
    r = client.post("/v1/models/不存在/reload")
    assert r.status_code == 404
    assert r.json()["error_code"] == "MODEL_NOT_FOUND"


def test_unload_registered_model_ok(client):
    """卸载已注册但未加载的 game 模型:200 no-op,真实轻量不触发权重加载。"""
    r = client.post("/v1/models/game/unload")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "game"
    assert body["status"] == "unloaded"
    # game 从未加载,卸载后 loaded 列表不含它。
    assert "game" not in body["loaded"]


def test_hot_management_requires_auth():
    """开启 api_keys 时,热管理端点无 key 应 401。"""
    c = make_client(settings=Settings(api_keys=["secret"], allowed_path_roots=[]))
    assert c.post("/v1/models/game/unload").status_code == 401
    assert c.post("/v1/models/game/reload").status_code == 401
