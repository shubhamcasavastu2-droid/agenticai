from __future__ import annotations

from typing import Any

from ..types import Tool, ToolSchema

TodoItem = dict[str, str]

TODO_SCHEMA = ToolSchema(
    name="todo",
    description=(
        "Create and manage a todo list for the current project. "
        "Use this to break down the user's request into ordered steps, "
        "mark items as in-progress when you start working on them, "
        "and mark them as done when complete. "
        "Always keep the todo list up to date so the user can see progress."
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "update"],
                "description": "create: set up a new todo list; update: change the status of an existing item",
            },
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "The todo step description"},
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "done"],
                            "description": "Current status of the todo item",
                        },
                    },
                    "required": ["title", "status"],
                },
                "description": "The todo items to create or update",
            },
        },
        "required": ["action"],
        "additionalProperties": False,
    },
)


class TodoTool(Tool):
    def __init__(self, todo_callback):
        self.todo_callback = todo_callback
        super().__init__(
            name=TODO_SCHEMA.name,
            description=TODO_SCHEMA.description,
            schema=TODO_SCHEMA,
        )

    async def execute(self, **kwargs: Any) -> str:
        action: str = kwargs["action"]
        items: list[dict[str, str]] = kwargs.get("items", [])
        if not items:
            raise ValueError("items cannot be empty")
        for item in items:
            if not item.get("title", "").strip():
                raise ValueError("todo item title cannot be empty")
            if item.get("status") not in ("pending", "in_progress", "done"):
                raise ValueError("todo item status must be pending, in_progress, or done")
        return await self.todo_callback(action, items)


def create_todo_tool(todo_callback) -> TodoTool:
    return TodoTool(todo_callback)
