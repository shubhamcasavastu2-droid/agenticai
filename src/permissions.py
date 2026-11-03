from __future__ import annotations

import os
import shlex
from pathlib import Path
from typing import Any


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


DENY_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "git push --force",
    "git push -f",
    "dd if=",
    "mkfs",
    "format ",
    "> /dev/sd",
    "chmod -R 777 /",
    "chown -R root /",
]


def check_deny_list(command: str) -> bool:
    """Check if command matches any deny patterns. Returns True if denied."""
    cmd_lower = command.lower().strip()
    for pattern in DENY_PATTERNS:
        if pattern.lower() in cmd_lower:
            return True
    return False


MAX_OUTPUT_SIZE = 2000


def truncate_output(output: str, max_size: int = MAX_OUTPUT_SIZE) -> str:
    if len(output) <= max_size:
        return output
    truncated = output[:max_size]
    return truncated + f"\n\n[OUTPUT TRUNCATED: {len(output)} chars, showing first {max_size}]"


class PermissionGate:
    def __init__(self):
        self._always_allow: set[str] = set()  # tool names allowed for session

    def check(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Returns (allowed, reason_if_denied).
        If allowed is False, reason explains why.
        """
        if tool_name in self._always_allow:
            return True, None

        if not is_write_tool(tool_name):
            return True, None

        # For bash, check deny list
        if tool_name == "bash":
            command = args.get("command", "")
            if check_deny_list(command):
                return False, f"Command matches deny list: {command}"

        return False, f"Tool '{tool_name}' requires permission"

    def allow_always(self, tool_name: str) -> None:
        self._always_allow.add(tool_name)

    def reset(self) -> None:
        self._always_allow.clear()