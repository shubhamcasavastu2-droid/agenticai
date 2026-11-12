from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from ..cli import CLI
    from . import CommandRegistry

PERMISSION_HELP = """
**Permission Commands:**
- `/permission` or `/permission list` - Show current permissions
- `/permission allow <tool> [always|auto]` - Allow a tool without prompting for this session
- `/permission deny <tool> [always]` - Return a tool to prompting, or deny it outright
- `/permission reset` - Restore default permissions

**Interactive prompt options:** `y` allow once, `a` allow always, `u` auto-allow,
`n` deny once, `d` deny always. Safety rules for bash apply in every mode.
"""


def show_permissions(cli: CLI) -> None:
    table = Table(title="Tool Permissions", border_style="blue")
    table.add_column("Tool", style="cyan")
    table.add_column("Default", style="yellow")
    table.add_column("Current", style="green")
    table.add_column("Description", style="white")
    gate = cli.permission_gate
    for tool in cli.registry.all():
        default = "auto" if tool.name in gate.default_auto_allow else "prompt"
        table.add_row(tool.name, default, gate.mode(tool.name), tool.description)
    cli.console.print(table)


async def permission_command(cli: CLI, args: list[str]) -> None:
    tool_names = [t.name for t in cli.registry.all()]
    gate = cli.permission_gate
    subcommand = args[0].lower() if args else "list"

    if subcommand == "list":
        show_permissions(cli)
        return
    if subcommand == "reset":
        gate.reset()
        cli.console.print("[green]All permissions reset to defaults[/green]")
        return
    if subcommand not in {"allow", "deny"}:
        cli.console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
        cli.console.print(Panel(Markdown(PERMISSION_HELP), title="Permission Help", border_style="blue"))
        return
    if len(args) < 2:
        cli.console.print(f"[red]Usage: /permission {subcommand} <tool-name> [...][/red]")
        return
    tool_name = args[1]
    if tool_name not in tool_names:
        cli.console.print(f"[red]Unknown tool: {tool_name}. Available: {', '.join(tool_names)}[/red]")
        return
    mode = args[2].lower() if len(args) > 2 else ""

    if subcommand == "allow":
        if mode == "always":
            gate.allow_always(tool_name)
            cli.console.print(f"[green]Permission set: {tool_name} = always[/green]")
        elif mode == "auto":
            gate.allow_auto(tool_name)
            cli.console.print(f"[green]Permission set: {tool_name} = auto (no prompts)[/green]")
        else:
            gate.clear(tool_name)
            cli.console.print(f"[green]Permission set: {tool_name} = prompt (will ask each time)[/green]")
    elif mode == "always":
        gate.deny(tool_name)
        cli.console.print(f"[red]Permission set: {tool_name} = denied always[/red]")
    else:
        gate.clear(tool_name)
        cli.console.print(f"[yellow]Permission set: {tool_name} = prompt (will ask each time)[/yellow]")


def register(registry: CommandRegistry) -> None:
    registry.add(
        "permission", "/permission [list|allow|deny|reset]", "View or set tool permissions", permission_command
    )
