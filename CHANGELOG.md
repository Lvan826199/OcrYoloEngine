# 更新日志

本项目的所有重要变更都会记录在本文件中。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 新增
- **AI 助手规则单源化**：`CLAUDE.md` 作为唯一规则源，`AGENTS.md` 只作为 Codex 入口引用 `CLAUDE.md`，不再复制规则正文，避免两份规范漂移；新增可复用 skill `skills/agent-rules-single-source`，便于在其他仓库落地同一规范。
- **自定义 YOLO 模型训练端到端教程**：`training/README.md` 重写为完整教程（采集 → 标注 → 组织数据集 → 训练 → 看懂结果 → 上线服务 → 迭代）；新增 `training/make_demo_dataset.py` 零标注合成数据集生成器（5 分钟 demo 通道）。CPU 实测全流程：40 轮训练 2.2 分钟、mAP50 两类均 0.995、自训模型经服务 `/v1/detect` 检出目标坐标偏差 <0.005。`train.py` 修复无 GPU 机器默认参数必崩的问题（默认自动选设备），训练完打印权重路径与上线三步提示。教程含「预标注自举」流程：用第一版模型批量预标注（`yolo predict save_txt`），人工只修不画，实测预标坐标与真值偏差 <0.003。
- **`X-Request-ID` 响应头**：所有响应（成功与错误）都带该头，与 body 的 `request_id` 一致，便于调用方/网关做日志关联。
- **JSON 结构化访问日志**：每个请求记一条（method / path / status / elapsed_ms / request_id），与现有 JSON 日志同格式。
- **夜间真实模型冒烟流水线**：`.github/workflows/smoke.yml` 每日定时 + 手动触发跑 `pytest -m smoke`，缓存 uv 依赖、PaddleOCR 模型与 yolov8n 权重。
- **覆盖率门禁**：`scripts/check.sh` 的测试步骤加 `--cov-fail-under=85`（当前实测 88%），防覆盖率滑坡。
- **真实游戏截图固定回归**：`tests/fixtures/` 收录开源游戏 SuperTuxKart 的两张真实截图（菜单 + 竞速 HUD，Wikimedia Commons，CC BY-SA 4.0，来源见该目录 README）。默认套件新增"从菜单截图裁真实按钮再找回"的模板匹配回归与防爆炸保护回归；冒烟套件新增真实 PaddleOCR 读 HUD 文字（计时器/圈数/赛道名）、读菜单标签、真实 yolov8n 检出画面角色 3 个用例。测试 143→148（默认 140 + 冒烟 8），全部通过。

### 变更
- **expected.json 字段规范**：`tests/fixtures/` 的期望结果文件统一字段结构（`scene`/`scene_size`/`description` + 按方法分组的 `expectations`），3 个既有文件迁移到位；新增 `scripts/gen_expected.py` 对样例图跑真实识别生成期望草稿，保证"期望值出自真实运行"。规范写入 `tests/fixtures/README.md`。
- **bug 修复日志改为长期文档**：迁移至 `docs/bug修复日志.md`（倒序累积，现象/根因/修法/验证），`plan/` 目录今后只放计划类文档；文档同步策略与 Bug 修复策略正式写入 `CLAUDE.md`。
- **跨机共享的项目记忆**：新增根目录 `MEMORY.md`（工作偏好 + 跨会话注意事项），由 `CLAUDE.md` 经 `@MEMORY.md` import 自动加载，随 git 在多台电脑间同步。
- **本地工具配置隔离**：`.claude/`、`.agent/`、`.agents/`、`.codex/`、`.Codex/` 统一视为本机私有目录，只放权限、缓存、机器路径等内容，不跨工具同步、不入库。

### 修复
- **工程收口修复批次**：结果缓存键保留 `methods` / `templates` 原始顺序，避免 `merge=priority` 等顺序敏感请求串缓存；Docker 镜像显式带上开箱 demo 小体积 fixture，根目录 `.dockerignore` 才作为真实构建上下文过滤规则；API Key 401 与请求校验 422 统一返回 `{request_id,error_code,message,details}`；运行配置补充范围约束；`/v1/recognize/upload` 补齐 `roi/debug/cache/merge` 字段；Windows 路径白名单比较支持大小写不敏感路径。新增 14 个默认测试，默认测试 149→163（含冒烟共 171）。
- **upload 解码前限额补齐**：`/v1/recognize/upload` 现在与 base64/path 输入一致，先校验 `max_image_bytes` 再解码，超限返回 `413 IMAGE_TOO_LARGE`。
- **单方式接口请求体简化**：`/v1/detect` 可只传 `image + model`，`/v1/match` 可只传 `image + templates`，不再强制额外传 `methods`；旧请求格式继续兼容。新增 3 个契约测试，默认测试 146→149（含冒烟共 157）。

## [0.2.1] - 2026-06-10

> 全量代码校验后的集中修复批次，计划见 `plan/2026-06-10-代码校验修复计划.md`,逐条修复记录见 `docs/bug修复日志.md`。

### 修复
- **错误响应 `request_id` 恒为 `"-"`**：request_id 改在 async 中间件绑定（线程池里绑定的 contextvar 传不回异常处理器），4xx/5xx 响应现在带真实 request_id，可关联日志排查。
- **`/v1/recognize/upload` 传非法参数返回裸 500**：非法 `methods`、yolo 缺 `model` 等现在与 JSON 接口一致返回 422 + 校验详情。
- **指标遗漏失败请求**：超时/过载/识别异常现在记入 `oye_requests_total{status="error"}`，此前只统计成功。
- **解压炸弹防护**：图片字节上限改在解码前校验（base64 与本地路径两条加载路径），恶意小文件无法再先吃光内存。
- **模板匹配候选框爆炸**：模板未配置相似度门槛时借用的全局门槛设 0.5 下限 + 每缩放档候选 top-200 截断；显式配置的门槛不受影响。设计见 ADR 0005。
- **超时后背压失真**：并发槽位改在任务真正结束时归还，超时的僵尸任务不再提前释放名额放新请求涌入。设计见 ADR 0006。
- **依赖前向兼容**：锁定 `paddleocr>=2.7,<3`（3.x 移除了现用 API，新装环境会启动失败）。

### 变更
- **性能**：结果缓存键改为哈希原始压缩字节（免去对解码后大数组做 sha256）；模型注册表改 per-name 加载锁（慢加载不再阻塞其他模型取用）；模板匹配（线程安全）不再被模型锁串行；upload 接口消除重复解码；模板灰度图按名缓存。
- **清理**：移除从未生效的 `OYE_WARMUP` 配置；API Key 改常数时间比较；服务关停时正确关闭推理线程池；JSON 日志增加 UTC 时间戳 `time` 字段；`serve` 在候选端口全被占用时明确报错（此前静默用必然失败的端口）。
- 测试新增 16 个（默认 122→138，含真实冒烟共 143 个，全部通过）。

## [0.2.0] - 2026-06-09

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

[未发布]: https://gitee.com/xiaozai-van-liu/OcrYoloEngine/compare/v0.2.1...HEAD
[0.2.1]: https://gitee.com/xiaozai-van-liu/OcrYoloEngine/compare/v0.2.0...v0.2.1
[0.2.0]: https://gitee.com/xiaozai-van-liu/OcrYoloEngine/releases/tag/v0.2.0
