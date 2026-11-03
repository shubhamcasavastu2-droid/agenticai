from __future__ import annotations

import platform
from datetime import datetime
from pathlib import Path


SYSTEM_PROMPT_TEMPLATE = """You are an agentic coding assistant. You help users by reading, writing, and running code in their project.

# Environment
- Working directory: {working_dir}
- OS: {os_name} {os_version}
- Date: {date}
- Shell: {shell}

# Tools
You have access to these tools:
{tool_descriptions}

# Rules
1. **Read before editing** - Always read a file before making changes to it.
2. **Minimal changes** - Make the smallest change that solves the problem.
3. **Verify** - Run tests or commands to verify your changes work.
4. **Don't claim success without checking** - Actually run the code, don't just say it works.
5. **Be concise** - Keep responses short. Show tool calls, not explanations.
6. **Follow project conventions** - Match existing code style, patterns, and architecture.

# Workflow
- When given a task, first explore the codebase to understand it.
- Use read_file, glob, grep to gather information.
- Make changes with write_file, edit_file.
- Run commands with bash to test.
- Report results clearly.

# Slash commands (handled by the CLI, not you)
- /help - Show help
- /clear - Clear conversation history
- /model - Show/change model
- /exit - Exit the CLI
"""

AGENT_MD_CONTENT = """# Project Instructions

This file is auto-loaded as additional context for the agent.
Add project-specific guidelines, conventions, and important information here.
"""


def build_system_prompt(
    project_root: Path,
    tool_descriptions: str,
    agent_md_path: Path | None = None,
) -> str:
    working_dir = str(project_root)
    os_name = platform.system()
    os_version = platform.release()
    date = datetime.now().strftime("%Y-%m-%d")
    shell = os.environ.get("SHELL", "unknown")

    prompt = SYSTEM_PROMPT_TEMPLATE.format(
        working_dir=working_dir,
        os_name=os_name,
        os_version=os_version,
        date=date,
        shell=shell,
        tool_descriptions=tool_descriptions,
    )

    # Load AGENT.md if it exists
    if agent_md_path and agent_md_path.exists():
        try:
            with open(agent_md_path, "r") as f:
                agent_md = f.read().strip()
            if agent_md:
                prompt += f"\n\n# Project Instructions (from AGENT.md)\n{agent_md}"
        except Exception:
            pass

    return prompt


def get_tool_descriptions(tools: list) -> str:
    lines = []
    for tool in tools:
        lines.append(f"- **{tool.name}**: {tool.description}")
    return "\n".join(lines)


import os