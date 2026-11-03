from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from .types import Block, Message, ModelResponse, Role, StopReason, TextBlock, ToolCall, ToolResult, ToolSchema


class Provider(ABC):
    @abstractmethod
    async def complete(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSchema],
    ) -> ModelResponse:
        pass


class OpenAICompatibleProvider(Provider):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def complete(
        self,
        system: str | None,
        messages: list[Message],
        tools: list[ToolSchema],
    ) -> ModelResponse:
        payload = self._build_payload(system, messages, tools)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = await self._client.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return self._parse_response(data)

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
            msg_list.append(self._convert_message(msg))

        tool_schemas = [self._convert_tool_schema(t) for t in tools]

        return {
            "model": self.model,
            "messages": msg_list,
            "tools": tool_schemas if tool_schemas else None,
            "tool_choice": "auto" if tool_schemas else None,
            "stream": False,
            "max_tokens": 32768,
            "num_ctx": 32768,
        }

    def _convert_message(self, msg: Message) -> dict[str, Any]:
        if msg.role == Role.USER:
            text = "".join(b.text for b in msg.content if isinstance(b, type(msg.content[0])) and hasattr(b, 'text') and b.text)
            return {"role": "user", "content": text}

        if msg.role == Role.ASSISTANT:
            content_parts = []
            tool_calls = []
            for block in msg.content:
                if hasattr(block, 'text') and block.text:
                    content_parts.append({"type": "text", "text": block.text})
                elif hasattr(block, 'id') and hasattr(block, 'name'):
                    tool_calls.append({
                        "id": block.id,
                        "type": "function",
                        "function": {
                            "name": block.name,
                            "arguments": json.dumps(block.arguments),
                        },
                    })
            result: dict[str, Any] = {"role": "assistant"}
            if content_parts:
                result["content"] = content_parts
            if tool_calls:
                result["tool_calls"] = tool_calls
            return result

        if msg.role == Role.TOOL:
            results = []
            for block in msg.content:
                if hasattr(block, 'call_id'):
                    results.append({
                        "role": "tool",
                        "tool_call_id": block.call_id,
                        "content": block.output,
                    })
            return results[0] if results else {"role": "tool", "content": ""}

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
        choice = data["choices"][0]
        message = choice["message"]

        blocks: list[Block] = []

        if message.get("content"):
            blocks.append(TextBlock(text=message["content"]))

        for tc in message.get("tool_calls", []):
            func = tc["function"]
            args = json.loads(func["arguments"])
            blocks.append(ToolCall(id=tc["id"], name=func["name"], arguments=args))

        stop_reason_map = {
            "stop": StopReason.END_TURN,
            "length": StopReason.MAX_TOKENS,
            "tool_calls": StopReason.TOOL_USE,
        }
        stop_reason = stop_reason_map.get(choice.get("finish_reason", "stop"), StopReason.END_TURN)

        usage = data.get("usage")
        usage_dict = None
        if usage:
            usage_dict = {
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            }

        return ModelResponse(blocks=blocks, stop_reason=stop_reason, usage=usage_dict)

    async def close(self):
        await self._client.aclose()


# Stubs for future providers
class AnthropicProvider(Provider):
    async def complete(self, system, messages, tools):
        raise NotImplementedError("Anthropic provider not yet implemented")


class GeminiProvider(Provider):
    async def complete(self, system, messages, tools):
        raise NotImplementedError("Gemini provider not yet implemented")