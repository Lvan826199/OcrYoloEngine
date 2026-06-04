# 更新日志

本项目的所有重要变更都会记录在本文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
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

[未发布]: https://gitee.com/xiaozai-van-liu/OcrYoloEngine/compare/master...HEAD
