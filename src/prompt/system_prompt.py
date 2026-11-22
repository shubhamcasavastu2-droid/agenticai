
"""
System Prompt Builder for Agentic CLI.

Responsibilities:
- Construct the runtime system prompt.
- Inject environment information.
- Generate tool descriptions with parameter schemas.
- Load optional AGENT.md project instructions.
- Inject discovered skills and agents.
- Build user-input normalization prompts.

This module only builds prompts. It does not execute tools or agents.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_TEMPLATE = """
You are an agentic coding assistant operating in a terminal environment.

Your responsibility is to understand the user's objective, inspect the environment,
perform the requested work using available tools, verify the results, and report
accurately.

# Runtime Environment

- Working directory: {{working_dir}}
- Operating system: {{os_name}} {{os_version}}
- Date: {{date}}
- Shell: {{shell}}

# Available Tools

{{tool_descriptions}}


# Tool Usage Rules

1. Explore first. Use search, glob, grep, and read tools to understand
   the workspace before making changes.
2. Read files before editing them.
3. Prefer edit operations for existing files instead of replacing their
   entire contents.
4. Make the smallest change that achieves the requested objective.
5. Verify changes using appropriate commands, tests, or builds.
6. Never claim success without evidence.
7. If a tool fails, analyze the failure and change your approach.
8. Do not repeatedly execute the same failed action without a reason.
9. If blocked after reasonable attempts, explain the blocker.
10. Perform independent inspection operations together when appropriate.
11. If output is truncated, narrow the search or retrieve the missing content.
12. Use only tools that are available in the current runtime.
13. Follow each tool's parameter schema and constraints.
14. Do not fabricate tool results.
15. Use English only for all user-facing text:
    questions and options passed to ask_user, plans, and final responses.

# Scope Control

1. Only modify files necessary to fulfill the user's request.
2. Do not perform unrelated refactoring.
3. Do not introduce dependencies unless necessary.
4. Do not change existing behavior outside the requested scope.
5. Do not create additional files unless they are required.
6. Do not assume a documentation request requires code changes.
7. Do not assume a code request requires configuration, deployment,
   or environment changes.
8. Distinguish workspace/environment operations from project modifications.
9. Before making a broader change outside the requested scope, explain
   why it is necessary.
10. Preserve existing user changes. Never overwrite unrelated modifications.
"""


# ---------------------------------------------------------------------------
# AGENT.MD DEFAULT CONTENT
# ---------------------------------------------------------------------------

AGENT_MD_CONTENT = """# Project Instructions

Add project-specific guidelines, conventions, architecture information,
development commands, testing requirements, and key project information here.

These instructions are loaded as project context for the agent.
They must not override system-level instructions or safety requirements.
"""


# ---------------------------------------------------------------------------
# USER INPUT NORMALIZER
# ---------------------------------------------------------------------------

INPUT_NORMALIZER_PROMPT = """
Analyze the user's input and preserve their exact intent.

Rules:

- Correct spelling and grammar only when necessary for clarity.
- Normalize the objective into clear, concise English.
- Preserve the user's original meaning, scope, constraints, priorities,
  and requested outcome.
- Break the objective into only the tasks necessary to achieve it.
- Do not expand scope.
- Do not introduce unrelated implementation tasks.
- Do not invent requirements, technical decisions, or expected behavior.
- Do not assume source code, configuration, imports, dependencies,
  deployment, or project files need modification unless the objective
  requires it.
- Distinguish workspace/environment changes from project changes.
- Do not assume a vague request has a specific technical solution.
- Preserve ambiguity when it cannot be resolved from the input.
- Identify missing information only if it prevents understanding or execution.
- Do not ask questions during normalization.
- Do not provide implementation advice.
- Do not create a plan beyond the necessary task list.
- Recommend skills or agents only when clearly relevant.
- Keep the result concise.

User input:
{{user_input}}

Return exactly in the following format:

User wants to achieve: <normalized objective>

Tasks to achieve:
- <necessary task>
- <necessary task>

