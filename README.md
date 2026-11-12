# Agentic CLI

A minimal agentic coding tool CLI built from scratch. Give it a coding task and it uses tools to read, edit, and run code until the task is done.

## Features

- **Provider-agnostic**: Works with any OpenAI-compatible API (Ollama, OpenAI, OpenRouter, etc.)
- **8 built-in tools**: `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `bash`, `ask_user`, `plan`
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
- `AGENTIC_BASE_URL` - OpenAI-compatible API endpoint
- `AGENTIC_API_KEY` - Provider API key; set it in your shell or secret manager, not in tracked files
- `AGENTIC_MODEL` - Model name

For NVIDIA NIM, set the API key in your terminal before starting the CLI. Keep the key out of chat and source control:

```bash
export AGENTIC_API_KEY="your-new-nvidia-api-key"
uv run python -m src.cli
```

Optional:
- `AGENTIC_PROJECT_ROOT` - Project directory (default: current directory)
- `AGENTIC_REQUEST_TIMEOUT_SECONDS` - Model request timeout in seconds (default: 300)
- `AGENTIC_MAX_COMPLETION_TOKENS` - Maximum generated tokens per response (default: 8192)
- `AGENTIC_CONTEXT_WINDOW_TOKENS` - Context budget used to compare reported prompt/completion tokens (default: 32768)
- `AGENTIC_MAX_OUTPUT_SIZE` - Tool output truncation limit (default: 8000)
- `AGENTIC_MAX_STEPS` - Max agent steps per task (default: 50)
- `AGENTIC_MAX_COMPLETION_ATTEMPTS` - Completion-review and repair attempts (default: 3)
- `AGENTIC_COMPLETION_REVIEW` - Set to `false` to skip the reviewer call (halves model calls; default: true)
- `AGENTIC_REVIEW_MODEL` - Use a different model for the completion review (default: same as `AGENTIC_MODEL`)
- `AGENTIC_MAX_RETRIES` - Retries for HTTP 408/409/429/5xx and connection errors, with exponential backoff and `Retry-After` (default: 3)
- `AGENTIC_STREAM` - Stream model output to the terminal as it is generated (default: true)
- `AGENTIC_LOG_DIR` - Log directory (default: `logs`); secrets in tool args/output are redacted
- `AGENTIC_SESSION_DIR` - Where session transcripts are saved (default: `<project>/.agentic/sessions`)

### Context management

The agent estimates prompt size before every model call (calibrated against provider-reported
usage). When it would exceed `AGENTIC_CONTEXT_WINDOW_TOKENS` minus the response reserve, older tool
outputs are elided first, then the oldest turns are dropped and replaced by a short note. The first
user message and tool-call/result pairs are always preserved.

### Provider Examples

**NVIDIA NIM**:
```bash
AGENTIC_BASE_URL=https://integrate.api.nvidia.com/v1
AGENTIC_API_KEY=your-new-nvidia-api-key
AGENTIC_MODEL=z-ai/glm-5.3-flash
```

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

**Anthropic** (OpenAI-compatible endpoint):
```bash
AGENTIC_BASE_URL=https://api.anthropic.com/v1
AGENTIC_API_KEY=sk-ant-...
AGENTIC_MODEL=claude-sonnet-5-5
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
| `/help` | Show help (generated from the command registry) |
| `/clear` | Clear conversation history and start a new session |
| `/model [name]` | Show or change model |
| `/resume [list\|<id>]` | List saved sessions or resume one (latest by default) |
| `/permission [list\|allow\|deny\|reset]` | View or set tool permissions |
| `/skills [list\|show\|create]` | List, inspect or design skills |
| `/agents [list\|show]` | List or inspect agents |
| `/plan`, `/ask` | Present a plan / ask a question manually |
| `/exit` | Exit the CLI |

### Permission Model

- **Auto-allowed**: `read_file`, `glob`, `grep` (confined to the project root)
- **Asks permission**: `write_file`, `edit_file`, `bash`
- Type `y` = allow once, `a`/`u` = allow for this session, `n` = deny, `d` = deny for this session
- **Always blocked** (even when bash is auto-allowed): `sudo`/`su`, recursive `rm`/`chmod`/`chown`
  outside the project root, `curl|wget ... | sh`, `git push --force`/`+refspec`, `dd of=/dev/...`,
  `mkfs`, fork bombs, shutdown/reboot. Rules are applied per sub-command after shell tokenizing,
  including inside `bash -c "..."` and `eval`. This is a guard rail, not a sandbox.

The agent can use `ask_user` to ask for a free-text answer or a choice from supplied options. Its `plan` tool presents a proposed plan and asks you to approve, request revisions, or reject it. These tools require an interactive terminal.

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
├── agent.py           # Agent loop (max steps, loop guard, compaction hook)
├── context.py         # Context-window estimation and compaction
├── completion.py      # Completion reviewer (optional, separate model)
├── permissions.py     # Permission gate, path validation
├── shell_safety.py    # Shell-aware bash safety rules
├── session.py         # JSONL session transcripts (/resume)
├── config.py          # Config from env/file
├── logger.py          # Rotating file log with secret redaction
├── system_prompt.py   # System prompt builder (+ AGENT.md loader)
├── commands/          # Slash commands (core, permission, skills, agents, interaction)
└── cli.py             # REPL, providers, display and permission callbacks
```

## Testing

```bash
uv sync --extra dev
uv run ruff check src tests
uv run pytest -q
```

CI (`.github/workflows/ci.yml`) runs lint and tests on Python 3.11–3.13.

## License

MIT