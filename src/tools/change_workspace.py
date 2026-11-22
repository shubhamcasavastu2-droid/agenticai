"""
Change workspace directory tool.

Allows the agent to change the working directory at runtime during a session.
Updates the Project singleton so all components use the new workspace.
"""

from __future__ import annotations

from pathlib import Path

from ..config.project_dir import Project
from ..types import Tool, ToolSchema

CHANGE_WORKSPACE_SCHEMA = ToolSchema(
    name="change_workspace",
    description="Change the working directory / workspace folder. "
    "Updates the project root so all subsequent file operations use the new directory.",
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


class ChangeWorkspaceTool(Tool):
    def __init__(self) -> None:
        super().__init__(
            name="change_workspace",
            description=CHANGE_WORKSPACE_SCHEMA.description,
            schema=CHANGE_WORKSPACE_SCHEMA,
        )

    async def execute(self, path: str) -> str:
        """Change the workspace directory and update the Project singleton."""
        new_dir = Path(path).expanduser()
        if not new_dir.is_absolute():
            # Resolve relative to current project root
            current = Project.get_instance().project_root
            new_dir = current / new_dir
        new_dir = new_dir.resolve()

        if not new_dir.is_dir():
            return f"Error: '{new_dir}' is not a valid directory"

        # Update the Project singleton
        Project.set_project_dir(new_dir)

        return (
            f"Workspace changed to: {new_dir}\n"
            f"All subsequent file operations will use this directory."
        )


def create_change_workspace_tool() -> ChangeWorkspaceTool:
    return ChangeWorkspaceTool()
