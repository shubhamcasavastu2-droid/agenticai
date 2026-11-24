"""
Agent command sub-package.

Handles /agent slash command: creates or updates agents based on user requirements.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from ...cli import CLI
    from .. import CommandRegistry


AGENT_HELP = """
**Agent Commands:**
- `/agent create <name> [description]` - Create a new agent
- `/agent show <name>` - Show agent details

Agents are defined in `.agents/agents/<name>.md` (YAML frontmatter).
"""


async def agent_command(cli: CLI, args: list[str]) -> None:
    subcommand = args[0].lower() if args else "list"
    if subcommand == "list":
        agents = cli.agent_loader.all()
        if not agents:
            cli._ui.warning("No agents loaded")
            return
        table = Table(title="Loaded Agents", border_style="ui.border")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Model", style="yellow")
        for agent in agents:
            table.add_row(agent.name, agent.description or "No description", agent.model)
        cli._ui.console.print(table)
    elif subcommand == "show":
        if len(args) < 2:
            cli._ui.error("Usage: /agent show <agent-name>")
            return
        agent = cli.agent_loader.get(args[1])
        if agent:
            content = f"**Name**: {agent.name}\n**Description**: {agent.description}\n**Model**: {agent.model}\n"
            if agent.tools:
                content += f"**Tools**: {', '.join(agent.tools)}\n"
            if agent.permissions:
                content += f"**Permissions**: {agent.permissions}\n"
            if agent.system_prompt:
                content += f"\n**System Prompt**:\n{agent.system_prompt[:300]}..."
            cli._ui.console.print(Panel(Markdown(content), title=f"Agent: {agent.name}", border_style="cyan"))
        else:
            cli._ui.error(f"Agent not found: {args[1]}")
    elif subcommand == "create":
        if len(args) < 2:
            cli._ui.error("Usage: /agent create <name> [description]")
            return
        # Agent creation logic would go here
        cli._ui.info(f"Creating agent: {args[1]}")
        description = " ".join(args[2:]) if len(args) > 2 else ""
        cli._ui.success(f"Agent '{args[1]}' created (conceptual) with description: {description or 'none'}")
    else:
        cli._ui.error(f"Unknown agent subcommand: {subcommand}")
        cli._ui.console.print(Panel(Markdown(AGENT_HELP), title="Agent Help", border_style="cyan"))


def register(registry: CommandRegistry) -> None:
    registry.add("agent", "/agent [list|show|create]", "Create or update agents", agent_command)
