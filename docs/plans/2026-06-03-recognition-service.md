# OcrYoloEngine 视觉识别服务 实现计划

> **执行说明:** 按 TDD 逐任务实现本计划——每个任务「先写失败测试 → 跑红 → 最小实现 → 跑绿 → 提交」。步骤用复选框(`- [ ]`)标记完成进度。

**Goal:** 实现一个面向自动化测试的视觉识别 HTTP 服务,统一封装 OCR / YOLO / 模板匹配三种识别手段,只做推理、返回坐标与文字,不执行动作。

**Architecture:** 分层单体(FastAPI)。请求经鉴权 → 图片加载/校验 → 预处理(通道统一、ROI 裁剪) → 有界工作池(每模型锁 + 背压) → 识别器(从注册表/模板库取资产) → 坐标回映射 + 归一化 → 统一响应。重依赖懒加载;训练目录物理隔离;识别器抽象 + 依赖注入保证可测试。

**Tech Stack:** Python 3.11+、uv、pydantic v2 / pydantic-settings、FastAPI、numpy、opencv-python(模板匹配)、ultralytics(YOLO,懒加载)、PaddleOCR(OCR,懒加载)、pytest、ruff、mypy、pre-commit。

---

## 命名约定(全计划统一,后续任务必须一致)

| 符号 | 定义位置 | 说明 |
|---|---|---|
| 包名 `ocr_yolo_engine` | `src/` | src 布局 |
| `Method` | `schemas.py` | `Literal["ocr","yolo","template"]` |
| `Settings` / `get_settings()` | `settings.py` | env 前缀 `OYE_`,`get_settings` 带 lru_cache |
| `ErrorCode` / `EngineError` | `errors.py` | `.code/.message/.http_status/.details` |
| `ImageInput/ROI/RecognizeRequest/Detection/MethodResult/RecognizeResponse/ErrorResponse` | `schemas.py` | pydantic 模型 |
| `decode_image_bytes/load_from_base64/load_from_path` | `image/loader.py` | 返回 BGR `np.ndarray` |
| `to_rgb/enforce_limits/crop_roi/finalize_detections` | `preprocessing/pipeline.py` | 预处理纯函数 |
| `RawDetection/InferContext/Recognizer` | `recognizers/base.py` | 识别器抽象 |
| `ModelSpec/ModelRegistry` | `models/registry.py` | 懒加载 + LRU |
| `TemplateSpec/TemplateStore` | `templates/store.py` | 模板库 |
| `OcrRecognizer/YoloRecognizer/TemplateRecognizer` | `recognizers/*.py` | 三识别器 |
| `InferenceExecutor` | `concurrency/executor.py` | `submit(model_key, fn)`,过载抛 `EngineError(OVERLOADED)` |
| `setup_logging/bind_request_id/current_request_id` | `observability/logging.py` | 结构化日志 |
| `require_api_key` | `service/auth.py` | API Key 依赖 |
| `get_registry/get_template_store/get_executor/get_recognizers` | `service/deps.py` | DI 提供者 |

**坐标契约:** 识别器返回 `RawDetection`,其 `bbox` 是**基于输入识别器的那张图(可能是 ROI 裁剪图)**的像素坐标 `[x1,y1,x2,y2]`。`finalize_detections` 统一加 ROI 偏移、按全图尺寸归一化,产出最终 `Detection`。识别器内部**绝不**自己做偏移或归一化。

---

## File Structure（决策锁定）

每个文件单一职责,优先小而专注:

- `pyproject.toml` — 依赖/打包/extras/工具配置(ruff、mypy、pytest)
- `src/ocr_yolo_engine/settings.py` — 配置(pydantic-settings)
- `src/ocr_yolo_engine/errors.py` — 错误码 + 异常 + HTTP 映射
- `src/ocr_yolo_engine/schemas.py` — 请求/响应/Detection 数据模型
- `src/ocr_yolo_engine/image/loader.py` — 图片来源加载 + 解码
- `src/ocr_yolo_engine/preprocessing/pipeline.py` — 通道统一/上限/ROI/回映射
- `src/ocr_yolo_engine/recognizers/base.py` — Recognizer 抽象 + RawDetection + InferContext
- `src/ocr_yolo_engine/recognizers/template.py` — OpenCV 模板匹配(多尺度+NMS)
- `src/ocr_yolo_engine/recognizers/ocr.py` — PaddleOCR 封装(懒加载)
- `src/ocr_yolo_engine/recognizers/yolo.py` — ultralytics 封装(懒加载)
- `src/ocr_yolo_engine/models/registry.py` — 模型注册表(懒加载 + LRU + 版本)
- `src/ocr_yolo_engine/templates/store.py` — 模板库(加载 + 版本 + 缓存)
- `src/ocr_yolo_engine/concurrency/executor.py` — 有界工作池 + 每模型锁 + 背压
- `src/ocr_yolo_engine/observability/logging.py` — 结构化日志 + request_id
- `src/ocr_yolo_engine/service/{deps,auth,routes,app}.py` — DI/鉴权/路由/装配
- `src/ocr_yolo_engine/cli.py` — serve / infer
- `training/` — 隔离训练入口
- `docker/Dockerfile.{cpu,gpu}`、`configs/{models,templates}.yaml`
- `tests/{conftest.py,fakes,fixtures,unit,contract,smoke}`

---

## 阶段总览

- **阶段 0(任务 1–4):基础设施** — 工程脚手架、配置、错误、数据模型。无重依赖,纯可测。
- **阶段 1(任务 5–6):图像与预处理** — 加载/校验/通道统一/ROI 回映射。纯逻辑,golden 友好。
- **阶段 2(任务 7–12):识别器与资产** — 抽象基类、注册表、模板库、三识别器。
- **阶段 3(任务 13):并发与背压** — 有界池 + 模型锁 + 503。
- **阶段 4(任务 14):可观测性** — 结构化日志 + request_id。
- **阶段 5(任务 15–18):HTTP 服务** — DI/fakes、鉴权、路由、契约测试。
- **阶段 6(任务 19):CLI**。
- **阶段 7(任务 20–22):训练隔离、Docker/configs、质量门禁(pre-commit + golden/smoke 约定)**。

每个任务结束都 commit。提交信息用简体中文、遵循 Conventional Commits(见 CLAUDE.md)。

---

# 阶段 0:基础设施

## Task 1: 工程脚手架与工具链

**Files:**
- Create: `pyproject.toml`
- Create: `src/ocr_yolo_engine/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/unit/test_smoke_import.py`
- Modify: `.gitignore`(追加 `models_store/`、`.venv/`、`uv` 缓存、`__pycache__/` 等若缺失)

- [ ] **Step 1: 写 `pyproject.toml`**

```toml
[project]
name = "ocr-yolo-engine"
version = "0.1.0"
description = "面向自动化测试的视觉识别服务:OCR + YOLO + 模板匹配,只做推理返回坐标"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "vincent" }]
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "pydantic>=2.6",
    "pydantic-settings>=2.2",
    "numpy>=1.26",
    "opencv-python-headless>=4.9",
    "pyyaml>=6.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
# 重依赖按需安装;CPU/GPU 由各自包源区分(见 docker/ 与 README)
ocr = ["paddleocr>=2.7", "paddlepaddle>=2.6"]
yolo = ["ultralytics>=8.1"]
dev = ["pytest>=8.0", "pytest-cov>=5.0", "httpx>=0.27", "ruff>=0.4", "mypy>=1.10", "pre-commit>=3.7", "types-PyYAML"]

[project.scripts]
ocr-yolo = "ocr_yolo_engine.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ocr_yolo_engine"]

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "W"]

[tool.mypy]
python_version = "3.11"
packages = ["ocr_yolo_engine"]
mypy_path = "src"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "smoke: 需要加载真实模型的端到端冒烟测试(默认不在 CI 跑)",
]
addopts = "-m 'not smoke'"
pythonpath = ["src"]
```

- [ ] **Step 2: 建包占位**

`src/ocr_yolo_engine/__init__.py`:

```python
"""OcrYoloEngine:面向自动化测试的视觉识别服务。"""

__version__ = "0.1.0"
```

`tests/__init__.py`、`tests/unit/__init__.py` 写入空内容(各一行注释即可):

```python
# 测试包
```

- [ ] **Step 3: 写最小失败测试**

`tests/unit/test_smoke_import.py`:

```python
def test_package_imports_and_exposes_version():
    import ocr_yolo_engine

    assert ocr_yolo_engine.__version__ == "0.1.0"
```

- [ ] **Step 4: 同步环境并运行测试**

Run:
```bash
cd /home/work2/MyProject/OcrYoloEngine
uv sync --extra dev
uv run pytest tests/unit/test_smoke_import.py -v
```
Expected: PASS（1 passed）。若 `uv` 未安装,先 `curl -LsSf https://astral.sh/uv/install.sh | sh`。

- [ ] **Step 5: 补 `.gitignore`(若缺项)**

确保包含以下行(已有则跳过):
```
.venv/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
models_store/
uv.lock
```
> 说明:`uv.lock` 首版先不纳管(避免锁文件在多人/多平台抖动);若团队决定锁版本,可后续移除该行并提交锁文件。

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src tests .gitignore
git commit -m "build: 初始化 Python 工程脚手架与工具链"
```

---

## Task 2: 配置 `settings.py`

**Files:**
- Create: `src/ocr_yolo_engine/settings.py`
- Test: `tests/unit/test_settings.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_settings.py`:

```python
from ocr_yolo_engine.settings import Settings


def test_defaults_match_spec():
    s = Settings()
    assert s.device == "auto"
    assert s.default_conf_threshold == 0.25
    assert s.model_cache_size == 3
    assert s.max_workers == 4
    assert s.max_queue == 32
    assert s.request_timeout_s == 30
    assert s.max_image_bytes == 10 * 1024 * 1024
    assert s.max_image_pixels == 4096 * 4096
    assert s.allowed_path_roots == []
    assert s.api_keys == []
    assert s.warmup is True


def test_env_override(monkeypatch):
    monkeypatch.setenv("OYE_DEVICE", "cpu")
    monkeypatch.setenv("OYE_MAX_WORKERS", "8")
    monkeypatch.setenv("OYE_API_KEYS", '["k1","k2"]')
    s = Settings()
    assert s.device == "cpu"
    assert s.max_workers == 8
    assert s.api_keys == ["k1", "k2"]


