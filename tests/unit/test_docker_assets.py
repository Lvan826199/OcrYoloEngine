"""Docker 构建上下文与开箱 demo 资产的守门测试。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_root_dockerignore_keeps_context_small_but_allows_demo_fixtures():
    """文档从仓库根目录 build,因此根 .dockerignore 才是实际生效的文件。"""
    ignore_path = ROOT / ".dockerignore"
    assert ignore_path.is_file()
    body = ignore_path.read_text(encoding="utf-8")

    assert "tests/**" in body
    assert "!tests/fixtures/golden_patch.png" in body
    assert "!tests/fixtures/golden_scene.png" in body
    assert not (ROOT / "docker" / ".dockerignore").exists()


def test_dockerfiles_copy_demo_template_assets():
    """示例模板配置指向 tests/fixtures/golden_patch.png,镜像里必须复制该小资产。"""
    for name in ("Dockerfile.cpu", "Dockerfile.gpu"):
        body = (ROOT / "docker" / name).read_text(encoding="utf-8")
        assert "COPY tests/fixtures/golden_patch.png ./tests/fixtures/golden_patch.png" in body
        assert "COPY tests/fixtures/golden_scene.png ./tests/fixtures/golden_scene.png" in body
