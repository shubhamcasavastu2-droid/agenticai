# Default Agent Configuration

This file is automatically loaded if it exists in the project root or `.agents/agents.md`.

## Default Agent Settings

```yaml
default_agent: code
model: anthropic/claude-sonnet
max_steps: 50
```

## Available Agents

| Agent | Description | Model |
|-------|-------------|-------|
| code | General coding assistant | claude-sonnet |
| reviewer | Code review specialist | claude-sonnet |
| tester | Test writing specialist | claude-sonnet |

## Global Permissions

Default permissions for all agents:
- read_file: auto
- write_file: prompt
- edit_file: prompt
- glob: auto
- grep: auto
- bash: prompt

## Project-Specific Instructions

Add project-specific guidance here that applies to all agents.