def test_auth_enabled_flag():
    assert Settings(api_keys=[]).auth_enabled is False
    assert Settings(api_keys=["k1"]).auth_enabled is True
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_settings.py -v`
Expected: FAIL（`ModuleNotFoundError: ocr_yolo_engine.settings`）。

- [ ] **Step 3: 实现 `settings.py`**

```python
"""集中配置:环境变量(前缀 OYE_)+ 默认值。"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Device = Literal["auto", "cpu", "cuda"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OYE_", env_file=".env", extra="ignore")

    device: Device = "auto"
    default_conf_threshold: float = 0.25

    models_config_path: str = "configs/models.yaml"
    templates_config_path: str = "configs/templates.yaml"

    model_cache_size: int = 3
    max_workers: int = 4
    max_queue: int = 32
    request_timeout_s: int = 30

    max_image_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 4096 * 4096

    allowed_path_roots: list[str] = Field(default_factory=list)
    api_keys: list[str] = Field(default_factory=list)
    warmup: bool = True

    @property
    def auth_enabled(self) -> bool:
        return len(self.api_keys) > 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_settings.py -v`
Expected: PASS（3 passed）。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/settings.py tests/unit/test_settings.py
git commit -m "feat(settings): 新增集中配置与环境变量覆盖"
```

---

## Task 3: 错误契约 `errors.py`

**Files:**
- Create: `src/ocr_yolo_engine/errors.py`
- Test: `tests/unit/test_errors.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_errors.py`:

```python
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode


def test_engine_error_carries_code_and_status():
    err = EngineError(ErrorCode.MODEL_NOT_FOUND, "模型 abc 不存在", details={"model": "abc"})
    assert err.code is ErrorCode.MODEL_NOT_FOUND
    assert err.http_status == 404
    assert err.details == {"model": "abc"}
    assert "abc" in str(err)


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (ErrorCode.INVALID_IMAGE, 400),
        (ErrorCode.IMAGE_TOO_LARGE, 413),
        (ErrorCode.PATH_NOT_ALLOWED, 403),
        (ErrorCode.MODEL_NOT_FOUND, 404),
        (ErrorCode.TEMPLATE_NOT_FOUND, 404),
        (ErrorCode.OVERLOADED, 503),
        (ErrorCode.TIMEOUT, 504),
        (ErrorCode.INTERNAL, 500),
    ],
)
def test_status_mapping(code, status):
    assert EngineError(code, "x").http_status == status


def test_to_response_body():
    body = EngineError(ErrorCode.INVALID_IMAGE, "坏图", details={"k": 1}).to_body("req-1")
    assert body == {
        "request_id": "req-1",
        "error_code": "INVALID_IMAGE",
        "message": "坏图",
        "details": {"k": 1},
    }
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_errors.py -v`
Expected: FAIL（导入错误）。

- [ ] **Step 3: 实现 `errors.py`**

```python
"""统一错误码、异常与 HTTP 映射。"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    INVALID_IMAGE = "INVALID_IMAGE"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    TEMPLATE_NOT_FOUND = "TEMPLATE_NOT_FOUND"
    OVERLOADED = "OVERLOADED"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


_STATUS: dict[ErrorCode, int] = {
    ErrorCode.INVALID_IMAGE: 400,
    ErrorCode.IMAGE_TOO_LARGE: 413,
    ErrorCode.PATH_NOT_ALLOWED: 403,
    ErrorCode.MODEL_NOT_FOUND: 404,
    ErrorCode.TEMPLATE_NOT_FOUND: 404,
    ErrorCode.OVERLOADED: 503,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.INTERNAL: 500,
}


class EngineError(Exception):
    """业务异常:携带错误码、可读信息与结构化细节。"""

    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    @property
    def http_status(self) -> int:
        return _STATUS[self.code]

    def to_body(self, request_id: str) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "error_code": self.code.value,
            "message": self.message,
            "details": self.details,
        }
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_errors.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/errors.py tests/unit/test_errors.py
git commit -m "feat(errors): 新增统一错误码与异常 HTTP 映射"
```

---

## Task 4: 数据模型 `schemas.py`

**Files:**
- Create: `src/ocr_yolo_engine/schemas.py`
- Test: `tests/unit/test_schemas.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError

from ocr_yolo_engine.schemas import (
    Detection,
    ImageInput,
    RecognizeRequest,
    RecognizeResponse,
    ROI,
)


def test_image_input_requires_exactly_one_source():
    ImageInput(base64="abc")
    ImageInput(path="/a/b.png")
    with pytest.raises(ValidationError):
        ImageInput()
    with pytest.raises(ValidationError):
        ImageInput(base64="abc", path="/a/b.png")


def test_recognize_request_yolo_requires_model():
    with pytest.raises(ValidationError):
        RecognizeRequest(image=ImageInput(base64="x"), methods=["yolo"])
    req = RecognizeRequest(image=ImageInput(base64="x"), methods=["yolo"], model="game_a")
    assert req.model == "game_a"


def test_recognize_request_template_requires_templates():
    with pytest.raises(ValidationError):
        RecognizeRequest(image=ImageInput(base64="x"), methods=["template"])
    req = RecognizeRequest(
        image=ImageInput(base64="x"), methods=["template"], templates=["settings_icon"]
    )
    assert req.templates == ["settings_icon"]


def test_roi_validation():
    ROI(x=0, y=0, w=10, h=10)
    with pytest.raises(ValidationError):
        ROI(x=0, y=0, w=0, h=10)


def test_detection_roundtrip():
    d = Detection(
        source="yolo",
        label="cat",
        text=None,
        confidence=0.9,
        bbox=[1, 2, 3, 4],
        center=[2, 3],
        bbox_norm=[0.1, 0.2, 0.3, 0.4],
        center_norm=[0.2, 0.3],
    )
    assert d.model_dump()["source"] == "yolo"


def test_response_builds():
    resp = RecognizeResponse(
        request_id="r1", image_size=[100, 200], method_results={}, debug_image=None
    )
    assert resp.image_size == [100, 200]
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_schemas.py -v`
Expected: FAIL（导入错误）。

- [ ] **Step 3: 实现 `schemas.py`**

```python
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
    bbox: list[float]          # [x1,y1,x2,y2] 全图原始像素
    center: list[float]        # [cx,cy] 全图原始像素
    bbox_norm: list[float]     # 归一化 [x1,y1,x2,y2]
    center_norm: list[float]   # 归一化 [cx,cy]


class MethodResult(BaseModel):
    detections: list[Detection] = Field(default_factory=list)
    model_version: str | None = None
    template_versions: dict[str, str] | None = None
    elapsed_ms: float = 0.0


class RecognizeResponse(BaseModel):
    request_id: str
    image_size: list[int]      # [width, height]
    method_results: dict[Method, MethodResult] = Field(default_factory=dict)
    debug_image: str | None = None


class ErrorResponse(BaseModel):
    request_id: str
    error_code: str
    message: str
    details: dict | None = None
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_schemas.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/schemas.py tests/unit/test_schemas.py
git commit -m "feat(schemas): 新增请求响应与统一 Detection 数据模型"
```

---

# 阶段 1:图像与预处理

## Task 5: 图片加载 `image/loader.py`

**Files:**
- Create: `src/ocr_yolo_engine/image/__init__.py`
- Create: `src/ocr_yolo_engine/image/loader.py`
- Test: `tests/unit/test_loader.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_loader.py`:

```python
import base64

import cv2
import numpy as np
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.image.loader import decode_image_bytes, load_from_base64, load_from_path


def _png_bytes(w=4, h=3):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:, :, 2] = 255  # BGR 红
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_decode_valid_png_returns_bgr_ndarray():
    img = decode_image_bytes(_png_bytes())
    assert img.shape == (3, 4, 3)
    assert img.dtype == np.uint8


def test_decode_garbage_raises_invalid_image():
    with pytest.raises(EngineError) as ei:
        decode_image_bytes(b"not-an-image")
    assert ei.value.code is ErrorCode.INVALID_IMAGE


def test_load_from_base64():
    b64 = base64.b64encode(_png_bytes()).decode()
    img = load_from_base64(b64)
    assert img.shape == (3, 4, 3)


def test_load_from_base64_with_data_uri_prefix():
    b64 = "data:image/png;base64," + base64.b64encode(_png_bytes()).decode()
    img = load_from_base64(b64)
    assert img.shape == (3, 4, 3)


def test_load_from_path_inside_whitelist(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes())
    img = load_from_path(str(p), allowed_roots=[str(tmp_path)])
    assert img.shape == (3, 4, 3)


def test_load_from_path_traversal_blocked(tmp_path):
    outside = tmp_path / "secret.png"
    outside.write_bytes(_png_bytes())
    root = tmp_path / "allowed"
    root.mkdir()
    sneaky = str(root / ".." / "secret.png")
    with pytest.raises(EngineError) as ei:
        load_from_path(sneaky, allowed_roots=[str(root)])
    assert ei.value.code is ErrorCode.PATH_NOT_ALLOWED


