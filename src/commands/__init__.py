"""
Slash-command registry for Agentic CLI.

This package provides the command registration system and organizes slash commands
into sub-packages:

- ``agents``      - Agent listing and inspection (/agents)
- ``ask``         - Question asking with optional choices (/ask)
- ``plan``        - Plan creation and approval (/plan)
- ``session``     - Session management: list, resume, switch, new (/session)
- ``scheduler``   - Schedule management (TODO placeholder) (/schedule)
- ``skillsCommand``  - Skill listing, inspection, and creation (/skills)
- ``agentCommand`` - Agent creation and inspection (/agent)
- ``hook``        - Hook management (TODO placeholder) (/hook)

Core commands (help, clear, model, exit, workspace, resume) remain in
``commands.core``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cli import CLI

Handler = Callable[["CLI", list[str]], Awaitable[None]]


@dataclass(frozen=True)
class SlashCommand:
    name: str  # without the leading slash
    usage: str
    summary: str
    handler: Handler


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, SlashCommand] = {}

    def add(self, name: str, usage: str, summary: str, handler: Handler) -> None:
        self._commands[name] = SlashCommand(name, usage, summary, handler)

    def get(self, name: str) -> SlashCommand | None:
        return self._commands.get(name.lstrip("/").lower())

    def all(self) -> list[SlashCommand]:
        return list(self._commands.values())


def build_registry() -> CommandRegistry:
    from . import (
        agentCommand,
        agents,
        ask,
        core,
        hook,
        permission,
        plan,
        scheduler,
        session,
        skillsCommand,
    )

    registry = CommandRegistry()
    for module in (
        core,
        agentCommand,
        agents,
        ask,
        permission,
        plan,
        session,
        scheduler,
        skillsCommand,
        hook,
    ):
        module.register(registry)
    return registry


__all__ = ["CommandRegistry", "SlashCommand", "build_registry"]
