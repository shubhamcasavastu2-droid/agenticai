from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal


class Role(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class StopReason(StrEnum):
    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    TOOL_USE = "tool_use"
    ERROR = "error"


@dataclass
class TextBlock:
    text: str = ""
    type: Literal["text"] = "text"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]
    type: Literal["tool_call"] = "tool_call"
    # Set when the model emitted arguments that are not a valid JSON object; the agent returns
    # this to the model as a tool error instead of executing the call.
    parse_error: str | None = None
    raw_arguments: str | None = None


@dataclass
class ToolResult:
    call_id: str
    output: str
    is_error: bool = False
    type: Literal["tool_result"] = "tool_result"


@dataclass
class ReasoningBlock:
    text: str = ""
    type: Literal["reasoning"] = "reasoning"


Block = TextBlock | ToolCall | ToolResult | ReasoningBlock


@dataclass
class Message:
    role: Role
    content: list[Block] = field(default_factory=list)

    @classmethod
    def user(cls, text: str) -> Message:
        return cls(role=Role.USER, content=[TextBlock(text=text)])

    @classmethod
    def assistant(cls, blocks: list[Block]) -> Message:
        return cls(role=Role.ASSISTANT, content=blocks)

    @classmethod
    def tool_result(cls, call_id: str, output: str, is_error: bool = False) -> Message:
        return cls(role=Role.TOOL, content=[ToolResult(call_id=call_id, output=output, is_error=is_error)])


@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass
class ModelResponse:
    blocks: list[Block]
    stop_reason: StopReason
    usage: dict[str, int] | None = None  # input_tokens, output_tokens


@dataclass
class Tool:
    name: str
    description: str
    schema: ToolSchema

    async def execute(self, **kwargs: Any) -> str:
        raise NotImplementedError
