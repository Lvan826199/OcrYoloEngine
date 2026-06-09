# 更新日志

本项目的所有重要变更都会记录在本文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- **资产配置改为 `.example` 模板模式**：`configs/models.yaml`、`configs/templates.yaml` 不再入库(改为 gitignore)，改为入库 `*.yaml.example` 模板(含 `yolov8n`/`demo_block` demo)。`config_loader` 在实际文件不存在时**自动回退**读取 `.example`，因此装完仍开箱即用；用户 `cp` 一份改自己的配置则不会与上游冲突、不会误提交。新增 3 个回退测试(默认测试 119→122，共 127 全绿)。
- 初始化项目脚手架：README、CLAUDE.md、贡献指南、行为准则、许可证、ADR 模板。
- 视觉识别服务设计文档（spec）与分阶段实现计划。
- 开发主线文档 `docs/DEVELOPMENT.md`（文档地图 + 进度表 + 约定速查）。
- CLAUDE.md 增补「文档引用规则」与「报错必修」强制规则；README 增设「开发文档」入口。
- 文档分类整理:`docs/specs`、`docs/plans`、`docs/adr`,并新增 `docs/README.md` 文档中心索引。
- **视觉识别服务首版骨架(22 个任务,全 TDD)**:
  - 工程脚手架(uv + pyproject + ruff/mypy/pytest)、集中配置 `settings`、统一错误契约 `errors`、数据模型 `schemas`。
  - 图片加载(base64/本地路径白名单防穿越)与预处理(通道统一、输入上限、ROI 裁剪与坐标回映射)。
  - 识别器统一抽象 + 三识别器:模板匹配(多尺度 + 归一化 SAD + NMS)、PaddleOCR、YOLO(均重依赖懒加载)。
  - 模型注册表(懒加载 + LRU + 卸载/重载)与模板库(加载缓存 + 版本)。
  - 并发工作池(有界池 + 每模型锁 + 背压 503 / 超时 504)、结构化日志 + request_id。
  - FastAPI `/v1` 路由(ocr/detect/match/recognize/upload/models/templates/health/ready)、API Key 鉴权、依赖注入与可注入 fake。
  - CLI(`serve`/`infer`)、隔离训练入口 `training/`、CPU/GPU Dockerfile、pre-commit 质量门禁。
  - 测试:单元 + HTTP 契约 + golden/smoke 约定,81 个测试全绿。
- 架构决策记录 ADR 0002:模板匹配采用归一化 SAD 置信度。
- 移除全部第三方 Claude Code 插件引用(保留 claude-hud),文档去除插件相关命名。
- 新增**使用指南** `docs/guide/`:快速开始、小白操作文档、使用文档(API/CLI/配置/错误码)、部署文档(本地/Docker/调优)、项目详细文档(流程/核心技术/架构);完善 README 的快速开始/使用方法/部署。
- `uv.lock` 纳入版本管理(锁定依赖版本)。
- 文档收敛:整合为 6 个中文文件名文档(项目说明/快速开始/使用文档/部署文档/设计与决策/开发说明),移除分散的 guide/specs/plans/adr 目录。
- **测试改造为真实数据**:移除全部假识别器(`FakeRecognizer`),契约/管线/模板测试改用真实 `TemplateRecognizer` + 真实图;新增真实模型冒烟测试(真实 PaddleOCR / yolov8n / 模板 HTTP 端到端);写入「测试用真实数据(强制)」规则与 `.env.example`。
- `debug=true` 时返回识别结果的**标注图**(在原图上画框,base64 PNG)。
- 新增**模型热管理 HTTP 接口**:`POST /v1/models/{name}/unload`、`POST /v1/models/{name}/reload`(不重启切换/刷新模型)。
- 新增 **golden 真实样例回归测试**(`tests/fixtures/` 提交确定性样例图 + 期望结果)。
- 新增**持续集成**:`scripts/check.sh`(门禁单一事实来源)、`Makefile` 快捷命令、`.github/workflows/ci.yml`(GitHub Actions),并说明 Gitee Go 接入方式。
- 新增 **Prometheus 指标端点** `GET /metrics`:各识别方法的请求数与推理累计耗时(零额外依赖,文本暴露格式)。
- **Docker 改用 uv**:CPU/GPU 镜像由 `pip install` 改为 `uv sync --frozen --no-dev --extra ocr --extra yolo`,按 `uv.lock` 安装,与开发/CI 同工具链、版本可复现、构建更快。
- 新增**可插拔结果缓存(默认关闭)**:`OYE_RESULT_CACHE_SIZE=0` 时核心管线零开销、行为与现状一致;开启后对相同图 + 参数的请求命中缓存直接返回。支持请求级三模式 `cache`(`auto`/`refresh`/`off`)、`from_cache` 字段与 `X-Cache` 响应头(HIT/MISS/BYPASS)、TTL 过期与 LRU 淘汰;模型 `unload`/`reload` 自动清空缓存;新增指标 `oye_cache_events_total{event="hit|miss"}`。设计见 ADR 0003。
- 新增 **`/recognize` 可插拔多方法合并策略**:`RecognizeRequest.merge`(`none`/`priority`/`dedup`/`concat`,默认 `none` 即现状,`merged=None`)、`RecognizeResponse.merged` 统一检测列表。`priority` 按 `methods` 顺序命中即停(省后续算力)、`dedup` 跨方法 NMS 去重(IoU ≥ 0.5)、`concat` 按置信度降序汇总;仅 `/recognize` 生效,单方法端点不受影响。与结果缓存兼容(缓存键含 `merge`、`merged` 进缓存,不同策略不串味)。设计见 ADR 0004。

