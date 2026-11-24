"""
Session command sub-package.

Handles /session slash command: creates, switches, or manages user sessions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from ...cli import CLI
    from .. import CommandRegistry

SESSION_HELP = """
**Session Commands:**
- `/session` or `/session list` - List saved sessions
- `/session resume <session-id>` - Resume a saved session
- `/session switch <session-id>` - Switch to an existing session
- `/session new <name>` - Create a new session
"""

async def session_command(cli: CLI, args: list[str]) -> None:
    subcommand = args[0].lower() if args else "list"
    if subcommand == "list":
        sessions = cli.session.list_sessions()
        if not sessions:
            cli._ui.warning("No saved sessions")
            return
        table = Table(title="Saved Sessions", border_style="ui.border")
        table.add_column("Session", style="cyan")
        table.add_column("Messages", style="yellow", justify="right")
        table.add_column("Last updated", style="white")
        for session_id, count, modified in sessions[:20]:
            marker = " (current)" if session_id == cli.session.session_id else ""
            table.add_row(session_id + marker, str(count), modified.strftime("%Y-%m-%d %H:%M"))
        cli._ui.console.print(table)
        return
    if subcommand in ("resume", "switch"):
        if len(args) < 2:
            cli._ui.error(f"Usage: /session {subcommand} <session-id>")
            return
        if cli.agent_loop is None:
            cli._ui.error("Agent is not initialized")
            return
        try:
            messages = cli.session.load(args[1])
        except FileNotFoundError as error:
            cli._ui.error(f"{error}")
            return
        cli.agent_loop.clear_history()
        cli.agent_loop.state.messages.extend(messages)
        cli._ui.console.print(
            f"[status.success]Resumed session {cli.session.session_id} ({len(messages)} messages)[/status.success]"
        )
    elif subcommand == "new":
        name = args[1] if len(args) > 1 else None
        cli.session.new_session(name)
        cli._ui.success(f"Created new session: {cli.session.session_id}")
    else:
        cli._ui.error(f"Unknown session subcommand: {subcommand}")
        cli._ui.console.print(Panel(Markdown(SESSION_HELP), title="Session Help", border_style="cyan"))


def register(registry: CommandRegistry) -> None:
    registry.add(
        "session", "/session [list|resume|switch|new]", "Create, switch, or manage sessions",
        session_command,
    )
