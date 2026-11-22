"""Keeps the agent's message history inside the model's context window.

Token counts are estimated (≈4 chars/token) and calibrated against the provider's reported
`input_tokens` whenever usage is available. When the estimate exceeds the budget, compaction
runs in two stages:

1. Elide the bodies of older tool results (they are usually the bulk of the context).
2. Drop the oldest turns after the first user message, replacing them with a short note.
   Turns are dropped on safe boundaries so a tool result never loses its tool call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from ..logger import log_info, log_warning
from ..types import Message, ReasoningBlock, Role, TextBlock, ToolCall, ToolResult, ToolSchema

CHARS_PER_TOKEN = 4.0
MESSAGE_OVERHEAD_TOKENS = 4
ELIDED_HEAD_CHARS = 300
ELIDE_THRESHOLD_CHARS = 600
DROPPED_NOTE_PREFIX = "[Context note]"


@dataclass
class CompactionReport:
    before_tokens: int
    after_tokens: int
    elided_results: int = 0
    dropped_messages: int = 0

    @property
    def changed(self) -> bool:
        return self.elided_results > 0 or self.dropped_messages > 0


def _block_chars(block: object) -> int:
    if isinstance(block, TextBlock | ReasoningBlock):
        return len(block.text)
    if isinstance(block, ToolCall):
        return len(block.name) + len(json.dumps(block.arguments, ensure_ascii=False))
    if isinstance(block, ToolResult):
        return len(block.output)
    return 0


class ContextManager:
    def __init__(
        self,
        context_window_tokens: int,
        max_completion_tokens: int,
        keep_recent_messages: int = 8,
        safety_ratio: float = 0.9,
    ):
        self.context_window_tokens = context_window_tokens
        # Reserve room for the response, but never more than half the window: some configs set
        # max_completion_tokens larger than the context window itself.
        reserve = min(max_completion_tokens, context_window_tokens // 2)
        self.budget_tokens = max(1, int((context_window_tokens - reserve) * safety_ratio))
        self.keep_recent_messages = keep_recent_messages
        self._calibration = 1.0
        self._last_estimate: int | None = None

    # ------------------------------------------------------------------ estimation

    def estimate(self, system: str, messages: list[Message], tools: list[ToolSchema]) -> int:
        chars = len(system)
        chars += sum(len(t.name) + len(t.description) + len(json.dumps(t.parameters)) for t in tools)
        tokens = chars / CHARS_PER_TOKEN
        for message in messages:
            tokens += MESSAGE_OVERHEAD_TOKENS + sum(_block_chars(b) for b in message.content) / CHARS_PER_TOKEN
        return int(tokens * self._calibration)

    def record_estimate(self, estimate: int) -> None:
        self._last_estimate = estimate

    def calibrate(self, reported_input_tokens: int | None) -> None:
        """Adjust the chars→tokens ratio using the provider's real prompt-token count."""
        if not reported_input_tokens or not self._last_estimate:
            return
        raw_estimate = self._last_estimate / self._calibration
        if raw_estimate <= 0:
            return
        ratio = reported_input_tokens / raw_estimate
        # Smooth and clamp so one odd response can't swing compaction wildly.
        self._calibration = min(4.0, max(0.25, 0.5 * self._calibration + 0.5 * ratio))

    # ------------------------------------------------------------------ compaction

    def compact(self, system: str, messages: list[Message], tools: list[ToolSchema]) -> CompactionReport:
        """Compact `messages` in place if the estimate is over budget."""
        before = self.estimate(system, messages, tools)
        report = CompactionReport(before_tokens=before, after_tokens=before)
        if before <= self.budget_tokens:
            return report

        report.elided_results = self._elide_old_tool_results(messages)
        current = self.estimate(system, messages, tools)

        while current > self.budget_tokens:
            dropped = self._drop_oldest_turn(messages)
            if dropped == 0:
                break
            report.dropped_messages += dropped
            current = self.estimate(system, messages, tools)

        report.after_tokens = current
        if report.changed:
            log_info(
                "CONTEXT_COMPACTED: "
                f"before_tokens≈{before} after_tokens≈{current} budget_tokens={self.budget_tokens} "
                f"elided_tool_results={report.elided_results} dropped_messages={report.dropped_messages}"
            )
        if current > self.budget_tokens:
            log_warning(
                f"CONTEXT_STILL_OVER_BUDGET: tokens≈{current} budget_tokens={self.budget_tokens}; "
                "the remaining recent messages are too large to compact further"
            )
        return report

    def _elide_old_tool_results(self, messages: list[Message]) -> int:
        cutoff = max(0, len(messages) - self.keep_recent_messages)
        elided = 0
        for message in messages[:cutoff]:
            if message.role != Role.TOOL:
                continue
            for index, block in enumerate(message.content):
                if isinstance(block, ToolResult) and len(block.output) > ELIDE_THRESHOLD_CHARS:
                    removed = len(block.output) - ELIDED_HEAD_CHARS
                    message.content[index] = ToolResult(
                        call_id=block.call_id,
                        output=(
                            block.output[:ELIDED_HEAD_CHARS]
                            + f"\n[... {removed} chars elided to save context; re-run the tool if needed ...]"
                        ),
                        is_error=block.is_error,
                    )
                    elided += 1
        return elided

    def _drop_oldest_turn(self, messages: list[Message]) -> int:
        """Drop the oldest turn after the first user message (an assistant message together with
        its tool results, or a single user message). Never drops the newest message.
        Returns the number of messages removed."""
        start = 2 if len(messages) > 1 and self._is_note(messages[1]) else 1
        if start >= len(messages) - 1:
            return 0
        end = start + 1
        while end < len(messages) and messages[end].role == Role.TOOL:
            end += 1
        if end >= len(messages):
            return 0
        removed = end - start
        del messages[start:end]
        self._upsert_note(messages, removed)
        return removed

    @staticmethod
    def _is_note(message: Message) -> bool:
        return (
            message.role == Role.USER
            and bool(message.content)
            and isinstance(message.content[0], TextBlock)
            and message.content[0].text.startswith(DROPPED_NOTE_PREFIX)
        )

    def _upsert_note(self, messages: list[Message], removed: int) -> None:
        total = removed
        if len(messages) > 1 and self._is_note(messages[1]):
            previous = messages[1].content[0]
            assert isinstance(previous, TextBlock)
            try:
                total += int(previous.text.split("(", 1)[1].split(" ", 1)[0])
            except (IndexError, ValueError):
                pass
            del messages[1]
        note = Message.user(
            f"{DROPPED_NOTE_PREFIX} Earlier conversation ({total} messages) was removed to fit the "
            "context window. Re-read files or re-run commands if you need details from it."
        )
        messages.insert(1, note)
