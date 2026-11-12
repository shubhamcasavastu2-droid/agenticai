from __future__ import annotations

from typing import TYPE_CHECKING

from rich.prompt import Prompt

if TYPE_CHECKING:
    from ..cli import CLI
    from . import CommandRegistry


async def plan_command(cli: CLI, args: list[str]) -> None:
    """Create a plan by hand and present it for approval."""
    if not cli.interactive:
        cli.console.print("[yellow]/plan requires an interactive terminal[/yellow]")
        return
    title = Prompt.ask("[bold cyan]Plan title[/bold cyan]")
    summary = Prompt.ask("[bold cyan]Summary[/bold cyan]")
    steps = [s.strip() for s in Prompt.ask("[bold cyan]Steps (comma-separated)[/bold cyan]").split(",") if s.strip()]
    if not steps:
        cli.console.print("[red]At least one step is required[/red]")
        return
    risks_input = Prompt.ask("[bold cyan]Risks (comma-separated, optional)[/bold cyan]", default="")
    risks = [r.strip() for r in risks_input.split(",") if r.strip()]
    result = await cli.present_plan(title, summary, steps, risks)
    cli.console.print(f"[green]{result}[/green]")


async def ask_command(cli: CLI, args: list[str]) -> None:
    """Ask a question, optionally with fixed choices."""
    if not cli.interactive:
        cli.console.print("[yellow]/ask requires an interactive terminal[/yellow]")
        return
    question = Prompt.ask("[bold cyan]Question[/bold cyan]")
    options_input = Prompt.ask("[bold cyan]Options (comma-separated, optional)[/bold cyan]", default="")
    options = [o.strip() for o in options_input.split(",") if o.strip()] or None
    answer = await cli.ask_user(question, options)
    cli.console.print(f"[green]Answer: {answer}[/green]")


def register(registry: CommandRegistry) -> None:
    registry.add("plan", "/plan", "Create a plan and present it for approval", plan_command)
    registry.add("ask", "/ask", "Ask a question, optionally with fixed choices", ask_command)
