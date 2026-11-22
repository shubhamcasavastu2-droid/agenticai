from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..types import Tool, ToolSchema

AskCallback = Callable[[str, list[str] | None], Awaitable[str]]

ASK_USER_SCHEMA = ToolSchema(
    name="ask_user",
    description=(
        "Ask the user for clarification or missing information. "
        "Use this tool whenever the user's request is ambiguous, "
        "a required decision is missing, or confirmation is needed. "
        "For fixed choices, provide English-language options. "
        "For open-ended questions, omit options. "
        "Wait for the user's answer before continuing."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "A clear, concise question in English."
            },
            "options": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional English-language choices. "
                    "Omit when a free-text answer is expected."
                )
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
