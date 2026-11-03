# Agentic CLI

A minimal agentic coding tool CLI built from scratch. Give it a coding task and it uses tools to read, edit, and run code until the task is done.

## Features

- **Provider-agnostic**: Works with any OpenAI-compatible API (Ollama, OpenAI, OpenRouter, etc.)
- **6 built-in tools**: `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `bash`
- **Permission gate**: Read-only tools auto-run; write tools ask for confirmation
- **Path safety**: Blocks paths outside project root, deny list for dangerous commands
- **Agent loop**: Automatic tool calling with max steps and loop detection
- **Slash commands**: `/help`, `/clear`, `/model`, `/exit`
- **Config via env/file**: `.env` or environment variables

## Installation

```bash
cd backend
uv sync
# or
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and customize:

```bash
cp .env.example .env
```

Required settings:
- `AGENTIC_BASE_URL` - OpenAI-compatible API endpoint (e.g., `http://localhost:11434/v1` for Ollama)
- `AGENTIC_API_KEY` - API key (use `ollama` for local Ollama)
- `AGENTIC_MODEL` - Model name (e.g., `llama3.1`, `gpt-4o-mini`)

Optional:
- `AGENTIC_PROJECT_ROOT` - Project directory (default: current directory)
- `AGENTIC_MAX_OUTPUT_SIZE` - Tool output truncation limit (default: 8000)
- `AGENTIC_MAX_STEPS` - Max agent steps per task (default: 50)

### Provider Examples

**Ollama (local)**:
```bash
AGENTIC_BASE_URL=http://localhost:11434/v1
AGENTIC_API_KEY=ollama
AGENTIC_MODEL=llama3.1
```

**OpenAI**:
```bash
AGENTIC_BASE_URL=https://api.openai.com/v1
AGENTIC_API_KEY=sk-...
AGENTIC_MODEL=gpt-4o-mini
```

**OpenRouter**:
```bash
AGENTIC_BASE_URL=https://openrouter.ai/api/v1
AGENTIC_API_KEY=sk-or-...
AGENTIC_MODEL=anthropic/claude-3.5-sonnet
```

## Running

```bash
# From backend directory
uv run python -m src.cli

# Or if installed
agentic-cli
```

## Usage

Start the CLI and give it a task:

```
>> Create a Python script that prints the first 10 Fibonacci numbers
```

The agent will:
1. Explore the project (if any)
2. Write the script using `write_file`
3. Run it with `bash` to verify
4. Show you the result

### Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/clear` | Clear conversation history |
| `/model [name]` | Show or change model |
| `/exit` | Exit the CLI |

### Permission Model

- **Auto-allowed**: `read_file`, `glob`, `grep`
- **Asks permission**: `write_file`, `edit_file`, `bash`
- Type `y` = allow once, `a` = always allow this session, `n` = deny

### Project Instructions (AGENT.md)

Create an `AGENT.md` in your project root to give the agent project-specific context:

```markdown
# Project Instructions

- Use pytest for tests
- Follow PEP 8 style
- Run `ruff check .` before committing
```

## Architecture

```
src/
├── types.py           # Internal message format (provider-independent)
├── provider.py        # Provider adapter interface + OpenAI-compatible impl
├── tools/
│   ├── registry.py    # Tool registry
│   ├── read_file.py
│   ├── write_file.py
│   ├── edit_file.py
│   ├── glob_tool.py
│   ├── grep_tool.py
│   └── bash_tool.py
├── agent.py           # Agent loop (MAX_STEPS, repeat detection)
├── permissions.py     # Permission gate, path validation
├── config.py          # Config from env/file
├── system_prompt.py   # System prompt builder (+ AGENT.md loader)
└── cli.py             # REPL with slash commands
```

## Testing

```bash
uv run pytest tests/ -v
```

## License

MIT