from __future__ import annotations

from typing import Any

from ..types import Tool, ToolSchema


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[ToolSchema]:
        return [t.schema for t in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> str:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return await tool.execute(**kwargs)


def create_tool_schema(name: str, description: str, parameters: dict[str, Any]) -> ToolSchema:
    return ToolSchema(name=name, description=description, parameters=parameters)