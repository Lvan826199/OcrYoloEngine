"""真实端到端冒烟测试:真实模型(PaddleOCR / YOLO)+ 真实模板 HTTP 链路。

运行:uv run pytest -m smoke
重依赖缺失时由 importorskip 优雅跳过;模型下载需联网,失败时 skip 并注明原因。
"""

from __future__ import annotations

import numpy as np
import pytest

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection

pytestmark = pytest.mark.smoke


def test_ocr_real_inference():
    """真实 PaddleOCR:在白底图上写 "HELLO",断言识别到非空文字(内容带容差)。"""
    pytest.importorskip("paddleocr")
    import cv2

    from ocr_yolo_engine.recognizers.ocr import OcrRecognizer

    img = np.full((120, 400, 3), 255, dtype=np.uint8)
    cv2.putText(img, "HELLO", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 4)

    rec = OcrRecognizer()  # engine=None → 懒加载真实 PaddleOCR
    try:
        out = rec.infer(img, InferContext(conf_threshold=0.0))
    except Exception as exc:  # noqa: BLE001 - 模型下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 PaddleOCR 模型:{exc}")

    assert isinstance(out, list)
    assert all(isinstance(d, RawDetection) for d in out)
    assert any((d.text or "").strip() for d in out), "应识别到至少一段非空文字"


def test_yolo_real_inference():
    """真实 YOLO:加载 yolov8n.pt,对真实图推理,断言返回规整 RawDetection 列表。"""
    pytest.importorskip("ultralytics")

    from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
    from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model

    registry = ModelRegistry(
        {"yolov8n": ModelSpec(name="yolov8n", path="yolov8n.pt", version="v8n", classes={})},
        loader_fn=load_yolo_model,
        cache_size=1,
    )
    rec = YoloRecognizer(registry=registry)
    img = np.zeros((640, 640, 3), dtype=np.uint8)

    try:
        out = rec.infer(img, InferContext(conf_threshold=0.25, model="yolov8n"))
    except Exception as exc:  # noqa: BLE001 - 权重下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 yolov8n 权重:{exc}")

    assert isinstance(out, list)
    for d in out:
        assert isinstance(d, RawDetection)
        assert len(d.bbox) == 4
        assert all(isinstance(v, float) for v in d.bbox)


def test_reload_real_model_http():
    """真实 TestClient + 真实可加载 registry:POST reload 真实加载 yolov8n 权重。"""
    pytest.importorskip("ultralytics")

    from fastapi.testclient import TestClient

    from ocr_yolo_engine.concurrency.executor import InferenceExecutor
    from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
    from ocr_yolo_engine.recognizers.ocr import OcrRecognizer
    from ocr_yolo_engine.recognizers.template import TemplateRecognizer
    from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model
    from ocr_yolo_engine.service.app import create_app
    from ocr_yolo_engine.service.deps import AppContext
    from ocr_yolo_engine.settings import Settings
    from tests.conftest import build_template_store

    settings = Settings(api_keys=[], allowed_path_roots=[])
    # 真实可加载 registry:reload 会触发 load_yolo_model 真实下载/加载权重。
    registry = ModelRegistry(
        {"yolov8n": ModelSpec(name="yolov8n", path="yolov8n.pt", version="v8n", classes={})},
        loader_fn=load_yolo_model,
        cache_size=1,
    )
    store = build_template_store()
    ctx = AppContext(
        settings=settings,
        registry=registry,
        template_store=store,
        executor=InferenceExecutor(max_workers=2, max_queue=8, timeout_s=30),
        recognizers={
            "ocr": OcrRecognizer(settings=settings),
            "yolo": YoloRecognizer(registry=registry),
            "template": TemplateRecognizer(store=store),
        },
    )
    client = TestClient(create_app(ctx=ctx))

    try:
        r = client.post("/v1/models/yolov8n/reload")
    except Exception as exc:  # noqa: BLE001 - 权重下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 yolov8n 权重:{exc}")

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "reloaded"
    assert body["version"] == "v8n"
    # 真实加载成功后,缓存里应含 yolov8n。
    assert "yolov8n" in registry.loaded_names()


def test_recognize_multi_method_merge_concat_real():
    """真实多方法 /v1/recognize:场景含文字 + 黑块,template+ocr,merge=concat。

    断言 merged 同时含模板与 OCR 的检测,且按置信度降序有序。
    """
    pytest.importorskip("paddleocr")

    import cv2

    from tests.conftest import TEMPLATE_NAME, make_client
    from tests.fixtures.factory import make_scene_with_patch, scene_b64

    # 真实场景:白底 + 文字 "HELLO"(供 OCR)+ 12x12 黑块(供模板匹配)。
    img = make_scene_with_patch(400, 160, (300, 120, 12, 12))
    cv2.putText(img, "HELLO", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 4)

    client = make_client()
    try:
        r = client.post(
            "/v1/recognize",
            json={
                "image": {"base64": scene_b64(img)},
                "methods": ["template", "ocr"],
                "templates": [TEMPLATE_NAME],
                "merge": "concat",
            },
        )
    except Exception as exc:  # noqa: BLE001 - 模型下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 PaddleOCR 模型:{exc}")

    assert r.status_code == 200, r.text
    body = r.json()
    tmpl = body["method_results"]["template"]["detections"]
    ocr = body["method_results"]["ocr"]["detections"]
    assert tmpl, "应检出模板黑块"
    assert ocr, "应识别到文字"
    merged = body["merged"]
    assert merged is not None
    # 合并后应同时包含模板与 OCR 来源的检测。
    sources = {d["source"] for d in merged}
    assert {"template", "ocr"} <= sources
    assert len(merged) == len(tmpl) + len(ocr)
    # 按置信度降序有序。
    confs = [d["confidence"] for d in merged]
    assert confs == sorted(confs, reverse=True)


