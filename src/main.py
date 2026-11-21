from __future__ import annotations

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


def main_sync() -> None:
    """Synchronous entry point for console script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main_sync()
