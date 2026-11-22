#!/usr/bin/env bash
set -euo pipefail

# Workspace directory: first command-line argument if it is a path, otherwise
# the directory where this script lives.
# Root directory: second argument if provided, otherwise defaults to workspace_dir.
# Root dir stays constant (global skills/agents); workspace_dir can change at runtime.
if [[ $# -gt 0 && "$1" != -* ]]; then
    WORKSPACE_DIR="$1"
    shift
else
    WORKSPACE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
fi

if [[ $# -gt 0 && "$1" != -* ]]; then
    ROOT_DIR="$1"
    shift
else
    ROOT_DIR="$WORKSPACE_DIR"
fi

# Normalize to absolute paths.
WORKSPACE_DIR="$(cd -- "$WORKSPACE_DIR" && pwd)"
ROOT_DIR="$(cd -- "$ROOT_DIR" && pwd)"

# The Agentic CLI backend lives under backend/ relative to the workspace.
BACKEND_DIR="$WORKSPACE_DIR/backend"

if [[ ! -d "$BACKEND_DIR" ]]; then
    echo "Error: backend directory not found at $BACKEND_DIR" >&2
    echo "Usage: $0 [workspace-dir] [root-dir] [cli-args...]" >&2
    echo "  workspace-dir : folder containing backend/ (defaults to this script's dir)" >&2
    echo "  root-dir      : root folder for global .agents skills/agents (defaults to workspace-dir)" >&2
    exit 1
fi

cd "$BACKEND_DIR"

# Ensure dev dependencies are synced (lint, tests)
uv sync --extra dev >/dev/null 2>&1 || true

# Run the agentic CLI, passing root_dir and workspace_dir as program arguments
# and forwarding all remaining CLI arguments.
exec uv run python -m src.main --root-dir "$ROOT_DIR" --workspace "$WORKSPACE_DIR" "$@"
