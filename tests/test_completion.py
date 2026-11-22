from __future__ import annotations

import pytest

from src.core.agent import AgentLoop
from src.core.completion import CompletionResolver
from src.security.permissions import PermissionGate
from src.tools.registry import ToolRegistry
from src.types import ModelResponse, StopReason, TextBlock, Tool, ToolCall, ToolSchema


class ScriptedProvider:
    def __init__(self, responses: list[ModelResponse]):
        self.responses = responses
        self.calls: list[dict] = []

    async def complete(self, system, messages, tools):
        self.calls.append({"system": system, "messages": list(messages), "tools": tools})
        return self.responses.pop(0)


def text_response(text: str) -> ModelResponse:
    return ModelResponse(blocks=[TextBlock(text=text)], stop_reason=StopReason.END_TURN)


def review_response(complete: bool, findings: str) -> ModelResponse:
    import json

    content = json.dumps({"complete": complete, "findings": findings})
    return text_response(content)


class WriteMarkerTool(Tool):
    def __init__(self):
        schema = ToolSchema(name="write_marker", description="Create marker", parameters={"type": "object"})
        super().__init__(name="write_marker", description="Create marker", schema=schema)

    async def execute(self, **kwargs):
        return "Created docs/overview.md"


@pytest.mark.asyncio
async def test_resolver_retries_incomplete_work_with_full_context():
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[ToolCall(id="write-1", name="write_marker", arguments={})],
                stop_reason=StopReason.TOOL_USE,
            ),
            text_response("Created the docs folder."),
            review_response(False, "Create docs/overview.md and verify it exists."),
            text_response("Created docs/overview.md and verified it exists."),
            review_response(True, "Requested document exists and was verified."),
        ]
    )
    registry = ToolRegistry()
    registry.register(WriteMarkerTool())
    permissions = PermissionGate()
    permissions.allow_auto("write_marker")
    agent = AgentLoop(provider, {"agent": provider}, registry, permissions, "coding agent", max_steps=2)
    agent.add_user_message("Create project documentation")
    resolver = CompletionResolver(provider, max_attempts=3)

    result = await resolver.run(
        agent,
        original_request="Please create an overview document for this project.",
        normalized_request="Create docs/overview.md with a project overview and verify it.",
    )

    assert result.complete is True
    assert result.attempts == 2
    assert result.response == "Created docs/overview.md and verified it exists."
    continuation = agent.state.messages[-2].content[0].text
    assert "Please create an overview document" in continuation
    assert "Create docs/overview.md and verify it exists" in continuation
    review_input = provider.calls[2]["messages"][0].content[0].text
    assert "Original user request:" in review_input
    assert "Normalized request sent to the coding agent:" in review_input
    assert "Created the docs folder." in review_input
    assert '"type": "tool_call"' in review_input
    assert '"type": "tool_result"' in review_input


@pytest.mark.asyncio
async def test_resolver_stops_at_attempt_limit_and_marks_unverified():
    provider = ScriptedProvider(
        [
            text_response("Created an empty folder."),
            review_response(False, "The requested document is missing."),
            text_response("Still only created the folder."),
            review_response(False, "The requested document is still missing."),
        ]
    )
    agent = AgentLoop(provider, {"agent": provider}, ToolRegistry(), PermissionGate(), "coding agent", max_steps=1)
    agent.add_user_message("Create a document")

    result = await CompletionResolver(provider, max_attempts=2).run(
        agent,
        original_request="Create docs/overview.md",
        normalized_request="Create docs/overview.md",
    )

    assert result.complete is False
    assert result.attempts == 2
    assert result.findings == "The requested document is still missing."
    assert len(provider.calls) == 4


@pytest.mark.asyncio
async def test_resolver_does_not_review_token_limited_error_as_complete():
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[TextBlock(text="partial")],
                stop_reason=StopReason.MAX_TOKENS,
                usage={"input_tokens": 4000, "output_tokens": 1024},
            ),
        ]
    )
    agent = AgentLoop(provider, {"agent": provider}, ToolRegistry(), PermissionGate(), "coding agent", max_steps=1)

    result = await CompletionResolver(provider, max_attempts=1).run(
        agent,
        original_request="Create a document",
        normalized_request="Create docs/overview.md",
    )

    assert result.complete is False
    assert "output-token limit" in result.findings
    assert result.response.startswith("Error:")
    assert len(provider.calls) == 1


@pytest.mark.asyncio
async def test_resolver_does_not_restart_task_after_output_limit_exhaustion():
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[TextBlock(text="partial")],
                stop_reason=StopReason.MAX_TOKENS,
                usage={"input_tokens": 4000, "output_tokens": 1024},
            ),
        ]
    )
    agent = AgentLoop(provider, {"agent": provider}, ToolRegistry(), PermissionGate(), "coding agent", max_steps=1)

    result = await CompletionResolver(provider, max_attempts=3).run(
        agent,
        original_request="Create a document",
        normalized_request="Create docs/overview.md",
    )

    assert result.complete is False
    assert result.attempts == 1
    assert "avoid retrying" in result.findings
    assert len(provider.calls) == 1


def test_resolver_requires_positive_attempt_budget():
    with pytest.raises(ValueError, match="at least 1"):
        CompletionResolver(ScriptedProvider([]), max_attempts=0)


def test_completion_attempt_budget_loads_from_environment(monkeypatch, tmp_path):
    from src.config.config import Config

    monkeypatch.setenv("AGENTIC_MAX_COMPLETION_ATTEMPTS", "5")
    config = Config.from_env(env_file=tmp_path / "missing.env")

    assert config.max_completion_attempts == 5
