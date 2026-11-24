"""
Data models for Agentic CLI.

Defines the core data structures used throughout the application:
- ConfigModel: Application configuration
- SessionModel: Session state and metadata
- TaskModel: Todo/task tracking
- MessageModel: Conversation messages
- CommandModel: Slash command definitions
- ProcessModel: Process channel state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class CommandType(StrEnum):
    ASK = "ask"
    PLAN = "plan"
    AGENTS_DEFAULT = "agents-default"
    SESSION = "session"
    SCHEDULE = "schedule"
    AGENT = "agent"
    SKILLS = "skills"
    HOOK = "hook"
    ORCHESTRATOR = "orchestrator"
    JOB = "job"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    BLOCKED = "blocked"


class ProcessStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ConfigModel:
    """Application configuration data model."""
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
    review_model: str = ""
    log_dir: str = "logs"
    session_dir: str | None = None
    root_dir: str = ""
    workspace_dir: str = ""
    normalizer_system_prompt: str = ""
    completion_review_prompt: str = ""
    system_prompt_template: str = ""
    user_input_refurbish_prompt: str = ""
    ask_system_prompt: str = ""
    plan_system_prompt: str = ""
    agents_default_system_prompt: str = ""
    session_system_prompt: str = ""
    agent_system_prompt: str = ""
    skills_system_prompt: str = ""
    env_vars: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model": self.model,
            "request_timeout_seconds": self.request_timeout_seconds,
            "max_completion_tokens": self.max_completion_tokens,
            "context_window_tokens": self.context_window_tokens,
            "max_completion_attempts": self.max_completion_attempts,
            "max_output_size": self.max_output_size,
            "max_steps": self.max_steps,
            "max_retries": self.max_retries,
            "stream": self.stream,
            "completion_review": self.completion_review,
            "review_model": self.review_model,
            "log_dir": self.log_dir,
            "session_dir": self.session_dir,
            "root_dir": self.root_dir,
            "workspace_dir": self.workspace_dir,
            "normalizer_system_prompt": self.normalizer_system_prompt,
            "completion_review_prompt": self.completion_review_prompt,
            "system_prompt_template": self.system_prompt_template,
            "user_input_refurbish_prompt": self.user_input_refurbish_prompt,
            "env_vars": self.env_vars,
        }


@dataclass
class SessionModel:
    """Session state and metadata."""
    session_id: str
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    workspace_dir: str = ""
    root_dir: str = ""
    current_command: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()


@dataclass
class TaskModel:
    """Todo/task tracking model."""
    task_id: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    depends_on: list[str] = field(default_factory=list)
    result: str | None = None
    error: str | None = None

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()


@dataclass
class MessageModel:
    """Conversation message model."""
    role: str  # "user", "assistant", "tool", "system"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandModel:
    """Slash command definition model."""
    name: str  # without leading slash
    usage: str
    summary: str
    processor: str  # processor module name
    allowed_tools: list[str] = field(default_factory=list)
    requires_confirmation: bool = False


@dataclass
class ProcessModel:
    """Process channel state model."""
    process_id: str
    command_type: CommandType
    status: ProcessStatus = ProcessStatus.CREATED
    session_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    current_task: str | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now().isoformat()


@dataclass
class NormalizedInput:
    """Result of input normalization."""
    objective: str
    tasks: list[str]
    gaps: list[str]
    assumptions: list[str]
    recommendations: list[str]
    readiness: str  # "READY", "READY_WITH_ASSUMPTIONS", "NEEDS_INPUT"
    raw: str = ""
