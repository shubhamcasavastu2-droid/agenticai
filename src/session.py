"""Session transcripts: one JSONL file per CLI session, one message per line."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .types import Block, Message, ReasoningBlock, Role, TextBlock, ToolCall, ToolResult

_BLOCK_TYPES: dict[str, type] = {
    "text": TextBlock,
    "tool_call": ToolCall,
    "tool_result": ToolResult,
    "reasoning": ReasoningBlock,
}


def message_to_dict(message: Message) -> dict[str, Any]:
    return {"role": str(message.role), "content": [asdict(block) for block in message.content]}


def message_from_dict(data: dict[str, Any]) -> Message:
    blocks: list[Block] = []
    for raw in data.get("content", []):
        block_type = _BLOCK_TYPES.get(raw.get("type", ""))
        if block_type is None:
            continue
        blocks.append(block_type(**raw))
    return Message(role=Role(data["role"]), content=blocks)


class SessionStore:
    def __init__(self, directory: Path):
        self.directory = directory
        self.session_id = self._new_id()

    @staticmethod
    def _new_id() -> str:
        return datetime.now().strftime("%Y%m%d-%H%M%S-%f")

    def new_session(self) -> None:
        self.session_id = self._new_id()

    @property
    def path(self) -> Path:
        return self.directory / f"{self.session_id}.jsonl"

    def save(self, messages: list[Message]) -> Path:
        """Rewrite the current session file with the full message history."""
        self.directory.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".jsonl.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            for message in messages:
                handle.write(json.dumps(message_to_dict(message), ensure_ascii=False) + "\n")
        tmp.replace(self.path)
        return self.path

    def list_sessions(self) -> list[tuple[str, int, datetime]]:
        """(session_id, message_count, modified_time), newest first."""
        if not self.directory.exists():
            return []
        sessions = []
        for file in self.directory.glob("*.jsonl"):
            with file.open(encoding="utf-8") as handle:
                count = sum(1 for line in handle if line.strip())
            sessions.append((file.stem, count, datetime.fromtimestamp(file.stat().st_mtime)))
        return sorted(sessions, key=lambda item: item[2], reverse=True)

    def load(self, session_id: str | None = None) -> list[Message]:
        """Load a session (latest other than the current one when `session_id` is None) and
        continue writing to it."""
        if session_id is None:
            candidates = [sid for sid, _, _ in self.list_sessions() if sid != self.session_id]
            if not candidates:
                raise FileNotFoundError("No previous sessions found")
            session_id = candidates[0]
        file = self.directory / f"{session_id}.jsonl"
        if not file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        messages = []
        with file.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    messages.append(message_from_dict(json.loads(line)))
        self.session_id = session_id
        return messages
