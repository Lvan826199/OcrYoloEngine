# 文档中心

本目录集中管理 `OcrYoloEngine` 的全部开发文档,按用途分类归档。**新会话或新成员从这里进入。**

## 🧭 先读这个

- [**DEVELOPMENT.md** — 开发主线索引](DEVELOPMENT.md):项目定位、文档地图、**任务进度表**、关键约定速查、接手指南。跨会话接手的第一入口。

## 📂 分类目录

| 分类 | 目录 | 内容 |
|---|---|---|
| 📐 设计文档 | [`specs/`](specs/) | 需求、范围与架构的权威来源 |
| 🗂️ 实现计划 | [`plans/`](plans/) | 分阶段、逐任务的 TDD 实现步骤与完整代码 |
| 🧭 架构决策 | [`adr/`](adr/) | 重要技术取舍的逐条记录(MADR) |

### 设计文档(specs)

- [2026-06-03 视觉识别服务设计](specs/2026-06-03-recognition-service-design.md)

### 实现计划(plans)

- [2026-06-03 视觉识别服务实现计划](plans/2026-06-03-recognition-service.md)

### 架构决策(adr)

- [ADR 索引与约定](adr/README.md)
- [0001 记录架构决策](adr/0001-record-architecture-decisions.md)
- [0002 模板匹配采用归一化 SAD 置信度](adr/0002-template-matching-scoring.md)

## 🔗 仓库根目录相关文档

- [`../README.md`](../README.md):项目门面说明与对外入口
- [`../CLAUDE.md`](../CLAUDE.md):Claude Code 工作规则(语言/提交/文档引用/报错必修)
- [`../CHANGELOG.md`](../CHANGELOG.md):变更记录(Keep a Changelog)
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md):贡献流程

## 📌 文档维护约定

- 一份文档一个职责;设计进 `specs/`,可执行步骤进 `plans/`,技术取舍进 `adr/`,进度与约定进 `DEVELOPMENT.md`。
- 每完成一个任务,回 `DEVELOPMENT.md` 更新进度表。
- 改动 spec/plan 需同步 `DEVELOPMENT.md`;调整工作规则需同步 `CLAUDE.md` 与根 `README.md`。
- 文档命名:`specs/`、`plans/` 用 `YYYY-MM-DD-<主题>.md`;`adr/` 用 `NNNN-<标题>.md`。
