"""Prompt construction.

Responsibility: build the system prompt and user-input normalizer prompt from environment, tools,
skills, agents and AGENT.md. Objective: give the model a consistent, grounded operating context.
"""

from .system_prompt import (
    AGENT_MD_CONTENT,
    INPUT_NORMALIZER_PROMPT,
    SYSTEM_PROMPT_TEMPLATE,
    build_input_normalization_prompt,
    build_system_prompt,
    build_user_input_refurbish_prompt,
    get_tool_descriptions,
)

__all__ = [
    "SYSTEM_PROMPT_TEMPLATE",
    "AGENT_MD_CONTENT",
    "INPUT_NORMALIZER_PROMPT",
    "build_system_prompt",
    "build_input_normalization_prompt",
    "build_user_input_refurbish_prompt",
    "get_tool_descriptions",
]
