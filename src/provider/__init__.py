"""
Provider abstraction for Agentic CLI.

Provides:
- Abstract Provider base class for LLM API interactions
- OpenAICompatibleProvider implementation working with OpenAI, Ollama, NVIDIA NIM,
  Anthropic (OpenAI-compatible endpoint), and OpenRouter
- Streaming support with Server-Sent Events (SSE) parsing
- Retry logic with exponential backoff and Retry-After header support
- Error classification (timeout, authentication, HTTP errors)
- Token usage tracking for context window management
"""

from __future__ import annotations

import asyncio
import inspect
import json
import random
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from ..logger import log_warning
from ..models import MessageModel as MessageModel
from ..types import (
    Block,
    Message,
    ModelResponse,
    ReasoningBlock,
    Role,
    StopReason,
    TextBlock,
    ToolCall,
    ToolResult,
    ToolSchema,
)

TextDeltaCallback = Callable[[str], Awaitable[None] | None]

# HTTP statuses worth retrying: request timeout, conflict, rate limit and transient server errors.
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504}
RETRYABLE_TRANSPORT_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.RemoteProtocolError,
    httpx.ReadError,
)
MAX_BACKOFF_SECONDS = 30.0


class Provider(ABC):
    """Abstract base class for LLM API providers."""

    @abstractmethod
    async def complete(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSchema],
    ) -> ModelResponse:
        """Generate a completion from the model."""
        pass


class ProviderTimeoutError(TimeoutError):
    """Raised when the model server doesn't respond within the configured timeout."""


class ProviderAuthenticationError(PermissionError):
    """Raised when the model provider rejects the configured API key."""


class ProviderHTTPError(RuntimeError):
    """Raised for non-retryable HTTP errors, or retryable ones after retries are exhausted."""

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Model provider returned HTTP {status_code}: {body[:2000]}")


class _RetryableStatus(Exception):
    def __init__(self, response_status: int, body: str, retry_after: float | None):
        self.status_code = response_status
        self.body = body
        self.retry_after = retry_after


def parse_tool_arguments(raw: Any) -> tuple[dict[str, Any], str | None]:
    """Parse a tool-call `arguments` value. Returns (arguments, error_message)."""
    if isinstance(raw, dict):
        return raw, None
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return {}, None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as error:
        return {}, f"arguments are not valid JSON ({error}): {str(raw)[:300]}"
    if not isinstance(parsed, dict):
        return {}, f"arguments must be a JSON object, got {type(parsed).__name__}"
    return parsed, None


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


