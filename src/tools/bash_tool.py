from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Any

from ..types import Tool, ToolSchema
from ..permissions import validate_path, truncate_output, check_deny_list


BASH_TOOL_SCHEMA = ToolSchema(
    name="bash",
    description="Execute a shell command. Captures stdout and stderr. Long output is truncated.",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "timeout_seconds": {"type": "integer", "description": "Timeout in seconds", "minimum": 1, "maximum": 300, "default": 60},
            "workdir": {"type": "string", "description": "Working directory (relative to project root)"},
        },
        "required": ["command"],
        "additionalProperties": False,
    },
)


class BashTool(Tool):
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        super().__init__(
            name="bash",
            description=BASH_TOOL_SCHEMA.description,
            schema=BASH_TOOL_SCHEMA,
        )

    async def execute(self, command: str, timeout_seconds: int = 60, workdir: str | None = None) -> str:
        # Check deny list
        if check_deny_list(command):
            raise PermissionError(f"Command denied by security policy: {command}")

        # Resolve working directory
        if workdir:
            cwd = validate_path(self.project_root, workdir)
        else:
            cwd = self.project_root

        # Execute command
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timed out after {timeout_seconds}s")

        except Exception as e:
            raise RuntimeError(f"Failed to execute command: {e}")

        stdout_str = stdout.decode("utf-8", errors="replace") if stdout else ""
        stderr_str = stderr.decode("utf-8", errors="replace") if stderr else ""

        output = ""
        if stdout_str:
            output += f"STDOUT:\n{stdout_str}"
        if stderr_str:
            if output:
                output += "\n"
            output += f"STDERR:\n{stderr_str}"

        if process.returncode != 0:
            output += f"\n[Exit code: {process.returncode}]"

        return truncate_output(output)


def create_bash_tool(project_root: Path) -> BashTool:
    return BashTool(project_root)