from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from ..capabilities.agents import Agent
    from ..cli import CLI
    from . import CommandRegistry

AGENTS_HELP = """
**Agents Commands:**
- `/agents` or `/agents list` - List all agents
- `/agents show <name>` - Show agent details

Agents are defined in `.agents/agents/<name>.md` (YAML frontmatter) or `agents/agents.md`.
"""


def show_agents(cli: CLI) -> None:
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


def show_agent_detail(cli: CLI, agent: Agent) -> None:
    content = f"**Name**: {agent.name}\n**Description**: {agent.description}\n**Model**: {agent.model}\n"
    if agent.tools:
        content += f"**Tools**: {', '.join(agent.tools)}\n"
    if agent.permissions:
        content += f"**Permissions**: {agent.permissions}\n"
    if agent.system_prompt:
        content += f"\n**System Prompt**:\n{agent.system_prompt[:300]}..."
    cli._ui.console.print(Panel(Markdown(content), title=f"Agent: {agent.name}", border_style="cyan"))


async def agents_command(cli: CLI, args: list[str]) -> None:
    subcommand = args[0].lower() if args else "list"
    if subcommand == "list":
        show_agents(cli)
    elif subcommand == "show":
        if len(args) < 2:
            cli._ui.error("Usage: /agents show <agent-name>")
            return
        agent = cli.agent_loader.get(args[1])
        if agent:
            show_agent_detail(cli, agent)
        else:
            cli._ui.error(f"Agent not found: {args[1]}")
    else:
        cli._ui.error(f"Unknown agents subcommand: {subcommand}")
        cli._ui.console.print(Panel(Markdown(AGENTS_HELP), title="Agents Help", border_style="cyan"))


def register(registry: CommandRegistry) -> None:
    registry.add("agents", "/agents [list|show]", "List or inspect agents", agents_command)
