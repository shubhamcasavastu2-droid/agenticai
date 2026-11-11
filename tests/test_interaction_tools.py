from __future__ import annotations

from io import StringIO
from typing import cast

import pytest
from rich.console import Console

from src.agent import AgentLoop
from src.completion import CompletionResolver, CompletionResult
from src.tools.ask_tool import create_ask_user_tool
from src.tools.plan_tool import create_plan_tool


@pytest.mark.asyncio
async def test_ask_user_tool_returns_callback_answer():
    received = {}

    async def ask_callback(question: str, options: list[str] | None) -> str:
        received.update(question=question, options=options)
        return "Option B"

    tool = create_ask_user_tool(ask_callback)
    result = await tool.execute(question="Which option?", options=["Option A", "Option B"])

    assert tool.name == "ask_user"
    assert result == "Option B"
    assert received == {
        "question": "Which option?",
        "options": ["Option A", "Option B"],
    }


@pytest.mark.asyncio
async def test_plan_tool_returns_user_decision():
    received = {}

    async def plan_callback(
        title: str,
        summary: str,
        steps: list[str],
        risks: list[str],
    ) -> str:
        received.update(title=title, summary=summary, steps=steps, risks=risks)
        return "APPROVED"

    tool = create_plan_tool(plan_callback)
    result = await tool.execute(
        title="Add feature",
        summary="Implement and verify the feature.",
        steps=["Add the tool", "Test it"],
        risks=["Existing behavior may change"],
    )

    assert tool.name == "plan"
    assert result == "APPROVED"
    assert received == {
        "title": "Add feature",
        "summary": "Implement and verify the feature.",
        "steps": ["Add the tool", "Test it"],
        "risks": ["Existing behavior may change"],
    }


@pytest.mark.asyncio
async def test_cli_registers_interaction_tools(tmp_path):
    from src.cli import CLI
    from src.config import Config

    cli = CLI(Config(project_root=tmp_path))
    await cli.initialize()

    try:
        schemas = {schema.name for schema in cli.registry.schemas()}
        assert {"ask_user", "plan"} <= schemas
    finally:
        assert cli.provider is not None
        await cli.provider.close()


@pytest.mark.asyncio
async def test_cli_normalizes_input_in_separate_loop(tmp_path, monkeypatch):
    import src.cli as cli_module
    from src.cli import CLI
    from src.config import Config

    cli = CLI(Config(project_root=tmp_path))
    received: dict[str, list[str]] = {"normalizer": [], "agent": []}
    output = StringIO()
    monkeypatch.setattr(cli_module, "console", Console(file=output, force_terminal=False))

    class LoopStub:
        def __init__(self, result: str, key: str):
            self.result = result
            self.key = key

        def add_user_message(self, message: str) -> None:
            received[self.key].append(message)

        async def run(self) -> str:
            return self.result

        def clear_history(self) -> None:
            return None

    cli.input_normalizer_loop = cast(
        AgentLoop,
        LoopStub("normalized request", "normalizer"),
    )
    cli.agent_loop = cast(AgentLoop, LoopStub("completed", "agent"))

    class ResolverStub:
        async def run(self, agent, original_request: str, normalized_request: str):
            assert original_request == "raw request"
            assert normalized_request == "normalized request"
            return CompletionResult("completed", True, 1)

    cli.completion_resolver = cast(CompletionResolver, ResolverStub())

    await cli.handle_input("raw request")

    assert "raw request" in received["normalizer"][0]
    assert received["agent"] == ["normalized request"]
    assert "Normalized input sent to coding agent" in output.getvalue()
    assert "normalized request" in output.getvalue()


@pytest.mark.asyncio
async def test_cli_does_not_send_normalization_error_to_agent(tmp_path):
    from src.cli import CLI
    from src.config import Config

    cli = CLI(Config(project_root=tmp_path))
    coding_messages: list[str] = []

    class NormalizerStub:
        def __init__(self, result: str):
            self.result = result

        def add_user_message(self, message: str) -> None:
            return None

        async def run(self) -> str:
            return self.result

        def clear_history(self) -> None:
            return None

    cli.input_normalizer_loop = cast(
        AgentLoop,
        NormalizerStub("Error: The model returned an empty response after a retry."),
    )

    class CodingAgentStub:
        def add_user_message(self, message: str) -> None:
            coding_messages.append(message)

        async def run(self) -> str:
            return "unused"

    cli.agent_loop = cast(AgentLoop, CodingAgentStub())

    await cli.handle_input("Create a document")

    assert coding_messages == []


def test_system_prompt_requires_english_for_user_facing_text(tmp_path):
    from src.system_prompt import build_system_prompt

    prompt = build_system_prompt(tmp_path, "ask_user and plan")

    assert "Use English only for all user-facing text" in prompt


@pytest.mark.asyncio
async def test_cli_normalizer_has_english_no_questions_system_prompt(tmp_path):
    from src.cli import CLI
    from src.config import Config

    cli = CLI(Config(project_root=tmp_path))
    await cli.initialize()

    try:
        assert cli.input_normalizer_loop is not None
        assert "in English" in cli.input_normalizer_loop.system_prompt
        assert "do not ask the user questions" in cli.input_normalizer_loop.system_prompt
        assert cli.input_normalizer_loop.registry.schemas() == []
        assert cli.input_normalizer_loop.reasoning_callback == cli._reasoning_callback
    finally:
        assert cli.provider is not None
        await cli.provider.close()


def test_log_exception_keeps_details_for_empty_message(monkeypatch):
    import importlib

    logger_module = importlib.import_module("src.logger")
    captured: list[str] = []

    def capture_exception(message: str, *args: object) -> None:
        captured.append(message % args)

    monkeypatch.setattr(logger_module.logger, "exception", capture_exception)

    logger_module.log_exception(RuntimeError())

    formatted = captured[0]
    assert "RuntimeError" in formatted
    assert "RuntimeError()" in formatted
