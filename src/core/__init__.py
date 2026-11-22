"""Agent orchestration core.

Responsibility: run the agent loop, manage the context window, review completion, and persist
session transcripts. Objective: turn a user request into tool-using model steps until the work is
verified complete.
"""

from .agent import CONTINUATION_STEPS, AgentLoop, AgentState
from .completion import CompletionResolver, CompletionResult
from .context import CompactionReport, ContextManager
from .session import SessionStore

__all__ = [
    "AgentLoop",
    "AgentState",
    "CONTINUATION_STEPS",
    "CompletionResolver",
    "CompletionResult",
    "ContextManager",
    "CompactionReport",
    "SessionStore",
]
