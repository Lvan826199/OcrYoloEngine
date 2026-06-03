# 开发文档（持续更新）

> 本文件是**跨会话的开发主线索引**,每完成一个任务都要回来更新「进度表」。
> 新会话接手时,先读本文件即可掌握:项目定位、文档分布、当前进度、关键约定、如何继续。

- 最近更新:2026-06-03
- 当前阶段:Task 1-9 已完成,识别器抽象与资产管理就绪

---

## 1. 一句话定位

`OcrYoloEngine` 是面向**自动化测试**的视觉识别 HTTP 服务:其他自动化脚本截图发来,本服务用 OCR / YOLO / 模板匹配识别,返回坐标、文字、置信度,**只识别、不执行动作**。

---

## 2. 文档地图（权威来源,改动需同步)

| 文档 | 作用 | 何时更新 |
|---|---|---|
| `docs/README.md` | **文档中心索引**:按分类(specs/plans/adr)归档导航 | 新增文档分类或条目时 |
| `docs/specs/2026-06-03-recognition-service-design.md` | **设计 spec**:背景/范围/架构/数据模型/接口/测试/安全等,需求与架构的权威来源 | 需求或架构变化时 |
| `docs/plans/2026-06-03-recognition-service.md` | **实现计划**:22 任务、8 阶段,逐任务 TDD 步骤与完整代码 | 任务拆分或实现策略调整时 |
| `docs/DEVELOPMENT.md`(本文件) | **开发主线索引 + 进度表 + 约定速查** | 每完成一个任务 |
| `docs/adr/` | 架构决策记录(MADR) | 做出重要技术取舍时新增一条 |
| `CLAUDE.md` | 给 Claude Code 的工作规则(语言/提交/文档引用/报错必修等) | 规则变化时 |
| `README.md` | 门面型说明 + 文档入口 | 对外信息变化时 |
| `CHANGELOG.md` | 变更记录(Keep a Changelog) | 每次有用户可见变更 |

**规则**:以上文档互为引用;改了 spec/plan 必须回本文件更新进度与约定,改了规则必须同步进 CLAUDE.md 与 README.md。

---

## 3. 进度表（每完成一任务勾选并写完成日期)

阶段与任务详见实现计划。状态:⬜ 未开始 / 🟡 进行中 / ✅ 已完成。

| # | 任务 | 状态 | 完成日期 |
|---|---|---|---|
| 0-1 | 工程脚手架与工具链 | ✅ | 2026-06-03 |
| 0-2 | 配置 settings.py | ✅ | 2026-06-03 |
| 0-3 | 错误契约 errors.py | ✅ | 2026-06-03 |
| 0-4 | 数据模型 schemas.py | ✅ | 2026-06-03 |
| 1-5 | 图片加载 loader.py | ✅ | 2026-06-03 |
| 1-6 | 预处理 pipeline.py | ✅ | 2026-06-03 |
| 2-7 | 识别器抽象 base.py | ✅ | 2026-06-03 |
| 2-8 | 模型注册表 registry.py | ✅ | 2026-06-03 |
| 2-9 | 模板库 store.py | ✅ | 2026-06-03 |
| 2-10 | 模板匹配识别器 template.py | ⬜ | |
| 2-11 | OCR 识别器 ocr.py | ⬜ | |
| 2-12 | YOLO 识别器 yolo.py | ⬜ | |
| 3-13 | 工作池 executor.py | ⬜ | |
| 4-14 | 结构化日志 logging.py | ⬜ | |
| 5-15 | 配置加载 + DI + fakes | ⬜ | |
| 5-16 | API Key 鉴权 auth.py | ⬜ | |
| 5-17 | 识别管线 + FastAPI 路由 | ⬜ | |
| 5-18 | HTTP 契约测试 | ⬜ | |
| 6-19 | CLI cli.py | ⬜ | |
| 7-20 | 隔离训练入口 training/ | ⬜ | |
| 7-21 | configs + 资产目录 + Docker | ⬜ | |
| 7-22 | 质量门禁(pre-commit + 门禁) | ⬜ | |

---

## 4. 关键约定速查（实现时务必遵守)

- **坐标契约**:识别器只吃预处理图,吐基于**输入图**坐标的 `RawDetection`;偏移回映射与归一化统一在 `preprocessing.finalize_detections`,识别器内部绝不自己做。
- **重依赖懒加载**:`torch`/`paddle` 只在对应识别器首次推理时 import,顶层与 `--help`/轻量命令不触发。
- **可测试接缝**:服务层、并发层、识别器全部可注入 fake;`tests/fakes/` 提供 `FakeRecognizer`,单测/契约测试不加载真实模型。
- **训练隔离**:`training/` 独立目录,`src/` 任何文件**不得** import,有测试 `test_training_isolation.py` 守门。
- **统一错误契约**:成功无目标 = 200 + 空 detections(不是错误);失败才 4xx/5xx + `error_code`。
- **每任务 TDD**:写失败测试 → 跑红 → 最小实现 → 跑绿 → 提交,每个大任务至少 3 个小步骤逐步实现逐步测试。
- **报错必修**:存在任何报错(测试失败、lint/type 报错)必须修复后才允许 commit/push。
- **提交规范**:Conventional Commits,描述用简体中文(见 CLAUDE.md)。

---

## 5. 环境与常用命令

```bash
uv sync --extra dev                 # 安装开发依赖
uv run pytest                       # 跑测试(默认跳过 smoke)
uv run pytest -m smoke              # 真实模型冒烟测试
uv run ruff check src tests         # lint
uv run mypy                         # 类型检查
uv run pre-commit run --all-files   # 全量质量门禁
uv run ocr-yolo serve               # 启动服务
```

> 所有 git 与项目命令都在 `MyProject/OcrYoloEngine/` 内执行;父级 `MyProject/.claude/` 不属于本仓库。

---

## 6. 后续会话如何接手

1. 读本文件 → 看「进度表」确定下一个 ⬜/🟡 任务。
2. 打开实现计划对应任务,按 TDD 步骤执行(完整代码已在计划里)。
3. 跑测试 + lint + type,**全绿**后 commit(报错必修)。
4. 回本文件把该任务标 ✅ 并写完成日期;有用户可见变更时更新 `CHANGELOG.md`。
5. 涉及架构取舍时在 `docs/adr/` 新增一条 ADR。
