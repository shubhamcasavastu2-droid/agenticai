# AIAgests Workspace — Claude Instructions

This workspace is a git superproject of four submodules (see `.gitmodules`). `backend/` is the project under active development; the other three are vendored forks of upstream tools. Read the relevant subproject's `AGENTS.md`/`README.md` before working in it.

## Subprojects

| Directory | Purpose | Language | Key Commands |
|-----------|---------|----------|--------------|
| `backend/` | **Agentic CLI** — provider-agnostic coding agent (own repo: JaiBharat27/aiagentic) | Python 3.11+ | `uv run python -m src.cli`, `uv run pytest -q`, `uv run ruff check src tests` |
| `browser-harness/` | CDP browser automation harness (fork of browser-use/browser-harness) | Python 3.11+ | `./browser-harness --doctor`, `uv run pytest tests/unit -q` |
| `scientific-agent-skills/` | Scientific Agent Skills collection (fork of K-Dense-AI/scientific-agent-skills) | Python 3.13+ | `uv run skills-ref validate skills/<name>`, `uv run pytest tests/_meta -q` |
| `openclaw/` | OpenClaw agent platform (fork of openclaw/openclaw) | TypeScript/Node.js 24+ | `pnpm dev`, `pnpm test`, `pnpm openclaw` |
| `rae-work/` | Empty placeholder (untracked) | — | — |

## Quick Start

```bash
# Fresh clone
git clone --recurse-submodules <this repo>

# Agentic CLI (from backend/)
uv sync --extra dev
uv run python -m src.cli

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

- **Kilo config**: `kilo.json` at workspace root — sets model, permissions, the browser-harness MCP server (`uv run --extra mcp browser-harness-mcp`, needs `uv sync --extra mcp` in `browser-harness/`), and skill paths.
- **Each subproject has its own**: `AGENTS.md`, `CLAUDE.md` (where applicable), and dependency management.

## Notes

- No shared dependencies across subprojects.
- Don't modify vendored forks (browser-harness, scientific-agent-skills, openclaw) for local needs; put local skills in `backend/.agents/skills/`.
- Sync forks from upstream with `git -C <dir> fetch upstream && git -C <dir> merge upstream/main` (add the `upstream` remote first).
- Skills are loaded from both `browser-harness/skills/` and `scientific-agent-skills/skills/` via `kilo.json`.
- For browser work, use `./browser-harness` from the `browser-harness/` directory to pick up local source changes.