# OcrYoloEngine 常用命令(本地与 CI 共用)
# 用法:make <目标>,例如 make check
UV ?= uv

.PHONY: help install install-all lint format type test smoke check serve

help:                ## 显示可用目标
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:             ## 安装开发依赖(不含 OCR/YOLO 重依赖)
	$(UV) sync --extra dev

install-all:         ## 安装含 OCR/YOLO 的全量依赖
	$(UV) sync --extra dev --extra ocr --extra yolo

lint:                ## ruff 静态检查
	$(UV) run ruff check src tests

format:              ## ruff 自动格式化
	$(UV) run ruff format src tests

type:                ## mypy 类型检查
	$(UV) run mypy

test:                ## 跑测试(默认跳过 smoke)
	$(UV) run pytest -q

smoke:               ## 跑真实模型冒烟测试(需 install-all)
	$(UV) run pytest -m smoke -q

check:               ## 全量门禁(CI 入口):lint + 格式 + 类型 + 测试
	bash scripts/check.sh

serve:               ## 启动服务
	$(UV) run ocr-yolo serve
