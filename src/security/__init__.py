"""Safety and permissions.

Responsibility: guard file-system and shell access, decide whether a tool call may run, and apply
shell-command safety rules. Objective: keep destructive or network-piped commands from executing
without explicit user approval.
"""

from .permissions import (
    INTERACTIVE_TOOLS,
    READ_ONLY_TOOLS,
    PathValidationError,
    PermissionGate,
    TruncationError,
    check_deny_list,
    is_write_tool,
    make_truncate_output,
    truncate_output,
    validate_path,
)
from .shell_safety import find_denied_reason

__all__ = [
    "READ_ONLY_TOOLS",
    "INTERACTIVE_TOOLS",
    "PermissionGate",
    "PathValidationError",
    "TruncationError",
    "validate_path",
    "is_write_tool",
    "check_deny_list",
    "truncate_output",
    "make_truncate_output",
    "find_denied_reason",
]
