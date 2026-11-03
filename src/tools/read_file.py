from __future__ import annotations

from pathlib import Path

from ..permissions import make_truncate_output, validate_path
from ..types import Tool, ToolSchema

READ_FILE_SCHEMA = ToolSchema(
    name="read_file",
    description="Read a file from the filesystem. Supports optional offset and limit for partial reads.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read"},
            "offset": {"type": "integer", "description": "Line number to start reading from (1-indexed)", "minimum": 1},
            "limit": {"type": "integer", "description": "Maximum number of lines to read"},
        },
        "required": ["path"],
        "additionalProperties": False,
    },
)


class ReadFileTool(Tool):
    def __init__(self, project_root: Path, max_output_size: int = 2000):
        self.project_root = project_root.resolve()
        self._truncate = make_truncate_output(max_output_size)
        super().__init__(
            name="read_file",
            description=READ_FILE_SCHEMA.description,
            schema=READ_FILE_SCHEMA,
        )

    async def execute(self, path: str, offset: int | None = None, limit: int | None = None) -> str:
        validated_path = validate_path(self.project_root, path)

        try:
            with open(validated_path, encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {path}")

        total_lines = len(lines)
        start = (offset - 1) if offset else 0
        end = start + limit if limit else total_lines

        start = max(0, min(start, total_lines))
        end = max(start, min(end, total_lines))

        selected = lines[start:end]

        # Format with line numbers
        output = ""
        for i, line in enumerate(selected, start=start + 1):
            output += f"{i}: {line}"

        if not output.endswith("\n") and output:
            output += "\n"

        # Add context about what was read
        if offset or limit:
            output = f"[Lines {start + 1}-{end} of {total_lines}]\n{output}"

        return self._truncate(output)


def create_read_file_tool(project_root: Path, max_output_size: int = 2000) -> ReadFileTool:
    return ReadFileTool(project_root, max_output_size)
