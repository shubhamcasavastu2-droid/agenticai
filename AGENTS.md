# AIAgests Workspace — Agent Guidance

This workspace is a git superproject of four submodules (see `.gitmodules`). `backend/` (Agentic CLI) is the project under active development; `browser-harness/`, `scientific-agent-skills/` and `openclaw/` are vendored forks of upstream projects. Read the relevant subproject's docs before working in it.

## Workspace Structure

```
/Users/glbtech/PycharmProjects/AIAgests/
├── .gitmodules                 # Submodule URLs
├── backend/                    # Agentic CLI (Python) — submodule, JaiBharat27/aiagentic
├── browser-harness/            # CDP browser automation harness (Python)
├── kilo.json                   # Kilo CLI configuration (this workspace)
├── openclaw/                   # OpenClaw agent platform (TypeScript/Node.js)
├── rae-work/                   # Empty placeholder (untracked)
└── scientific-agent-skills/    # Collection of scientific Agent Skills (Python)
```

## Subproject Overview

### backend/ (Agentic CLI)
**Purpose**: Minimal, provider-agnostic coding agent CLI (any OpenAI-compatible API).
**Language**: Python 3.11+ (uv)
**Key files**:
- `src/cli.py` — REPL, providers, display and permission callbacks
- `src/commands/` — slash commands (registry, core, permission, skills, agents, interaction)
- `src/agent.py` — agent loop (max steps, loop guard, context compaction hook)
- `src/provider.py` — OpenAI-compatible client (retries, streaming)
- `src/context.py` — context-window estimation and compaction
- `src/completion.py` — completion reviewer
- `src/permissions.py`, `src/shell_safety.py` — permission gate, path jail, bash safety rules
- `src/session.py` — JSONL session transcripts (`/resume`)
- `.agents/skills/`, `.agents/agents/` — skills and agents loaded by the CLI

**Commands** (run from `backend/`):
```bash
uv sync --extra dev
uv run python -m src.cli
uv run ruff check src tests
uv run pytest -q
```

### browser-harness/
**Purpose**: Thin CDP layer connecting agents to browsers.  
**Language**: Python 3.12+  
**Key files**:
- `src/browser_harness/admin.py` — daemon lifecycle, diagnostics, updates, profiles
- `src/browser_harness/daemon.py` — long-lived middleman between browser and agent
- `src/browser_harness/helpers.py` — CDP wrapper and browser primitives
- `src/browser_harness/run.py` — `browser-harness` CLI entry point
- `SKILL.md` — agent skill definition (name: `browser-use`)
- `install.md` — installation and troubleshooting guide
- `agent-workspace/` — agent-editable area (helpers, domain skills)

**Commands** (run from this directory):
```bash
./browser-harness --doctor          # check install/daemon/browser state
./browser-harness <<<'print(page_info())'  # smoke test (needs Chrome remote debugging)
uv run --with pytest python -m pytest tests/unit -q  # unit tests
./browser-harness --reload          # reload daemon after src changes
```

### scientific-agent-skills/
**Purpose**: Curated collection of Agent Skills for science/research. Each skill in `skills/<name>/` follows the Agent Skills specification.  
**Language**: Python 3.12+ (per-skill isolated environments)  
**Key files**:
- `plugin.json` — Agent Plugins manifest (root)
- `skills/<name>/SKILL.md` — required skill definition
- `skills/<name>/references/` — long-form documentation (loaded on demand)
- `skills/<name>/scripts/` — executable helpers
- `skills/<name>/assets/` — templates and static resources
- `tests/<name>/` — skill tests (never under `skills/`)
- `tests/_meta/` — repo-wide guard (validates all skills, plugin.json, versions)
- `tests/skill-requirements.toml` — per-skill dependencies for isolated testing
- `scan_skills.py` — skill discovery and validation
- `scan_pr_skills.py` — PR skill scanning wrapper

**Common commands**:
```bash
uv sync
uv run skills-ref validate skills/<name>           # validate one skill
uv run --with pytest python -m pytest tests/_meta -q  # repo-wide guard
uv run --with pytest python tests/run_all.py --isolated <name>  # isolated skill tests
uv run python scan_pr_skills.py skills/<name>      # security scan (needs SKILL_SCANNER_LLM_API_KEY)
```

### openclaw/
**Purpose**: OpenClaw agent platform — Gateway, Control UI, plugins, and CLI.  
**Language**: TypeScript (Node.js 20+, pnpm)  
**Key directories**:
- `src/` — core Gateway, agents, channels, plugins, storage
- `ui/` — Control UI (SolidJS, Vite)
- `extensions/` — user-facing plugins (integrations)
- `packages/` — internal npm packages
- `crates/` — Rust components
- `scripts/` — build, test, release tooling
- `docs/` — documentation (markdown, generated)
- `skills/` — internal agent skills
- `.agents/skills/` — agent-specific skills

**Common commands**:
```bash
pnpm install
pnpm dev                    # dev Gateway + UI
pnpm test                   # run tests (see docs/help/testing/suites.md)
pnpm build                  # production build
pnpm openclaw ...           # CLI commands
pnpm docs:list              # list documentation
```

### rae-work/
Empty placeholder directory. (`.github/` and `.vscode/` at the root are local-only and ignored.)

## Cross-Project Notes

- **Kilo configuration**: `kilo.json` at workspace root configures the default model, permissions, the browser-harness MCP server (`uv run --extra mcp browser-harness-mcp`; run `uv sync --extra mcp` in `browser-harness/` once), and skill paths for both `browser-harness/skills` and `scientific-agent-skills/skills`.
- **Vendored forks**: don't add local files to `browser-harness/`, `scientific-agent-skills/` or `openclaw/` (e.g. a local skill there breaks the fork's contract tests). Local skills go in `backend/.agents/skills/`.
- **No shared dependencies**: Each subproject manages its own dependencies and environments. Do not assume packages from one are available in another.
- **Agent instructions**: When working in a subproject, read its `AGENTS.md` first. Subproject `AGENTS.md` files are authoritative for their directory.
- **Skills**: The `skills` config in `kilo.json` points to both skill collections. Use the `skill` tool to load a specific skill by name.

## Quick Reference

| Task | Location | Command |
|------|----------|---------|
| Agentic CLI | `backend/` | `uv run python -m src.cli` |
| Browser automation | `browser-harness/` | `./browser-harness` |
| Scientific skills | `scientific-agent-skills/skills/` | `uv run skills-ref validate skills/<name>` |
| OpenClaw platform | `openclaw/` | `pnpm dev` / `pnpm openclaw` |
| Validate all skills | `scientific-agent-skills/` | `uv run --with pytest python -m pytest tests/_meta -q` |
| Run Kilo | workspace root | `kilo` |