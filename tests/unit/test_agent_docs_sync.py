"""守护 CLAUDE.md 与 AGENTS.md 的生成同步关系。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load_sync_module() -> ModuleType:
    module_path = ROOT / "scripts" / "sync_agent_docs.py"
    spec = importlib.util.spec_from_file_location("sync_agent_docs", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agents_md_is_generated_from_claude_md():
    """改了 CLAUDE.md 后必须重新生成 AGENTS.md,否则本测试会失败。"""
    sync = _load_sync_module()
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert agents == sync.render_agents_text(claude)
