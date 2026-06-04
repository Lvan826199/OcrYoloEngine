"""依赖注入容器:装配 registry / template_store / executor / recognizers。"""

from __future__ import annotations

from dataclasses import dataclass

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.config_loader import load_model_specs, load_template_specs
from ocr_yolo_engine.models.registry import ModelRegistry
from ocr_yolo_engine.recognizers.ocr import OcrRecognizer
from ocr_yolo_engine.recognizers.template import TemplateRecognizer
from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model
from ocr_yolo_engine.schemas import Method
from ocr_yolo_engine.settings import Settings, get_settings
from ocr_yolo_engine.templates.store import TemplateStore


@dataclass
class AppContext:
    settings: Settings
    registry: ModelRegistry
    template_store: TemplateStore
    executor: InferenceExecutor
    recognizers: dict[Method, object]


def build_context(settings: Settings | None = None) -> AppContext:
    settings = settings or get_settings()
    registry = ModelRegistry(
        load_model_specs(settings.models_config_path),
        loader_fn=load_yolo_model,
        cache_size=settings.model_cache_size,
    )
    template_store = TemplateStore(load_template_specs(settings.templates_config_path))
    executor = InferenceExecutor(
        max_workers=settings.max_workers,
        max_queue=settings.max_queue,
        timeout_s=settings.request_timeout_s,
    )
    recognizers: dict[Method, object] = {
        "ocr": OcrRecognizer(settings=settings),
        "yolo": YoloRecognizer(registry=registry),
        "template": TemplateRecognizer(store=template_store),
    }
    return AppContext(settings, registry, template_store, executor, recognizers)
