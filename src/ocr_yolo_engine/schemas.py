"""请求/响应与统一结果数据模型(pydantic v2)。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Method = Literal["ocr", "yolo", "template"]


class ImageInput(BaseModel):
    base64: str | None = None
    path: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> ImageInput:
        provided = [v for v in (self.base64, self.path) if v]
        if len(provided) != 1:
            raise ValueError("image 必须且只能提供 base64 或 path 之一")
        return self


class ROI(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(gt=0)
    h: int = Field(gt=0)


class RecognizeRequest(BaseModel):
    image: ImageInput
    methods: list[Method] = Field(min_length=1)
    model: str | None = None
    templates: list[str] | None = None
    conf_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    roi: ROI | None = None
    debug: bool = False

    @model_validator(mode="after")
    def _method_requirements(self) -> RecognizeRequest:
        if "yolo" in self.methods and not self.model:
            raise ValueError("methods 含 yolo 时必须提供 model")
        if "template" in self.methods and not self.templates:
            raise ValueError("methods 含 template 时必须提供 templates")
        return self


class Detection(BaseModel):
    source: Method
    label: str | None = None
    text: str | None = None
    confidence: float
    bbox: list[float]
    center: list[float]
    bbox_norm: list[float]
    center_norm: list[float]


class MethodResult(BaseModel):
    detections: list[Detection] = Field(default_factory=list)
    model_version: str | None = None
    template_versions: dict[str, str] | None = None
    elapsed_ms: float = 0.0


class RecognizeResponse(BaseModel):
    request_id: str
    image_size: list[int]
    method_results: dict[Method, MethodResult] = Field(default_factory=dict)
    debug_image: str | None = None


class ErrorResponse(BaseModel):
    request_id: str
    error_code: str
    message: str
    details: dict | None = None  # type: ignore[type-arg]
