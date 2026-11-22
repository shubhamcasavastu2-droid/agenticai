"""
Change workspace directory tool.

Allows the agent to change the working directory at runtime during a session.
Only updates workspace_dir; root_dir (where global skills/agents live) stays constant.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from ..config.project_dir import Project
from ..types import Tool, ToolSchema

CHANGE_WORKSPACE_SCHEMA = ToolSchema(
    name="change_workspace",
    description="Change the working directory / workspace folder. "
    "Updates workspace_dir so all subsequent file operations use the new directory. "
    "root_dir (where global skills/agents live) stays unchanged.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "New workspace directory path (absolute or relative)",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
)

# Callback type for workspace refresh (re-registers tools, reloads skills/agents, rebuilds system prompt)
WorkspaceRefreshCallback = Callable[[str | Path], Awaitable[None]]


class ChangeWorkspaceTool(Tool):
    def __init__(self, refresh_callback: WorkspaceRefreshCallback | None = None) -> None:
        self.refresh_callback = refresh_callback
        super().__init__(
            name="change_workspace",
            description=CHANGE_WORKSPACE_SCHEMA.description,
            schema=CHANGE_WORKSPACE_SCHEMA,
        )

    async def execute(self, path: str) -> str:
        """Change the workspace directory and update the Project singleton."""
        new_dir = Path(path).expanduser()
        if not new_dir.is_absolute():
            # Resolve relative to current workspace dir
            current = Project.get_instance().workspace_dir
            new_dir = current / new_dir
        new_dir = new_dir.resolve()

        if not new_dir.is_dir():
            return f"Error: '{new_dir}' is not a valid directory"

        # Update only workspace_dir in the Project singleton; root_dir stays constant
        Project.set_workspace_dir(new_dir)

        # If a refresh callback is provided, call it to re-register tools, reload skills/agents, etc.
        if self.refresh_callback:
            await self.refresh_callback(new_dir)

        return (
            f"Workspace changed to: {new_dir}\n"
            f"Root dir (skills/agents): {Project.get_instance().root_dir}\n"
            f"All subsequent file operations will use this workspace directory."
        )


def create_change_workspace_tool(
    refresh_callback: WorkspaceRefreshCallback | None = None
) -> ChangeWorkspaceTool:
    return ChangeWorkspaceTool(refresh_callback)
