"""共享 fixture:构造注入假识别器的测试 app。"""

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
from ocr_yolo_engine.service.app import create_app
from ocr_yolo_engine.service.deps import AppContext
from ocr_yolo_engine.settings import Settings
from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore
from tests.fakes.recognizers import FakeRecognizer


@pytest.fixture
def png_b64():
    img = np.zeros((80, 100, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode()


def make_client(settings=None, ocr_canned=None):
    settings = settings or Settings(api_keys=[], allowed_path_roots=[])
    registry = ModelRegistry(
        {"game": ModelSpec(name="game", path="x.pt", version="v1", classes={})},
        loader_fn=lambda s: None,
        cache_size=1,
    )
    store = TemplateStore(
        {"icon": TemplateSpec(name="icon", path="x.png", version="v1", params={})}
    )
    ctx = AppContext(
        settings=settings,
        registry=registry,
        template_store=store,
        executor=InferenceExecutor(max_workers=2, max_queue=8, timeout_s=5),
        recognizers={
            "ocr": FakeRecognizer(ocr_canned or []),
            "yolo": FakeRecognizer([]),
            "template": FakeRecognizer([]),
        },
    )
    return TestClient(create_app(ctx=ctx))


@pytest.fixture
def client():
    return make_client()
