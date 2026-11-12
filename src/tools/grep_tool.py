from __future__ import annotations

import re
from pathlib import Path

from ..permissions import make_truncate_output, validate_path
from ..types import Tool, ToolSchema

GREP_SCHEMA = ToolSchema(
    name="grep",
    description="Search for a regex pattern in files. Returns matching lines with file paths and line numbers.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {
                "type": "string",
                "description": "Directory or file to search in (relative to project root)",
                "default": ".",
            },
            "include": {"type": "string", "description": "File pattern to include (e.g., '*.py')"},
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
)


class GrepTool(Tool):
    def __init__(self, project_root: Path, max_output_size: int = 2000):
        self.project_root = project_root.resolve()
        self._truncate = make_truncate_output(max_output_size)
        super().__init__(
            name="grep",
            description=GREP_SCHEMA.description,
            schema=GREP_SCHEMA,
        )

    async def execute(self, pattern: str, path: str = ".", include: str | None = None) -> str:
        search_root = validate_path(self.project_root, path)

        # Compile regex
        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        matches = []

        if search_root.is_file():
            files = [search_root]
        else:
            if include:
                files = list(search_root.rglob(include))
            else:
                files = [f for f in search_root.rglob("*") if f.is_file()]

        for file_path in files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    lines = f.readlines()
            except (UnicodeDecodeError, PermissionError):
                continue

            for i, line in enumerate(lines, 1):
                if regex.search(line):
                    try:
                        rel_path = file_path.relative_to(self.project_root)
                    except ValueError:
                        rel_path = file_path
                    matches.append(f"{rel_path}:{i}: {line.rstrip()}")

        if not matches:
            return f"No matches for pattern: {pattern}"

        output = "\n".join(matches)
        return self._truncate(output)


def create_grep_tool(project_root: Path, max_output_size: int = 2000) -> GrepTool:
    return GrepTool(project_root, max_output_size)
