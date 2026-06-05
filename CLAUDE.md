# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言要求（强制）

**在本仓库内，Claude Code 的所有输出一律使用简体中文。**

- 与用户对话、解释、总结、报告：必须使用简体中文。
- 代码注释、提交信息（commit message）、文档（`.md`）：使用简体中文。
- 仅以下内容保留英文：代码标识符（变量/函数/类名等）、第三方库名、命令行命令、文件路径、URL、以及约定俗成的英文术语（如 OCR、YOLO、ONNX）。
- 即使用户用英文提问，也使用简体中文回答。

## 项目状态

首版骨架 + 全部增强已完成(22 个基础任务 + 首版后增强):FastAPI `/v1` 服务、OCR/YOLO/模板匹配三识别器、模型注册表与模板库、并发限流、鉴权、CLI、隔离训练入口、CPU/GPU 镜像(uv 构建)与质量门禁。debug 标注图、模型热卸载/重载、Prometheus `/metrics`、可插拔结果缓存、多方法合并策略等增强已落地。默认 119 + 真实冒烟 5 共 124 个测试全绿,覆盖率 89%。后续工作见 `docs/开发说明.md` 进度表与 `README.md` 路线图。**模型权重不入库,需另行获取并在 `configs/models.yaml` 登记。**

## 文档引用规则（强制）

本仓库的文档已收敛为 `docs/` 下 6 个扁平的中文文件，**每个会话开始前先读 `docs/开发说明.md` 掌握进度与约定**：

| 文档 | 作用 |
|------|------|
| `docs/项目说明.md` | **项目说明 + 文档导航**：流程/核心技术/架构，顶部含 6 文件导航表 |
| `docs/快速开始.md` | 快速开始(5 分钟)+ 从零开始的小白手把手 |
| `docs/使用文档.md` | 使用指南：API / CLI / 配置 / 错误码 |
| `docs/接口集成指南.md` | 平台对接：Python 客户端类 + 所有接口调用代码 + 返回结构速查 |
| `docs/部署文档.md` | 部署指南：本地 / Docker / 调优 / 安全 |
| `docs/设计与决策.md` | 设计 spec(需求与架构的权威来源)+ 架构决策记录(ADR/MADR) |
| `docs/开发说明.md` | **开发主线索引 + 进度表 + 任务清单 + 约定速查**，跨会话接手的第一入口 |

规则：

- **每完成一个任务**，回 `docs/开发说明.md` 更新「进度表」（标 ✅ + 完成日期）。
- 改动设计 / 架构后，必须同步 `docs/开发说明.md` 的进度与约定。
- 新增或调整工作规则时，同步进本文件（CLAUDE.md）与 `README.md`。
- 有用户可见变更时更新 `CHANGELOG.md`；涉及架构取舍时在 `docs/设计与决策.md` 的「架构决策记录」一节新增一条。

## 报错必修（强制）

**存在任何报错（测试失败、`ruff`/`mypy` 报错、构建失败）必须先修复，修复后全绿才允许 `git commit` / `git push`。** 严禁带着已知报错提交或推送代码。

## 测试用真实数据（强制）

**测试一律使用真实数据与真实依赖，不得用 mock / 假实现替代被测对象的核心行为。**

- 图像处理、模板匹配、预处理、并发等:用**真实图片**(`numpy`/`cv2` 生成或样例图)、真实线程、真实文件,断言真实输出。
- OCR / YOLO:用**真实模型**端到端验证(PaddleOCR 真实推理、YOLO 加载真实权重如 `yolov8n.pt`),放在 `tests/smoke/` 并打 `@pytest.mark.smoke`,通过 `uv run pytest -m smoke` 运行。
- HTTP / 服务层:优先用**真实识别器**(如真实 `TemplateRecognizer` + 真实模板图)做端到端契约测试,而非注入假识别器。
- 仅当某外部依赖在该测试环境**确实无法获得**时,才允许临时替身,且**必须有对应的真实冒烟测试兜底**,并在测试里注明原因。
- 新增功能时,真实数据测试与代码同批提交;`tests/fixtures/` 放样例图与期望结果(坐标/置信度带容差)。

## 项目简介

`OcrYoloEngine` 是一个 OCR + YOLO 引擎。根据 `.gitignore` 判断，这是一个 **Python** 项目，使用 PyTorch / ONNX 格式的模型权重（`*.pt`、`*.pth`、`*.weights`、`*.onnx`）。这些权重文件已被 git 忽略，**不应提交入库**，需单独获取或下载。

## 仓库位置

本仓库作为更大工作区的子目录存在（`MyProject/OcrYoloEngine/`）。父级的 `MyProject/.claude/` 是本地工具配置，**不属于**本仓库。所有 git 与项目命令都应在 `OcrYoloEngine/` 目录内执行。

## Git 提交规范

提交信息**正文使用简体中文**，遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 风格。

### 格式

```
<类型>(<可选范围>): <简短描述>

<可选正文：说明改动动机与细节，每行不超过 72 字符>

<可选脚注：关联 Issue，如 "关联 #12"、"修复 #34">
```

- `<类型>` 用英文小写关键字（见下表），冒号后的**描述用简体中文**。
- 简短描述用祈使语气、不加句号，控制在 50 字符以内。
- 一次提交只做一件事；改动较大时用正文补充说明。

### 类型

| 类型 | 用途 |
|------|------|
| `feat` | 新增功能 |
| `fix` | 修复缺陷 |
| `docs` | 仅文档变更 |
| `style` | 不影响逻辑的格式调整（空格、缩进、分号等） |
| `refactor` | 重构（既非新功能也非修复缺陷） |
| `perf` | 性能优化 |
| `test` | 新增或修改测试 |
| `build` | 构建系统或依赖变更 |
| `ci` | CI 配置与脚本变更 |
| `chore` | 杂项（不影响源码或测试的日常维护） |
| `revert` | 回滚某次提交 |

### 示例

```
feat(detector): 接入 YOLO 检测模块

支持从 .pt 权重加载模型并输出文字区域候选框。

关联 #5
```

```
fix: 修复 OCR 识别区域越界导致的崩溃
```

```
docs: 完善安装说明与环境要求
```

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
uv run ocr-yolo serve          # 启动服务(默认 8000,被占自动切下一个)
uv run ocr-yolo infer img.png --methods ocr   # 本地单图推理
```

## 架构

分层单体:`service`(FastAPI/v1)→ `concurrency`(有界池+模型锁)→ `preprocessing`(通道统一/ROI 回映射)→ `recognizers`(ocr/yolo/template 统一抽象)→ `models.registry`/`templates.store`(资产管理)。识别器只吃预处理图、吐基于输入图坐标的 `RawDetection`,坐标回映射与归一化统一在 `preprocessing.finalize_detections`。详见 `docs/设计与决策.md` 与 `docs/开发说明.md`。
