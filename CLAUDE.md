# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目记忆（自动加载，跨机共享）

@MEMORY.md

仓库根目录的 `MEMORY.md` 是跨机共享的项目记忆（上方已通过 import 自动加载）：新增「重要记忆」（工作偏好、跨会话注意事项）写入该文件并随 git 提交；本机 `~/.claude` 持久 memory 只放机器特定内容。两边冲突时以 `MEMORY.md` 为准。

## 语言要求（强制）

**在本仓库内，Claude Code 的所有输出一律使用简体中文。**

- 与用户对话、解释、总结、报告：必须使用简体中文。
- 代码注释、提交信息（commit message）、文档（`.md`）：使用简体中文。
- 仅以下内容保留英文：代码标识符（变量/函数/类名等）、第三方库名、命令行命令、文件路径、URL、以及约定俗成的英文术语（如 OCR、YOLO、ONNX）。
- 即使用户用英文提问，也使用简体中文回答。

## 项目状态

首版骨架 + 全部增强已完成(22 个基础任务 + 首版后增强 + v0.2.1 代码校验修复批次):FastAPI `/v1` 服务、OCR/YOLO/模板匹配三识别器、模型注册表与模板库、并发限流、鉴权、CLI、隔离训练入口、CPU/GPU 镜像(uv 构建)与质量门禁。debug 标注图、模型热卸载/重载、Prometheus `/metrics`、可插拔结果缓存、多方法合并策略等增强已落地。默认 143 + 真实冒烟 8 共 151 个测试全绿。修复/优化批次的计划放 `plan/`、修复日志记 `docs/bug修复日志.md`。后续工作见 `docs/开发说明.md` 进度表与 `README.md` 路线图。**模型权重不入库,需另行获取并在 `configs/models.yaml` 登记;资产配置采用 `.example` 模板入库 + 实际文件 gitignore + 加载时自动回退读 `.example`(开箱即用且规范)。**

## 文档引用与同步策略（强制）

本仓库的文档已收敛为 `docs/` 下 7 个扁平的中文文件，**每个会话开始前先读 `docs/开发说明.md` 掌握进度与约定**：

| 文档 | 作用 |
|------|------|
| `docs/项目说明.md` | **项目说明 + 文档导航**：流程/核心技术/架构，顶部含文档导航表 |
| `docs/快速开始.md` | 快速开始(5 分钟)+ 从零开始的小白手把手 |
| `docs/使用文档.md` | 使用指南：API / CLI / 配置 / 错误码 |
| `docs/接口集成指南.md` | 平台对接：Python 客户端类 + 所有接口调用代码 + 返回结构速查 |
| `docs/部署文档.md` | 部署指南：本地 / Docker / 调优 / 安全 |
| `docs/设计与决策.md` | 设计 spec(需求与架构的权威来源)+ 架构决策记录(ADR/MADR) |
| `docs/开发说明.md` | **开发主线索引 + 进度表 + 任务清单 + 约定速查**，跨会话接手的第一入口 |
| `docs/bug修复日志.md` | **长期累积的 bug 修复记录**（倒序），每条按「现象/根因/修法/验证」 |
| `MEMORY.md`（根目录） | **跨机共享的项目记忆**：工作偏好 + 跨会话注意事项，经 `@import` 自动加载 |

目录职责：`docs/` 放长期维护的文档（含修复日志）；`plan/` 只放**计划类**文档（一次性的批次方案，命名 `YYYY-MM-DD-xxx.md`），不放日志。

同步时机（**每完成一个任务/批次就同步，不积压**）：

- **每完成一个任务**，回 `docs/开发说明.md` 更新「进度表」（标 ✅ + 完成日期）。
- 改动设计 / 架构后，必须同步 `docs/开发说明.md` 的进度与约定。
- 新增或调整工作规则时，同步进本文件（CLAUDE.md）与 `README.md`。
- 有用户可见变更时更新 `CHANGELOG.md`；涉及架构取舍时在 `docs/设计与决策.md` 的「架构决策记录」一节新增一条 ADR。
- 修了 bug 必须在 `docs/bug修复日志.md` 追加记录（见下节）。
- 接口 / 配置 / 错误码变化时同步 `docs/使用文档.md` 与 `docs/接口集成指南.md`；部署方式变化时同步 `docs/部署文档.md`。
- 测试数量、版本号等事实数据变化时，同步本文件「项目状态」、`README.md`、`docs/开发说明.md` 三处的计数。

## Bug 修复策略（强制）

1. **先计划**：批次性修复/优化开工前，把方案写入 `plan/YYYY-MM-DD-<主题>.md`（问题清单 + 位置 + 修法 + 批次划分），不在对话里散落。
2. **TDD 逐条修**：每个 bug 先写失败测试（真实数据）跑红，再修复跑绿；按批次提交（Conventional Commits）。
3. **每修一条记日志**：在 `docs/bug修复日志.md` 追加记录，格式固定为「**现象 → 根因 → 修法 → 验证**」；新批次放文件**最上方**（倒序），批次标题带日期与版本号。该文件长期累积、只增不删。
4. **明确不修的要留痕**：评估后决定不修的项，连同理由记入修复日志「明确不改」小节，避免后续会话当成新发现重复评估。
5. **收尾做文档同步**：按上节「同步时机」逐项核对（CHANGELOG、进度表、ADR、计数）。

## 报错必修（强制）

**存在任何报错（测试失败、`ruff`/`mypy` 报错、构建失败）必须先修复，修复后全绿才允许 `git commit` / `git push`。** 严禁带着已知报错提交或推送代码。

## 测试用真实数据（强制）

**测试一律使用真实数据与真实依赖，不得用 mock / 假实现替代被测对象的核心行为。**

- 图像处理、模板匹配、预处理、并发等:用**真实图片**(`numpy`/`cv2` 生成或样例图)、真实线程、真实文件,断言真实输出。
- OCR / YOLO:用**真实模型**端到端验证(PaddleOCR 真实推理、YOLO 加载真实权重如 `yolov8n.pt`),放在 `tests/smoke/` 并打 `@pytest.mark.smoke`,通过 `uv run pytest -m smoke` 运行。
- HTTP / 服务层:优先用**真实识别器**(如真实 `TemplateRecognizer` + 真实模板图)做端到端契约测试,而非注入假识别器。
- 仅当某外部依赖在该测试环境**确实无法获得**时,才允许临时替身,且**必须有对应的真实冒烟测试兜底**,并在测试里注明原因。
- 新增功能时,真实数据测试与代码同批提交;`tests/fixtures/` 放样例图与期望结果(坐标/置信度带容差)。
- 期望结果文件(`*.expected.json`)必须遵循 `tests/fixtures/README.md` 的字段规范;**期望值必须出自真实运行**,用 `scripts/gen_expected.py` 生成草稿后人工审定容差入库。

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
