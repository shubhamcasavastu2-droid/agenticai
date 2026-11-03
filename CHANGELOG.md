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

