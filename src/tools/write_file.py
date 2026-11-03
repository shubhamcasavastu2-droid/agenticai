from __future__ import annotations

from pathlib import Path

from ..permissions import validate_path
from ..types import Tool, ToolSchema

WRITE_FILE_SCHEMA = ToolSchema(
    name="write_file",
    description="Write content to a file. Creates parent directories if needed. Overwrites existing file.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to write"},
            "content": {"type": "string", "description": "Content to write to the file"},
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
)


class WriteFileTool(Tool):
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        super().__init__(
            name="write_file",
            description=WRITE_FILE_SCHEMA.description,
            schema=WRITE_FILE_SCHEMA,
        )

    async def execute(self, path: str, content: str) -> str:
        validated_path = validate_path(self.project_root, path)

        # Create parent directories
        validated_path.parent.mkdir(parents=True, exist_ok=True)

        with open(validated_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Written {len(content)} chars to {path}"


def create_write_file_tool(project_root: Path) -> WriteFileTool:
    return WriteFileTool(project_root)
