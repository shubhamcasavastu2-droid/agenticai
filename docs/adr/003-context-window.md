# ADR 003: Context Window Management

## Status
Accepted

## Context
LLMs have finite context windows. Long conversations with tool outputs (especially file reads, grep results) can exceed the window. We need a strategy to keep the conversation within bounds while preserving critical information.

## Decision
Implement a `ContextManager` with two-stage compaction:

1. **Elision**: Replace bodies of older tool results with a truncated summary (first 300 chars + "[...elided...]"). Preserves tool call/result linkage so the model knows a tool was called.

2. **Turn Dropping**: Drop oldest turns (user/assistant pairs) after the first user message, replacing with a note: "[Context note: N messages dropped]". Drops on safe boundaries so tool results never lose their calls.

Token estimation uses ~4 chars/token heuristic, calibrated against provider-reported `input_tokens` when available. Budget reserves space for response tokens.

## Consequences
- **Positive**: Prevents context overflow; preserves recent context and first user message; calibration improves accuracy over time
- **Negative**: Loss of older tool output details; estimation may be inaccurate for some tokenizers
- **Mitigation**: Configurable context window; calibration from provider usage; elision preserves call structure

## Related
- ADR 001: Provider Abstraction Layer (provides token usage for calibration)
