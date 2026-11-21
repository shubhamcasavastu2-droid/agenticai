from __future__ import annotations

from pathlib import Path

from ..security.permissions import validate_path
from ..types import Tool, ToolSchema

EDIT_FILE_SCHEMA = ToolSchema(
    name="edit_file",
    description="Edit a file by replacing an exact string match. Fails if match is missing or not unique.",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Path to the file to edit"},
            "old_string": {"type": "string", "description": "Exact string to replace (must match uniquely)"},
            "new_string": {"type": "string", "description": "String to replace with"},
        },
        "required": ["path", "old_string", "new_string"],
        "additionalProperties": False,
    },
)


class EditFileError(Exception):
    def __init__(self, message: str, context: str = ""):
        self.context = context
        super().__init__(message)


class EditFileTool(Tool):
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        super().__init__(
            name="edit_file",
            description=EDIT_FILE_SCHEMA.description,
            schema=EDIT_FILE_SCHEMA,
        )

    async def execute(self, path: str, old_string: str, new_string: str) -> str:
        validated_path = validate_path(self.project_root, path)

        try:
            with open(validated_path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            raise EditFileError(f"File not found: {path}")
        except PermissionError:
            raise EditFileError(f"Permission denied: {path}")

        if not old_string:
            raise EditFileError("old_string cannot be empty")

        # Count occurrences
        count = content.count(old_string)

        if count == 0:
            # Show nearby context for debugging
            context = self._get_context(content, old_string)
            raise EditFileError(
                f"old_string not found in file. Showing context:\n{context}"
            )

        if count > 1:
            context = self._get_context(content, old_string)
            raise EditFileError(
                f"old_string matches {count} times (must be unique). Showing first match context:\n{context}"
            )

        # Replace
        new_content = content.replace(old_string, new_string)

        with open(validated_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"Edited {path}: replaced {len(old_string)} chars with {len(new_string)} chars"

    def _get_context(self, content: str, search: str, lines_before: int = 3, lines_after: int = 3) -> str:
        """Get context around the first occurrence of search string."""
        lines = content.splitlines(keepends=True)
        search_lines = search.splitlines(keepends=True)

        # Find first occurrence
        for i in range(len(lines) - len(search_lines) + 1):
            if lines[i:i+len(search_lines)] == search_lines:
                start = max(0, i - lines_before)
                end = min(len(lines), i + len(search_lines) + lines_after)

                context_lines = []
                for j in range(start, end):
                    marker = ">>> " if i <= j < i + len(search_lines) else "    "
                    context_lines.append(f"{j+1:4d} {marker}{lines[j].rstrip()}")

                return "\n".join(context_lines)

        # Fallback: show first 20 lines
        return "\n".join(f"{i+1:4d}    {line.rstrip()}" for i, line in enumerate(lines[:20]))


def create_edit_file_tool(project_root: Path) -> EditFileTool:
    return EditFileTool(project_root)
