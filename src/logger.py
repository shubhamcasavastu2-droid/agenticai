from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys


def setup_logging(
    log_dir: str | Path = "logs",
    log_filename: str = "log.log",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console_level: int = logging.WARNING,
) -> logging.Logger:
    """Set up logging to file and optionally console."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / log_filename

    logger = logging.getLogger("agentic_cli")
    logger.setLevel(level)
    logger.handlers.clear()

    # File handler - all logs go to log.log
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler - only warnings and errors to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(message)s",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = setup_logging()


def log_info(message: str) -> None:
    logger.info(message)


def log_warning(message: str) -> None:
    logger.warning(message)


def log_error(message: str) -> None:
    logger.error(message)


def log_debug(message: str) -> None:
    logger.debug(message)


def log_tool_call(tool_name: str, args: dict, output: str, is_error: bool = False) -> None:
    """Log tool execution details."""
    level = logging.ERROR if is_error else logging.INFO
    logger.log(
        level,
        "TOOL_CALL: %s args=%s output=%s",
        tool_name,
        args,
        output[:500] if len(output) > 500 else output,
    )


def log_permission(tool_name: str, allowed: bool, reason: str | None = None) -> None:
    """Log permission decisions."""
    level = logging.INFO if allowed else logging.WARNING
    logger.log(level, "PERMISSION: %s allowed=%s reason=%s", tool_name, allowed, reason)


def log_command(command: str) -> None:
    """Log slash commands."""
    logger.info("COMMAND: %s", command)


def log_reasoning(reasoning: str) -> None:
    """Log model reasoning."""
    logger.debug("REASONING: %s", reasoning[:1000])
