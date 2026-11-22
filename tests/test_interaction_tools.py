from __future__ import annotations

from io import StringIO
from typing import Any, cast

import pytest
from rich.console import Console

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
    from src.app import Application
    from src.config.config import Config

    app = Application(Config(root_dir=tmp_path))
    await app.initialize()

    try:
        cli = app.cli
        schemas = {schema.name for schema in cli.registry.schemas()}
        assert {"ask_user", "plan"} <= schemas
    finally:
        assert app.provider is not None
        await app.provider.close()


@pytest.mark.asyncio
async def test_cli_normalizes_input_via_provider(tmp_path, monkeypatch):
    import src.cli as cli_module
    from src.cli import CLI
    from src.config.config import Config
    from src.provider import ModelResponse
    from src.types import StopReason, TextBlock

    cli = CLI(Config(root_dir=tmp_path))
    output = StringIO()
    monkeypatch.setattr(cli_module, "console", Console(file=output, force_terminal=False))

    class ProviderStub:
        async def complete(self, system, messages, tools):
            return ModelResponse(
                blocks=[TextBlock(text="normalized request")],
                stop_reason=StopReason.END_TURN,
            )

    cli.provider = cast(Any, ProviderStub())

    result = await cli.normalize_input("raw request")

    assert result == "normalized request"
    assert "Normalized input sent to coding agent" in output.getvalue()
    assert "normalized request" in output.getvalue()


@pytest.mark.asyncio
async def test_cli_does_not_send_normalization_error_to_agent(tmp_path, monkeypatch):
    import src.cli as cli_module
    from src.cli import CLI
    from src.config.config import Config
    from src.provider import ModelResponse
    from src.types import StopReason, TextBlock

    cli = CLI(Config(root_dir=tmp_path))
    output = StringIO()
    monkeypatch.setattr(cli_module, "console", Console(file=output, force_terminal=False))

    class ProviderStub:
        async def complete(self, system, messages, tools):
            return ModelResponse(
                blocks=[TextBlock(text="Error: The model returned an empty response after a retry.")],
                stop_reason=StopReason.END_TURN,
            )

    cli.provider = cast(Any, ProviderStub())

    result = await cli.normalize_input("Create a document")

    assert result.startswith("Error:")


def test_system_prompt_requires_english_for_user_facing_text(tmp_path):
    from src.prompt.system_prompt import build_system_prompt

    prompt = build_system_prompt(tmp_path, "ask_user and plan")

    assert "Use English only for all user-facing text" in prompt


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
