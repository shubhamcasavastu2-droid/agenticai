from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

_TRUE_VALUES = {"1", "true", "yes", "on"}


def get_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _env_bool(name: str, default: bool) -> bool:
    value = get_env(name)
    if not value.strip():
        return default
    return value.strip().lower() in _TRUE_VALUES


@dataclass
class Config:
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: str = "llama3.1"
    request_timeout_seconds: float = 300.0
    max_completion_tokens: int = 8192
    context_window_tokens: int = 32768
    max_completion_attempts: int = 3
    max_output_size: int = 8000
    max_steps: int = 50
    max_retries: int = 3
    stream: bool = True
    completion_review: bool = True
    review_model: str = ""  # empty -> reuse `model`
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    session_dir: Path | None = None  # None -> <project_root>/.agentic/sessions
    project_root: Path = field(default_factory=Path.cwd)

    @property
    def sessions_path(self) -> Path:
        return self.session_dir or (self.project_root / ".agentic" / "sessions")

    @classmethod
    def getValues(cls, key: str, default_val: str = "", is_option: bool = False) -> Any:

        value = get_env(key, default_val)

        if is_option:
            if value == default_val:
                return value
            raise Exception(f"Invalid value for {key}: {value}. Expected one of: {default_val}")

        return value

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            default_locations = [
                Path.cwd() / ".env",
                Path.cwd() / ".env.local",
                Path.home() / ".config" / "agentic-cli" / ".env",
            ]
            for path in default_locations:
                if path.exists():
                    load_dotenv(path)
                    break

        session_dir = get_env("AGENTIC_SESSION_DIR")
        return cls(
            base_url=get_env("AGENTIC_BASE_URL", "http://localhost:11434/v1"),
            api_key=get_env("AGENTIC_API_KEY", "ollama"),
            model=get_env("AGENTIC_MODEL", "llama3.1"),
            request_timeout_seconds=float(get_env("AGENTIC_REQUEST_TIMEOUT_SECONDS", "300")),
            max_completion_tokens=int(get_env("AGENTIC_MAX_COMPLETION_TOKENS", "8192")),
            context_window_tokens=int(get_env("AGENTIC_CONTEXT_WINDOW_TOKENS", "32768")),
            max_completion_attempts=int(get_env("AGENTIC_MAX_COMPLETION_ATTEMPTS", "3")),
            max_output_size=int(get_env("AGENTIC_MAX_OUTPUT_SIZE", "8000")),
            max_steps=int(get_env("AGENTIC_MAX_STEPS", "50")),
            max_retries=int(get_env("AGENTIC_MAX_RETRIES", "3")),
            stream=_env_bool("AGENTIC_STREAM", True),
            completion_review=_env_bool("AGENTIC_COMPLETION_REVIEW", True),
            review_model=get_env("AGENTIC_REVIEW_MODEL", ""),
            log_dir=Path(get_env("AGENTIC_LOG_DIR", "logs")),
            session_dir=Path(session_dir).expanduser() if session_dir else None,
            project_root=Path(get_env("AGENTIC_PROJECT_ROOT", ".")).resolve(),
        )


