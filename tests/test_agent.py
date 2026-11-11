from __future__ import annotations

import pytest

from src.agent import AgentLoop
from src.permissions import PermissionGate
from src.tools.registry import ToolRegistry
from src.types import (
    ModelResponse,
    ReasoningBlock,
    StopReason,
    TextBlock,
    Tool,
    ToolCall,
    ToolSchema,
)


class ScriptedProvider:
    def __init__(self, responses: list[ModelResponse]):
        self.responses = responses
        self.calls = 0
        self.received_messages = []

    async def complete(self, system, messages, tools):
        self.calls += 1
        self.received_messages.append(list(messages))
        return self.responses.pop(0)


class RecordTool(Tool):
    def __init__(self):
        schema = ToolSchema(name="record", description="Record action", parameters={"type": "object"})
        super().__init__(name="record", description="Record action", schema=schema)
        self.calls = 0

    async def execute(self, **kwargs):
        self.calls += 1
        return "Action completed"


@pytest.mark.asyncio
async def test_agent_retries_empty_response_after_tool_call():
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[ToolCall(id="call-1", name="record", arguments={})],
                stop_reason=StopReason.TOOL_USE,
            ),
            ModelResponse(
                blocks=[ReasoningBlock(text="thinking")],
                stop_reason=StopReason.END_TURN,
            ),
            ModelResponse(
                blocks=[TextBlock(text="Document created")],
                stop_reason=StopReason.END_TURN,
            ),
        ]
    )
    registry = ToolRegistry()
    record_tool = RecordTool()
    registry.register(record_tool)
    permission_gate = PermissionGate()
    permission_gate.allow_auto("record")
    agent = AgentLoop(provider, registry, permission_gate, "test", max_steps=4)
    agent.add_user_message("Create a document")

    result = await agent.run()

    assert result == "Document created"
    assert record_tool.calls == 1
    assert provider.calls == 3


@pytest.mark.asyncio
async def test_agent_reports_repeated_empty_responses():
    provider = ScriptedProvider(
        [
            ModelResponse(blocks=[], stop_reason=StopReason.END_TURN),
            ModelResponse(blocks=[], stop_reason=StopReason.END_TURN),
        ]
    )
    agent = AgentLoop(provider, ToolRegistry(), PermissionGate(), "test", max_steps=2)
    agent.add_user_message("Do something")

    result = await agent.run()

    assert result.startswith("Error:")
    assert "empty response" in result
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_agent_logs_complete_empty_response(monkeypatch):
    import src.agent as agent_module

    logged_messages: list[str] = []
    monkeypatch.setattr(agent_module, "log_warning", logged_messages.append)
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[ReasoningBlock(text="internal reasoning only")],
                stop_reason=StopReason.END_TURN,
                usage={"input_tokens": 12, "output_tokens": 4},
            ),
            ModelResponse(blocks=[TextBlock(text="Recovered")], stop_reason=StopReason.END_TURN),
        ]
    )
    agent = AgentLoop(provider, ToolRegistry(), PermissionGate(), "test", max_steps=2)

    result = await agent.run()

    assert result == "Recovered"
    assert len(logged_messages) == 1
    assert "ModelResponse(" in logged_messages[0]
    assert "ReasoningBlock(text='internal reasoning only'" in logged_messages[0]
    assert "input_tokens': 12" in logged_messages[0]


