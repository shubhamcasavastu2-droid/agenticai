from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .permissions import PermissionGate
from .provider import Provider
from .tools.registry import ToolRegistry
from .types import (
    Message,
    ReasoningBlock,
    ToolCall,
    ToolResult,
)

MAX_STEPS = 50


@dataclass
class AgentState:
    messages: list[Message]
    step_count: int = 0
    last_tool_calls: list[tuple[str, dict[str, Any]]] = None

    def __post_init__(self):
        if self.last_tool_calls is None:
            self.last_tool_calls = []


class AgentLoop:
    def __init__(
        self,
        provider: Provider,
        registry: ToolRegistry,
        permission_gate: PermissionGate,
        system_prompt: str,
        max_steps: int = MAX_STEPS,
        permission_callback: Callable[[str, dict[str, Any]], Awaitable[tuple[bool, str | None]]] | None = None,
        reasoning_callback: Callable[[str], Awaitable[None]] | None = None,
        tool_callback: Callable[[str, dict[str, Any], str, bool], Awaitable[None]] | None = None,
    ):
        self.provider = provider
        self.registry = registry
        self.permission_gate = permission_gate
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.permission_callback = permission_callback
        self.reasoning_callback = reasoning_callback
        self.tool_callback = tool_callback
        self.state = AgentState(messages=[])

    def add_user_message(self, text: str) -> None:
        self.state.messages.append(Message.user(text))

    async def run(self) -> str:
        """Run the agent loop until completion or max steps."""
        self.state.step_count = 0
        self.state.last_tool_calls = []

        while self.state.step_count < self.max_steps:
            self.state.step_count += 1

            # Get model response
            response = await self.provider.complete(
                system=self.system_prompt,
                messages=self.state.messages,
                tools=self.registry.schemas(),
            )

            # Handle reasoning if present
            reasoning_blocks = [b for b in response.blocks if isinstance(b, ReasoningBlock)]
            for rb in reasoning_blocks:
                if rb.text and self.reasoning_callback:
                    await self.reasoning_callback(rb.text)

            # Add assistant message to history
            self.state.messages.append(Message.assistant(response.blocks))

            # Check for tool calls
            tool_calls = [b for b in response.blocks if isinstance(b, ToolCall)]

            if not tool_calls:
                # No tool calls - return text content
                text_blocks = [b for b in response.blocks if hasattr(b, 'text') and b.text]
                return "".join(b.text for b in text_blocks)

            # Check for repeated identical tool calls
            current_calls = [(tc.name, tc.arguments) for tc in tool_calls]
            if current_calls == self.state.last_tool_calls:
                return "Error: Repeated identical tool calls detected. Stopping to prevent loop."
            self.state.last_tool_calls = current_calls

            # Execute tool calls
            for tool_call in tool_calls:
                result = await self._execute_tool(tool_call)
                self.state.messages.append(Message.tool_result(
                    call_id=tool_call.id,
                    output=result.output,
                    is_error=result.is_error,
                ))

        return f"Error: Maximum steps ({self.max_steps}) reached."

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        # Check permission via callback or gate
        if self.permission_callback:
            allowed, reason = await self.permission_callback(tool_call.name, tool_call.arguments)
        else:
            allowed, reason = self.permission_gate.check(tool_call.name, tool_call.arguments)

        if not allowed:
            return ToolResult(
                call_id=tool_call.id,
                output=f"Permission denied: {reason}",
                is_error=True,
            )

        # Notify tool call start
        if self.tool_callback:
            await self.tool_callback(tool_call.name, tool_call.arguments, "started", False)

        # Execute tool
        try:
            output = await self.registry.execute(tool_call.name, **tool_call.arguments)
            
            # Notify tool call completed
            if self.tool_callback:
                await self.tool_callback(tool_call.name, tool_call.arguments, output, False)
            
            return ToolResult(call_id=tool_call.id, output=output, is_error=False)
        except Exception as e:
            error_output = f"Tool error: {type(e).__name__}: {e}"
            
            # Notify tool call error
            if self.tool_callback:
                await self.tool_callback(tool_call.name, tool_call.arguments, error_output, True)
            
            return ToolResult(
                call_id=tool_call.id,
                output=error_output,
                is_error=True,
            )

    def clear_history(self) -> None:
        self.state.messages.clear()
        self.state.step_count = 0
        self.state.last_tool_calls = []
