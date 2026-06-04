# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言要求（强制）

**在本仓库内，Claude Code 的所有输出一律使用简体中文。**

- 与用户对话、解释、总结、报告：必须使用简体中文。
- 代码注释、提交信息（commit message）、文档（`.md`）：使用简体中文。
- 仅以下内容保留英文：代码标识符（变量/函数/类名等）、第三方库名、命令行命令、文件路径、URL、以及约定俗成的英文术语（如 OCR、YOLO、ONNX）。
- 即使用户用英文提问，也使用简体中文回答。

## 项目状态

首版骨架已实现(22 个任务全 TDD 完成):FastAPI `/v1` 服务、OCR/YOLO/模板匹配三识别器、模型注册表与模板库、并发背压、鉴权、CLI、隔离训练入口、CPU/GPU 镜像与质量门禁,81 个测试全绿。后续工作见 `docs/DEVELOPMENT.md` 进度表与 `README.md` 路线图。**模型权重不入库,需另行获取并在 `configs/models.yaml` 登记。**

## 文档引用规则（强制）

本仓库的开发主线由以下文档承载，**每个会话开始前先读 `docs/DEVELOPMENT.md` 掌握进度与约定**：

| 文档 | 作用 |
|------|------|
| `docs/README.md` | **文档中心索引**，按分类归档导航 |
| `docs/DEVELOPMENT.md` | **开发主线索引 + 进度表 + 约定速查**，跨会话接手的第一入口 |
| `docs/specs/2026-06-03-recognition-service-design.md` | 设计 spec：需求与架构的权威来源 |
| `docs/plans/2026-06-03-recognition-service.md` | 实现计划：逐任务 TDD 步骤与完整代码 |
| `docs/adr/` | 架构决策记录（MADR），重要技术取舍逐条记录 |

规则：

- **每完成一个任务**，回 `docs/DEVELOPMENT.md` 更新「进度表」（标 ✅ + 完成日期）。
- 改动 spec / plan 后，必须同步 `docs/DEVELOPMENT.md` 的进度与约定。
- 新增或调整工作规则时，同步进本文件（CLAUDE.md）与 `README.md`。
- 有用户可见变更时更新 `CHANGELOG.md`；涉及架构取舍时在 `docs/adr/` 新增一条。

## 报错必修（强制）

**存在任何报错（测试失败、`ruff`/`mypy` 报错、构建失败）必须先修复，修复后全绿才允许 `git commit` / `git push`。** 严禁带着已知报错提交或推送代码。

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
uv run ocr-yolo serve          # 启动服务
uv run ocr-yolo infer img.png --methods ocr   # 本地单图推理
```

## 架构

分层单体:`service`(FastAPI/v1)→ `concurrency`(有界池+模型锁)→ `preprocessing`(通道统一/ROI 回映射)→ `recognizers`(ocr/yolo/template 统一抽象)→ `models.registry`/`templates.store`(资产管理)。识别器只吃预处理图、吐基于输入图坐标的 `RawDetection`,坐标回映射与归一化统一在 `preprocessing.finalize_detections`。详见 `docs/specs/2026-06-03-recognition-service-design.md` 与 `docs/plans/2026-06-03-recognition-service.md`。
