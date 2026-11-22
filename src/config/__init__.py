"""
Configuration package for Agentic CLI.

Provides centralized configuration management and the project directory singleton.
"""

from .config import (
    COMPLETION_REVIEW_PROMPT_DEFAULT,
    NORMALIZER_SYSTEM_PROMPT_DEFAULT,
    SYSTEM_PROMPT_TEMPLATE_DEFAULT,
    USER_INPUT_REFURBISH_PROMPT_DEFAULT,
    Config,
    get_env,
)
from .project_dir import Project, get_project_dir, project

__all__ = [
    "Config",
    "get_env",
    "Project",
    "get_project_dir",
    "project",
    "NORMALIZER_SYSTEM_PROMPT_DEFAULT",
    "COMPLETION_REVIEW_PROMPT_DEFAULT",
    "SYSTEM_PROMPT_TEMPLATE_DEFAULT",
    "USER_INPUT_REFURBISH_PROMPT_DEFAULT",
]
