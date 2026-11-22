#!/usr/bin/env bash
set -euo pipefail

# The workspace directory is passed as the first command-line argument.
# If omitted, fall back to the caller's current working directory.
if [[ $# -gt 0 ]]; then
    WORKSPACE_DIR="$1"
    shift
else
    WORKSPACE_DIR="$(pwd)"
fi

# Normalize to an absolute path.
WORKSPACE_DIR="$(cd -- "$WORKSPACE_DIR" && pwd)"

# The Agentic CLI backend lives under backend/ relative to the workspace.
BACKEND_DIR="$WORKSPACE_DIR/backend"

if [[ ! -d "$BACKEND_DIR" ]]; then
    echo "Error: backend directory not found at $BACKEND_DIR" >&2
    echo "Usage: $0 [workspace-dir] [cli-args...]" >&2
    echo "  workspace-dir : folder containing backend/ (defaults to current directory)" >&2
    exit 1
fi

cd "$BACKEND_DIR"

# Ensure dev dependencies are synced (lint, tests)
uv sync --extra dev >/dev/null 2>&1 || true

# Run the agentic CLI, forwarding all remaining arguments
exec uv run python -m src.main "$@"
