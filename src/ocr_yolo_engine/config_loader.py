"""从 yaml 读取模型/模板规格。"""

from __future__ import annotations

import os

import yaml

from ocr_yolo_engine.models.registry import ModelSpec
from ocr_yolo_engine.templates.store import TemplateSpec


def load_model_specs(path: str) -> dict[str, ModelSpec]:
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    out: dict[str, ModelSpec] = {}
    for name, cfg in (data.get("models") or {}).items():
        out[name] = ModelSpec(
            name=name,
            path=cfg["path"],
            version=str(cfg.get("version", "unknown")),
            classes={int(k): str(v) for k, v in (cfg.get("classes") or {}).items()},
        )
    return out


def load_template_specs(path: str) -> dict[str, TemplateSpec]:
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    out: dict[str, TemplateSpec] = {}
    for name, cfg in (data.get("templates") or {}).items():
        out[name] = TemplateSpec(
            name=name,
            path=cfg["path"],
            version=str(cfg.get("version", "unknown")),
            params=dict(cfg.get("params") or {}),
        )
    return out
