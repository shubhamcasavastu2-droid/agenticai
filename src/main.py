from __future__ import annotations

import argparse
import asyncio

from .app import Application
from .config import Config
from .logger import setup_logging


async def main() -> None:
    config = Config.from_env()
    setup_logging(config.log_dir)
    app = Application(config)
    try:
        await app.run()
    finally:
        await app.close()


def main_sync(workspace_dir: str | None = None) -> None:
    """Synchronous entry point for console script.

    Args:
        workspace_dir: Path to the workspace directory. If None, defaults to
            the current working directory (or AGENTIC_PROJECT_ROOT env var).
    """
    try:
        config = Config.from_env(project_root=workspace_dir)
        setup_logging(config.log_dir)
        app = Application(config)
        try:
            asyncio.run(app.run())
        finally:
            asyncio.run(app.close())
    except KeyboardInterrupt:
        pass


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic CLI")
    parser.add_argument(
        "--workspace",
        "-w",
        default=None,
        help="Workspace directory (defaults to current working directory)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main_sync(workspace_dir=args.workspace)
