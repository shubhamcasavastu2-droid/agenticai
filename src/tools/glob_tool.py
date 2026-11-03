from __future__ import annotations

import glob as glob_module
from pathlib import Path

from ..permissions import make_truncate_output
from ..types import Tool, ToolSchema

GLOB_SCHEMA = ToolSchema(
    name="glob",
    description="Find files matching a glob pattern. Returns sorted list of relative paths.",
    parameters={
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py', 'src/**/*.ts')"},
        },
        "required": ["pattern"],
        "additionalProperties": False,
    },
)


class GlobTool(Tool):
    def __init__(self, project_root: Path, max_output_size: int = 2000):
        self.project_root = project_root.resolve()
        self._truncate = make_truncate_output(max_output_size)
        super().__init__(
            name="glob",
            description=GLOB_SCHEMA.description,
            schema=GLOB_SCHEMA,
        )

    async def execute(self, pattern: str) -> str:
        # Validate pattern doesn't escape project root
        # Use project_root as base for glob
        search_path = self.project_root / pattern
        matches = glob_module.glob(str(search_path), recursive=True)

        # Convert to relative paths
        relative_matches = []
        for match in matches:
            try:
                rel = Path(match).relative_to(self.project_root)
                relative_matches.append(str(rel))
            except ValueError:
                continue

        relative_matches.sort()

        if not relative_matches:
            return f"No files match pattern: {pattern}"

        output = "\n".join(relative_matches)
        return self._truncate(output)


def create_glob_tool(project_root: Path, max_output_size: int = 2000) -> GlobTool:
    return GlobTool(project_root, max_output_size)
