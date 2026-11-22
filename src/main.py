from __future__ import annotations

import argparse
import asyncio

from .app import Application
from .config.config import Config
from .logger import setup_logging


async def main() -> None:
    config = Config.from_env()
    setup_logging(config.log_dir)
    app = Application(config)
    try:
        await app.run()
    finally:
        await app.close()


def main_sync(root_dir: str | None = None, workspace_dir: str | None = None) -> None:
    """Synchronous entry point for console script.

    Args:
        root_dir: Fixed root directory where global skills/agents live.
        workspace_dir: Changeable working directory. If None, defaults to root_dir.
    """
    try:
        config = Config.from_env(root_dir=root_dir, workspace_dir=workspace_dir)
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
        "--root-dir",
        "-r",
        default=None,
        help="Root directory for global skills/agents (defaults to current directory)",
    )
    parser.add_argument(
        "--workspace",
        "-w",
        default=None,
        help="Workspace directory (defaults to root_dir)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    main_sync(root_dir=args.root_dir, workspace_dir=args.workspace)
