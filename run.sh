#!/usr/bin/env bash
set -euo pipefail

# Workspace directory defaults to the directory where this script lives.
# This lets you run ./run.sh from anywhere — the script's own folder is
# always treated as the workspace.
WORKSPACE_DIR="${1:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)}"

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

# Shift off the workspace-dir argument so the rest are forwarded to the CLI.
shift

cd "$BACKEND_DIR"

# Ensure dev dependencies are synced (lint, tests)
uv sync --extra dev >/dev/null 2>&1 || true

# Run the agentic CLI, forwarding all remaining arguments
exec uv run python -m src.main "$@"
