#!/usr/bin/env bash
set -euo pipefail

# The workspace folder is wherever this script is invoked from (the caller's CWD),
# NOT where this script lives. This lets you run ./run.sh from any project folder
# and have that folder treated as the workspace.
WORKSPACE_DIR="$(pwd)"

# The Agentic CLI backend lives under backend/ relative to the workspace.
BACKEND_DIR="$WORKSPACE_DIR/backend"

if [[ ! -d "$BACKEND_DIR" ]]; then
    echo "Error: backend directory not found at $BACKEND_DIR" >&2
    echo "Make sure you run this script from a folder that contains backend/." >&2
    exit 1
fi

cd "$BACKEND_DIR"

# Ensure dev dependencies are synced (lint, tests)
uv sync --extra dev >/dev/null 2>&1 || true

# Run the agentic CLI, forwarding all arguments
exec uv run python -m src.main "$@"
