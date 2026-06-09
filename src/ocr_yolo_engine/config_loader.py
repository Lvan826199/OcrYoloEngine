"""从 yaml 读取模型/模板规格。"""

from __future__ import annotations

import logging
import os

import yaml

from ocr_yolo_engine.models.registry import ModelSpec
from ocr_yolo_engine.templates.store import TemplateSpec

logger = logging.getLogger(__name__)


def _resolve_config_path(path: str) -> str | None:
    """解析配置文件路径:实际文件优先,不存在则回退到 `<path>.example` 模板。

    设计意图:实际配置文件(如 configs/models.yaml)不入库、由用户复制 .example
    后自行维护;若用户尚未复制,则回退读取入库的 .example,保证开箱即用。
    两者都不存在时返回 None(视为无配置,服务照常启动但无内置资产)。
    """
    if os.path.isfile(path):
        return path
    example = f"{path}.example"
    if os.path.isfile(example):
        logger.info("配置文件 %s 不存在,回退使用示例模板 %s", path, example)
        return example
    return None


def load_model_specs(path: str) -> dict[str, ModelSpec]:
    resolved = _resolve_config_path(path)
    if resolved is None:
        return {}
    with open(resolved, encoding="utf-8") as fh:
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
    resolved = _resolve_config_path(path)
    if resolved is None:
        return {}
    with open(resolved, encoding="utf-8") as fh:
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
