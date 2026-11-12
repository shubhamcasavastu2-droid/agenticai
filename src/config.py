from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
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

        session_dir = os.getenv("AGENTIC_SESSION_DIR")
        return cls(
            base_url=os.getenv("AGENTIC_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("AGENTIC_API_KEY", "ollama"),
            model=os.getenv("AGENTIC_MODEL", "llama3.1"),
            request_timeout_seconds=float(os.getenv("AGENTIC_REQUEST_TIMEOUT_SECONDS", "300")),
            max_completion_tokens=int(os.getenv("AGENTIC_MAX_COMPLETION_TOKENS", "8192")),
            context_window_tokens=int(os.getenv("AGENTIC_CONTEXT_WINDOW_TOKENS", "32768")),
            max_completion_attempts=int(os.getenv("AGENTIC_MAX_COMPLETION_ATTEMPTS", "3")),
            max_output_size=int(os.getenv("AGENTIC_MAX_OUTPUT_SIZE", "8000")),
            max_steps=int(os.getenv("AGENTIC_MAX_STEPS", "50")),
            max_retries=int(os.getenv("AGENTIC_MAX_RETRIES", "3")),
            stream=_env_bool("AGENTIC_STREAM", True),
            completion_review=_env_bool("AGENTIC_COMPLETION_REVIEW", True),
            review_model=os.getenv("AGENTIC_REVIEW_MODEL", ""),
            log_dir=Path(os.getenv("AGENTIC_LOG_DIR", "logs")),
            session_dir=Path(session_dir).expanduser() if session_dir else None,
            project_root=Path(os.getenv("AGENTIC_PROJECT_ROOT", ".")).resolve(),
        )
