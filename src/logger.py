"""
Logging infrastructure for Agentic CLI.

This module provides:
- Rotating file logger with configurable size and backup count
- Secret redaction for API keys, tokens, passwords, and authorization headers
- Console logging at WARNING level by default
- Structured log messages for context usage, permissions, and errors

The logger is configured with a NullHandler by default so importing this module
does not create log files. Call setup_logging() from the CLI entry point to
initialize file and console handlers.
"""

from __future__ import annotations

import logging
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "agentic_cli"

# The module logger has no handlers until setup_logging() is called from the CLI entry point,
# so importing this module (e.g. from tests) never creates directories or files.
logger = logging.getLogger(LOGGER_NAME)
logger.addHandler(logging.NullHandler())
logger.propagate = False

_SECRET_PATTERNS = [
    # key=value / key: value style assignments for common secret names
    re.compile(
        r"(?i)\b([A-Z0-9_]*(?:API_KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Z0-9_]*)\s*([=:])\s*"
        r"(\"[^\"]*\"|'[^']*'|\S+)"
    ),
    # Authorization headers
    re.compile(r"(?i)\b(authorization)\s*([:=])\s*(bearer\s+\S+|\S+)"),
]
_TOKEN_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),  # OpenAI / OpenRouter style
    re.compile(r"\bnvapi-[A-Za-z0-9_\-]{16,}"),  # NVIDIA NIM
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),  # GitHub tokens
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key id
]


def redact(text: str) -> str:
    """Mask obvious secrets before they are written to the log file."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}***REDACTED***", text)
    for pattern in _TOKEN_PATTERNS:
        text = pattern.sub("***REDACTED***", text)
    return text


def setup_logging(
    log_dir: str | Path = "logs",
    log_filename: str = "log.log",
    level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    console_level: int = logging.WARNING,
) -> logging.Logger:
    """Attach a rotating file handler and a console handler (warnings and above)."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    log_file = log_path / log_filename

    logger.setLevel(level)
    logger.handlers.clear()

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(fmt="[%(levelname)s] %(message)s"))
    logger.addHandler(console_handler)

    return logger


def log_info(message: str) -> None:
    logger.info(message)


def log_warning(message: str) -> None:
    logger.warning(message)


def log_error(message: str) -> None:
    logger.error(message)


def log_exception(error: BaseException) -> None:
    logger.exception("Unhandled exception: %s: %r", type(error).__name__, error)


def log_debug(message: str) -> None:
    logger.debug(message)


def log_tool_call(tool_name: str, args: dict, output: str, is_error: bool = False) -> None:
    """Log tool execution details with secrets masked and output capped."""
    level = logging.ERROR if is_error else logging.INFO
    shown = output[:500]
    logger.log(
        level,
        "TOOL_CALL: %s args=%s output=%s",
        tool_name,
        redact(repr(args)),
        redact(shown),
    )


def log_permission(tool_name: str, allowed: bool, reason: str | None = None) -> None:
    """Log permission decisions."""
    level = logging.INFO if allowed else logging.WARNING
    logger.log(level, "PERMISSION: %s allowed=%s reason=%s", tool_name, allowed, reason)


def log_command(command: str) -> None:
    """Log slash commands."""
    logger.info("COMMAND: %s", redact(command))


def log_reasoning(reasoning: str) -> None:
    """Log model reasoning."""
    logger.debug("REASONING: %s", redact(reasoning[:1000]))