Do not add any other sections.
"""


# ---------------------------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------------------------

@dataclass
class SkillInfo:
    """Details about a discovered skill."""

    name: str
    description: str
    path: str
    source: str  # root or workspace
    tag: str  # [EXISTING] or [NEW]


@dataclass
class AgentInfo:
    """Details about a discovered agent."""

    name: str
    description: str
    path: str
    source: str  # root or workspace
    tag: str  # [EXISTING] or [NEW]


# ---------------------------------------------------------------------------
# SKILLS SECTION BUILDER
# ---------------------------------------------------------------------------

def build_skills_section(skills: Sequence[SkillInfo]) -> str:
    """Build the skills registry section."""

    if not skills:
        return ""

    lines = [
        "# Available Skills",
        "",
        "Skills are specialized instruction resources.",
        "Read relevant skill files before using them.",
        "",
    ]

    for skill in skills:
        lines.extend(
            [
                f"## {skill.name} {skill.tag}",
                f"- Description: {skill.description}",
                f"- Path: {skill.path}",
                f"- Source: {skill.source}",
                "",
            ]
        )

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# AGENTS SECTION BUILDER
# ---------------------------------------------------------------------------

def build_agents_section(agents: Sequence[AgentInfo]) -> str:
    """Build the available agents registry section."""

    if not agents:
        return ""

    lines = [
        "# Available Agents",
        "",
        "Agents provide specialized capabilities.",
        "Use them only when they materially help the current task.",
        "",
    ]

    for agent in agents:
        lines.extend(
            [
                f"## {agent.name} {agent.tag}",
                f"- Description: {agent.description}",
                f"- Path: {agent.path}",
                f"- Source: {agent.source}",
                "",
            ]
        )

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# TOOL SCHEMA HELPERS
# ---------------------------------------------------------------------------

def _get_tool_schema(tool: Any) -> Any:
    """
    Extract a tool's parameter schema from common tool representations.

    Supported attributes:
    - input_schema
    - parameters
    - args_schema
    - schema

    The schema may be a dict, Pydantic model, or JSON-schema provider.
    """

    for attribute in (
        "input_schema",
        "parameters",
        "args_schema",
        "schema",
    ):
        schema = getattr(tool, attribute, None)

        if schema is None:
            continue

        # Some tools expose schema as a method.
        if callable(schema):
            try:
                schema = schema()
            except Exception:
                continue

        # Pydantic v2
        if hasattr(schema, "model_json_schema"):
            try:
                schema = schema.model_json_schema()
            except Exception:
                continue

        # Pydantic v1
        elif hasattr(schema, "schema") and callable(schema.schema):
            try:
                schema = schema.schema()
            except Exception:
                continue

        if schema is not None:
            return schema

    return None


def get_tool_descriptions(tools: Sequence[Any]) -> str:
    """
    Generate readable tool descriptions including parameter schemas.

    Supports tools exposing:
    - name
    - description
    - input_schema / parameters / args_schema / schema
    """

    if not tools:
        return "No tools are currently available."

    lines = ["# Tool Registry", ""]

    for tool in tools:
        name = getattr(tool, "name", "unknown_tool")
        description = getattr(tool, "description", "No description provided.")

        lines.append(f"## {name}")
        lines.append(f"Description: {description}")

        schema = _get_tool_schema(tool)

        if schema is not None:
            try:
                schema_json = json.dumps(
                    schema,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
                lines.append("Parameters JSON Schema:")
                lines.append(schema_json)
            except (TypeError, ValueError):
                lines.append(f"Parameters: {schema}")
        else:
            lines.append("Parameters: Schema unavailable.")

        lines.append("")

    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# PROJECT INSTRUCTIONS LOADER
# ---------------------------------------------------------------------------

def load_agent_md(agent_md_path: Path | None) -> str:
    """
    Load AGENT.md project instructions.

    Missing files are normal.
    Read errors are logged instead of silently ignored.
    """

    if agent_md_path is None:
        return ""

    agent_md_path = Path(agent_md_path)

    if not agent_md_path.exists():
        return ""

    if not agent_md_path.is_file():
        logger.warning(
            "Project instructions path is not a file: %s",
            agent_md_path,
        )
        return ""

    try:
        content = agent_md_path.read_text(
            encoding="utf-8"
        ).strip()

        return content

    except OSError as exc:
        logger.warning(
            "Unable to read project instructions from %s: %s",
            agent_md_path,
            exc,
        )
        return ""


# ---------------------------------------------------------------------------
# SYSTEM PROMPT BUILDER
# ---------------------------------------------------------------------------

def build_system_prompt(
    project_root: Path,
    tool_descriptions: str,
    agent_md_path: Path | None = None,
    skills_info: str = "",
    agents_info: str = '',
    system_prompt_template: str = SYSTEM_PROMPT_TEMPLATE,
) -> str:
    """
    Build the complete runtime system prompt.

    The prompt is dynamically constructed using the current environment,
    tool descriptions, discovered skills, discovered agents, and project
    instructions.
    """

    project_root = Path(project_root)

    working_dir = str(project_root.resolve())

    os_name = platform.system()
    os_version = platform.release()

    date = datetime.now().strftime("%Y-%m-%d")

    shell = os.environ.get("SHELL", "unknown")

    # Use explicit token replacement rather than str.format().
    # This avoids conflicts with JSON braces in injected content.
    replacements = {
        "{{working_dir}}": working_dir,
        "{{os_name}}": os_name,
        "{{os_version}}": os_version,
        "{{date}}": date,
        "{{shell}}": shell,
        "{{tool_descriptions}}": tool_descriptions,
    }

    prompt = system_prompt_template

    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, str(value))

    # Add discovered skills.
    if skills_info.strip():
        prompt += f"\n\n{skills_info.strip()}"

    # Add discovered agents.
    if agents_info.strip():
        prompt += f"\n\n{agents_info.strip()}"

    # Add project instructions.
    agent_md = load_agent_md(agent_md_path)

    if agent_md:
        prompt += (
            "\n\n# Project Instructions (from AGENT.md)\n"
            "These are project-specific instructions. Follow them only when "
            "they do not conflict with higher-priority instructions.\n\n"
            f"{agent_md}"
        )

    return prompt.strip()


# ---------------------------------------------------------------------------
# USER INPUT NORMALIZATION PROMPT BUILDER
# ---------------------------------------------------------------------------

def build_input_normalization_prompt(
    user_input: str,
    prompt_template: str = INPUT_NORMALIZER_PROMPT,
    user_input_refurbish_prompt: str | None = None,
) -> str:
    """
    Build a prompt used to normalize user input.

    This function does not invoke an LLM. It only constructs the prompt.
    """

    if not isinstance(user_input, str):
        raise TypeError("user_input must be a string")

    user_input = user_input.strip()

    if not user_input:
        raise ValueError("User input cannot be empty.")

    # Use user_input_refurbish_prompt if provided, otherwise fall back to prompt_template
    template = user_input_refurbish_prompt or prompt_template

    # Replace placeholder directly to avoid formatting conflicts
    # when the user input contains braces or JSON.
    return template.replace("{{user_input}}", user_input)


# Backward-compatible alias for the older function name
build_user_input_refurbish_prompt = build_input_normalization_prompt
