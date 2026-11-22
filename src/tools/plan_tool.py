from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..types import Tool, ToolSchema

PlanCallback = Callable[[str, str, list[str], list[str]], Awaitable[str]]

PLAN_SCHEMA = ToolSchema(
    name="plan",
    description=(
        "Present an implementation plan to the user for review and approval. "
        "Include the objective, ordered implementation steps, and risks. "
        "Pause execution and wait for the user's decision. "
        "The user may approve the plan, request revisions, or reject it. "
        "Do not execute implementation tasks before approval."
    ),
    parameters={
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Short plan title"
            },
            "summary": {
                "type": "string",
                "description": "Objective and expected outcome"
            },
            "steps": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "description": "Ordered implementation steps"
            },
            "risks": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Risks, dependencies, and assumptions"
            },
        },
        "required": ["title", "summary", "steps"],
        "additionalProperties": False,
    },
)


class PlanTool(Tool):
    def __init__(self, plan_callback: PlanCallback):
        self.plan_callback = plan_callback
        super().__init__(
            name=PLAN_SCHEMA.name,
            description=PLAN_SCHEMA.description,
            schema=PLAN_SCHEMA,
        )

    async def execute(self, **kwargs: Any) -> str:
        title: str = kwargs["title"]
        summary: str = kwargs["summary"]
        steps: list[str] = kwargs["steps"]
        risks: list[str] | None = kwargs.get("risks")
        if not title.strip():
            raise ValueError("title cannot be empty")
        if not summary.strip():
            raise ValueError("summary cannot be empty")
        if not steps:
            raise ValueError("steps cannot be empty")
        return await self.plan_callback(title, summary, steps, risks or [])


def create_plan_tool(plan_callback: PlanCallback) -> PlanTool:
    return PlanTool(plan_callback)
