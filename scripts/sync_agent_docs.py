"""从 CLAUDE.md 生成 AGENTS.md,避免两套助手规则手工漂移。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CLAUDE.md"
TARGET = ROOT / "AGENTS.md"

SOURCE_COMMENT_RE = re.compile(r"<!-- agent-doc-source:.*?-->\n\n?", re.DOTALL)
GENERATED_NOTICE = (
    "<!-- agent-doc-generated: 本文件由 CLAUDE.md 生成，请勿手改；"
    "修改 CLAUDE.md 后运行 `uv run python scripts/sync_agent_docs.py`。 -->"
)


def render_agents_text(source_text: str) -> str:
    """把 Claude 规则文本转换为 Codex 规则文本。"""
    text = SOURCE_COMMENT_RE.sub("", source_text, count=1)
    replacements = (
        ("claude.ai/code", "Codex.ai/code"),
        ("Claude Code", "Codex"),
        ("Claude", "Codex"),
        ("CLAUDE.md", "AGENTS.md"),
        ("~/.claude", "~/.Codex"),
        (".claude/", ".Codex/"),
        (".claude", ".Codex"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    text = text.replace(
        "先改本文件（AGENTS.md），再运行 `uv run python scripts/sync_agent_docs.py` 生成 `AGENTS.md`",
        "先改 `CLAUDE.md`，再运行 `uv run python scripts/sync_agent_docs.py` 生成本文件（AGENTS.md）",
    )
    text = text.replace(
        "uv run python scripts/sync_agent_docs.py   # 从 AGENTS.md 生成 AGENTS.md",
        "uv run python scripts/sync_agent_docs.py   # 从 CLAUDE.md 生成 AGENTS.md",
    )
    return text.replace("# AGENTS.md\n\n", f"# AGENTS.md\n\n{GENERATED_NOTICE}\n\n", 1)


def main() -> int:
    source_text = SOURCE.read_text(encoding="utf-8")
    TARGET.write_text(render_agents_text(source_text), encoding="utf-8")
    print(f"已从 {SOURCE.name} 生成 {TARGET.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