@pytest.mark.asyncio
async def test_agent_compares_context_and_continues_after_max_tokens(monkeypatch):
    import src.agent as agent_module

    context_logs: list[str] = []
    monkeypatch.setattr(agent_module, "log_warning", context_logs.append)
    monkeypatch.setattr(agent_module, "log_info", context_logs.append)
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[TextBlock(text="Partial response")],
                stop_reason=StopReason.MAX_TOKENS,
                usage={"input_tokens": 8000, "output_tokens": 1024},
            ),
            ModelResponse(
                blocks=[TextBlock(text="Completed response")],
                stop_reason=StopReason.END_TURN,
                usage={"input_tokens": 4000, "output_tokens": 200},
            ),
        ]
    )
    agent = AgentLoop(
        provider,
        ToolRegistry(),
        PermissionGate(),
        "test",
        max_steps=3,
        context_window_tokens=8192,
    )
    agent.add_user_message("Complete this task")

    result = await agent.run()

    assert result == "Completed response"
    assert agent.state.model_output_limit_reached is True
    continuation_message = provider.received_messages[1][-1]
    assert "reached the model output-token limit" in continuation_message.content[0].text
    assert any("compared_context_tokens=9024" in entry for entry in context_logs)
    assert any("context_window_tokens=8192" in entry for entry in context_logs)
    assert any("status=over_context_window" in entry for entry in context_logs)


@pytest.mark.asyncio
async def test_agent_never_returns_partial_max_token_response_as_final():
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[TextBlock(text="Partial only")],
                stop_reason=StopReason.MAX_TOKENS,
                usage={"input_tokens": 100, "output_tokens": 1024},
            )
        ]
    )
    agent = AgentLoop(provider, ToolRegistry(), PermissionGate(), "test", max_steps=1)
    agent.add_user_message("Complete this task")

    result = await agent.run()

    assert result.startswith("Error:")
    assert "may be incomplete" in result
    assert result != "Partial only"


@pytest.mark.asyncio
async def test_agent_stops_after_repeated_output_limit_responses(monkeypatch):
    import src.agent as agent_module

    warnings: list[str] = []
    monkeypatch.setattr(agent_module, "log_warning", warnings.append)
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[TextBlock(text=f"Partial {index}")],
                stop_reason=StopReason.MAX_TOKENS,
                usage={"input_tokens": 9000, "output_tokens": 1024},
            )
            for index in range(3)
        ]
    )
    agent = AgentLoop(
        provider,
        ToolRegistry(),
        PermissionGate(),
        "test",
        max_steps=10,
        max_completion_tokens=8192,
    )

    result = await agent.run()

    assert result.startswith("Error:")
    assert "8192 configured" in result
    assert provider.calls == 3
    assert any("configured_max_completion_tokens=8192" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_agent_asks_for_details_after_retried_empty_response():
    provider = ScriptedProvider(
        [
            ModelResponse(blocks=[], stop_reason=StopReason.END_TURN),
            ModelResponse(blocks=[], stop_reason=StopReason.END_TURN),
            ModelResponse(
                blocks=[TextBlock(text="Created the requested document")],
                stop_reason=StopReason.END_TURN,
            ),
        ]
    )
    questions: list[str] = []

    async def clarify(question: str) -> str:
        questions.append(question)
        return "Create a QA-agent setup guide in docs/qa-agent.md"

    agent = AgentLoop(
        provider,
        ToolRegistry(),
        PermissionGate(),
        "test",
        max_steps=3,
        clarification_callback=clarify,
    )
    agent.add_user_message("Create a document")

    result = await agent.run()

    assert result == "Created the requested document"
    assert len(questions) == 1
    assert "last response was blank" in questions[0]
    assert "What would you like me to do next?" in questions[0]
    clarification_message = provider.received_messages[2][-1]
    assert "Create a QA-agent setup guide" in clarification_message.content[0].text


@pytest.mark.asyncio
async def test_agent_reports_when_clarification_is_not_interactive():
    provider = ScriptedProvider(
        [
            ModelResponse(blocks=[], stop_reason=StopReason.END_TURN),
            ModelResponse(blocks=[], stop_reason=StopReason.END_TURN),
        ]
    )

    async def clarify(question: str) -> str:
        raise RuntimeError("ask_user requires an interactive terminal")

    agent = AgentLoop(
        provider,
        ToolRegistry(),
        PermissionGate(),
        "test",
        max_steps=3,
        clarification_callback=clarify,
    )
    agent.add_user_message("Create a document")

    result = await agent.run()

    assert result.startswith("Error: I couldn't ask for more details")