def test_load_from_path_empty_whitelist_blocks_all(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(_png_bytes())
    with pytest.raises(EngineError) as ei:
        load_from_path(str(p), allowed_roots=[])
    assert ei.value.code is ErrorCode.PATH_NOT_ALLOWED
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_loader.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `image/loader.py`**

`src/ocr_yolo_engine/image/__init__.py`:
```python
# 图像加载子包
```

`src/ocr_yolo_engine/image/loader.py`:
```python
"""图片来源加载与解码:base64 / 本地路径(白名单) / 原始字节。"""

from __future__ import annotations

import base64
import binascii
import os

import cv2
import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode


def decode_image_bytes(data: bytes) -> np.ndarray:
    """把图片字节解码为 BGR ndarray;失败抛 INVALID_IMAGE。"""
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise EngineError(ErrorCode.INVALID_IMAGE, "无法解码为图片")
    return img


def load_from_base64(b64: str) -> np.ndarray:
    payload = b64.split(",", 1)[1] if b64.startswith("data:") else b64
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EngineError(ErrorCode.INVALID_IMAGE, "base64 解码失败") from exc
    return decode_image_bytes(data)


def load_from_path(path: str, allowed_roots: list[str]) -> np.ndarray:
    real = os.path.realpath(path)
    roots = [os.path.realpath(r) for r in allowed_roots]
    if not any(real == r or real.startswith(r + os.sep) for r in roots):
        raise EngineError(
            ErrorCode.PATH_NOT_ALLOWED,
            "路径不在允许的根目录白名单内",
            details={"path": path},
        )
    if not os.path.isfile(real):
        raise EngineError(ErrorCode.INVALID_IMAGE, "文件不存在", details={"path": path})
    with open(real, "rb") as fh:
        return decode_image_bytes(fh.read())
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_loader.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/image tests/unit/test_loader.py
git commit -m "feat(image): 新增图片加载与路径白名单防穿越"
```

---

## Task 6: 预处理 `preprocessing/pipeline.py`

**Files:**
- Create: `src/ocr_yolo_engine/preprocessing/__init__.py`
- Create: `src/ocr_yolo_engine/preprocessing/pipeline.py`
- Test: `tests/unit/test_preprocessing.py`

> 依赖 `RawDetection`(在 Task 7 的 `recognizers/base.py` 定义)。为避免循环依赖且让本任务独立可测,`RawDetection` 在 Task 7 才落地,但本任务的 `finalize_detections` **只读取 `raw.bbox/confidence/label/text/source` 字段**。本任务测试用一个等价的本地轻量 stub 表示 raw(用 `types.SimpleNamespace`),Task 7 落地后字段一致即可。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_preprocessing.py`:

```python
from types import SimpleNamespace

import numpy as np
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.preprocessing.pipeline import (
    crop_roi,
    enforce_limits,
    finalize_detections,
    to_rgb,
)
from ocr_yolo_engine.schemas import ROI


def test_to_rgb_swaps_channels():
    bgr = np.zeros((1, 1, 3), dtype=np.uint8)
    bgr[0, 0] = [10, 20, 30]  # B,G,R
    rgb = to_rgb(bgr)
    assert list(rgb[0, 0]) == [30, 20, 10]


def test_enforce_limits_bytes():
    img = np.zeros((2, 2, 3), dtype=np.uint8)
    with pytest.raises(EngineError) as ei:
        enforce_limits(b"x" * 100, img, max_bytes=10, max_pixels=10_000)
    assert ei.value.code is ErrorCode.IMAGE_TOO_LARGE


def test_enforce_limits_pixels():
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    with pytest.raises(EngineError) as ei:
        enforce_limits(b"x", img, max_bytes=10_000, max_pixels=100)
    assert ei.value.code is ErrorCode.IMAGE_TOO_LARGE


def test_enforce_limits_ok():
    img = np.zeros((5, 5, 3), dtype=np.uint8)
    enforce_limits(b"x" * 5, img, max_bytes=10, max_pixels=100)  # 不抛即通过


def test_crop_roi_returns_cropped_and_offset():
    img = np.arange(100 * 100 * 3, dtype=np.uint8).reshape(100, 100, 3)
    roi = ROI(x=10, y=20, w=30, h=40)
    cropped, offset = crop_roi(img, roi)
    assert cropped.shape == (40, 30, 3)
    assert offset == (10, 20)


def test_crop_roi_out_of_bounds_raises():
    img = np.zeros((50, 50, 3), dtype=np.uint8)
    with pytest.raises(EngineError) as ei:
        crop_roi(img, ROI(x=40, y=40, w=20, h=20))
    assert ei.value.code is ErrorCode.INVALID_IMAGE


def test_crop_roi_none_returns_full_and_zero_offset():
    img = np.zeros((50, 60, 3), dtype=np.uint8)
    cropped, offset = crop_roi(img, None)
    assert cropped.shape == (50, 60, 3)
    assert offset == (0, 0)


def test_finalize_applies_offset_and_normalizes():
    raw = SimpleNamespace(
        source="yolo", label="cat", text=None, confidence=0.8, bbox=[10.0, 20.0, 30.0, 40.0]
    )
    dets = finalize_detections([raw], offset=(100, 200), full_w=400, full_h=400)
    d = dets[0]
    assert d.bbox == [110.0, 220.0, 130.0, 240.0]
    assert d.center == [120.0, 230.0]
    assert d.bbox_norm == [110 / 400, 220 / 400, 130 / 400, 240 / 400]
    assert d.center_norm == [120 / 400, 230 / 400]
    assert d.source == "yolo"
    assert d.label == "cat"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_preprocessing.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `preprocessing/pipeline.py`**

`src/ocr_yolo_engine/preprocessing/__init__.py`:
```python
# 预处理子包
```

`src/ocr_yolo_engine/preprocessing/pipeline.py`:
```python
"""预处理:通道统一、输入上限校验、ROI 裁剪与坐标回映射。"""

from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.schemas import ROI, Detection, Method


class _RawLike(Protocol):
    source: Method
    label: str | None
    text: str | None
    confidence: float
    bbox: list[float]


def to_rgb(bgr: np.ndarray) -> np.ndarray:
    """BGR → RGB,内部统一以 RGB 流转。"""
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def enforce_limits(raw_bytes: bytes, image: np.ndarray, *, max_bytes: int, max_pixels: int) -> None:
    if len(raw_bytes) > max_bytes:
        raise EngineError(
            ErrorCode.IMAGE_TOO_LARGE,
            "图片字节数超过上限",
            details={"bytes": len(raw_bytes), "max_bytes": max_bytes},
        )
    h, w = image.shape[:2]
    if w * h > max_pixels:
        raise EngineError(
            ErrorCode.IMAGE_TOO_LARGE,
            "图片分辨率超过上限",
            details={"pixels": w * h, "max_pixels": max_pixels},
        )


def crop_roi(image: np.ndarray, roi: ROI | None) -> tuple[np.ndarray, tuple[int, int]]:
    """按 ROI 裁剪;返回(裁剪图, (offset_x, offset_y))。roi 为 None 返回全图。"""
    if roi is None:
        return image, (0, 0)
    h, w = image.shape[:2]
    if roi.x + roi.w > w or roi.y + roi.h > h:
        raise EngineError(
            ErrorCode.INVALID_IMAGE,
            "ROI 超出图片边界",
            details={"roi": roi.model_dump(), "image": [w, h]},
        )
    cropped = image[roi.y : roi.y + roi.h, roi.x : roi.x + roi.w]
    return cropped, (roi.x, roi.y)


def finalize_detections(
    raws: list[_RawLike], *, offset: tuple[int, int], full_w: int, full_h: int
) -> list[Detection]:
    """把识别器原始结果加偏移回映射到全图,并计算归一化坐标。"""
    ox, oy = offset
    out: list[Detection] = []
    for r in raws:
        x1, y1, x2, y2 = r.bbox
        x1 += ox
        y1 += oy
        x2 += ox
        y2 += oy
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        out.append(
            Detection(
                source=r.source,
                label=r.label,
                text=r.text,
                confidence=r.confidence,
                bbox=[x1, y1, x2, y2],
                center=[cx, cy],
                bbox_norm=[x1 / full_w, y1 / full_h, x2 / full_w, y2 / full_h],
                center_norm=[cx / full_w, cy / full_h],
            )
        )
    return out
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_preprocessing.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/preprocessing tests/unit/test_preprocessing.py
git commit -m "feat(preprocessing): 新增通道统一/上限校验/ROI 回映射"
```

---

# 阶段 2:识别器与资产

## Task 7: 识别器抽象 `recognizers/base.py`

**Files:**
- Create: `src/ocr_yolo_engine/recognizers/__init__.py`
- Create: `src/ocr_yolo_engine/recognizers/base.py`
- Test: `tests/unit/test_recognizer_base.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_recognizer_base.py`:

```python
import numpy as np
import pytest

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection, Recognizer


def test_rawdetection_fields():
    r = RawDetection(source="ocr", label=None, text="hi", confidence=0.7, bbox=[0, 0, 5, 5])
    assert r.source == "ocr"
    assert r.text == "hi"
    assert r.bbox == [0, 0, 5, 5]


def test_recognizer_is_abstract():
    with pytest.raises(TypeError):
        Recognizer()  # 抽象类不可实例化


def test_concrete_recognizer_runs():
    class Echo(Recognizer):
        def infer(self, image, ctx):
            return [RawDetection(source="ocr", label=None, text="x", confidence=1.0, bbox=[0, 0, 1, 1])]

    out = Echo().infer(np.zeros((2, 2, 3), dtype=np.uint8), InferContext(conf_threshold=0.25))
    assert out[0].text == "x"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_recognizer_base.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `recognizers/base.py`**

`src/ocr_yolo_engine/recognizers/__init__.py`:
```python
# 识别器子包
```

`src/ocr_yolo_engine/recognizers/base.py`:
```python
"""识别器统一抽象与原始结果结构。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np

from ocr_yolo_engine.schemas import Method


@dataclass
class RawDetection:
    """识别器原始输出:bbox 基于传入识别器的那张图(可能是 ROI 裁剪图)。"""

    source: Method
    label: str | None
    text: str | None
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


@dataclass
class InferContext:
    """单次推理上下文。"""

    conf_threshold: float
    model: str | None = None
    templates: list[str] = field(default_factory=list)


class Recognizer(ABC):
    """所有识别器的统一契约:吃预处理图 + 上下文,吐 RawDetection。"""

    @abstractmethod
    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        """坐标基于输入图,偏移与归一化由上层 finalize_detections 完成。"""
        raise NotImplementedError
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_recognizer_base.py -v`
Expected: PASS。

- [ ] **Step 5: 回归预处理测试(确认字段契约一致)**

Run: `uv run pytest tests/unit/test_preprocessing.py tests/unit/test_recognizer_base.py -v`
Expected: 全部 PASS（`RawDetection` 与 `finalize_detections` 读取字段一致)。

- [ ] **Step 6: Commit**

```bash
git add src/ocr_yolo_engine/recognizers/__init__.py src/ocr_yolo_engine/recognizers/base.py tests/unit/test_recognizer_base.py
git commit -m "feat(recognizers): 新增识别器抽象基类与原始结果结构"
```

---

## Task 8: 模型注册表 `models/registry.py`

**Files:**
- Create: `src/ocr_yolo_engine/models/__init__.py`
- Create: `src/ocr_yolo_engine/models/registry.py`
- Test: `tests/unit/test_registry.py`

设计:`ModelRegistry` 从 yaml 读 `ModelSpec`;真正加载模型对象由注入的 `loader_fn(spec) -> Any` 完成(测试注入假 loader,生产注入 ultralytics 加载)。`get(name)` 懒加载并缓存,超过 `cache_size` 按 LRU 淘汰;`unload/reload`;线程安全。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_registry.py`:

```python
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec


def _specs():
    return {
        "a": ModelSpec(name="a", path="a.pt", version="v1", classes={0: "cat"}),
        "b": ModelSpec(name="b", path="b.pt", version="v1", classes={0: "dog"}),
        "c": ModelSpec(name="c", path="c.pt", version="v1", classes={}),
    }


def test_get_lazy_loads_and_caches():
    calls = []
    reg = ModelRegistry(_specs(), loader_fn=lambda s: calls.append(s.name) or f"obj-{s.name}", cache_size=3)
    assert reg.get("a") == "obj-a"
    assert reg.get("a") == "obj-a"
    assert calls == ["a"]  # 只加载一次


def test_get_unknown_raises():
    reg = ModelRegistry(_specs(), loader_fn=lambda s: object(), cache_size=3)
    with pytest.raises(EngineError) as ei:
        reg.get("zzz")
    assert ei.value.code is ErrorCode.MODEL_NOT_FOUND


def test_lru_eviction():
    loaded = []
    reg = ModelRegistry(_specs(), loader_fn=lambda s: loaded.append(s.name) or s.name, cache_size=2)
    reg.get("a")
    reg.get("b")
    reg.get("a")  # a 变最近使用
    reg.get("c")  # 淘汰最久未用的 b
    assert "b" not in reg.loaded_names()
    assert set(reg.loaded_names()) == {"a", "c"}


def test_unload_and_reload():
    loaded = []
    reg = ModelRegistry(_specs(), loader_fn=lambda s: loaded.append(s.name) or s.name, cache_size=3)
    reg.get("a")
    reg.unload("a")
    assert "a" not in reg.loaded_names()
    reg.get("a")  # 重新加载
    assert loaded == ["a", "a"]


def test_spec_version_lookup():
    reg = ModelRegistry(_specs(), loader_fn=lambda s: s.name, cache_size=3)
    assert reg.spec("a").version == "v1"
    assert reg.list_models() == ["a", "b", "c"]
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `models/registry.py`**

`src/ocr_yolo_engine/models/__init__.py`:
```python
# 模型资产子包
```

`src/ocr_yolo_engine/models/registry.py`:
```python
"""模型注册表:从配置读规格,懒加载 + LRU 缓存 + 卸载/重载,线程安全。"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ocr_yolo_engine.errors import EngineError, ErrorCode


@dataclass
class ModelSpec:
    name: str
    path: str
    version: str
    classes: dict[int, str] = field(default_factory=dict)


class ModelRegistry:
    def __init__(
        self,
        specs: dict[str, ModelSpec],
        loader_fn: Callable[[ModelSpec], Any],
        cache_size: int,
    ) -> None:
        self._specs = specs
        self._loader = loader_fn
        self._cache_size = cache_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()

    def spec(self, name: str) -> ModelSpec:
        if name not in self._specs:
            raise EngineError(ErrorCode.MODEL_NOT_FOUND, f"模型 {name} 未注册", details={"model": name})
        return self._specs[name]

    def list_models(self) -> list[str]:
        return list(self._specs.keys())

    def loaded_names(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())

    def get(self, name: str) -> Any:
        spec = self.spec(name)
        with self._lock:
            if name in self._cache:
                self._cache.move_to_end(name)
                return self._cache[name]
            obj = self._loader(spec)
            self._cache[name] = obj
            self._cache.move_to_end(name)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
            return obj

    def unload(self, name: str) -> None:
        with self._lock:
            self._cache.pop(name, None)

    def reload(self, name: str) -> Any:
        self.unload(name)
        return self.get(name)
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_registry.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/models tests/unit/test_registry.py
git commit -m "feat(models): 新增模型注册表(懒加载+LRU+卸载重载)"
```

---

## Task 9: 模板库 `templates/store.py`

**Files:**
- Create: `src/ocr_yolo_engine/templates/__init__.py`
- Create: `src/ocr_yolo_engine/templates/store.py`
- Test: `tests/unit/test_template_store.py`

- [ ] **Step 1: 写失败测试**

`tests/unit/test_template_store.py`:

```python
import cv2
import numpy as np
import pytest

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore


def _write_png(path, w=6, h=6):
    cv2.imwrite(str(path), np.zeros((h, w, 3), dtype=np.uint8))


def test_get_loads_and_caches(tmp_path):
    p = tmp_path / "icon.png"
    _write_png(p)
    specs = {"icon": TemplateSpec(name="icon", path=str(p), version="v1", params={"threshold": 0.8})}
    store = TemplateStore(specs)
    img1 = store.get_image("icon")
    img2 = store.get_image("icon")
    assert img1 is img2  # 命中缓存,同一对象
    assert img1.shape == (6, 6, 3)


def test_get_unknown_raises(tmp_path):
    store = TemplateStore({})
    with pytest.raises(EngineError) as ei:
        store.get_image("nope")
    assert ei.value.code is ErrorCode.TEMPLATE_NOT_FOUND


def test_spec_and_versions(tmp_path):
    p = tmp_path / "icon.png"
    _write_png(p)
    specs = {"icon": TemplateSpec(name="icon", path=str(p), version="v3", params={})}
    store = TemplateStore(specs)
    assert store.spec("icon").version == "v3"
    assert store.versions(["icon"]) == {"icon": "v3"}
    assert store.list_templates() == ["icon"]
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_template_store.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `templates/store.py`**

`src/ocr_yolo_engine/templates/__init__.py`:
```python
# 模板库子包
```

`src/ocr_yolo_engine/templates/store.py`:
```python
"""模板库:从配置读规格,按需加载模板图并缓存,带版本。"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode


@dataclass
class TemplateSpec:
    name: str
    path: str
    version: str
    params: dict[str, Any] = field(default_factory=dict)


class TemplateStore:
    def __init__(self, specs: dict[str, TemplateSpec]) -> None:
        self._specs = specs
        self._cache: dict[str, np.ndarray] = {}
        self._lock = threading.RLock()

    def spec(self, name: str) -> TemplateSpec:
        if name not in self._specs:
            raise EngineError(
                ErrorCode.TEMPLATE_NOT_FOUND, f"模板 {name} 未注册", details={"template": name}
            )
        return self._specs[name]

    def list_templates(self) -> list[str]:
        return list(self._specs.keys())

    def versions(self, names: list[str]) -> dict[str, str]:
        return {n: self.spec(n).version for n in names}

    def get_image(self, name: str) -> np.ndarray:
        spec = self.spec(name)
        with self._lock:
            if name in self._cache:
                return self._cache[name]
            img = cv2.imread(spec.path, cv2.IMREAD_COLOR)
            if img is None:
                raise EngineError(
                    ErrorCode.TEMPLATE_NOT_FOUND,
                    f"模板图无法读取:{spec.path}",
                    details={"template": name},
                )
            self._cache[name] = img
            return img
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_template_store.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/templates tests/unit/test_template_store.py
git commit -m "feat(templates): 新增模板库加载缓存与版本"
```

---

## Task 10: 模板匹配识别器 `recognizers/template.py`

**Files:**
- Create: `src/ocr_yolo_engine/recognizers/template.py`
- Test: `tests/unit/test_template_recognizer.py`

设计:NMS 纯函数 + 多尺度 `matchTemplate`。识别器吃 RGB 图(预处理后),对每个模板名从 store 取图、转同色彩空间、多尺度匹配、阈值过滤、NMS,产出 `RawDetection(source="template", label=模板名)`。

- [ ] **Step 1: 写 NMS 失败测试**

`tests/unit/test_template_recognizer.py`:

```python
import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.template import TemplateRecognizer, non_max_suppression


def test_nms_keeps_highest_and_drops_overlap():
    boxes = [
        (10, 10, 50, 50, 0.9),
        (12, 12, 52, 52, 0.7),   # 与上高度重叠 → 抑制
        (200, 200, 240, 240, 0.8),
    ]
    kept = non_max_suppression(boxes, iou_threshold=0.4)
    assert len(kept) == 2
    assert kept[0][4] == 0.9
    assert kept[1][4] == 0.8


def test_nms_empty():
    assert non_max_suppression([], iou_threshold=0.4) == []


def test_recognizer_finds_template_in_scene():
    # 场景图 100x100 白底,在 (30,40) 放一个 10x10 黑块作为目标
    scene = np.full((100, 100, 3), 255, dtype=np.uint8)
    scene[40:50, 30:40] = 0
    template = np.zeros((10, 10, 3), dtype=np.uint8)

    class StubStore:
        def get_image(self, name):
            return template

        def spec(self, name):
            from ocr_yolo_engine.templates.store import TemplateSpec

            return TemplateSpec(name=name, path="x", version="v1", params={"threshold": 0.8})

    rec = TemplateRecognizer(store=StubStore(), scales=(1.0,))
    out = rec.infer(scene, InferContext(conf_threshold=0.8, templates=["blk"]))
    assert len(out) == 1
    d = out[0]
    assert d.source == "template"
    assert d.label == "blk"
    # 命中位置应接近 (30,40)-(40,50)
    assert abs(d.bbox[0] - 30) <= 2 and abs(d.bbox[1] - 40) <= 2
    assert d.confidence >= 0.8
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_template_recognizer.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `recognizers/template.py`**

```python
"""OpenCV 模板匹配识别器:多尺度 + 阈值 + NMS 去重。"""

from __future__ import annotations

from typing import Protocol

import cv2
import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection

Box = tuple[float, float, float, float, float]  # x1,y1,x2,y2,score


class _StoreLike(Protocol):
    def get_image(self, name: str) -> np.ndarray: ...
    def spec(self, name: str): ...


def _iou(a: Box, b: Box) -> float:
    ax1, ay1, ax2, ay2, _ = a
    bx1, by1, bx2, by2, _ = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / (area_a + area_b - inter)


def non_max_suppression(boxes: list[Box], iou_threshold: float) -> list[Box]:
    ordered = sorted(boxes, key=lambda b: b[4], reverse=True)
    kept: list[Box] = []
    for box in ordered:
        if all(_iou(box, k) < iou_threshold for k in kept):
            kept.append(box)
    return kept


class TemplateRecognizer:
    def __init__(
        self,
        store: _StoreLike,
        scales: tuple[float, ...] = (0.8, 0.9, 1.0, 1.1, 1.2),
        iou_threshold: float = 0.4,
    ) -> None:
        self._store = store
        self._scales = scales
        self._iou = iou_threshold

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        scene = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        results: list[RawDetection] = []
        for name in ctx.templates:
            spec = self._store.spec(name)
            threshold = float(spec.params.get("threshold", ctx.conf_threshold))
            tmpl = cv2.cvtColor(self._store.get_image(name), cv2.COLOR_BGR2GRAY)
            boxes: list[Box] = []
            for scale in self._scales:
                th, tw = int(tmpl.shape[0] * scale), int(tmpl.shape[1] * scale)
                if th < 4 or tw < 4 or th > scene.shape[0] or tw > scene.shape[1]:
                    continue
                resized = cv2.resize(tmpl, (tw, th))
                res = cv2.matchTemplate(scene, resized, cv2.TM_CCOEFF_NORMED)
                ys, xs = np.where(res >= threshold)
                for x, y in zip(xs.tolist(), ys.tolist()):
                    score = float(res[y, x])
                    boxes.append((float(x), float(y), float(x + tw), float(y + th), score))
            for x1, y1, x2, y2, score in non_max_suppression(boxes, self._iou):
                results.append(
                    RawDetection(
                        source="template",
                        label=name,
                        text=None,
                        confidence=score,
                        bbox=[x1, y1, x2, y2],
                    )
                )
        return results
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_template_recognizer.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/recognizers/template.py tests/unit/test_template_recognizer.py
git commit -m "feat(recognizers): 新增模板匹配识别器(多尺度+NMS)"
```

---

## Task 11: OCR 识别器 `recognizers/ocr.py`(懒加载)

**Files:**
- Create: `src/ocr_yolo_engine/recognizers/ocr.py`
- Test: `tests/unit/test_ocr_recognizer.py`

设计:`OcrRecognizer` 构造时接收一个 `engine`(可注入)。生产中默认 `engine=None`,首次 `infer` 时懒加载 PaddleOCR(隔离在 `_load_engine` 内,import 在函数体内,避免顶层导入 paddle)。测试注入假 engine。PaddleOCR 返回结构 `[[ [box4点], (text, conf) ], ...]`,封装成 RawDetection(用外接矩形)。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_ocr_recognizer.py`:

```python
import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.ocr import OcrRecognizer


class FakePaddle:
    """模拟 PaddleOCR.ocr 的返回结构。"""

    def ocr(self, img, cls=True):
        return [
            [
                [[[10, 20], [60, 20], [60, 40], [10, 40]], ("登录", 0.95)],
                [[[10, 50], [40, 50], [40, 70], [10, 70]], ("OK", 0.80)],
            ]
        ]


def test_ocr_wraps_results_with_bounding_box():
    rec = OcrRecognizer(engine=FakePaddle())
    out = rec.infer(np.zeros((100, 100, 3), dtype=np.uint8), InferContext(conf_threshold=0.0))
    assert len(out) == 2
    first = out[0]
    assert first.source == "ocr"
    assert first.label is None
    assert first.text == "登录"
    assert first.confidence == 0.95
    assert first.bbox == [10, 20, 60, 40]  # 四点外接矩形


def test_ocr_filters_by_confidence():
    rec = OcrRecognizer(engine=FakePaddle())
    out = rec.infer(np.zeros((100, 100, 3), dtype=np.uint8), InferContext(conf_threshold=0.9))
    assert [d.text for d in out] == ["登录"]


def test_ocr_handles_empty_page():
    class EmptyPaddle:
        def ocr(self, img, cls=True):
            return [None]

    rec = OcrRecognizer(engine=EmptyPaddle())
    out = rec.infer(np.zeros((10, 10, 3), dtype=np.uint8), InferContext(conf_threshold=0.0))
    assert out == []
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_ocr_recognizer.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `recognizers/ocr.py`**

```python
"""PaddleOCR 识别器:仅文字识别;重依赖懒加载。"""

from __future__ import annotations

from typing import Any

import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection
from ocr_yolo_engine.settings import Settings, get_settings


class OcrRecognizer:
    def __init__(self, engine: Any | None = None, settings: Settings | None = None) -> None:
        self._engine = engine
        self._settings = settings or get_settings()

    def _ensure_engine(self) -> Any:
        if self._engine is None:
            from paddleocr import PaddleOCR  # 懒加载,避免顶层导入 paddle

            use_gpu = self._settings.device == "cuda"
            self._engine = PaddleOCR(use_angle_cls=True, lang="ch", use_gpu=use_gpu)
        return self._engine

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        engine = self._ensure_engine()
        pages = engine.ocr(image, cls=True)
        out: list[RawDetection] = []
        for page in pages:
            if not page:
                continue
            for box, (text, conf) in page:
                if conf < ctx.conf_threshold:
                    continue
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                out.append(
                    RawDetection(
                        source="ocr",
                        label=None,
                        text=text,
                        confidence=float(conf),
                        bbox=[float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))],
                    )
                )
        return out
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_ocr_recognizer.py -v`
Expected: PASS（测试注入 fake,不触发真实 paddle 导入)。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/recognizers/ocr.py tests/unit/test_ocr_recognizer.py
git commit -m "feat(recognizers): 新增 PaddleOCR 识别器(懒加载)"
```

