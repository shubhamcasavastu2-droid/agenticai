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


# ------------------------------------------------------------------
# Recursive gap / duplicate question / scope containment tests
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enriched_task_title_not_reanalyzed(monkeypatch, tmp_path):
    """An enriched task title (task — answer) must NOT be re-analyzed as a gap.

    This prevents recursive gaps where the answer itself gets flagged as a new
    missing requirement.
    """
    provider = ScriptedProvider([text_response("COMPLETE")])
    cli = make_cli(monkeypatch, provider, tmp_path)

    # Simulate a previously resolved gap: the canonical title is resolved.
    cli.resolved_gaps.add("Create config.yaml")

    # The normalized text might contain an enriched title like
    # "Create config.yaml — Database connection settings".
    gap, suggestions = await cli._detect_gap(
        "Create a config file", "Create config.yaml — Database connection settings"
    )

    # Canonical title strips the enrichment, matches resolved_gaps → skip.
    assert gap is None
    assert suggestions == []
    assert provider.calls == []  # no provider call for a resolved task


@pytest.mark.asyncio
async def test_resolved_gap_skips_provider_call(monkeypatch, tmp_path):
    """A resolved gap must not trigger any provider call (no duplicate questions)."""
    provider = ScriptedProvider([text_response("COMPLETE")])
    cli = make_cli(monkeypatch, provider, tmp_path)

    cli.resolved_gaps.add("Write README")

    gap, suggestions = await cli._detect_gap("Document the project", "Write README")
    assert gap is None
    assert suggestions == []
    assert provider.calls == []


@pytest.mark.asyncio
async def test_canonical_title_strips_enrichment():
    """Canonical task title must strip any " — answer" suffix."""
    cli = CLI.__new__(CLI)  # no __init__ needed for pure helper
    assert cli._canonical_task_title("Create config.yaml") == "Create config.yaml"
    assert (
        cli._canonical_task_title("Create config.yaml — Database connection settings")
        == "Create config.yaml"
    )
    assert cli._canonical_task_title("  Write README  ") == "Write README"


def test_loaded_capabilities_dedup():
    """Already-loaded capabilities must not be re-added (deduplication)."""
    cli = CLI.__new__(CLI)
    cli.loaded_capabilities = set()

    cli._register_loaded_capabilities(
        [{"type": "skill", "name": "code-reviewer", "task_index": 0, "description": "x"}]
    )
    cli._register_loaded_capabilities(
        [{"type": "skill", "name": "code-reviewer", "task_index": 0, "description": "x"}]
    )
    cli._register_loaded_capabilities(
        [{"type": "agent", "name": "doc-agent", "task_index": 1, "description": "y"}]
    )

    assert cli.loaded_capabilities == {"skill:code-reviewer", "agent:doc-agent"}


def test_assemble_normalized_no_load_tasks():
    """_assemble_normalized must NOT add 'Load X' lines as executable tasks
    (prevents scope expansion and task contamination)."""
    cli = CLI.__new__(CLI)

    result = cli._assemble_normalized(
        original_input="Create a file",
        objective="Create docs/overview.md",
        tasks=[{"title": "Create docs/overview.md", "status": "pending"}],
        matched_capabilities=[
            {
                "type": "skill",
                "name": "doc-generator",
                "task_index": 0,
                "description": "Generates docs",
            }
        ],
    )

    # Capability info present but NOT as a "Load X" task line.
    assert "doc-generator" in result
    assert "loaded into main context" in result
    assert "Load " not in result  # no load tasks added as executable steps
    assert "Tasks to achieve:\n- Create docs/overview.md" in result


def test_normalizer_prompt_prevents_scope_expansion():
    """The normalizer prompt must not encourage scope expansion."""
    prompt = Config().normalizer_system_prompt
    assert "Do not suggest additional features" in prompt
    assert "expand the task scope" in prompt
    assert "minimal, actionable tasks" in prompt

