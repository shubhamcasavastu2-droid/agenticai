# AIAgests Workspace — Agent Guidance

This workspace contains multiple independent projects. Each subdirectory has its own `AGENTS.md` with detailed guidance — read the relevant one before working in that project.

## Workspace Structure

```
/Users/glbtech/PycharmProjects/AIAgests/
├── .github/                    # GitHub Actions workflows (workspace-level)
├── backend/                    # Empty — placeholder for future backend services
├── browser-harness/            # CDP browser automation harness (Python)
├── kilo.json                   # Kilo CLI configuration (this workspace)
├── openclaw/                   # OpenClaw agent platform (TypeScript/Node.js)
├── rae-work/                   # Empty — placeholder for RAE work
└── scientific-agent-skills/    # Collection of scientific Agent Skills (Python)
```

## Subproject Overview

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

### .github/
Workspace-level GitHub Actions:
- `modernize/java-upgrade/` — Java modernization workflow (hooks, scripts)

### backend/ and rae-work/
Empty placeholder directories for future work.

## Cross-Project Notes

- **Kilo configuration**: `kilo.json` at workspace root configures default model (Claude Sonnet 4), permissions, MCP servers, and skill paths for both `browser-harness/skills` and `scientific-agent-skills/skills`.
- **No shared dependencies**: Each subproject manages its own dependencies and environments. Do not assume packages from one are available in another.
- **Agent instructions**: When working in a subproject, read its `AGENTS.md` first. Subproject `AGENTS.md` files are authoritative for their directory.
- **Skills**: The `skills` config in `kilo.json` points to both skill collections. Use the `skill` tool to load a specific skill by name.

## Quick Reference

| Task | Location | Command |
|------|----------|---------|
| Browser automation | `browser-harness/` | `./browser-harness` |
| Scientific skills | `scientific-agent-skills/skills/` | `uv run skills-ref validate skills/<name>` |
| OpenClaw platform | `openclaw/` | `pnpm dev` / `pnpm openclaw` |
| Validate all skills | `scientific-agent-skills/` | `uv run --with pytest python -m pytest tests/_meta -q` |
| Run Kilo | workspace root | `kilo` |