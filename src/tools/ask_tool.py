from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..types import Tool, ToolSchema

AskCallback = Callable[[str, list[str] | None], Awaitable[str]]

ASK_USER_SCHEMA = ToolSchema(
    name="ask_user",
    description=(
        "Ask the user an English-language question and return their answer. "
        "Use English options for a fixed choice."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Question to ask the user"},
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of allowed answers",
            },
        },
        "required": ["question"],
        "additionalProperties": False,
    },
)


class AskUserTool(Tool):
    def __init__(self, ask_callback: AskCallback):
        self.ask_callback = ask_callback
        super().__init__(
            name=ASK_USER_SCHEMA.name,
            description=ASK_USER_SCHEMA.description,
            schema=ASK_USER_SCHEMA,
        )

    async def execute(self, **kwargs: Any) -> str:
        question: str = kwargs["question"]
        options: list[str] | None = kwargs.get("options")
        if not question.strip():
            raise ValueError("question cannot be empty")
        if options is not None and not options:
            raise ValueError("options cannot be empty when provided")
        return await self.ask_callback(question, options)


def create_ask_user_tool(ask_callback: AskCallback) -> AskUserTool:
    return AskUserTool(ask_callback)
