"""共享 fixture:用真实识别器(真实 TemplateRecognizer + 真实模板图)装配测试 app。

不再注入任何假识别器:模板匹配无重依赖,可做完整真实端到端;
OCR/YOLO 识别器以真实对象懒加载方式注入,默认套件不触发其真实推理。
"""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
from ocr_yolo_engine.recognizers.ocr import OcrRecognizer
from ocr_yolo_engine.recognizers.template import TemplateRecognizer
from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model
from ocr_yolo_engine.service.app import create_app
from ocr_yolo_engine.service.deps import AppContext
from ocr_yolo_engine.settings import Settings
from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore
from tests.fixtures.factory import make_blank_scene, make_scene_with_patch, scene_b64, write_png

# 场景与目标块的真实几何:白底 100x80,黑块左上角 (30, 40),尺寸 12x12。
SCENE_W = 100
SCENE_H = 80
PATCH_XYWH = (30, 40, 12, 12)
TEMPLATE_NAME = "patch"
TEMPLATE_VERSION = "v1"
TEMPLATE_THRESHOLD = 0.6
# 黑块真实中心,供契约/管线测试断言(带容差)。
PATCH_CENTER = (PATCH_XYWH[0] + PATCH_XYWH[2] / 2, PATCH_XYWH[1] + PATCH_XYWH[3] / 2)


def build_template_store() -> TemplateStore:
    """在临时目录真实写出一张 12x12 黑块模板 PNG 并注册为 "patch"。"""
    tmp_dir = tempfile.mkdtemp(prefix="ocr_yolo_tmpl_")
    tmpl_path = os.path.join(tmp_dir, "patch.png")
    # 模板自身就是一块 12x12 纯黑图(与场景黑块同色),模板匹配可定位。
    write_png(tmpl_path, make_scene_with_patch(12, 12, (0, 0, 12, 12), patch_color=(0, 0, 0)))
    return TemplateStore(
        {
            TEMPLATE_NAME: TemplateSpec(
                name=TEMPLATE_NAME,
                path=tmpl_path,
                version=TEMPLATE_VERSION,
                params={"threshold": TEMPLATE_THRESHOLD},
            )
        }
    )


def build_context(settings: Settings | None = None) -> AppContext:
    """构造真实 AppContext:真实模板识别器 + 真实(懒加载)OCR/YOLO 识别器。"""
    settings = settings or Settings(api_keys=[], allowed_path_roots=[])
    # registry 仅用于 /v1/models 列举,不真实加载权重(默认套件不触发 get)。
    registry = ModelRegistry(
        {"game": ModelSpec(name="game", path="game.pt", version="v1", classes={})},
        loader_fn=load_yolo_model,
        cache_size=1,
    )
    store = build_template_store()
    return AppContext(
        settings=settings,
        registry=registry,
        template_store=store,
        executor=InferenceExecutor(max_workers=2, max_queue=8, timeout_s=5),
        recognizers={
            "ocr": OcrRecognizer(settings=settings),
            "yolo": YoloRecognizer(registry=registry),
            "template": TemplateRecognizer(store=store),
        },
    )


def make_client(settings: Settings | None = None) -> TestClient:
    """构造注入真实识别器的 TestClient。"""
    return TestClient(create_app(ctx=build_context(settings)))


@pytest.fixture
def client() -> TestClient:
    return make_client()


@pytest.fixture
def scene_with_target_b64() -> str:
    """含目标黑块的真实场景图 base64。"""
    return scene_b64(make_scene_with_patch(SCENE_W, SCENE_H, PATCH_XYWH))


@pytest.fixture
def scene_without_target_b64() -> str:
    """无目标的纯白真实场景图 base64。"""
    return scene_b64(make_blank_scene(SCENE_W, SCENE_H))
