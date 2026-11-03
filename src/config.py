from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: str = "llama3.1"
    max_output_size: int = 8000
    max_steps: int = 50
    project_root: Path = field(default_factory=Path.cwd)

    @classmethod
    def from_env(cls, env_file: Path | None = None) -> Config:
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            # Try default locations
            for path in [Path.cwd() / ".env", Path.cwd() / ".env.local", Path.home() / ".config" / "agentic-cli" / ".env"]:
                if path.exists():
                    load_dotenv(path)
                    break

        return cls(
            base_url=os.getenv("AGENTIC_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("AGENTIC_API_KEY", "ollama"),
            model=os.getenv("AGENTIC_MODEL", "llama3.1"),
            max_output_size=int(os.getenv("AGENTIC_MAX_OUTPUT_SIZE", "8000")),
            max_steps=int(os.getenv("AGENTIC_MAX_STEPS", "50")),
            project_root=Path(os.getenv("AGENTIC_PROJECT_ROOT", ".")).resolve(),
        )
