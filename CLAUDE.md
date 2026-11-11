# AIAgests Workspace — Claude Instructions

This workspace contains multiple independent projects. Read the relevant subproject's `AGENTS.md` before working in it.

## Subprojects

| Directory | Purpose | Language | Key Commands |
|-----------|---------|----------|--------------|
| `browser-harness/` | CDP browser automation harness | Python 3.12+ | `./browser-harness --doctor`, `uv run pytest tests/unit -q` |
| `scientific-agent-skills/` | Scientific Agent Skills collection | Python 3.12+ | `uv run skills-ref validate skills/<name>`, `uv run pytest tests/_meta -q` |
| `openclaw/` | OpenClaw agent platform (Gateway, UI, plugins) | TypeScript/Node.js 20+ | `pnpm dev`, `pnpm test`, `pnpm openclaw` |
| `.github/` | Workspace-level GitHub Actions | — | — |
| `backend/` | Empty placeholder | — | — |
| `rae-work/` | Empty placeholder | — | — |

## Quick Start

```bash
# Browser automation (from browser-harness/)
./browser-harness --doctor
./browser-harness <<<'print(page_info())'

# Scientific skills (from scientific-agent-skills/)
uv sync
uv run skills-ref validate skills/<name>

# OpenClaw (from openclaw/)
pnpm install
pnpm dev

# Kilo (from workspace root)
kilo
```

## Configuration

- **Kilo config**: `kilo.json` at workspace root — sets model (Claude Sonnet 4), permissions, MCP server for browser-harness, and skill paths.
- **Each subproject has its own**: `AGENTS.md`, `CLAUDE.md` (where applicable), and dependency management.

## Notes

- No shared dependencies across subprojects.
- Skills are loaded from both `browser-harness/skills/` and `scientific-agent-skills/skills/` via `kilo.json`.
- For browser work, use `./browser-harness` from the `browser-harness/` directory to pick up local source changes.