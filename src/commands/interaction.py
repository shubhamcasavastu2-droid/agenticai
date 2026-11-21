from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..cli import CLI
    from . import CommandRegistry


async def plan_command(cli: CLI, args: list[str]) -> None:
    """Create a plan by hand and present it for approval."""
    if not cli.interactive:
        cli._ui.warning("/plan requires an interactive terminal")
        return
    title = cli._ui.prompt("Plan title")
    summary = cli._ui.prompt("Summary")
    steps = [s.strip() for s in cli._ui.prompt("Steps (comma-separated)").split(",") if s.strip()]
    if not steps:
        cli._ui.error("At least one step is required")
        return
    risks_input = cli._ui.prompt("Risks (comma-separated, optional)", default="")
    risks = [r.strip() for r in risks_input.split(",") if r.strip()]
    result = await cli.present_plan(title, summary, steps, risks)
    cli._ui.success(result)


async def ask_command(cli: CLI, args: list[str]) -> None:
    """Ask a question, optionally with fixed choices.

    Uses the ask_user tool from the registry for schema validation,
    then prompts the user through cli.ask_user().
    """
    if not cli.interactive:
        cli._ui.warning("/ask requires an interactive terminal")
        return

    # Associate with the ask_user tool: verify it exists in the registry
    tool = cli.registry.get("ask_user")
    if tool is None:
        cli._ui.error("ask_user tool not available in registry")
        return

    question = cli._ui.prompt("Question")
    options_input = cli._ui.prompt("Options (comma-separated, optional)", default="")
    options = [o.strip() for o in options_input.split(",") if o.strip()] or None

    # Validate against ask_user tool schema
    if not question.strip():
        cli._ui.error("question cannot be empty")
        return
    if options is not None and not options:
        cli._ui.error("options cannot be empty when provided")
        return

    answer = await cli.ask_user(question, options)
    cli._ui.success(f"Answer: {answer}")


def register(registry: CommandRegistry) -> None:
    registry.add("plan", "/plan", "Create a plan and present it for approval", plan_command)
    registry.add("ask", "/ask", "Ask a question, optionally with fixed choices", ask_command)
