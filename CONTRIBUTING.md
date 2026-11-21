# Contributing to Agentic CLI

Thank you for your interest in contributing to Agentic CLI! This document outlines the process and guidelines for contributing.

## Code Style

We use **ruff** for linting and formatting:

```bash
# Check code style
uv run ruff check src tests

# Auto-fix issues
uv run ruff check --fix src tests

# Format code
uv run ruff format src tests
```

### Python Version
- Minimum: Python 3.11
- Target: Python 3.11+

### Type Hints
- All public APIs must have type hints
- Use `from __future__ import annotations` for forward references
- Run `uv run mypy src` to check types (if mypy is configured)

## Testing

### Running Tests
```bash
# Run all tests
uv run pytest -q

# Run with coverage
uv run pytest --cov=src --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_tools.py -v
```

### Writing Tests
- Place tests in `tests/` directory
- Use `@pytest.mark.asyncio` for async tests
- Use `tempfile.TemporaryDirectory` for file system tests
- Follow existing patterns in `tests/test_tools.py` and `tests/test_agent.py`
- Mock external dependencies (HTTP, filesystem) using `httpx.MockTransport` or similar

### Test Requirements
- All new features must have tests
- Bug fixes must include a regression test
- Maintain or improve test coverage

## Pull Request Process

1. **Fork the repository** and create a feature branch
2. **Make your changes** following the code style guidelines
3. **Run the full test suite** and ensure all tests pass
4. **Run linting** (`uv run ruff check src tests`)
5. **Update documentation** if needed (README, docstrings, etc.)
6. **Submit a PR** with a clear description of changes

### PR Requirements
- All CI checks must pass
- Code must be formatted with ruff
- Type hints for new public APIs
- Tests for new functionality
- Update CHANGELOG.md if applicable

## Commit Messages

Follow conventional commits format:
```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(tools): add new grep tool with regex support
fix(agent): handle empty response retry correctly
docs: update README with new configuration options
```

## Development Setup

```bash
# Clone and enter project
cd backend

# Install dependencies with dev extras
uv sync --extra dev

# Install pre-commit hooks (optional)
uv run pre-commit install
```

## Architecture Overview

The codebase follows a layered architecture:

```
src/
├── cli.py              # REPL, slash commands, display
├── core/agent.py       # Agent loop, step execution
├── provider.py         # Provider abstraction + OpenAI-compatible impl
├── tools/              # Tool implementations
├── security/           # Permissions, shell safety
├── commands/           # Slash command implementations
├── config.py           # Configuration from env/file
├── logger.py           # Rotating file log with secret redaction
├── session.py          # JSONL session transcripts
├── context.py          # Context-window estimation and compaction
├── completion.py       # Completion reviewer
├── prompt/             # System prompt builder
├── types.py            # Internal message format
└── ui/                 # Display and theme
```

## Adding New Tools

1. Create a new file in `src/tools/` (e.g., `my_tool.py`)
2. Implement a class inheriting from `Tool` base class
3. Define a `ToolSchema` with JSON Schema parameters
4. Register the tool in `src/tools/registry.py` or via `Application`
5. Add tests in `tests/test_tools.py`

## Security Considerations

- All file operations must use `validate_path()` from `security.permissions`
- Shell commands go through `shell_safety.find_denied_reason()`
- Never log API keys or secrets (logger redacts automatically)
- Path traversal is prevented by `validate_path()` using `os.path.commonpath`

## Questions?

Open an issue or start a discussion for any questions about contributing.