### 修复
- **本地路径传图绕过文件大小限制**:`load_from_path` 现在返回原始字节用于大小校验,修复了 `OYE_MAX_IMAGE_BYTES` 对本地路径传图无效的问题。
- **OCR 的 `auto` 设备设置被忽略**:`OYE_DEVICE=auto` 时 OCR 现在正确检测 GPU 可用性,而非始终走 CPU。
- **OCR 引擎懒加载竞态**:加入双重检查锁,防止并发首次调用时重复创建引擎实例。
- **base64 图片双重解码浪费**:重构 `_load_bytes_and_image`,base64 只解码一次同时获得原始字节和图像。

### 变更
- 文档同步:`项目说明`/`使用文档`/`部署文档`/`开发说明`/`设计与决策` 更新真实数据测试、新端点(`/metrics`、模型热管理)、debug 标注图、Docker(uv)等;去除过时的 fake/计数描述。
- **全量文档小白友好化改写**:6 个核心文档 + README 全部重写为通俗易懂的简体中文,去除大量专业术语（如 LRU/NMS/IoU/背压/依赖注入/pydantic 等）,改用大白话解释,保持技术准确性。README 路线图更新为实际完成状态。
- 开发说明新增"需要手动测试的部分"清单,标注出自动化测试无法覆盖的 5 个功能点。
- **文档体系梳理**：消除使用文档、接口集成指南、快速开始之间的大量重复内容。接口集成指南精简为纯代码指南(862→300行)；快速开始合并两个版本为单一流程(403→110行)；各文档职责明确，互相引用而非重复。Swagger `/docs` 页面已有完整中文描述，作为字段参考的权威来源。
- **开箱即用体验优化**：`configs/templates.yaml.example` 预置 `demo_block` 示例模板(指向仓库自带 golden 图片)、`configs/models.yaml.example` 预置 `yolov8n` 通用检测模型(含 COCO 常用类名),安装完即可发请求验证(靠自动回退读 `.example`)。
- **快速开始文档重构**：模板匹配(零额外依赖)替代 OCR 成为首个体验步骤；示例改为跨平台 Python 代码(不再依赖 `base64` shell 命令)；新增 pip 备选安装方案；新增 Python 集成示例。
- 使用文档加强 `/v1/ocr` 与其他接口请求格式差异的警示。
- README 使用方法改为 Python 示例 + 模板匹配优先展示。
- 新增 **接口集成指南**（`docs/接口集成指南.md`）：面向平台对接的 Python 客户端类（纯标准库、零依赖）+ 调用示例 + 重试策略 + 完整对接示例。
- `ocr-yolo serve` 启动时**自动检测端口占用**：默认端口 8000 被占时自动尝试 8001~8009，找到空闲端口后提示并使用。
- 启动时打印 `http://localhost:端口/docs` 地址（不再显示 `0.0.0.0`，Windows 浏览器无法访问）。
- 访问根路径 `/` 自动跳转到 `/docs` 接口文档页面（之前返回 404）。

[未发布]: https://gitee.com/xiaozai-van-liu/OcrYoloEngine/compare/master...HEAD
