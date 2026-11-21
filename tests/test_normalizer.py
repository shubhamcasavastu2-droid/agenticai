from __future__ import annotations

import pytest

from src.cli import CLI
from src.config import Config
from src.types import ModelResponse, StopReason, TextBlock


class ScriptedProvider:
    def __init__(self, responses: list[ModelResponse]):
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def complete(self, system, messages, tools):
        self.calls.append(
            {"system": system, "messages": list(messages), "tools": tools}
        )
        return self.responses.pop(0)


def text_response(text: str) -> ModelResponse:
    return ModelResponse(
        blocks=[TextBlock(text=text)], stop_reason=StopReason.END_TURN
    )


def make_cli(monkeypatch, provider, tmp_path) -> CLI:
    """Build a CLI with interactive mode forced on and a scripted provider."""
    monkeypatch.setattr("src.cli.IS_INTERACTIVE", True)
    config = Config.from_env(env_file=tmp_path / "missing.env")
    cli = CLI(config)
    cli.provider = provider
    return cli


@pytest.mark.asyncio
async def test_detect_gap_complete_task_returns_none(monkeypatch, tmp_path):
    """A clear, complete task yields no gap (COMPLETE)."""
    provider = ScriptedProvider([text_response("COMPLETE")])
    cli = make_cli(monkeypatch, provider, tmp_path)

    gap, suggestions = await cli._detect_gap(
        "Create a project overview document",
        "Create docs/overview.md with a short project summary.",
    )

    assert gap is None
    assert suggestions == []
    assert provider.calls[0]["system"] == (
        "You are a precise gap-detection assistant. Reply only in the requested format."
    )
    assert "Create docs/overview.md with a short project summary." in provider.calls[0][
        "messages"
    ][0].content[0].text


@pytest.mark.asyncio
async def test_detect_gap_file_without_content_is_a_gap(monkeypatch, tmp_path):
    """Creating a file without specified content/purpose is a GAP, not invented."""
    provider = ScriptedProvider(
        [
            text_response(
                "GAP: The file content or purpose is not specified.\n"
                "SUGGEST: Provide the file contents | Describe what the file should contain | Skip creating the file"
            )
        ]
    )
    cli = make_cli(monkeypatch, provider, tmp_path)

    gap, suggestions = await cli._detect_gap(
        "Create a project overview document", "Create docs/overview.md"
    )

    assert gap is not None
    assert "content or purpose is not specified" in gap
    assert len(suggestions) == 3
    assert "Provide the file contents" in suggestions


@pytest.mark.asyncio
async def test_detect_gap_routine_detail_is_complete(monkeypatch, tmp_path):
    """Routine implementation details the agent can default are NOT gaps."""
    provider = ScriptedProvider([text_response("COMPLETE")])
    cli = make_cli(monkeypatch, provider, tmp_path)

    gap, suggestions = await cli._detect_gap(
        "Refactor the login function",
        "Rename variables in auth.py for clarity.",
    )

    assert gap is None
    assert suggestions == []


@pytest.mark.asyncio
async def test_detect_gap_inferred_context_is_complete(monkeypatch, tmp_path):
    """Information inferrable from context is not flagged as a gap."""
    provider = ScriptedProvider([text_response("COMPLETE")])
    cli = make_cli(monkeypatch, provider, tmp_path)

    gap, suggestions = await cli._detect_gap(
        "Add a unit test for the calculator",
        "Write a test asserting add(2, 3) == 5 in tests/test_calculator.py.",
    )

    assert gap is None
    assert suggestions == []


@pytest.mark.asyncio
async def test_confirmed_decision_skips_reask(monkeypatch, tmp_path):
    """Once a gap is confirmed, the task is excluded from re-detection."""
    provider = ScriptedProvider([text_response("COMPLETE")])
    cli = make_cli(monkeypatch, provider, tmp_path)

    # Simulate a previously confirmed decision.
    cli.confirmed_decisions["Create docs/overview.md"] = "Include team contacts"

    pending = [t for t in ["Create docs/overview.md"] if t not in cli.confirmed_decisions]
    assert pending == []

    # No provider call should be made for a confirmed task.
    assert provider.calls == []


@pytest.mark.asyncio
async def test_confirmed_decision_stored_after_answer(monkeypatch, tmp_path):
    """A user answer to a gap is stored in confirmed_decisions."""
    provider = ScriptedProvider(
        [
            text_response(
                "GAP: The file content is not specified.\n"
                "SUGGEST: Provide the file contents | Describe the file purpose | Skip creating the file"
            )
        ]
    )
    cli = make_cli(monkeypatch, provider, tmp_path)

    gap, suggestions = await cli._detect_gap(
        "Create a config file", "Create config.yaml"
    )
    assert gap is not None

    # Simulate storing the user's confirmed answer.
    cli.confirmed_decisions["Create config.yaml"] = "Database connection settings"

    # Re-detection should now skip this task.
    pending = [t for t in ["Create config.yaml"] if t not in cli.confirmed_decisions]
    assert pending == []


def test_normalizer_prompt_prohibits_invented_content():
    """The default normalizer prompt explicitly forbids inventing file content."""
    prompt = Config().normalizer_system_prompt
    assert "Do NOT invent file content" in prompt
    assert "flag that as a gap" in prompt
    assert "materially affects" in prompt


def test_refurbish_prompt_prohibits_invented_content():
    """The default refurbish prompt explicitly forbids inventing file content."""
    prompt = Config().user_input_refurbish_prompt
    assert "Do not invent requirements, assumptions, or file content" in prompt
    assert "flag it as missing information" in prompt
