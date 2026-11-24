"""
Scheduler command sub-package.

Handles /schedule slash command (TODO placeholder).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel

if TYPE_CHECKING:
    from ...cli import CLI
    from .. import CommandRegistry


async def scheduler_command(cli: CLI, args: list[str]) -> None:
    """Scheduler command - TODO placeholder."""
    cli._ui.console.print(
        Panel(
            Markdown(
                "/schedule command is a TODO placeholder.\n"
                "No implementation yet. Schedule management will be added in a future release."
            ),
            title="Schedule",
            border_style="yellow",
        )
    )


def register(registry: CommandRegistry) -> None:
    registry.add("schedule", "/schedule", "Schedule management (TODO)", scheduler_command)
