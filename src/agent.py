from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from .logger import log_info, log_warning
from .permissions import PermissionGate
from .provider import Provider
from .tools.registry import ToolRegistry
from .types import (
    Message,
    ModelResponse,
    ReasoningBlock,
    StopReason,
    TextBlock,
    ToolCall,
    ToolResult,
)

MAX_STEPS = 50
MAX_OUTPUT_LIMIT_CONTINUATIONS = 2


@dataclass
class AgentState:
    messages: list[Message]
    step_count: int = 0
    last_tool_calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    model_output_limit_reached: bool = False


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
        clarification_callback: Callable[[str], Awaitable[str]] | None = None,
        context_window_tokens: int = 32768,
        max_completion_tokens: int = 8192,
    ):
        if context_window_tokens < 1:
            raise ValueError("context_window_tokens must be at least 1")
        if max_completion_tokens < 1:
            raise ValueError("max_completion_tokens must be at least 1")
        self.provider = provider
        self.registry = registry
        self.permission_gate = permission_gate
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.permission_callback = permission_callback
        self.reasoning_callback = reasoning_callback
        self.tool_callback = tool_callback
        self.clarification_callback = clarification_callback
        self.context_window_tokens = context_window_tokens
        self.max_completion_tokens = max_completion_tokens
        self.state = AgentState(messages=[])

    def add_user_message(self, text: str) -> None:
        self.state.messages.append(Message.user(text))

    async def run(self, noTool: bool = False, custom_prompt: str = "") -> str:
        """Run the agent loop until completion or max steps."""
        self.state.step_count = 0
        self.state.last_tool_calls = []
        self.state.model_output_limit_reached = False
        empty_response_retries = 0
        clarification_requested = False
        output_limit_continuations = 0

        while self.state.step_count < self.max_steps:
            self.state.step_count += 1

            # Get model response
            response = await self.provider.complete(
                system="" if custom_prompt else self.system_prompt,
                messages=self.state.messages if not custom_prompt else [Message.user(custom_prompt)],
                tools=self.registry.schemas() if not noTool else [],
            )
            self._log_context_usage(response)

            if self.reasoning_callback:
                for block in response.blocks:
                    if isinstance(block, ReasoningBlock) and block.text:
                        await self.reasoning_callback(block.text)

            # Check for tool calls
            tool_calls = [b for b in response.blocks if isinstance(b, ToolCall)]
            text_blocks = [b for b in response.blocks if isinstance(b, TextBlock) and b.text]

            if response.stop_reason == StopReason.MAX_TOKENS:
                self.state.model_output_limit_reached = True
                output_limit_continuations += 1
                log_warning(
                    "MODEL_OUTPUT_TOKEN_LIMIT: response is partial. "
                    f"configured_max_completion_tokens={self.max_completion_tokens} "
                    f"context_window_tokens={self.context_window_tokens} "
                    f"continuation={output_limit_continuations}/"
                    f"{MAX_OUTPUT_LIMIT_CONTINUATIONS} usage={response.usage!r}"
                )
                self.state.messages.append(Message.assistant(response.blocks))
                if (
                    output_limit_continuations <= MAX_OUTPUT_LIMIT_CONTINUATIONS
                    and self.state.step_count < self.max_steps
                ):
                    self.state.messages.append(
                        Message.user(
                            "Your previous response reached the model output-token limit and may "
                            "be incomplete. Compare the remaining user request with the work "
                            "already completed, then continue from where you stopped. Do not "
                            "repeat completed work; finish and verify the request."
                        )
                    )
                    continue
                return (
                    "Error: The model repeatedly reached its per-response output-token limit "
                    f"({self.max_completion_tokens} configured), so the response may be "
                    "incomplete. The model's context window is separate from its output limit. "
                    "Restart the CLI to load current settings, verify the provider accepts the "
                    "configured output limit, or reduce the amount requested per response."
                )

            if not tool_calls and not text_blocks:
                log_warning(f"EMPTY_MODEL_RESPONSE: {response!r}")
                if empty_response_retries == 0 and self.state.step_count < self.max_steps:
                    empty_response_retries += 1
                    self.state.messages.append(
                        Message.user(
                            "Your previous response was empty. Continue the task and either "
                            "call the required tool or provide a concise user-facing result."
                        )
                    )
                    continue
                if (
                    not clarification_requested
                    and self.clarification_callback
                    and self.state.step_count < self.max_steps
                ):
                    clarification_requested = True
                    try:
                        additional_details = await self.clarification_callback(
                            "My last response was blank, so I couldn't confirm the result. "
                            "What would you like me to do next? Please add any details needed "
                            "to continue."
                        )
                    except Exception as error:
                        detail = str(error).strip() or repr(error)
                        return f"Error: I couldn't ask for more details: {detail}"
                    if not additional_details.strip():
                        return "Error: No additional details were provided; please retry the request."
                    self.state.messages.append(
                        Message.user(
                            f"Additional details from the user: {additional_details}\n"
                            "Continue the original task using these details and provide a clear result."
                        )
                    )
                    continue
                return (
                    "Error: The model returned an empty response after retry and clarification. "
                    "No further action was taken; please retry the request."
                )

            self.state.messages.append(Message.assistant(response.blocks))

            if not tool_calls:
                return "".join(block.text for block in text_blocks)

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

    def _log_context_usage(self, response: ModelResponse) -> None:
        usage = response.usage
        if not usage or "input_tokens" not in usage:
            log_info(
                "CONTEXT_USAGE_UNAVAILABLE: provider did not return token usage; "
                f"configured_context_window_tokens={self.context_window_tokens}"
            )
            return

        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        context_tokens = input_tokens + output_tokens
        remaining_tokens = self.context_window_tokens - context_tokens
        utilization = context_tokens / self.context_window_tokens
        message = (
            "CONTEXT_USAGE: "
            f"input_tokens={input_tokens} output_tokens={output_tokens} "
            f"compared_context_tokens={context_tokens} "
            f"context_window_tokens={self.context_window_tokens} "
            f"remaining_tokens={remaining_tokens} utilization={utilization:.1%}"
        )
        if remaining_tokens <= 0:
            log_warning(message + " status=over_context_window")
        else:
            log_info(message + " status=within_context_window")

    async def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
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

        if self.tool_callback:
            await self.tool_callback(tool_call.name, tool_call.arguments, "started", False)

        try:
            output = await self.registry.execute(tool_call.name, **tool_call.arguments)
            if self.tool_callback:
                await self.tool_callback(tool_call.name, tool_call.arguments, output, False)
            return ToolResult(call_id=tool_call.id, output=output, is_error=False)
        except Exception as e:
            detail = str(e).strip() or repr(e)
            error_output = f"Tool error: {type(e).__name__}: {detail}"
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
