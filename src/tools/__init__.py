"""
Built-in Tools for Agentic CLI.

This package provides the core tools available to the agent:
- read_file: Read files with optional offset/limit
- write_file: Write content to files (creates parent directories)
- edit_file: Edit files by replacing exact string matches
- glob: Find files matching glob patterns
- grep: Search for regex patterns in files
- bash: Execute shell commands with safety checks
- ask_user: Ask the user for clarification or choices
- plan: Present a plan for user approval
- todo: Manage a todo list for task tracking

Tools are registered via ToolRegistry and exposed to the model via JSON schemas.
Each tool implements the Tool base class with an async execute() method.
"""

from __future__ import annotations

from .ask_tool import create_ask_user_tool
from .bash_tool import create_bash_tool
from .change_workspace import create_change_workspace_tool
from .edit_file import EditFileError, create_edit_file_tool
from .glob_tool import create_glob_tool
from .grep_tool import create_grep_tool
from .plan_tool import create_plan_tool
from .read_file import create_read_file_tool
from .registry import ToolRegistry, create_tool_schema
from .todo_tool import create_todo_tool
from .write_file import create_write_file_tool

__all__ = [
    "ToolRegistry",
    "create_tool_schema",
    "create_read_file_tool",
    "create_write_file_tool",
    "create_edit_file_tool",
    "EditFileError",
    "create_glob_tool",
    "create_grep_tool",
    "create_bash_tool",
    "create_ask_user_tool",
    "create_plan_tool",
    "create_todo_tool",
    "create_change_workspace_tool",
]