---

## Task 12: YOLO 识别器 `recognizers/yolo.py`(懒加载)

**Files:**
- Create: `src/ocr_yolo_engine/recognizers/yolo.py`
- Test: `tests/unit/test_yolo_recognizer.py`

设计:`YoloRecognizer(registry)`。`infer` 从 `ctx.model` 取模型对象(registry.get),调用 `model.predict(image, conf=ctx.conf_threshold)`,解析 ultralytics Results(boxes.xyxy/conf/cls)+ 该模型 spec 的类别表得到 label。模型对象由 registry 的 loader_fn 加载(生产注入 ultralytics 加载函数)。测试注入假 registry + 假 model。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_yolo_recognizer.py`:

```python
import numpy as np

from ocr_yolo_engine.models.registry import ModelSpec
from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.yolo import YoloRecognizer


class FakeBoxes:
    def __init__(self):
        self.xyxy = np.array([[10.0, 20.0, 30.0, 40.0], [50.0, 60.0, 70.0, 80.0]])
        self.conf = np.array([0.9, 0.6])
        self.cls = np.array([0, 1])


class FakeResult:
    def __init__(self):
        self.boxes = FakeBoxes()


class FakeModel:
    def __init__(self):
        self.last_conf = None

    def predict(self, image, conf, verbose=False):
        self.last_conf = conf
        return [FakeResult()]


