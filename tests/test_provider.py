from __future__ import annotations

import json

import httpx
import pytest

from src.provider import OpenAICompatibleProvider, ProviderHTTPError, parse_tool_arguments
from src.types import Message, TextBlock, ToolCall


def make_provider(handler, **kwargs) -> OpenAICompatibleProvider:
    provider = OpenAICompatibleProvider(base_url="http://test/v1", api_key="k", model="m", **kwargs)
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    provider._sleep = fake_sleep
    provider.sleeps = sleeps  # type: ignore[attr-defined]
    return provider


def ok_body(content: str = "hi", tool_calls=None) -> dict:
    message: dict = {"content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls
    return {"choices": [{"message": message, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5}}


@pytest.mark.asyncio
async def test_retries_transient_errors_then_succeeds():
    statuses = iter([503, 429, 200])

    def handler(request: httpx.Request) -> httpx.Response:
        status = next(statuses)
        if status == 200:
            return httpx.Response(200, json=ok_body("done"))
        return httpx.Response(status, text="busy", headers={"retry-after": "2"} if status == 429 else {})

    provider = make_provider(handler, max_retries=3)
    response = await provider.complete(None, [Message.user("x")], [])
    assert response.blocks[0].text == "done"
    assert len(provider.sleeps) == 2
    assert provider.sleeps[1] == 2.0  # Retry-After honoured
    await provider.close()


@pytest.mark.asyncio
async def test_gives_up_after_max_retries():
    provider = make_provider(lambda request: httpx.Response(503, text="down"), max_retries=2)
    with pytest.raises(ProviderHTTPError) as error:
        await provider.complete(None, [], [])
    assert error.value.status_code == 503
    assert len(provider.sleeps) == 2
    await provider.close()


@pytest.mark.asyncio
async def test_client_errors_are_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(400, text="bad request")

    provider = make_provider(handler, max_retries=3)
    with pytest.raises(ProviderHTTPError, match="400"):
        await provider.complete(None, [], [])
    assert len(calls) == 1
    await provider.close()


@pytest.mark.asyncio
async def test_malformed_tool_arguments_do_not_crash():
    body = ok_body("", tool_calls=[{"id": "c1", "function": {"name": "bash", "arguments": "{not json"}}])
    provider = make_provider(lambda request: httpx.Response(200, json=body))
    response = await provider.complete(None, [], [])
    call = response.blocks[0]
    assert isinstance(call, ToolCall)
    assert call.arguments == {}
    assert call.parse_error and "not valid JSON" in call.parse_error
    await provider.close()


def test_parse_tool_arguments_variants():
    assert parse_tool_arguments('{"a": 1}') == ({"a": 1}, None)
    assert parse_tool_arguments("") == ({}, None)
    assert parse_tool_arguments({"a": 1}) == ({"a": 1}, None)
    assert parse_tool_arguments("[1]")[1] is not None


@pytest.mark.asyncio
async def test_streaming_assembles_text_and_tool_calls():
    first_call = {"index": 0, "id": "c1", "function": {"name": "glob", "arguments": '{"pat'}}
    chunks = [
        {"choices": [{"delta": {"content": "Hel"}}]},
        {"choices": [{"delta": {"content": "lo"}}]},
        {"choices": [{"delta": {"tool_calls": [first_call]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'tern": "*.py"}'}}]}}]},
        {"choices": [{"delta": {}, "finish_reason": "tool_calls"}]},
        {"choices": [], "usage": {"prompt_tokens": 11, "completion_tokens": 3}},
    ]
    sse = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"
    seen_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payloads.append(json.loads(request.content))
        return httpx.Response(200, text=sse, headers={"content-type": "text/event-stream"})

    deltas: list[str] = []
    provider = make_provider(handler, stream=True, on_text_delta=deltas.append)
    response = await provider.complete(None, [], [])

    assert seen_payloads[0]["stream"] is True
    assert deltas == ["Hel", "lo"]
    assert isinstance(response.blocks[0], TextBlock) and response.blocks[0].text == "Hello"
    call = response.blocks[1]
    assert isinstance(call, ToolCall) and call.arguments == {"pattern": "*.py"}
    assert response.usage == {"input_tokens": 11, "output_tokens": 3}
    await provider.close()


def test_payload_uses_string_content_and_omits_empty_tools():
    provider = OpenAICompatibleProvider(base_url="http://test/v1", api_key="k", model="m")
    messages = [
        Message.user("hello"),
        Message.assistant([TextBlock(text="calling"), ToolCall(id="c1", name="glob", arguments={"pattern": "*"})]),
        Message.tool_result("c1", "a.py"),
    ]
    payload = provider._build_payload("sys", messages, [])
    assert "tools" not in payload and "tool_choice" not in payload
    assert payload["messages"][1] == {"role": "user", "content": "hello"}
    assert payload["messages"][2]["content"] == "calling"
    assert payload["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": "a.py"}