def _game_fixture(name: str):
    """读入库的真实游戏截图样例(来源/许可见 tests/fixtures/README.md)。"""
    import json
    from pathlib import Path

    import cv2

    fixtures = Path(__file__).resolve().parent.parent / "fixtures"
    with (fixtures / f"{name}.expected.json").open(encoding="utf-8") as f:
        expected = json.load(f)
    img = cv2.imread(str(fixtures / expected["scene"]), cv2.IMREAD_COLOR)
    assert img is not None, f"样例图 {expected['scene']} 应可读取"
    return img, expected


def test_ocr_game_race_hud_real():
    """真实 PaddleOCR 读真实游戏竞速 HUD:计时器/圈数/赛道名,坐标带容差。"""
    pytest.importorskip("paddleocr")
    import cv2

    from ocr_yolo_engine.recognizers.ocr import OcrRecognizer

    img, expected = _game_fixture("game_race")
    rec = OcrRecognizer()
    try:
        out = rec.infer(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), InferContext(conf_threshold=0.5))
    except Exception as exc:  # noqa: BLE001 - 模型下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 PaddleOCR 模型:{exc}")

    for want in expected["expectations"]["ocr"]:
        hits = [d for d in out if want["text_contains"] in (d.text or "")]
        assert hits, f"应识别到含 '{want['text_contains']}' 的文字,实际:{[d.text for d in out]}"
        d = hits[0]
        cx = (d.bbox[0] + d.bbox[2]) / 2
        cy = (d.bbox[1] + d.bbox[3]) / 2
        tol = want["tolerance_px"]
        assert abs(cx - want["center"][0]) <= tol
        assert abs(cy - want["center"][1]) <= tol


def test_ocr_game_menu_labels_real():
    """真实 PaddleOCR 读真实游戏菜单:按钮文字标签应可识别(供文字定位点击)。"""
    pytest.importorskip("paddleocr")
    import cv2

    from ocr_yolo_engine.recognizers.ocr import OcrRecognizer

    img, _ = _game_fixture("game_menu")
    rec = OcrRecognizer()
    try:
        out = rec.infer(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), InferContext(conf_threshold=0.5))
    except Exception as exc:  # noqa: BLE001 - 模型下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 PaddleOCR 模型:{exc}")

    texts = [(d.text or "") for d in out]
    for label in ("Story Mode", "Online"):
        assert any(label in t for t in texts), f"菜单标签 '{label}' 应被识别,实际:{texts}"


def test_yolo_game_race_real():
    """真实 yolov8n 看真实游戏画面:应检出赛道旁的站立角色(person),位置带容差。"""
    pytest.importorskip("ultralytics")

    from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
    from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model

    img, expected = _game_fixture("game_race")
    want = expected["expectations"]["yolo"][0]
    registry = ModelRegistry(
        {
            want["model"]: ModelSpec(
                name=want["model"],
                path=f"{want['model']}.pt",
                version="v8n",
                classes={0: "person"},
            )
        },
        loader_fn=load_yolo_model,
        cache_size=1,
    )
    rec = YoloRecognizer(registry=registry)
    try:
        out = rec.infer(img, InferContext(conf_threshold=0.25, model=want["model"]))
    except Exception as exc:  # noqa: BLE001 - 权重下载/联网失败时优雅跳过
        pytest.skip(f"无法获取 {want['model']} 权重:{exc}")

    persons = [
        d for d in out if d.label == want["label"] and d.confidence >= want["min_confidence"]
    ]
    assert persons, f"应检出 {want['label']},实际:{[(d.label, d.confidence) for d in out]}"
    tol = want["tolerance_px"]
    best = max(persons, key=lambda d: d.confidence)
    cx = (best.bbox[0] + best.bbox[2]) / 2
    cy = (best.bbox[1] + best.bbox[3]) / 2
    assert abs(cx - want["center"][0]) <= tol
    assert abs(cy - want["center"][1]) <= tol


def test_template_real_http_e2e():
    """真实 TestClient + 真实模板:无重依赖,完整 HTTP 跑通模板匹配。"""
    from tests.conftest import PATCH_CENTER, SCENE_H, SCENE_W, TEMPLATE_NAME, make_client
    from tests.fixtures.factory import make_scene_with_patch, scene_b64

    client = make_client()
    b64 = scene_b64(make_scene_with_patch(SCENE_W, SCENE_H, (30, 40, 12, 12)))
    r = client.post(
        "/v1/match",
        json={
            "image": {"base64": b64},
            "methods": ["template"],
            "templates": [TEMPLATE_NAME],
        },
    )
    assert r.status_code == 200
    dets = r.json()["method_results"]["template"]["detections"]
    assert dets
    cx, cy = dets[0]["center"]
    assert abs(cx - PATCH_CENTER[0]) <= 3
    assert abs(cy - PATCH_CENTER[1]) <= 3