class FakeRegistry:
    def __init__(self, model):
        self._model = model
        self._spec = ModelSpec(name="game", path="x.pt", version="v2", classes={0: "boss", 1: "coin"})

    def get(self, name):
        return self._model

    def spec(self, name):
        return self._spec


def test_yolo_maps_classes_and_passes_threshold():
    model = FakeModel()
    rec = YoloRecognizer(registry=FakeRegistry(model))
    out = rec.infer(np.zeros((100, 100, 3), dtype=np.uint8), InferContext(conf_threshold=0.5, model="game"))
    assert model.last_conf == 0.5
    assert len(out) == 2
    assert out[0].source == "yolo"
    assert out[0].label == "boss"
    assert out[0].confidence == 0.9
    assert out[0].bbox == [10.0, 20.0, 30.0, 40.0]
    assert out[1].label == "coin"


def test_yolo_unknown_class_falls_back_to_index_string():
    model = FakeModel()
    reg = FakeRegistry(model)
    reg._spec = ModelSpec(name="game", path="x.pt", version="v2", classes={})
    rec = YoloRecognizer(registry=reg)
    out = rec.infer(np.zeros((100, 100, 3), dtype=np.uint8), InferContext(conf_threshold=0.0, model="game"))
    assert out[0].label == "0"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_yolo_recognizer.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `recognizers/yolo.py`**

```python
"""ultralytics YOLO 识别器:从注册表取模型,输出类别+框+置信度;重依赖懒加载。"""

from __future__ import annotations

from typing import Protocol

import numpy as np

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.models.registry import ModelSpec
from ocr_yolo_engine.recognizers.base import InferContext, RawDetection


class _RegistryLike(Protocol):
    def get(self, name: str): ...
    def spec(self, name: str) -> ModelSpec: ...


class YoloRecognizer:
    def __init__(self, registry: _RegistryLike) -> None:
        self._registry = registry

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        if not ctx.model:
            raise EngineError(ErrorCode.MODEL_NOT_FOUND, "yolo 推理缺少 model 参数")
        model = self._registry.get(ctx.model)
        classes = self._registry.spec(ctx.model).classes
        results = model.predict(image, conf=ctx.conf_threshold, verbose=False)
        out: list[RawDetection] = []
        for res in results:
            boxes = res.boxes
            xyxy = np.asarray(boxes.xyxy)
            conf = np.asarray(boxes.conf)
            cls = np.asarray(boxes.cls)
            for i in range(len(xyxy)):
                cls_idx = int(cls[i])
                label = classes.get(cls_idx, str(cls_idx))
                x1, y1, x2, y2 = (float(v) for v in xyxy[i])
                out.append(
                    RawDetection(
                        source="yolo",
                        label=label,
                        text=None,
                        confidence=float(conf[i]),
                        bbox=[x1, y1, x2, y2],
                    )
                )
        return out


def load_yolo_model(spec: ModelSpec):
    """生产用 loader_fn:懒加载 ultralytics 模型。注入到 ModelRegistry。"""
    from ultralytics import YOLO  # 懒加载,避免顶层导入 torch

    return YOLO(spec.path)
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_yolo_recognizer.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/recognizers/yolo.py tests/unit/test_yolo_recognizer.py
git commit -m "feat(recognizers): 新增 YOLO 识别器(懒加载+类别映射)"
```

---

# 阶段 3:并发与背压

## Task 13: 工作池 `concurrency/executor.py`

**Files:**
- Create: `src/ocr_yolo_engine/concurrency/__init__.py`
- Create: `src/ocr_yolo_engine/concurrency/executor.py`
- Test: `tests/unit/test_executor.py`

设计:`InferenceExecutor(max_workers, max_queue, timeout_s)`。`submit(model_key, fn)`:用信号量限制在途任务总数(> max_queue 抛 OVERLOADED);用每 `model_key` 一把锁串行化同模型;提交到线程池并按 timeout 等结果(超时抛 TIMEOUT)。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_executor.py`:

```python
import threading
import time

import pytest

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.errors import EngineError, ErrorCode


def test_submit_returns_result():
    ex = InferenceExecutor(max_workers=2, max_queue=8, timeout_s=5)
    assert ex.submit("m", lambda: 41 + 1) == 42
    ex.shutdown()


