"""Slash-command registry. Each command module registers its handlers in `build_registry()`."""

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
    from . import agents, core, interaction, permission, skills

    registry = CommandRegistry()
    for module in (core, permission, skills, agents, interaction):
        module.register(registry)
    return registry


__all__ = ["CommandRegistry", "SlashCommand", "build_registry"]
