#!/usr/bin/env bash
set -euo pipefail

# Resolve the directory where this script lives, regardless of where it's invoked from.
# This makes the workspace folder (where run.sh resides) the working directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
WORKSPACE_DIR="$SCRIPT_DIR"

# The Agentic CLI backend lives under backend/
BACKEND_DIR="$WORKSPACE_DIR/backend"

if [[ ! -d "$BACKEND_DIR" ]]; then
    echo "Error: backend directory not found at $BACKEND_DIR" >&2
    exit 1
fi

cd "$BACKEND_DIR"

# Ensure dev dependencies are synced (lint, tests)
uv sync --extra dev >/dev/null 2>&1 || true

# Run the agentic CLI, forwarding all arguments
exec uv run python -m src.main "$@"
