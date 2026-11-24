"""
Hook command sub-package.

Handles /hook slash command (TODO placeholder).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel

if TYPE_CHECKING:
    from ...cli import CLI
    from .. import CommandRegistry


async def hook_command(cli: CLI, args: list[str]) -> None:
    """Hook command - TODO placeholder."""
    cli._ui.console.print(
        Panel(
            Markdown(
                "/hook command is a TODO placeholder.\n"
                "No implementation yet. Hook management will be added in a future release."
            ),
            title="Hook",
            border_style="yellow",
        )
    )


def register(registry: CommandRegistry) -> None:
    registry.add("hook", "/hook", "Hook management (TODO)", hook_command)
