"""请求/响应与统一结果数据模型(pydantic v2)。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

Method = Literal["ocr", "yolo", "template"]


class ImageInput(BaseModel):
    """图片输入：base64 和 path 二选一。"""

    base64: str | None = Field(default=None, description="图片的 base64 编码字符串")
    path: str | None = Field(default=None, description="服务器上的图片文件路径")

    @model_validator(mode="after")
    def _exactly_one(self) -> ImageInput:
        provided = [v for v in (self.base64, self.path) if v]
        if len(provided) != 1:
            raise ValueError("image 必须且只能提供 base64 或 path 之一")
        return self


class ROI(BaseModel):
    """感兴趣区域：只识别图片中的这个矩形范围，返回的坐标会自动换算回原图。"""

    x: int = Field(ge=0, description="左上角 x 坐标（像素）")
    y: int = Field(ge=0, description="左上角 y 坐标（像素）")
    w: int = Field(gt=0, description="宽度（像素）")
    h: int = Field(gt=0, description="高度（像素）")


class RecognizeRequest(BaseModel):
    """识别请求：传图片 + 选择识别方式。"""

    image: ImageInput = Field(description="要识别的图片")
    methods: list[Method] = Field(
        min_length=1, description='识别方式列表，可选 "ocr"、"yolo"、"template"'
    )
    model: str | None = Field(default=None, description="YOLO 模型名（用 yolo 时必填）")
    templates: list[str] | None = Field(
        default=None, description="模板名列表（用 template 时必填）"
    )
    conf_threshold: float | None = Field(
        default=None, ge=0.0, le=1.0, description="置信度门槛 0~1，只返回高于此值的结果"
    )
    roi: ROI | None = Field(default=None, description="只识别图片中的这个区域")
    debug: bool = Field(default=False, description="设为 true 时额外返回标注了结果的图片")
    cache: Literal["auto", "refresh", "off"] = Field(
        default="auto", description="缓存行为：auto=自动读写、refresh=强制重新计算、off=不用缓存"
    )
    merge: Literal["none", "priority", "dedup", "concat"] = Field(
        default="none",
        description="多方式合并策略：none=分开返回、priority=按顺序取首个命中、"
        "dedup=合并去重、concat=全部合在一起排序",
    )

    @model_validator(mode="after")
    def _method_requirements(self) -> RecognizeRequest:
        if "yolo" in self.methods and not self.model:
            raise ValueError("methods 含 yolo 时必须提供 model")
        if "template" in self.methods and not self.templates:
            raise ValueError("methods 含 template 时必须提供 templates")
        return self


class DetectRequest(BaseModel):
    """单方式目标检测请求：客户端无需传 methods,路由内部固定为 yolo。"""

    image: ImageInput = Field(description="要识别的图片")
    model: str = Field(min_length=1, description="YOLO 模型名")
    conf_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="置信度门槛 0~1")
    roi: ROI | None = Field(default=None, description="只识别图片中的这个区域")
    debug: bool = Field(default=False, description="设为 true 时额外返回标注图")
    cache: Literal["auto", "refresh", "off"] = Field(
        default="auto", description="缓存行为：auto/refresh/off"
    )

    def to_recognize_request(self) -> RecognizeRequest:
        return RecognizeRequest(
            image=self.image,
            methods=["yolo"],
            model=self.model,
            conf_threshold=self.conf_threshold,
            roi=self.roi,
            debug=self.debug,
            cache=self.cache,
        )


class MatchRequest(BaseModel):
    """单方式模板匹配请求：客户端无需传 methods,路由内部固定为 template。"""

    image: ImageInput = Field(description="要识别的图片")
    templates: list[str] = Field(min_length=1, description="模板名列表")
    conf_threshold: float | None = Field(default=None, ge=0.0, le=1.0, description="置信度门槛 0~1")
    roi: ROI | None = Field(default=None, description="只识别图片中的这个区域")
    debug: bool = Field(default=False, description="设为 true 时额外返回标注图")
    cache: Literal["auto", "refresh", "off"] = Field(
        default="auto", description="缓存行为：auto/refresh/off"
    )

    def to_recognize_request(self) -> RecognizeRequest:
        return RecognizeRequest(
            image=self.image,
            methods=["template"],
            templates=self.templates,
            conf_threshold=self.conf_threshold,
            roi=self.roi,
            debug=self.debug,
            cache=self.cache,
        )


class Detection(BaseModel):
    """单个检测结果。"""

    source: Method = Field(description="来自哪种识别方式")
    label: str | None = Field(default=None, description="类别名或模板名（OCR 时为空）")
    text: str | None = Field(default=None, description="识别出的文字（非 OCR 时为空）")
    confidence: float = Field(description="置信度 0~1，越高越有把握")
    bbox: list[float] = Field(description="目标框 [左上x, 左上y, 右下x, 右下y]（像素）")
    center: list[float] = Field(description="中心点坐标 [x, y]（像素）—— 点击用这个")
    bbox_norm: list[float] = Field(description="归一化目标框（0~1，跨分辨率适配用）")
    center_norm: list[float] = Field(description="归一化中心点（0~1）")


class MethodResult(BaseModel):
    """某种识别方式的结果。"""

    detections: list[Detection] = Field(default_factory=list, description="检测结果列表")
    model_version: str | None = Field(default=None, description="使用的模型版本")
    template_versions: dict[str, str] | None = Field(default=None, description="使用的模板版本")
    elapsed_ms: float = Field(default=0.0, description="该方式耗时（毫秒）")


class RecognizeResponse(BaseModel):
    """识别响应。"""

    request_id: str = Field(description="本次请求的唯一编号")
    image_size: list[int] = Field(description="原图尺寸 [宽, 高]（像素）")
    method_results: dict[Method, MethodResult] = Field(
        default_factory=dict, description="各方式的识别结果"
    )
    debug_image: str | None = Field(default=None, description="标注图的 base64（debug=true 时）")
    from_cache: bool = Field(default=False, description="本次结果是否来自缓存")
    merged: list[Detection] | None = Field(
        default=None, description="合并后的统一结果列表（用了 merge 时）"
    )


class ErrorResponse(BaseModel):
    """错误响应。"""

    request_id: str = Field(description="本次请求的唯一编号")
    error_code: str = Field(description="错误码，如 INVALID_IMAGE、MODEL_NOT_FOUND")
    message: str = Field(description="错误描述（中文）")
    details: dict | None = Field(default=None, description="补充信息")  # type: ignore[type-arg]
