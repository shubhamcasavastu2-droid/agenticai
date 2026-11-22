from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

AGENTIC_THEME = Theme(
    {
        # Status levels
        "status.info": "bold cyan",
        "status.success": "bold green",
        "status.warning": "bold yellow",
        "status.error": "bold red",
        # UI elements
        "ui.header": "bold magenta",
        "ui.subheader": "bold cyan",
        "ui.border": "blue",
        "ui.accent": "magenta",
        # User / agent distinction
        "user.input": "bold blue",
        "agent.output": "bold green",
        # Tool calls / results
        "tool.running": "bold cyan",
        "tool.done": "bold green",
        "tool.error": "bold red",
        # Todo / progress
        "todo.pending": "yellow",
        "todo.in_progress": "cyan",
        "todo.done": "green",
        # Code / syntax
        "code.block": "white",
        # Misc
        "dim.text": "dim",
    }
)


def create_console(
    *,
    force_terminal: bool | None = None,
    width: int | None = None,
    height: int | None = None,
    no_color: bool = False,
) -> Console:
    """Create a Rich Console configured with the agentic theme.

    Args:
        force_terminal: Force terminal mode on/off. None = auto-detect.
        width: Console width. None = auto-detect.
        height: Console height. None = auto-detect.
        no_color: Disable color output (for non-color terminals or testing).
    """
    return Console(
        theme=AGENTIC_THEME if not no_color else None,
        force_terminal=force_terminal,
        width=width,
        height=height,
        no_color=no_color,
        soft_wrap=True,
    )


# Default console used by the CLI. Can be replaced by tests via monkeypatch.
console = create_console()
