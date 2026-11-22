"""
Core Slash Commands for Agentic CLI.

This module implements the fundamental slash commands:
- /help: Display available commands and tools
- /clear: Clear conversation history and start new session
- /model: Show or change the current model
- /exit: Exit the CLI

These commands are always available and form the basic CLI interface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ..security.permissions import READ_ONLY_TOOLS

if TYPE_CHECKING:
    from ..cli import CLI
    from . import CommandRegistry


async def help_command(cli: CLI, args: list[str]) -> None:
    lines = ["**Slash Commands:**"]
    lines += [f"- `{command.usage}` - {command.summary}" for command in cli.commands.all()]
    lines += ["", "**Tools available to the agent:**"]
    lines += [f"- `{tool.name}` - {tool.description}" for tool in cli.registry.all()]
    lines += [
        "",
        "**Permission model:**",
        f"- Read-only tools ({', '.join(sorted(READ_ONLY_TOOLS))}) run automatically inside the project root",
        "- write_file, edit_file and bash ask first: `y` once, `a`/`u` for the session, `n` deny, `d` deny always",
        "- Dangerous shell commands (sudo, rm -rf outside the project, curl | sh, force-push, ...) are always blocked",
        "",
        "**Sessions:** every conversation is saved under `.agentic/sessions/`; use `/resume` to continue one.",
        "",
        "**Skills & Agents:** `.agents/skills/<name>/SKILL.md`, `.agents/agents/<name>.md`, `agents/agents.md`",
    ]
    cli.console.print(Panel(Markdown("\n".join(lines)), title="Help", border_style="blue"))


async def clear_command(cli: CLI, args: list[str]) -> None:
    if cli.agent_loop:
        cli.agent_loop.clear_history()
    cli.permission_gate.reset()
    cli.session.new_session()
    cli.console.print("[status.success]History cleared (new session started)[/status.success]")


async def model_command(cli: CLI, args: list[str]) -> None:
    if not args:
        cli.console.print(f"[ui.subheader]Current model:[/ui.subheader]  [cyan]{cli.config.model}[/cyan]")
        if cli.config.review_model:
            cli.console.print(
                f"[ui.subheader]Review model:[/ui.subheader]  [cyan]{cli.config.review_model}[/cyan]"
            )
        cli.console.print("Usage: /model <model-name>")
        return
    cli.config.model = args[0]
    await cli.rebuild_providers()
    cli.console.print(f"[status.success]Model changed to:[/status.success] {args[0]}")


async def exit_command(cli: CLI, args: list[str]) -> None:
    cli.console.print("[status.warning]Goodbye![/status.warning]")
    cli.running = False
    await cli.close()


async def workspace_command(cli: CLI, args: list[str]) -> None:
    """Change or show the current workspace directory."""
    from ..config.project_dir import Project

    if not args:
        current = Project.get_instance().project_root
        cli.console.print(
            f"[ui.subheader]Current workspace:[/ui.subheader]  [cyan]{current}[/cyan]"
        )
        cli.console.print("Usage: /workspace <directory-path>")
        return

    new_dir = args[0]
    cli.console.print(f"[status.info]Changing workspace to:[/status.info] {new_dir}")

    # Call the Application's refresh_workspace to update Project singleton
    # and re-register all tools with the new root
    app = getattr(cli, "app", None)
    if app is not None:
        await app.refresh_workspace(new_dir)
    else:
        # Fallback: update Project singleton directly
        Project.set_project_dir(new_dir)
        cli.console.print(f"[status.success]Workspace changed to:[/status.success] {new_dir}")


async def resume_command(cli: CLI, args: list[str]) -> None:
    if args and args[0] == "list":
        sessions = cli.session.list_sessions()
        if not sessions:
            cli.console.print("[status.warning]No saved sessions[/status.warning]")
            return
        table = Table(title="Saved Sessions", border_style="ui.border")
        table.add_column("Session", style="cyan")
        table.add_column("Messages", style="yellow", justify="right")
        table.add_column("Last updated", style="white")
        for session_id, count, modified in sessions[:20]:
            marker = " (current)" if session_id == cli.session.session_id else ""
            table.add_row(session_id + marker, str(count), modified.strftime("%Y-%m-%d %H:%M"))
        cli.console.print(table)
        return
    if cli.agent_loop is None:
        cli.console.print("[status.error]Agent is not initialized[/status.error]")
        return
    try:
        messages = cli.session.load(args[0] if args else None)
    except FileNotFoundError as error:
        cli.console.print(f"[status.error]{error}[/status.error]")
        return
    cli.agent_loop.clear_history()
    cli.agent_loop.state.messages.extend(messages)
    cli.console.print(
        f"[status.success]Resumed session {cli.session.session_id} ({len(messages)} messages)[/status.success]"
    )


def register(registry: CommandRegistry) -> None:
    registry.add("help", "/help", "Show this help", help_command)
    registry.add("clear", "/clear", "Clear conversation history and session permissions", clear_command)
    registry.add("model", "/model [name]", "Show or change the model", model_command)
    registry.add("resume", "/resume [list|<session-id>]", "List or resume a saved session", resume_command)
    registry.add("exit", "/exit", "Exit the CLI", exit_command)
    registry.add("workspace", "/workspace [path]", "Show or change workspace directory", workspace_command)
