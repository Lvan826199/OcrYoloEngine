#!/usr/bin/env bash
# 全量质量门禁:依赖同步 + lint + 格式 + 类型 + 测试。
# CI 与本地共用的"单一事实来源";任一步失败即非零退出(报错必修)。
set -euo pipefail
export PATH="$HOME/.local/bin:$PATH"

echo "==> uv sync (dev)"
uv sync --extra dev

echo "==> ruff check"
uv run ruff check src tests

echo "==> ruff format --check"
uv run ruff format --check src tests

echo "==> mypy"
uv run mypy

echo "==> pytest(默认跳过 smoke,覆盖率门禁 85%)"
uv run pytest -q --cov=ocr_yolo_engine --cov-fail-under=85

echo "✅ 全部门禁通过"
