"""契约测试:全部真实数据、真实 TemplateRecognizer 端到端,不引用任何 fake。"""

from __future__ import annotations

import base64
import os

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


def test_error_response_carries_real_request_id(client):
    """错误响应的 request_id 必须是真实生成的 id,而非占位 "-"(可用于日志关联)。"""
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": "@@notbase64@@"},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    assert r.status_code == 400
    rid = r.json()["request_id"]
    assert rid != "-"
    assert len(rid) == 32  # uuid4().hex


def test_upload_invalid_methods_returns_422_not_500(client):
    """upload 传非法 methods:应走统一校验契约返回 422,而非裸 500。"""
    ok, buf = cv2.imencode(".png", np.zeros((10, 10, 3), dtype=np.uint8))
    assert ok
    r = client.post(
        "/v1/recognize/upload",
        files={"file": ("a.png", buf.tobytes(), "image/png")},
        data={"methods": "bogus"},
    )
    assert r.status_code == 422


def test_upload_yolo_without_model_returns_422(client):
    """upload methods=yolo 缺 model:与 JSON 接口一致返回 422。"""
    ok, buf = cv2.imencode(".png", np.zeros((10, 10, 3), dtype=np.uint8))
    assert ok
    r = client.post(
        "/v1/recognize/upload",
        files={"file": ("a.png", buf.tobytes(), "image/png")},
        data={"methods": "yolo"},
    )
    assert r.status_code == 422


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


def _match_body(b64: str, cache: str | None = None) -> dict:
    body: dict = {
        "image": {"base64": b64},
        "methods": ["template"],
        "templates": [TEMPLATE_NAME],
    }
    if cache is not None:
        body["cache"] = cache
    return body


def test_cache_hit_on_second_match(scene_with_target_b64):
    """开缓存:同一 /v1/match 连发两次,第一次 MISS、第二次 HIT,detections 一致。"""
    c = make_client(result_cache_size=16)
    r1 = c.post("/v1/match", json=_match_body(scene_with_target_b64))
    assert r1.status_code == 200
    assert r1.headers["X-Cache"] == "MISS"
    assert r1.json()["from_cache"] is False

    r2 = c.post("/v1/match", json=_match_body(scene_with_target_b64))
    assert r2.status_code == 200
    assert r2.headers["X-Cache"] == "HIT"
    assert r2.json()["from_cache"] is True
    # 命中结果与首次一致。
    d1 = r1.json()["method_results"]["template"]["detections"]
    d2 = r2.json()["method_results"]["template"]["detections"]
    assert d1 == d2
    assert d2, "应有检出"


def test_cache_off_always_bypass(scene_with_target_b64):
    """开缓存但请求 cache=off:两次都 from_cache=False、X-Cache=BYPASS。"""
    c = make_client(result_cache_size=16)
    for _ in range(2):
        r = c.post("/v1/match", json=_match_body(scene_with_target_b64, cache="off"))
        assert r.status_code == 200
        assert r.headers["X-Cache"] == "BYPASS"
        assert r.json()["from_cache"] is False


def test_cache_invalidated_by_model_unload(scene_with_target_b64):
    """开缓存→match(写入)→再 match(HIT)→unload 模型(清缓存)→再 match 应 MISS。"""
    c = make_client(result_cache_size=16)
    c.post("/v1/match", json=_match_body(scene_with_target_b64))
    r_hit = c.post("/v1/match", json=_match_body(scene_with_target_b64))
    assert r_hit.headers["X-Cache"] == "HIT"

    r_unload = c.post("/v1/models/game/unload")
    assert r_unload.status_code == 200

    r_after = c.post("/v1/match", json=_match_body(scene_with_target_b64))
    assert r_after.status_code == 200
    assert r_after.headers["X-Cache"] == "MISS", "卸载后缓存应被清空"
    assert r_after.json()["from_cache"] is False


def test_cache_disabled_by_default_bypass(client, scene_with_target_b64):
    """默认 client(缓存关闭):X-Cache=BYPASS、from_cache=False,确认零影响。"""
    r = client.post("/v1/match", json=_match_body(scene_with_target_b64))
    assert r.status_code == 200
    assert r.headers["X-Cache"] == "BYPASS"
    assert r.json()["from_cache"] is False


def test_cache_refresh_recomputes_then_writes(scene_with_target_b64):
    """cache=refresh:不读、强制算并写(MISS);随后 auto 应能命中。"""
    c = make_client(result_cache_size=16)
    c.post("/v1/match", json=_match_body(scene_with_target_b64))  # 写入
    r_refresh = c.post("/v1/match", json=_match_body(scene_with_target_b64, cache="refresh"))
    assert r_refresh.headers["X-Cache"] == "MISS"
    assert r_refresh.json()["from_cache"] is False
    r_auto = c.post("/v1/match", json=_match_body(scene_with_target_b64))
    assert r_auto.headers["X-Cache"] == "HIT"


