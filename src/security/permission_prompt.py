"""
Click-based permission selection prompts for the agentic CLI.

Provides interactive permission selection forms using the click framework
for asking the user to approve, deny, or pre-approve tool calls.
"""

from __future__ import annotations

from typing import Any

import click

_PERMISSION_CHOICES = [
    ("y", "allow_once", "Allow once"),
    ("a", "allow_always", "Allow always"),
    ("u", "auto_allow", "Auto-allow (no prompts this session)"),
    ("n", "deny_once", "Deny once"),
    ("d", "deny_always", "Deny always"),
]


def prompt_permission(tool_name: str, args: dict[str, Any]) -> str:
    """
    Present an interactive permission selection form using click.

    Shows the tool name and its arguments, then asks the user to choose
    a permission decision via a numbered select form.

    Returns one of: "allow_once", "allow_always", "auto_allow",
    "deny_once", "deny_always".
    """
    click.echo()
    click.echo(click.style("Permission Required", fg="yellow", bold=True))
    click.echo(f"  Tool: {click.style(tool_name, fg='cyan', bold=True)}")

    # Show arguments as a suggestion form
    if args:
        click.echo("  Arguments:")
        for key, value in args.items():
            click.echo(f"    {key}: {value}")

    click.echo()

    # Build the action keys from _PERMISSION_CHOICES (short_key, action_key, label)
    choice_actions = [action for _, action, _ in _PERMISSION_CHOICES]

    click.echo("Select permission:")
    for index, (_, _, label) in enumerate(_PERMISSION_CHOICES, 1):
        click.echo(f"  [{index}] {label}")

    raw = click.prompt(
        "Enter choice number",
        type=click.Choice([str(i) for i in range(1, len(_PERMISSION_CHOICES) + 1)]),
        show_choices=False,
    )

    index = int(raw) - 1
    return choice_actions[index]


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask a yes/no confirmation question using click."""
    return click.confirm(message, default=default)


def prompt_text(message: str, default: str | None = None) -> str:
    """Ask for free-text input using click."""
    return click.prompt(message, default=default, show_default=default is not None)
