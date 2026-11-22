from __future__ import annotations

import re
from typing import TYPE_CHECKING

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ..capabilities.skills import Skill
from ..core.agent import AgentLoop
from ..security.permissions import READ_ONLY_TOOLS, PermissionGate
from ..tools import ToolRegistry

if TYPE_CHECKING:
    from ..cli import CLI
    from . import CommandRegistry

SKILL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n\s*```\s*$", re.DOTALL)

SKILLS_HELP = """
**Skills Commands:**
- `/skills` or `/skills list` - List all skills
- `/skills show <name>` - Show skill details
- `/skills create <name> [description]` - Design a new skill with the agent

Skill names use lowercase letters, digits and hyphens.
"""

QUESTIONS = [
    ("trigger", "When should this skill be used? (e.g. 'user wants to plan a project')"),
    ("inputs", "What inputs does the skill need from the user?"),
    ("outputs", "What should the skill produce? (e.g. plan document, code changes, analysis)"),
    ("tools", "What tools does it need? (read_file, write_file, edit_file, glob, grep, bash - or 'all')"),
    ("workflow", "Describe the step-by-step workflow in 3-5 steps"),
    ("constraints", "Any special requirements, constraints, or example use cases?"),
]


def strip_code_fence(text: str) -> str:
    """Models often wrap the whole file in ```markdown ... ```; unwrap it."""
    match = FENCE.match(text.strip())
    return match.group(1).strip() + "\n" if match else text.strip() + "\n"


def show_skills(cli: CLI) -> None:
    skills = cli.skill_loader.all()
    if not skills:
        cli._ui.warning("No skills loaded")
        return
    table = Table(title="Loaded Skills", border_style="ui.border")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Version", style="yellow")
    for skill in skills:
        table.add_row(skill.name, skill.description, str(skill.metadata.get("version", "1.0")))
    cli._ui.console.print(table)


def show_skill_detail(cli: CLI, skill: Skill) -> None:
    content = f"**Name**: {skill.name}\n**Description**: {skill.description}\n"
    if skill.metadata:
        content += f"**Metadata**: {skill.metadata}\n"
    if skill.content:
        content += f"\n---\n{skill.content}"
    cli._ui.console.print(Panel(Markdown(content), title=f"Skill: {skill.name}", border_style="cyan"))


def _collect_answers(cli: CLI, description: str) -> dict[str, str]:
    if not cli.interactive:
        cli._ui.warning("Non-interactive mode: using description to generate skill")
        return {
            "trigger": description,
            "inputs": "User request",
            "outputs": "Generated skill file",
            "tools": "all",
            "workflow": "Generate skill from description",
            "constraints": "Follow standard skill format",
        }
    answers: dict[str, str] = {}
    for key, question in QUESTIONS:
        answer = cli._ui.prompt(question)
        if answer.lower() in ("done", "finish", "complete", "skip"):
            cli._ui.warning("Skipping remaining questions...")
            break
        answers[key] = answer
    return answers


def _design_prompt(name: str, answers: dict[str, str]) -> str:
    return f"""Create a complete SKILL.md file for a skill named "{name}".

User requirements:
- Trigger: {answers.get('trigger', 'Not specified')}
- Inputs: {answers.get('inputs', 'Not specified')}
- Outputs: {answers.get('outputs', 'Not specified')}
- Tools: {answers.get('tools', 'all')}
- Workflow: {answers.get('workflow', 'Not specified')}
- Constraints: {answers.get('constraints', 'None')}

Generate a complete skill file with:
1. YAML frontmatter (name, description, license, compatibility, metadata)
2. Markdown content with:
   - ## When to use (trigger conditions)
   - ## Workflow (step-by-step)
   - ## Tools required
   - ## Inputs/Outputs
   - Any references/scripts/assets sections if needed

You may read existing skills under .agents/skills/ for reference.
Output ONLY the skill file content (no code fences), nothing else."""


async def create_skill(cli: CLI, name: str, description: str) -> None:
    if not SKILL_NAME.match(name):
        cli._ui.error("Invalid skill name: use lowercase letters, digits and hyphens (max 64)")
        return
    skill_dir = cli.config.project_root / ".agents" / "skills" / name
    if (skill_dir / "SKILL.md").exists():
        cli._ui.error(f"Skill already exists: {name}")
        return
    if cli.provider is None:
        raise RuntimeError("Provider is not initialized")

    cli._ui.info(f"Designing skill: {name}")
    if description:
        cli._ui.console.print(f"Initial idea: {description}\n")
    prompt = _design_prompt(name, _collect_answers(cli, description))

    # The designer only needs to read existing skills; it never writes files or runs commands.
    design_tools = ToolRegistry()
    for tool in cli.registry.all():
        if tool.name in READ_ONLY_TOOLS:
            design_tools.register(tool)
    design_agent = AgentLoop(
        provider=cli.provider,
        registry=design_tools,
        permission_gate=PermissionGate(cli.config.project_root, default_auto_allow=READ_ONLY_TOOLS),
        system_prompt="You design SKILL.md files for a coding agent. Follow the user's requirements exactly.",
        max_steps=5,
        reasoning_callback=cli.on_reasoning,
        tool_callback=cli.on_tool,
        context_window_tokens=cli.config.context_window_tokens,
        max_completion_tokens=cli.config.max_completion_tokens,
    )
    design_agent.add_user_message(prompt)
    with cli.console.status("[bold cyan]Generating skill...[/bold cyan]"):
        design = await design_agent.run()
    cli.end_stream()

    if not design or design.startswith("Error"):
        cli._ui.error(f"Failed to generate skill: {design}")
        return
    content = strip_code_fence(design)
    if not content.startswith("---"):
        content = (
            f"---\nname: {name}\ndescription: {description or 'Auto-generated skill'}\nlicense: MIT\n"
            'metadata:\n  version: "1.0"\n  skill-author: Agent Designer\n---\n\n' + content
        )
    cli._ui.console.print(Panel(Markdown(content), title="📋 Generated Skill", border_style="green"))

    if cli.interactive:
        if cli._ui.prompt("Create this skill?", choices=["y", "n"], default="y") != "y":
            cli._ui.warning("Skill creation cancelled")
            return
    else:
        cli._ui.warning("Non-interactive: auto-confirming skill creation")

    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    cli._ui.success(f"Created skill: {name}")
    cli._ui.console.print(f"Path: {skill_file}")
    cli.skill_loader.discover()


async def skills_command(cli: CLI, args: list[str]) -> None:
    subcommand = args[0].lower() if args else "list"
    if subcommand == "list":
        show_skills(cli)
    elif subcommand == "show":
        if len(args) < 2:
            cli._ui.error("Usage: /skills show <skill-name>")
            return
        skill = cli.skill_loader.get(args[1])
        if skill:
            show_skill_detail(cli, skill)
        else:
            cli._ui.error(f"Skill not found: {args[1]}")
    elif subcommand == "create":
        if len(args) < 2:
            cli._ui.error("Usage: /skills create <skill-name> [description]")
            return
        await create_skill(cli, args[1], " ".join(args[2:]).strip("\"'"))
    else:
        cli._ui.error(f"Unknown skills subcommand: {subcommand}")
        cli._ui.console.print(Panel(Markdown(SKILLS_HELP), title="Skills Help", border_style="cyan"))


def register(registry: CommandRegistry) -> None:
    registry.add("skills", "/skills [list|show|create]", "List, inspect or design skills", skills_command)