def _recognize_body(b64: str, merge: str) -> dict:
    return {
        "image": {"base64": b64},
        "methods": ["template"],
        "templates": [TEMPLATE_NAME],
        "merge": merge,
    }


def test_recognize_merge_concat_fills_merged(client, scene_with_target_b64):
    """/v1/recognize + merge=concat:merged 非空,且与单方法 detections 同量同序。"""
    r = client.post("/v1/recognize", json=_recognize_body(scene_with_target_b64, "concat"))
    assert r.status_code == 200
    body = r.json()
    dets = body["method_results"]["template"]["detections"]
    assert dets, "含目标场景应有检出"
    merged = body["merged"]
    assert merged is not None
    # 单方法时 concat 即原列表(同量、同序)。
    assert len(merged) == len(dets)
    assert [d["confidence"] for d in merged] == [d["confidence"] for d in dets]


def test_recognize_merge_none_default_is_null(client, scene_with_target_b64):
    """默认 merge=none:merged 为 None,method_results 不变(行为与改动前一致)。"""
    r = client.post(
        "/v1/recognize",
        json={
            "image": {"base64": scene_with_target_b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merged"] is None
    assert body["method_results"]["template"]["detections"]


def test_recognize_merge_priority_single_hit(client, scene_with_target_b64):
    """merge=priority + 单 template 命中:merged = template 的检测。"""
    r = client.post("/v1/recognize", json=_recognize_body(scene_with_target_b64, "priority"))
    assert r.status_code == 200
    body = r.json()
    dets = body["method_results"]["template"]["detections"]
    merged = body["merged"]
    assert merged is not None
    assert merged == dets


def test_recognize_merge_cache_roundtrip_and_no_cross_contamination(scene_with_target_b64):
    """缓存兼容:concat 连发两次第二次 HIT 且 merged 正确;同图 dedup 应 MISS(键含 merge)。"""
    c = make_client(result_cache_size=8)
    r1 = c.post("/v1/recognize", json=_recognize_body(scene_with_target_b64, "concat"))
    assert r1.status_code == 200
    assert r1.headers["X-Cache"] == "MISS"
    assert r1.json()["from_cache"] is False

    r2 = c.post("/v1/recognize", json=_recognize_body(scene_with_target_b64, "concat"))
    assert r2.status_code == 200
    assert r2.headers["X-Cache"] == "HIT"
    assert r2.json()["from_cache"] is True
    # merged 进了缓存,命中后仍正确且与首次一致。
    assert r2.json()["merged"] == r1.json()["merged"]
    assert r2.json()["merged"]

    # 同图但 merge=dedup → 缓存键不同 → MISS,不串味。
    r3 = c.post("/v1/recognize", json=_recognize_body(scene_with_target_b64, "dedup"))
    assert r3.status_code == 200
    assert r3.headers["X-Cache"] == "MISS"
    assert r3.json()["from_cache"] is False
    assert r3.json()["merged"] is not None


def test_oversized_bytes_rejected_before_decode():
    """超限字节即使不是合法图片也应 413(字节上限先于解码,防解压炸弹吃内存)。"""
    c = make_client(settings=Settings(api_keys=[], allowed_path_roots=[], max_image_bytes=64))
    blob = base64.b64encode(os.urandom(1024)).decode()
    r = c.post(
        "/v1/match",
        json={"image": {"base64": blob}, "methods": ["template"], "templates": [TEMPLATE_NAME]},
    )
    assert r.status_code == 413
    assert r.json()["error_code"] == "IMAGE_TOO_LARGE"


def test_metrics_records_error_status(client, scene_with_target_b64):
    """识别失败也必须进指标:未知模板 → 404,/metrics 出现 status=\"error\" 计数。"""
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": scene_with_target_b64},
            "methods": ["template"],
            "templates": ["不存在的模板"],
        },
    )
    assert r.status_code == 404
    m = client.get("/metrics").text
    assert 'oye_requests_total{method="template",status="error"}' in m


def test_metrics_endpoint_after_match(client, scene_with_target_b64):
    """真实端到端:先发一次模板识别,再拉 /metrics,断言计数已记录(真实数据)。"""
    client.post(
        "/v1/match",
        json={
            "image": {"base64": scene_with_target_b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.text
    assert "oye_requests_total" in body
    assert 'method="template"' in body
    assert "oye_inference_seconds_count" in body