class OpenAICompatibleProvider(Provider):
    """Chat Completions client for any OpenAI-compatible endpoint (Ollama, OpenAI, OpenRouter, NIM,
    and Anthropic's OpenAI-compatible endpoint at https://api.anthropic.com/v1/)."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 300.0,
        max_completion_tokens: int = 8192,
        max_retries: int = 0,
        backoff_base_seconds: float = 1.0,
        stream: bool = False,
        on_text_delta: TextDeltaCallback | None = None,
    ):
        if max_completion_tokens < 1:
            raise ValueError("max_completion_tokens must be at least 1")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_completion_tokens = max_completion_tokens
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.stream = stream
        self.on_text_delta = on_text_delta
        self._sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
        self._client = httpx.AsyncClient(timeout=timeout)

    # ------------------------------------------------------------------ request / retry

    async def complete(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSchema],
    ) -> ModelResponse:
        payload = self._build_payload(system, messages, tools)
        attempt = 0
        while True:
            emitted = False

            async def emit(text: str) -> None:
                nonlocal emitted
                emitted = True
                await self._emit_delta(text)

            try:
                if self.stream:
                    return await self._complete_streaming(payload, emit)
                return await self._complete_once(payload)
            except _RetryableStatus as error:
                if attempt >= self.max_retries or emitted:
                    raise ProviderHTTPError(error.status_code, error.body) from None
                delay = self._backoff_delay(attempt, error.retry_after)
                log_warning(
                    f"PROVIDER_RETRY: HTTP {error.status_code} attempt={attempt + 1}/"
                    f"{self.max_retries} sleeping={delay:.1f}s"
                )
            except RETRYABLE_TRANSPORT_ERRORS as error:
                if attempt >= self.max_retries or emitted:
                    if isinstance(error, httpx.TimeoutException):
                        raise ProviderTimeoutError(
                            f"Model request timed out after {self.timeout:g} seconds. "
                            "Check that the model server is running and responsive, or increase "
                            "AGENTIC_REQUEST_TIMEOUT_SECONDS."
                        ) from error
                    raise
                delay = self._backoff_delay(attempt, None)
                log_warning(
                    f"PROVIDER_RETRY: {type(error).__name__} attempt={attempt + 1}/"
                    f"{self.max_retries} sleeping={delay:.1f}s"
                )
            attempt += 1
            await self._sleep(delay)

    def _backoff_delay(self, attempt: int, retry_after: float | None) -> float:
        if retry_after is not None:
            return min(retry_after, MAX_BACKOFF_SECONDS)
        base = self.backoff_base_seconds * (2**attempt)
        return min(base + random.uniform(0, self.backoff_base_seconds), MAX_BACKOFF_SECONDS)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _check_status(self, status_code: int, body: str, headers: httpx.Headers) -> None:
        if status_code == 401:
            raise ProviderAuthenticationError(
                "The model provider rejected AGENTIC_API_KEY (HTTP 401). "
                "Create or rotate the API key in the provider console, update the local "
                "environment, and restart the CLI. Do not paste the key into chat or source files."
            )
        if status_code in RETRYABLE_STATUS:
            raise _RetryableStatus(status_code, body, _parse_retry_after(headers.get("retry-after")))
        if status_code >= 400:
            raise ProviderHTTPError(status_code, body)

    async def _complete_once(self, payload: dict[str, Any]) -> ModelResponse:
        response = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
        )
        self._check_status(response.status_code, response.text, response.headers)
        return self._parse_response(response.json())

    async def _complete_streaming(
        self,
        payload: dict[str, Any],
        emit: Callable[[str], Awaitable[None]],
    ) -> ModelResponse:
        stream_payload = {**payload, "stream": True, "stream_options": {"include_usage": True}}
        async with self._client.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=stream_payload,
        ) as response:
            if response.status_code >= 400:
                body = (await response.aread()).decode("utf-8", errors="replace")
                self._check_status(response.status_code, body, response.headers)

            content: list[str] = []
            reasoning: list[str] = []
            tool_parts: dict[int, dict[str, Any]] = {}
            finish_reason: str | None = None
            usage: dict[str, Any] | None = None

            async for line in response.aiter_lines():
                line = line.strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:") :].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    log_warning(f"STREAM_PARSE_ERROR: {data[:200]}")
                    continue
                if chunk.get("usage"):
                    usage = chunk["usage"]
                for choice in chunk.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if delta.get("content"):
                        content.append(delta["content"])
                        await emit(delta["content"])
                    piece = delta.get("reasoning") or delta.get("reasoning_content")
                    if piece:
                        reasoning.append(piece)
                    for tc in delta.get("tool_calls") or []:
                        slot = tool_parts.setdefault(
                            tc.get("index", len(tool_parts)), {"id": "", "name": "", "arguments": ""}
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        function = tc.get("function") or {}
                        if function.get("name"):
                            slot["name"] += function["name"]
                        if function.get("arguments"):
                            slot["arguments"] += function["arguments"]
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]

        message: dict[str, Any] = {"content": "".join(content)}
        if reasoning:
            message["reasoning"] = "".join(reasoning)
        if tool_parts:
            message["tool_calls"] = [
                {
                    "id": part["id"] or f"call_{index}",
                    "function": {"name": part["name"], "arguments": part["arguments"]},
                }
                for index, part in sorted(tool_parts.items())
            ]
        return self._parse_response(
            {"choices": [{"message": message, "finish_reason": finish_reason or "stop"}], "usage": usage}
        )

    async def _emit_delta(self, text: str) -> None:
        if not self.on_text_delta:
            return
        result = self.on_text_delta(text)
        if inspect.isawaitable(result):
            await result

    # ------------------------------------------------------------------ payload conversion

    def _build_payload(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSchema],
    ) -> dict[str, Any]:
        msg_list: list[dict[str, Any]] = []
        if system:
            msg_list.append({"role": "system", "content": system})
        for msg in messages:
            msg_list.extend(self._convert_message(msg))

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": msg_list,
            "stream": False,
            "max_tokens": self.max_completion_tokens,
            "temperature": 0.5,
            "top_p": 1,
        }
        if tools:
            payload["tools"] = [self._convert_tool_schema(t) for t in tools]
            payload["tool_choice"] = "auto"
        return payload

    def _convert_message(self, msg: Message) -> list[dict[str, Any]]:
        if msg.role == Role.USER:
            text = "".join(b.text for b in msg.content if isinstance(b, TextBlock))
            return [{"role": "user", "content": text}]

        if msg.role == Role.ASSISTANT:
            # Reasoning blocks are intentionally not sent back: OpenAI-compatible servers either
            # ignore them or reject them (e.g. DeepSeek's reasoning_content).
            text = "".join(b.text for b in msg.content if isinstance(b, TextBlock) and b.text)
            tool_calls = [
                {
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": (
                            block.raw_arguments
                            if block.parse_error and block.raw_arguments is not None
                            else json.dumps(block.arguments)
                        ),
                    },
                }
                for block in msg.content
                if isinstance(block, ToolCall)
            ]
            result: dict[str, Any] = {"role": "assistant", "content": text or None}
            if tool_calls:
                result["tool_calls"] = tool_calls
            elif result["content"] is None:
                result["content"] = ""
            return [result]

        if msg.role == Role.TOOL:
            return [
                {"role": "tool", "tool_call_id": block.call_id, "content": block.output}
                for block in msg.content
                if isinstance(block, ToolResult)
            ]

        raise ValueError(f"Unknown role: {msg.role}")

    def _convert_tool_schema(self, tool: ToolSchema) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    def _parse_response(self, data: dict[str, Any]) -> ModelResponse:
        choices = data.get("choices") or []
        if not choices:
            raise ProviderHTTPError(200, f"Response contained no choices: {json.dumps(data)[:500]}")
        choice = choices[0]
        message = choice.get("message") or {}

        blocks: list[Block] = []
        if message.get("content"):
            blocks.append(TextBlock(text=message["content"]))

        # Reasoning from thinking models (qwen3, deepseek-r1, glm, ...)
        reasoning = message.get("reasoning") or message.get("reasoning_content")
        if reasoning:
            blocks.append(ReasoningBlock(text=reasoning))

        for tc in message.get("tool_calls") or []:
            func = tc.get("function") or {}
            raw = func.get("arguments")
            args, error = parse_tool_arguments(raw)
            blocks.append(
                ToolCall(
                    id=tc.get("id") or "",
                    name=func.get("name", ""),
                    arguments=args,
                    parse_error=error,
                    raw_arguments=raw if isinstance(raw, str) else None,
                )
            )

        stop_reason_map = {
            "stop": StopReason.END_TURN,
            "length": StopReason.MAX_TOKENS,
            "tool_calls": StopReason.TOOL_USE,
        }
        stop_reason = stop_reason_map.get(choice.get("finish_reason") or "stop", StopReason.END_TURN)

        usage = data.get("usage")
        usage_dict = None
        if usage:
            usage_dict = {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            }

        return ModelResponse(blocks=blocks, stop_reason=stop_reason, usage=usage_dict)

    async def close(self) -> None:
        await self._client.aclose()
