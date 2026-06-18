---
name: agent-rules-single-source
description: Set up or audit single-source AI assistant rules for repositories that use Claude Code, Codex, AGENTS.md, CLAUDE.md, MEMORY.md, or local tool config folders such as .claude, .agent, .agents, .codex, and .Codex. Use when Codex needs to create, migrate, standardize, or document assistant-rule files across one or more repos while avoiding duplicated rules, config drift, and accidental commits of local permissions or machine-specific settings.
---

# Agent Rules Single Source

## Core Pattern

Use three layers:

1. `CLAUDE.md`: the only complete rule source.
2. `AGENTS.md`: a thin Codex entrypoint that points to `CLAUDE.md`.
3. `MEMORY.md`: optional shared non-sensitive project memory.

Keep local tool folders private:

- `.claude/`
- `.agent/`
- `.agents/`
- `.codex/`
- `.Codex/`

These folders are for local permissions, caches, machine paths, temporary state, or tool-specific settings. Do not synchronize them across tools and do not commit them.

## Setup Workflow

1. Inspect existing `CLAUDE.md`, `AGENTS.md`, `MEMORY.md`, `.gitignore`, and local tool folders.
2. Move all durable assistant rules into `CLAUDE.md`.
3. Replace `AGENTS.md` with a small entrypoint that tells Codex to read `CLAUDE.md`.
4. Keep `MEMORY.md` only for non-sensitive shared preferences and cross-session notes.
5. Add all local tool folders to `.gitignore`.
6. Remove generator scripts, duplicated rule copies, or sync tests that only exist to keep `CLAUDE.md` and `AGENTS.md` identical.
7. Update project docs or changelog if the repository tracks workflow changes.
8. Run the repo's normal validation before committing.

## AGENTS.md Template

Use this as the default content:

```md
# AGENTS.md

This file provides guidance to Codex when working with code in this repository.

## 唯一规则源

本仓库的完整 AI 助手规则以 `CLAUDE.md` 为唯一权威来源。

Codex 在本仓库开始任何工作前，必须先读取并遵守 `CLAUDE.md`。`CLAUDE.md` 中出现的 “Claude Code” / “Claude” 对 Codex 等价适用；其中涉及本地工具配置目录的 `.claude` / `~/.claude`，在 Codex 场景下等价理解为 `.Codex` / `~/.Codex`，除非某条规则明确只针对 Claude Code。

以后新增或调整助手规则时，只修改 `CLAUDE.md`，不要在 `AGENTS.md` 复制规则正文。
```

## .gitignore Template

Add this block, adjusting names only if the repository has a known different local-config convention:

```gitignore
# AI 助手本地配置（权限、缓存、机器路径等只留本机，不跨工具同步、不入库）
.claude/
.agent/
.agents/
.codex/
.Codex/
```

## MEMORY.md Guidance

Use `MEMORY.md` for shared, non-sensitive project memory:

- user workflow preferences
- cross-session project notes
- repo-specific gotchas
- decisions that should survive across machines

Do not put secrets, tokens, credentials, private machine paths, or tool permission allowlists in `MEMORY.md`.

## Audit Checklist

Before finishing, verify:

- `AGENTS.md` does not duplicate the full rule body.
- `CLAUDE.md` contains the complete durable rule set.
- `.gitignore` ignores local AI tool folders.
- `.claude/`, `.agent/`, `.agents/`, `.codex/`, and `.Codex/` are not tracked.
- Documentation says rules live in `CLAUDE.md`, `AGENTS.md` is only an entrypoint, and local tool configs stay private.
- No sync script is required unless the user explicitly wants generated copies.