def test_same_model_serialized():
    ex = InferenceExecutor(max_workers=4, max_queue=16, timeout_s=5)
    active = 0
    max_active = 0
    lock = threading.Lock()

    def work():
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return True

    threads = [threading.Thread(target=lambda: ex.submit("same", work)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert max_active == 1  # 同模型串行
    ex.shutdown()


def test_overload_raises_503():
    ex = InferenceExecutor(max_workers=1, max_queue=1, timeout_s=5)
    started = threading.Event()
    release = threading.Event()

    def block():
        started.set()
        release.wait()
        return 1

    t = threading.Thread(target=lambda: ex.submit("m", block))
    t.start()
    started.wait()
    # 此刻 1 个在跑,队列容量 1。再塞 2 个,其中至少 1 个应过载。
    errors = []

    def try_submit():
        try:
            ex.submit("m", lambda: 1)
        except EngineError as e:
            errors.append(e.code)

    extra = [threading.Thread(target=try_submit) for _ in range(3)]
    for th in extra:
        th.start()
    for th in extra:
        th.join(timeout=2)
    release.set()
    t.join()
    assert ErrorCode.OVERLOADED in errors
    ex.shutdown()


def test_timeout_raises_504():
    ex = InferenceExecutor(max_workers=1, max_queue=4, timeout_s=0)

    def slow():
        time.sleep(0.2)
        return 1

    with pytest.raises(EngineError) as ei:
        ex.submit("m", slow)
    assert ei.value.code is ErrorCode.TIMEOUT
    ex.shutdown()
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_executor.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `concurrency/executor.py`**

`src/ocr_yolo_engine/concurrency/__init__.py`:
```python
# 并发子包
```

`src/ocr_yolo_engine/concurrency/executor.py`:
```python
"""有界工作池 + 每模型锁 + 背压:推理在线程池跑,过载 503,超时 504。"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, TypeVar

from ocr_yolo_engine.errors import EngineError, ErrorCode

T = TypeVar("T")


class InferenceExecutor:
    def __init__(self, max_workers: int, max_queue: int, timeout_s: float) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._slots = threading.Semaphore(max_queue + max_workers)
        self._timeout = timeout_s
        self._model_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    def _model_lock(self, key: str) -> threading.Lock:
        with self._locks_guard:
            if key not in self._model_locks:
                self._model_locks[key] = threading.Lock()
            return self._model_locks[key]

    def submit(self, model_key: str, fn: Callable[[], T]) -> T:
        if not self._slots.acquire(blocking=False):
            raise EngineError(ErrorCode.OVERLOADED, "服务繁忙,请稍后重试", details={"retry_after": 1})
        try:
            lock = self._model_lock(model_key)

            def guarded() -> T:
                with lock:
                    return fn()

            future = self._pool.submit(guarded)
            try:
                return future.result(timeout=self._timeout)
            except TimeoutError as exc:
                future.cancel()
                raise EngineError(ErrorCode.TIMEOUT, "推理超时", details={"timeout_s": self._timeout}) from exc
        finally:
            self._slots.release()

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
```

> 说明:`OVERLOADED` 的 `details.retry_after` 供路由层设置 `Retry-After` 响应头。`_slots` 容量 = `max_queue + max_workers`(在跑 + 排队总量上限),贴合 spec 的"队列超过 max_queue 返回 503"。

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_executor.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/concurrency tests/unit/test_executor.py
git commit -m "feat(concurrency): 新增有界工作池与每模型锁背压"
```

---

# 阶段 4:可观测性

## Task 14: 结构化日志 `observability/logging.py`

**Files:**
- Create: `src/ocr_yolo_engine/observability/__init__.py`
- Create: `src/ocr_yolo_engine/observability/logging.py`
- Test: `tests/unit/test_logging.py`

设计:用标准库 logging + `contextvars` 贯穿 request_id;JSON 行格式;提供 `setup_logging()`、`bind_request_id(rid)`、`current_request_id()`、`new_request_id()`。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_logging.py`:

```python
import json
import logging

from ocr_yolo_engine.observability.logging import (
    JsonFormatter,
    bind_request_id,
    current_request_id,
    new_request_id,
)


def test_request_id_contextvar_roundtrip():
    token = bind_request_id("req-123")
    assert current_request_id() == "req-123"
    token.var.reset(token) if hasattr(token, "var") else None


def test_new_request_id_is_unique():
    a = new_request_id()
    b = new_request_id()
    assert a != b
    assert len(a) >= 8


def test_json_formatter_includes_request_id():
    bind_request_id("req-xyz")
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "hello %s", ("world",), None)
    line = JsonFormatter().format(record)
    payload = json.loads(line)
    assert payload["message"] == "hello world"
    assert payload["request_id"] == "req-xyz"
    assert payload["level"] == "INFO"
```

> 注:`bind_request_id` 返回 contextvars Token;测试中重置非必须,这里主要验证读取。第一个用例简化为只验证设置后能读到。

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_logging.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `observability/logging.py`**

`src/ocr_yolo_engine/observability/__init__.py`:
```python
# 可观测性子包
```

`src/ocr_yolo_engine/observability/logging.py`:
```python
"""结构化(JSON)日志 + request_id 贯穿。"""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar, Token

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def new_request_id() -> str:
    return uuid.uuid4().hex


def bind_request_id(request_id: str) -> Token[str]:
    return _request_id.set(request_id)


def current_request_id() -> str:
    return _request_id.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": current_request_id(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_logging.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/observability tests/unit/test_logging.py
git commit -m "feat(observability): 新增结构化日志与 request_id 贯穿"
```

---

# 阶段 5:HTTP 服务

## Task 15: 配置加载 + DI 提供者 + fakes

**Files:**
- Create: `src/ocr_yolo_engine/config_loader.py`
- Create: `src/ocr_yolo_engine/service/__init__.py`
- Create: `src/ocr_yolo_engine/service/deps.py`
- Create: `tests/fakes/__init__.py`
- Create: `tests/fakes/recognizers.py`
- Test: `tests/unit/test_config_loader.py`

设计:`config_loader.py` 从 yaml 读出 `dict[str, ModelSpec]` 与 `dict[str, TemplateSpec]`。`deps.py` 用一个 `AppContext` 持有 registry/template_store/executor/recognizers,FastAPI 通过依赖函数取;支持测试覆盖。`tests/fakes` 提供 `FakeRecognizer`。

- [ ] **Step 1: 写 config_loader 失败测试**

`tests/unit/test_config_loader.py`:

```python
from ocr_yolo_engine.config_loader import load_model_specs, load_template_specs


def test_load_model_specs(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text(
        "models:\n"
        "  game_a:\n"
        "    path: models_store/game_a.pt\n"
        "    version: v1\n"
        "    classes:\n"
        "      0: boss\n"
        "      1: coin\n",
        encoding="utf-8",
    )
    specs = load_model_specs(str(p))
    assert specs["game_a"].path == "models_store/game_a.pt"
    assert specs["game_a"].version == "v1"
    assert specs["game_a"].classes == {0: "boss", 1: "coin"}


def test_load_model_specs_missing_file_returns_empty(tmp_path):
    assert load_model_specs(str(tmp_path / "nope.yaml")) == {}


def test_load_template_specs(tmp_path):
    p = tmp_path / "templates.yaml"
    p.write_text(
        "templates:\n"
        "  settings_icon:\n"
        "    path: templates_store/settings.png\n"
        "    version: v1\n"
        "    params:\n"
        "      threshold: 0.85\n",
        encoding="utf-8",
    )
    specs = load_template_specs(str(p))
    assert specs["settings_icon"].path == "templates_store/settings.png"
    assert specs["settings_icon"].params == {"threshold": 0.85}
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_config_loader.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `config_loader.py`**

```python
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
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_config_loader.py -v`
Expected: PASS。

- [ ] **Step 5: 实现 DI 容器 `service/deps.py`**

`src/ocr_yolo_engine/service/__init__.py`:
```python
# HTTP 服务子包
```

`src/ocr_yolo_engine/service/deps.py`:
```python
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
```

- [ ] **Step 6: 实现测试假件 `tests/fakes/recognizers.py`**

`tests/fakes/__init__.py`:
```python
# 测试假件
```

`tests/fakes/recognizers.py`:
```python
"""测试用假识别器:不加载任何真实模型。"""

from __future__ import annotations

import numpy as np

from ocr_yolo_engine.recognizers.base import InferContext, RawDetection


class FakeRecognizer:
    """返回预置 RawDetection,记录调用。"""

    def __init__(self, canned: list[RawDetection] | None = None) -> None:
        self.canned = canned or []
        self.calls: list[InferContext] = []

    def infer(self, image: np.ndarray, ctx: InferContext) -> list[RawDetection]:
        self.calls.append(ctx)
        return list(self.canned)
```

- [ ] **Step 7: 运行全部已存在单测确保无回归**

Run: `uv run pytest tests/unit -v`
Expected: 全部 PASS。

- [ ] **Step 8: Commit**

```bash
git add src/ocr_yolo_engine/config_loader.py src/ocr_yolo_engine/service tests/fakes tests/unit/test_config_loader.py
git commit -m "feat(service): 新增配置加载、DI 容器与测试假识别器"
```

---

## Task 16: API Key 鉴权 `service/auth.py`

**Files:**
- Create: `src/ocr_yolo_engine/service/auth.py`
- Test: `tests/unit/test_auth.py`

设计:`verify_api_key(provided, settings)` 纯函数 —— `auth_enabled` 为 False 直接放行;否则 `provided` 必须在 `api_keys` 内,否则抛 401(用 `fastapi.HTTPException`)。FastAPI 依赖 `require_api_key` 从 `X-API-Key` 头取值。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_auth.py`:

```python
import pytest
from fastapi import HTTPException

from ocr_yolo_engine.service.auth import verify_api_key
from ocr_yolo_engine.settings import Settings


def test_auth_disabled_allows_any():
    verify_api_key(None, Settings(api_keys=[]))  # 不抛即放行


def test_auth_enabled_accepts_valid_key():
    verify_api_key("k1", Settings(api_keys=["k1", "k2"]))


def test_auth_enabled_rejects_missing_or_wrong():
    with pytest.raises(HTTPException) as ei:
        verify_api_key(None, Settings(api_keys=["k1"]))
    assert ei.value.status_code == 401
    with pytest.raises(HTTPException) as ei2:
        verify_api_key("bad", Settings(api_keys=["k1"]))
    assert ei2.value.status_code == 401
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_auth.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `service/auth.py`**

```python
"""API Key 鉴权:api_keys 为空时关闭(本地友好)。"""

from __future__ import annotations

from fastapi import Header, HTTPException

from ocr_yolo_engine.settings import Settings, get_settings


def verify_api_key(provided: str | None, settings: Settings) -> None:
    if not settings.auth_enabled:
        return
    if provided is None or provided not in settings.api_keys:
        raise HTTPException(status_code=401, detail="无效或缺失的 API Key")


async def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    verify_api_key(x_api_key, get_settings())
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_auth.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/ocr_yolo_engine/service/auth.py tests/unit/test_auth.py
git commit -m "feat(service): 新增 API Key 鉴权(可关闭)"
```

---

## Task 17: 核心识别管线 + FastAPI 应用与路由

**Files:**
- Create: `src/ocr_yolo_engine/pipeline_runner.py`
- Create: `src/ocr_yolo_engine/service/routes.py`
- Create: `src/ocr_yolo_engine/service/app.py`
- Test: `tests/unit/test_pipeline_runner.py`

设计:把"加载图→校验→预处理→executor 跑识别器→回映射→组装 MethodResult"抽到 `pipeline_runner.run_recognition(ctx_app, request) -> RecognizeResponse`,与 HTTP 解耦,便于单测(注入 FakeRecognizer)。`routes.py` 仅做参数解析 + 调 runner + 错误→HTTP。

- [ ] **Step 1: 写 runner 失败测试**

`tests/unit/test_pipeline_runner.py`:

```python
import base64

import cv2
import numpy as np

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.models.registry import ModelRegistry
from ocr_yolo_engine.pipeline_runner import run_recognition
from ocr_yolo_engine.recognizers.base import RawDetection
from ocr_yolo_engine.schemas import ImageInput, RecognizeRequest
from ocr_yolo_engine.service.deps import AppContext
from ocr_yolo_engine.settings import Settings
from ocr_yolo_engine.templates.store import TemplateStore
from tests.fakes.recognizers import FakeRecognizer


def _b64_image(w=100, h=80):
    img = np.zeros((h, w, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", img)
    return base64.b64encode(buf.tobytes()).decode()


def _ctx(recognizers, settings=None):
    settings = settings or Settings(api_keys=[], allowed_path_roots=[])
    return AppContext(
        settings=settings,
        registry=ModelRegistry({}, loader_fn=lambda s: None, cache_size=1),
        template_store=TemplateStore({}),
        executor=InferenceExecutor(max_workers=2, max_queue=8, timeout_s=5),
        recognizers=recognizers,
    )


def test_run_ocr_returns_finalized_detections():
    fake = FakeRecognizer([RawDetection(source="ocr", label=None, text="hi", confidence=0.9, bbox=[10, 20, 30, 40])])
    ctx = _ctx({"ocr": fake})
    req = RecognizeRequest(image=ImageInput(base64=_b64_image()), methods=["ocr"])
    resp = run_recognition(ctx, req)
    assert resp.image_size == [100, 80]
    det = resp.method_results["ocr"].detections[0]
    assert det.text == "hi"
    assert det.bbox == [10, 20, 30, 40]
    assert det.center == [20, 30]
    assert det.bbox_norm[0] == 10 / 100
    ctx.executor.shutdown()


def test_run_applies_roi_offset():
    fake = FakeRecognizer([RawDetection(source="template", label="x", text=None, confidence=1.0, bbox=[0, 0, 5, 5])])
    ctx = _ctx({"template": fake})
    req = RecognizeRequest(
        image=ImageInput(base64=_b64_image()),
        methods=["template"],
        templates=["x"],
        roi={"x": 10, "y": 10, "w": 40, "h": 40},
    )
    resp = run_recognition(ctx, req)
    det = resp.method_results["template"].detections[0]
    assert det.bbox == [10, 10, 15, 15]  # 加上 ROI 偏移
    ctx.executor.shutdown()


def test_conf_threshold_passed_to_recognizer():
    fake = FakeRecognizer([])
    ctx = _ctx({"ocr": fake})
    req = RecognizeRequest(image=ImageInput(base64=_b64_image()), methods=["ocr"], conf_threshold=0.7)
    run_recognition(ctx, req)
    assert fake.calls[0].conf_threshold == 0.7
    ctx.executor.shutdown()
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_pipeline_runner.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `pipeline_runner.py`**

```python
"""核心识别管线:与 HTTP 解耦,串起加载/预处理/并发/识别/回映射/组装。"""

from __future__ import annotations

import time

from ocr_yolo_engine.image.loader import decode_image_bytes, load_from_base64, load_from_path
from ocr_yolo_engine.observability.logging import current_request_id
from ocr_yolo_engine.preprocessing.pipeline import (
    crop_roi,
    enforce_limits,
    finalize_detections,
    to_rgb,
)
from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.schemas import MethodResult, RecognizeRequest, RecognizeResponse
from ocr_yolo_engine.service.deps import AppContext


def _load_bytes_and_image(ctx: AppContext, req: RecognizeRequest):
    """返回 (raw_bytes, bgr_image)。raw_bytes 仅用于大小上限校验。"""
    if req.image.base64 is not None:
        import base64 as _b64

        payload = req.image.base64.split(",", 1)[1] if req.image.base64.startswith("data:") else req.image.base64
        raw = _b64.b64decode(payload)
        return raw, load_from_base64(req.image.base64)
    assert req.image.path is not None
    img = load_from_path(req.image.path, ctx.settings.allowed_path_roots)
    return b"", img  # 路径来源不强制字节上限(已在白名单内)


def run_recognition(ctx: AppContext, req: RecognizeRequest) -> RecognizeResponse:
    request_id = current_request_id()
    raw_bytes, bgr = _load_bytes_and_image(ctx, req)
    enforce_limits(
        raw_bytes,
        bgr,
        max_bytes=ctx.settings.max_image_bytes,
        max_pixels=ctx.settings.max_image_pixels,
    )
    full_h, full_w = bgr.shape[:2]
    rgb = to_rgb(bgr)
    cropped, offset = crop_roi(rgb, req.roi)

    conf = req.conf_threshold if req.conf_threshold is not None else ctx.settings.default_conf_threshold
    infer_ctx = InferContext(conf_threshold=conf, model=req.model, templates=req.templates or [])

    method_results: dict = {}
    for method in req.methods:
        recognizer = ctx.recognizers[method]
        model_key = req.model if method == "yolo" and req.model else method
        started = time.perf_counter()
        raws = ctx.executor.submit(model_key, lambda r=recognizer: r.infer(cropped, infer_ctx))
        elapsed_ms = (time.perf_counter() - started) * 1000
        detections = finalize_detections(raws, offset=offset, full_w=full_w, full_h=full_h)

        model_version = ctx.registry.spec(req.model).version if method == "yolo" and req.model else None
        template_versions = (
            ctx.template_store.versions(req.templates) if method == "template" and req.templates else None
        )
        method_results[method] = MethodResult(
            detections=detections,
            model_version=model_version,
            template_versions=template_versions,
            elapsed_ms=elapsed_ms,
        )

    return RecognizeResponse(
        request_id=request_id,
        image_size=[full_w, full_h],
        method_results=method_results,
        debug_image=None,  # 首版预留;debug 标注图在后续任务落地
    )
```

- [ ] **Step 4: 运行 runner 测试通过**

Run: `uv run pytest tests/unit/test_pipeline_runner.py -v`
Expected: PASS。

- [ ] **Step 5: 实现路由 `service/routes.py`**

```python
"""/v1 路由:单方法 + 合并 + 上传 + 资产列表 + 健康检查。"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile

from ocr_yolo_engine.errors import EngineError, ErrorCode
from ocr_yolo_engine.image.loader import decode_image_bytes
from ocr_yolo_engine.observability.logging import bind_request_id, new_request_id
from ocr_yolo_engine.pipeline_runner import run_recognition
from ocr_yolo_engine.schemas import ImageInput, Method, RecognizeRequest, RecognizeResponse
from ocr_yolo_engine.service.auth import require_api_key
from ocr_yolo_engine.service.deps import AppContext

router = APIRouter()


def _ctx(request: Request) -> AppContext:
    return request.app.state.ctx


def _run(request: Request, req: RecognizeRequest) -> RecognizeResponse:
    bind_request_id(new_request_id())
    return run_recognition(_ctx(request), req)


@router.post("/v1/ocr", response_model=RecognizeResponse, dependencies=[Depends(require_api_key)])
def ocr(request: Request, body: ImageInput) -> RecognizeResponse:
    return _run(request, RecognizeRequest(image=body, methods=["ocr"]))


@router.post("/v1/detect", response_model=RecognizeResponse, dependencies=[Depends(require_api_key)])
def detect(request: Request, body: RecognizeRequest) -> RecognizeResponse:
    body.methods = ["yolo"]
    return _run(request, body)


@router.post("/v1/match", response_model=RecognizeResponse, dependencies=[Depends(require_api_key)])
def match(request: Request, body: RecognizeRequest) -> RecognizeResponse:
    body.methods = ["template"]
    return _run(request, body)


@router.post("/v1/recognize", response_model=RecognizeResponse, dependencies=[Depends(require_api_key)])
def recognize(request: Request, body: RecognizeRequest) -> RecognizeResponse:
    return _run(request, body)


@router.post(
    "/v1/recognize/upload", response_model=RecognizeResponse, dependencies=[Depends(require_api_key)]
)
async def recognize_upload(
    request: Request,
    file: UploadFile = File(...),
    methods: str = Form(...),
    model: str | None = Form(default=None),
    templates: str | None = Form(default=None),
    conf_threshold: float | None = Form(default=None),
) -> RecognizeResponse:
    data = await file.read()
    image = decode_image_bytes(data)  # 校验可解码
    b64 = base64.b64encode(data).decode()
    method_list: list[Method] = [m.strip() for m in methods.split(",") if m.strip()]  # type: ignore[misc]
    template_list = [t.strip() for t in templates.split(",")] if templates else None
    req = RecognizeRequest(
        image=ImageInput(base64=b64),
        methods=method_list,
        model=model,
        templates=template_list,
        conf_threshold=conf_threshold,
    )
    _ = image
    return _run(request, req)


@router.get("/v1/models", dependencies=[Depends(require_api_key)])
def list_models(request: Request) -> dict:
    reg = _ctx(request).registry
    return {"models": [{"name": n, "version": reg.spec(n).version} for n in reg.list_models()]}


@router.get("/v1/templates", dependencies=[Depends(require_api_key)])
def list_templates(request: Request) -> dict:
    store = _ctx(request).template_store
    return {"templates": [{"name": n, "version": store.spec(n).version} for n in store.list_templates()]}


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> dict:
    ctx = _ctx(request)
    return {"status": "ready", "models": ctx.registry.list_models()}
```

- [ ] **Step 6: 实现应用装配 `service/app.py`**

```python
"""FastAPI 应用装配:DI 容器、异常处理、路由。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ocr_yolo_engine.errors import EngineError
from ocr_yolo_engine.observability.logging import current_request_id, setup_logging
from ocr_yolo_engine.service.deps import AppContext, build_context
from ocr_yolo_engine.service.routes import router
from ocr_yolo_engine.settings import Settings


def create_app(ctx: AppContext | None = None, settings: Settings | None = None) -> FastAPI:
    setup_logging()
    app = FastAPI(title="OcrYoloEngine", version="0.1.0")
    app.state.ctx = ctx or build_context(settings)

    @app.exception_handler(EngineError)
    async def _engine_error_handler(request: Request, exc: EngineError) -> JSONResponse:
        headers = {}
        if exc.code.value == "OVERLOADED":
            headers["Retry-After"] = str(exc.details.get("retry_after", 1))
        return JSONResponse(
            status_code=exc.http_status, content=exc.to_body(current_request_id()), headers=headers
        )

    app.include_router(router)
    return app
```

- [ ] **Step 7: 运行全部单测无回归**

Run: `uv run pytest tests/unit -v`
Expected: 全部 PASS。

- [ ] **Step 8: Commit**

```bash
git add src/ocr_yolo_engine/pipeline_runner.py src/ocr_yolo_engine/service/routes.py src/ocr_yolo_engine/service/app.py tests/unit/test_pipeline_runner.py
git commit -m "feat(service): 新增识别管线、FastAPI 路由与应用装配"
```

---

## Task 18: HTTP 契约测试

**Files:**
- Create: `tests/contract/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/contract/test_api_contract.py`

设计:用 `TestClient` + 注入了 FakeRecognizer 的 `AppContext`,验证状态码、schema、错误码、有目标/无目标/失败区分、鉴权。

- [ ] **Step 1: 写 conftest 与契约测试**

`tests/contract/__init__.py`:
```python
# 契约测试
```

`tests/conftest.py`:
```python
"""共享 fixture:构造注入假识别器的测试 app。"""

from __future__ import annotations

import base64

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.models.registry import ModelRegistry, ModelSpec
from ocr_yolo_engine.recognizers.base import RawDetection
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
    store = TemplateStore({"icon": TemplateSpec(name="icon", path="x.png", version="v1", params={})})
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
```

`tests/contract/test_api_contract.py`:
```python
from ocr_yolo_engine.recognizers.base import RawDetection
from tests.conftest import make_client


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ocr_with_detections(png_b64):
    c = make_client(ocr_canned=[RawDetection("ocr", None, "登录", 0.9, [10, 20, 30, 40])])
    r = c.post("/v1/ocr", json={"base64": png_b64})
    assert r.status_code == 200
    body = r.json()
    assert body["image_size"] == [100, 80]
    dets = body["method_results"]["ocr"]["detections"]
    assert dets[0]["text"] == "登录"
    assert dets[0]["bbox"] == [10, 20, 30, 40]


def test_ocr_empty_is_200_not_error(client, png_b64):
    r = client.post("/v1/ocr", json={"base64": png_b64})
    assert r.status_code == 200
    assert r.json()["method_results"]["ocr"]["detections"] == []


def test_invalid_base64_returns_400_error_code(client):
    r = client.post("/v1/ocr", json={"base64": "@@notbase64@@"})
    assert r.status_code == 400
    assert r.json()["error_code"] == "INVALID_IMAGE"


def test_detect_requires_model_422(client, png_b64):
    # detect 路由强制 methods=yolo;未给 model 触发 schema 校验失败
    r = client.post("/v1/detect", json={"image": {"base64": png_b64}, "methods": ["yolo"]})
    assert r.status_code == 422


def test_models_listing(client):
    r = client.get("/v1/models")
    assert r.status_code == 200
    assert r.json()["models"] == [{"name": "game", "version": "v1"}]


def test_auth_rejects_when_enabled(png_b64):
    from ocr_yolo_engine.settings import Settings

    c = make_client(settings=Settings(api_keys=["secret"], allowed_path_roots=[]))
    r = c.post("/v1/ocr", json={"base64": png_b64})
    assert r.status_code == 401
    r2 = c.post("/v1/ocr", json={"base64": png_b64}, headers={"X-API-Key": "secret"})
    assert r2.status_code == 200
```

- [ ] **Step 2: 运行验证(先失败后修)**

Run: `uv run pytest tests/contract -v`
Expected: 首次运行应 PASS（前序任务已实现路由)。若失败,按报错修正路由/装配,直到 PASS。

- [ ] **Step 3: 全量测试**

Run: `uv run pytest -v`
Expected: 全部 PASS（smoke 默认被 `-m 'not smoke'` 跳过)。

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/contract
git commit -m "test(contract): 新增 HTTP API 契约测试"
```

---

# 阶段 6:CLI

## Task 19: 命令行入口 `cli.py`

**Files:**
- Create: `src/ocr_yolo_engine/cli.py`
- Test: `tests/unit/test_cli.py`

设计:argparse 两子命令 `serve`(uvicorn 起服务,懒导入 uvicorn)、`infer`(本地单图,调 run_recognition 打印 JSON)。`--help` 与参数解析不触发重依赖。

- [ ] **Step 1: 写失败测试**

`tests/unit/test_cli.py`:

```python
import pytest

from ocr_yolo_engine.cli import build_parser


def test_parser_serve_defaults():
    args = build_parser().parse_args(["serve"])
    assert args.command == "serve"
    assert args.host == "0.0.0.0"
    assert args.port == 8000


def test_parser_infer_args():
    args = build_parser().parse_args(
        ["infer", "img.png", "--methods", "ocr,yolo", "--model", "game", "--conf", "0.4"]
    )
    assert args.command == "infer"
    assert args.image == "img.png"
    assert args.methods == "ocr,yolo"
    assert args.model == "game"
    assert args.conf == 0.4


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: FAIL（导入错误)。

- [ ] **Step 3: 实现 `cli.py`**

```python
"""CLI:serve 启动服务;infer 本地单图推理。重依赖懒加载。"""

from __future__ import annotations

import argparse
import json
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ocr-yolo", description="OcrYoloEngine 视觉识别服务")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="启动 HTTP 服务")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)

    infer = sub.add_parser("infer", help="本地单图推理")
    infer.add_argument("image", help="本地图片路径")
    infer.add_argument("--methods", default="ocr", help="逗号分隔:ocr,yolo,template")
    infer.add_argument("--model", default=None)
    infer.add_argument("--templates", default=None, help="逗号分隔模板名")
    infer.add_argument("--conf", type=float, default=None)
    return parser


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn  # 懒加载

    from ocr_yolo_engine.service.app import create_app

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


def _cmd_infer(args: argparse.Namespace) -> int:
    import os

    from ocr_yolo_engine.observability.logging import bind_request_id, new_request_id
    from ocr_yolo_engine.schemas import ImageInput, RecognizeRequest
    from ocr_yolo_engine.service.deps import build_context
    from ocr_yolo_engine.settings import Settings

    bind_request_id(new_request_id())
    from ocr_yolo_engine.pipeline_runner import run_recognition

    root = os.path.dirname(os.path.realpath(args.image)) or "."
    ctx = build_context(Settings(allowed_path_roots=[root]))
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    templates = [t.strip() for t in args.templates.split(",")] if args.templates else None
    req = RecognizeRequest(
        image=ImageInput(path=os.path.realpath(args.image)),
        methods=methods,  # type: ignore[arg-type]
        model=args.model,
        templates=templates,
        conf_threshold=args.conf,
    )
    resp = run_recognition(ctx, req)
    print(json.dumps(resp.model_dump(), ensure_ascii=False, indent=2))
    ctx.executor.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "serve":
        return _cmd_serve(args)
    if args.command == "infer":
        return _cmd_infer(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/unit/test_cli.py -v`
Expected: PASS。

- [ ] **Step 5: 验证 `--help` 不触发重依赖**

Run: `uv run ocr-yolo --help`
Expected: 正常打印帮助,无 torch/paddle 导入报错。

- [ ] **Step 6: Commit**

```bash
git add src/ocr_yolo_engine/cli.py tests/unit/test_cli.py
git commit -m "feat(cli): 新增 serve 与 infer 命令行入口"
```

---

# 阶段 7:训练隔离、Docker/configs、质量门禁

## Task 20: 隔离训练入口 `training/`

**Files:**
- Create: `training/README.md`
- Create: `training/train.py`
- Create: `training/dataset.md`
- Create: `training/configs/example.yaml`
- Test: `tests/unit/test_training_isolation.py`

- [ ] **Step 1: 写隔离性测试**

`tests/unit/test_training_isolation.py`:

```python
import pathlib


def test_src_never_imports_training():
    """服务代码 src/ 任何文件都不得 import training。"""
    src = pathlib.Path(__file__).resolve().parents[2] / "src"
    offenders = []
    for py in src.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "import training" in text or "from training" in text:
            offenders.append(str(py))
    assert offenders == [], f"src 不应 import training: {offenders}"
```

- [ ] **Step 2: 运行验证(应直接通过——src 本就未引用 training)**

Run: `uv run pytest tests/unit/test_training_isolation.py -v`
Expected: PASS。

- [ ] **Step 3: 写训练入口文件**

`training/README.md`:
```markdown
# 训练入口（与服务隔离）

本目录用于训练 YOLO 模型,**服务运行时绝不 import 本目录**。
产出权重放到 `../models_store/`,再在 `../configs/models.yaml` 登记即可被服务加载。

## 用法

```bash
uv pip install ultralytics
python training/train.py --data training/configs/example.yaml --epochs 100 --weights yolov8n.pt
```

数据集与标注格式见 [`dataset.md`](dataset.md)。
```

`training/train.py`:
```python
"""YOLO 训练脚本(基于 ultralytics)。与服务隔离,服务运行时不导入本文件。"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 YOLO 模型")
    parser.add_argument("--data", required=True, help="数据集 yaml 路径")
    parser.add_argument("--weights", default="yolov8n.pt", help="预训练权重")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0", help="GPU id 或 'cpu'")
    args = parser.parse_args()

    from ultralytics import YOLO  # 懒加载

    model = YOLO(args.weights)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, device=args.device)


if __name__ == "__main__":
    main()
```

`training/dataset.md`:
```markdown
# 数据集与标注约定（YOLO 格式）

```
dataset/
├── images/{train,val}/*.jpg
├── labels/{train,val}/*.txt   # 每行: <cls> <cx> <cy> <w> <h>（归一化 0~1）
└── data.yaml                  # train/val 路径 + names 类别表
```

`data.yaml` 中的 `names` 顺序必须与服务端 `configs/models.yaml` 的 `classes` 索引一致。
```

`training/configs/example.yaml`:
```yaml
# 示例数据集配置(ultralytics 格式)
path: ./dataset
train: images/train
val: images/val
names:
  0: boss
  1: coin
```

- [ ] **Step 4: 再次运行隔离测试**

Run: `uv run pytest tests/unit/test_training_isolation.py -v`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add training tests/unit/test_training_isolation.py
git commit -m "feat(training): 新增隔离训练入口与数据集约定"
```

---

## Task 21: configs 示例 + 资产目录 + Docker

**Files:**
- Create: `configs/models.yaml`
- Create: `configs/templates.yaml`
- Create: `models_store/.gitkeep`
- Create: `templates_store/.gitkeep`
- Create: `docker/Dockerfile.cpu`
- Create: `docker/Dockerfile.gpu`
- Create: `docker/.dockerignore`

- [ ] **Step 1: 写 configs 示例**

`configs/models.yaml`:
```yaml
# 模型注册表:名称 → 权重路径/版本/类别表
models: {}
  # 示例(取消注释并放好权重后启用):
  # game_a:
  #   path: models_store/game_a.pt
  #   version: v1
  #   classes:
  #     0: boss
  #     1: coin
```

`configs/templates.yaml`:
```yaml
# 模板库:名称 → 模板图路径/版本/匹配参数
templates: {}
  # 示例:
  # settings_icon:
  #   path: templates_store/settings.png
  #   version: v1
  #   params:
  #     threshold: 0.85
```

`models_store/.gitkeep` 与 `templates_store/.gitkeep`:空文件(内容写一行注释):
```
# 占位:权重/模板图按需放入,权重已被 .gitignore 忽略
```

- [ ] **Step 2: 写 Dockerfile(CPU)**

`docker/Dockerfile.cpu`:
```dockerfile
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install ".[ocr,yolo]"

COPY configs ./configs
ENV OYE_DEVICE=cpu
EXPOSE 8000
CMD ["ocr-yolo", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 写 Dockerfile(GPU)**

`docker/Dockerfile.gpu`:
```dockerfile
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 python3-pip libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install ".[ocr,yolo]"

COPY configs ./configs
ENV OYE_DEVICE=cuda
EXPOSE 8000
CMD ["ocr-yolo", "serve", "--host", "0.0.0.0", "--port", "8000"]
```

`docker/.dockerignore`:
```
.venv
__pycache__
tests
docs
models_store
templates_store
*.pt
*.onnx
```

- [ ] **Step 4: 校验 CPU 镜像可构建(可选,耗时)**

Run: `docker build -f docker/Dockerfile.cpu -t ocr-yolo:cpu .`
Expected: 构建成功。无 docker 环境则跳过,标注"未在本机验证"。

- [ ] **Step 5: Commit**

```bash
git add configs models_store templates_store docker
git commit -m "build(docker): 新增 configs 示例、资产目录与 CPU/GPU 镜像"
```

---

## Task 22: 质量门禁(pre-commit + lint/type + golden/smoke 约定)

**Files:**
- Create: `.pre-commit-config.yaml`
- Create: `tests/fixtures/__init__.py`
- Create: `tests/fixtures/README.md`
- Create: `tests/smoke/__init__.py`
- Create: `tests/smoke/test_smoke_placeholder.py`
- Modify: `CLAUDE.md`(补"常用命令"段)

- [ ] **Step 1: 写 pre-commit 配置**

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, types-PyYAML]
        args: [--config-file=pyproject.toml]
        files: ^src/
```

- [ ] **Step 2: 写 golden fixtures 说明与 smoke 占位**

`tests/fixtures/__init__.py`:
```python
# golden 样例图与期望结果
```

`tests/fixtures/README.md`:
```markdown
# golden 测试样例

放置固定样例图与期望结果(坐标/置信度带容差)。每新增一个识别场景:
1. 在此目录放 `<场景>.png` 与 `<场景>.expected.json`。
2. 在 `tests/unit/` 或 `tests/smoke/` 写断言:坐标允许 ±N 像素、置信度 ±0.05。

golden 用于防止模型/预处理改动悄悄改变行为。
```

`tests/smoke/__init__.py`:
```python
# 冒烟测试(加载真实模型)
```

`tests/smoke/test_smoke_placeholder.py`:
```python
import pytest


@pytest.mark.smoke
def test_real_model_smoke_placeholder():
    """占位:接入真实权重后,在此加载模型跑端到端。

    运行方式:uv run pytest -m smoke
    默认 CI 用 -m 'not smoke' 跳过(见 pyproject.toml)。
    """
    pytest.skip("尚未配置真实权重;放好 models_store 后实现")
```

- [ ] **Step 3: 运行 lint 与类型检查**

Run:
```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
```
Expected: ruff 无错误(必要时 `uv run ruff check --fix`、`uv run ruff format`);mypy 通过。逐项修复直到全绿。

- [ ] **Step 4: 安装并运行 pre-commit**

Run:
```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
Expected: 全部 hook 通过(或自动修复后再次运行通过)。

- [ ] **Step 5: 补 `CLAUDE.md` 常用命令段**

把 `CLAUDE.md` 中"常用命令"占位段替换为:

```markdown
## 常用命令

```bash
uv sync --extra dev            # 安装开发依赖
uv run pytest                  # 跑测试(默认跳过 smoke)
uv run pytest -m smoke         # 跑真实模型冒烟测试
uv run pytest tests/unit/test_xxx.py::test_name -v   # 跑单个测试
uv run ruff check src tests    # lint
uv run ruff format src tests   # 格式化
uv run mypy                    # 类型检查
uv run pre-commit run --all-files   # 全量质量门禁
uv run ocr-yolo serve          # 启动服务
uv run ocr-yolo infer img.png --methods ocr   # 本地单图推理
```
```

并把"架构"占位段替换为一句指向 spec/plan 的说明:

```markdown
## 架构

分层单体:`service`(FastAPI/v1)→ `concurrency`(有界池+模型锁)→ `preprocessing`(通道统一/ROI 回映射)→ `recognizers`(ocr/yolo/template 统一抽象)→ `models.registry`/`templates.store`(资产管理)。识别器只吃预处理图、吐基于输入图坐标的 `RawDetection`,坐标回映射与归一化统一在 `preprocessing.finalize_detections`。详见 `docs/specs/2026-06-03-recognition-service-design.md` 与 `docs/plans/2026-06-03-recognition-service.md`。
```

- [ ] **Step 6: 全量测试 + 收尾提交**

Run: `uv run pytest -v`
Expected: 全部 PASS。

```bash
git add .pre-commit-config.yaml tests/fixtures tests/smoke CLAUDE.md
git commit -m "build(quality): 接入 pre-commit、lint/type 门禁与测试约定"
```

- [ ] **Step 7: 推送**

```bash
git push origin master
```
Expected: 推送成功。

---

## Self-Review（计划对照 spec 的覆盖检查）

逐条核对 spec 第 2 节"目标(首版交付)":

| spec 目标 | 对应任务 |
|---|---|
| FastAPI `/v1` 版本化路由 | Task 17 |
| 三识别器统一抽象与结果结构 | Task 7、10、11、12 |
| 模型注册表(按名加载/版本/LRU/卸载重载) | Task 8 |
| 模板库(加载/版本/缓存) | Task 9 |
| 统一预处理(通道统一/ROI 回映射/上限) | Task 6 |
| 并发与背压(有界池/模型锁/503) | Task 13 |
| 统一错误契约 | Task 3、17(异常处理器) |
| 结构化日志 + request_id | Task 14、17 |
| CPU/GPU 配置 + 懒加载 + extras + 两套 Dockerfile | Task 1(extras/懒加载)、2(device)、21(Docker) |
| 可测试接缝(抽象/可注入 fake/golden) | Task 7、15(fakes)、18、22(golden 约定) |
| 质量门禁 ruff+mypy+pytest+pre-commit | Task 1、22 |
| 独立训练入口(运行时不导入) | Task 20(含隔离测试) |
| 基础鉴权 API Key | Task 16 |
| 图片来源 base64/路径白名单/上传 | Task 5(加载)、17(upload 端点) |
| `/health`、`/ready`、`/models`、`/templates` | Task 17 |
| 输入大小/分辨率上限、防穿越、防 decompression bomb | Task 5、6 |
| debug 标注图 | 预留(`debug_image=None`),首版接口已留字段,标注图绘制列为后续 |

**非目标对齐**:不执行 UI 动作(本服务只返回坐标);结果缓存仅留位(未实现);ROI 框架已落地但默认核心已通;`/recognize` 合并按串行实现(Task 17 循环 methods)。均与 spec 第 2 节非目标一致。

**占位扫描**:无 TODO/TBD 残留于实现代码;`debug_image`、smoke 占位、ROI 均为 spec 明确的"预留/后续",非计划缺口。

**类型一致性**:`RawDetection`(7)字段被 `finalize_detections`(6)、`FakeRecognizer`(15)、各识别器(10/11/12)一致使用;`AppContext`(15)被 runner(17)、routes(17)、conftest(18)一致使用;`ModelSpec`/`TemplateSpec` 在 registry/store/config_loader 一致。

---

## 执行交接

计划已就绪。两种执行方式:

1. **子代理逐任务执行(推荐)** — 每个任务派发独立子代理,任务间我来 review,迭代快。
2. **本会话内执行** — 用 executing-plans,分批执行 + 检查点。

请选择执行方式。
