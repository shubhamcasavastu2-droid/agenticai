#!/usr/bin/env bash
set -euo pipefail

# Workspace directory: first command-line argument if it is a path, otherwise
# the directory where this script lives. This lets you run ./run.sh from
# anywhere and have the script's own folder treated as the workspace.
if [[ $# -gt 0 && "$1" != -* ]]; then
    WORKSPACE_DIR="$1"
    shift
else
    WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
fi

# Normalize to an absolute path.
WORKSPACE_DIR="$(cd -- "$WORKSPACE_DIR" && pwd)"

# The Agentic CLI backend lives under backend/ relative to the workspace.
BACKEND_DIR="$WORKSPACE_DIR/backend"

if [[ ! -d "$BACKEND_DIR" ]]; then
    echo "Error: backend directory not found at $BACKEND_DIR" >&2
    echo "Usage: $0 [workspace-dir] [cli-args...]" >&2
    echo "  workspace-dir : folder containing backend/ (defaults to this script's dir)" >&2
    exit 1
fi

cd "$BACKEND_DIR"

# Ensure dev dependencies are synced (lint, tests)
uv sync --extra dev >/dev/null 2>&1 || true

# Run the agentic CLI, passing the workspace dir as a program argument
# and forwarding all remaining CLI arguments.
exec uv run python -m src.main --workspace "$WORKSPACE_DIR" "$@"
