from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .shell_safety import find_denied_reason


class PathValidationError(ValueError):
    pass


class TruncationError(Exception):
    pass


def validate_path(project_root: Path, path: str) -> Path:
    """Resolve and validate a path is within the project root."""
    project_root = Path(os.path.realpath(project_root))

    # Expand user and resolve relative to project root
    target = Path(path).expanduser()

    if not target.is_absolute():
        target = project_root / target

    target = Path(os.path.realpath(target))

    # Check for directory traversal attempts using commonpath
    try:
        common = os.path.commonpath([str(project_root), str(target)])
    except ValueError:
        raise PathValidationError(f"Path escapes project root: {path}")

    if common != str(project_root):
        raise PathValidationError(f"Path escapes project root: {path}")

    return target


def is_write_tool(tool_name: str) -> bool:
    return tool_name in {"write_file", "edit_file", "bash"}


def check_deny_list(command: str, project_root: Path | None = None) -> bool:
    """True if the shell command matches a safety rule and must not run."""
    return find_denied_reason(command, project_root) is not None


MAX_OUTPUT_SIZE = 2000


def truncate_output(output: str, max_size: int = MAX_OUTPUT_SIZE) -> str:
    if len(output) <= max_size:
        return output
    truncated = output[:max_size]
    return truncated + f"\n\n[OUTPUT TRUNCATED: {len(output)} chars, showing first {max_size}]"


def make_truncate_output(max_size: int):
    """Create a truncate_output function with a specific max size."""
    def _truncate(output: str) -> str:
        return truncate_output(output, max_size)
    return _truncate


# Read-only tools are confined to the project root by validate_path, so the CLI runs them
# without prompting. Write tools and bash always start in "prompt" mode.
READ_ONLY_TOOLS = frozenset({"read_file", "glob", "grep"})
# Tools that interact with the user themselves and therefore need no separate approval.
INTERACTIVE_TOOLS = frozenset({"ask_user", "plan"})


class PermissionGate:
    """Per-session tool permissions. Safety rules are always evaluated before allow-lists."""

    def __init__(self, project_root: Path | None = None, default_auto_allow: frozenset[str] = frozenset()):
        self.project_root = project_root
        self.default_auto_allow = default_auto_allow
        self._always_allow: set[str] = set()  # tool names always allowed
        self._auto_allow: set[str] = set(default_auto_allow)  # tool names auto-allowed (no prompt)
        self._always_deny: set[str] = set()  # tool names denied without prompting

    def safety_violation(self, tool_name: str, args: dict[str, Any]) -> str | None:
        """Reason the call is unconditionally refused, regardless of allow-lists."""
        if tool_name in self._always_deny:
            return f"Tool '{tool_name}' is denied for this session"
        if tool_name == "bash":
            command = str(args.get("command", ""))
            reason = find_denied_reason(command, self.project_root)
            if reason:
                return f"Command blocked by safety policy: {reason}"
        return None

    def is_preapproved(self, tool_name: str) -> bool:
        return tool_name in self._always_allow or tool_name in self._auto_allow

    def mode(self, tool_name: str) -> str:
        if tool_name in self._always_deny:
            return "denied"
        if tool_name in self._always_allow:
            return "always"
        if tool_name in self._auto_allow:
            return "auto"
        return "prompt"

    def check(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Returns (allowed, reason_if_denied).
        If allowed is False, reason explains why.
        """
        violation = self.safety_violation(tool_name, args)
        if violation:
            return False, violation
        if self.is_preapproved(tool_name):
            return True, None
        return False, f"Tool '{tool_name}' requires permission"

    def allow_always(self, tool_name: str) -> None:
        self._always_deny.discard(tool_name)
        self._always_allow.add(tool_name)

    def allow_auto(self, tool_name: str) -> None:
        self._always_deny.discard(tool_name)
        self._auto_allow.add(tool_name)

    def clear(self, tool_name: str) -> None:
        """Return a tool to the default 'prompt' mode."""
        self._always_allow.discard(tool_name)
        self._auto_allow.discard(tool_name)
        self._always_deny.discard(tool_name)

    def deny(self, tool_name: str) -> None:
        self._always_allow.discard(tool_name)
        self._auto_allow.discard(tool_name)
        self._always_deny.add(tool_name)

    def reset(self) -> None:
        """Restore the defaults this gate was created with."""
        self._always_allow.clear()
        self._auto_allow = set(self.default_auto_allow)
        self._always_deny.clear()
