# Changelog

## [8d2cdbcd] - 2026-11-03
- **Type**: feat
- **Author**: jaibharat27
- **Description**: Initial Agentic CLI with 6 tools, agent loop, permissions, CLI
- **Files** (60):
  - feat: src/__init__.py, src/agent.py, src/cli.py, src/config.py, src/permissions.py ... (+11 more)
  - docs: README.md, package_structure.md
  - test: tests/__init__.py, tests/__pycache__/__init__.cpython-310.pyc, tests/__pycache__/test_tools.cpython-310-pytest-9.1.1.pyc, tests/test_tools.py
  - chore: .env, .env.example, .vscode/launch.json, .vscode/settings.json, pyproject.toml ... (+33 more)

## [22227769] - 2026-11-03
- **Type**: feat
- **Author**: jaibharat27
- **Description**: Add /permission slash command to view and manage tool permissions
- **Files** (4):
  - feat: src/cli.py
  - docs: CHANGELOG.md
  - chore: src/__pycache__/cli.cpython-310.pyc, src/__pycache__/cli.cpython-314.pyc

## [6e03fbd4] - 2026-11-03
- **Type**: feat
- **Author**: jaibharat27
- **Description**: Add reasoning display in console and interactive permission prompts for ALL tools with options: allow once, always, auto, deny, deny always
- **Files** (16):
  - feat: src/agent.py, src/cli.py, src/permissions.py, src/provider.py, src/types.py
  - docs: CHANGELOG.md
  - chore: src/__pycache__/agent.cpython-310.pyc, src/__pycache__/agent.cpython-314.pyc, src/__pycache__/cli.cpython-310.pyc, src/__pycache__/cli.cpython-314.pyc, src/__pycache__/permissions.cpython-310.pyc ... (+5 more)

## [dd7a35e5] - 2026-11-04
- **Type**: feat
- **Author**: jaibharat27
- **Description**: Add skills and agents support with .md format (industrial standard): .agents/skills/<name>/SKILL.md, .agents/agents/<name>.md, agents/agents.md, /skills and /agents commands
- **Files** (20):
  - feat: src/agents.py, src/cli.py, src/skills.py, src/system_prompt.py
  - docs: .agents/agents/code-reviewer.md, .agents/agents/example-agent.md, .agents/skills/example-skill/SKILL.md, .agents/skills/my-new-skill/SKILL.md, CHANGELOG.md ... (+1 more)
  - chore: pyproject.toml, src/__pycache__/agents.cpython-310.pyc, src/__pycache__/agents.cpython-314.pyc, src/__pycache__/cli.cpython-310.pyc, src/__pycache__/cli.cpython-314.pyc ... (+5 more)

## [63070a9a] - 2026-11-04
- **Type**: fix
- **Author**: jaibharat27
- **Description**: Fix issues from audit: console script entry, tool output truncation config, duplicate permission_help, missing imports
- **Files** (43):
  - feat: src/__init__.py, src/agent.py, src/agents.py, src/cli.py, src/config.py ... (+13 more)
  - docs: CHANGELOG.md, projectfile.md
  - test: tests/__init__.py, tests/__pycache__/__init__.cpython-314.pyc, tests/__pycache__/test_tools.cpython-314-pytest-9.2.0.pyc, tests/test_tools.py
  - chore: pyproject.toml, src/__pycache__/__init__.cpython-314.pyc, src/__pycache__/agent.cpython-314.pyc, src/__pycache__/agents.cpython-314.pyc, src/__pycache__/cli.cpython-314.pyc ... (+14 more)

