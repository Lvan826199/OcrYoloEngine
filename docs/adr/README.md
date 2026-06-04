# 架构决策记录（ADR）

本目录用于记录项目中重要的架构决策（Architecture Decision Records）。

模板采用 [MADR](https://github.com/adr/madr)。每当做出会影响架构的重要选择（例如选用哪种 YOLO 版本、哪个 OCR 后端、推理框架等），就新增一条记录。

## 约定

- 文件命名：`NNNN-简短标题.md`，编号四位、递增，例如 `0001-记录架构决策.md`。
- 决策一旦写下不要删除；若被推翻，新增一条并把旧记录状态改为「已废弃 / 被 NNNN 取代」。
- 复制 [`template.md`](template.md) 作为新记录的起点。

## 索引

- 0001 - 记录架构决策（见 [`0001-record-architecture-decisions.md`](0001-record-architecture-decisions.md)）
- 0002 - 模板匹配采用归一化 SAD 置信度（见 [`0002-template-matching-scoring.md`](0002-template-matching-scoring.md)）
