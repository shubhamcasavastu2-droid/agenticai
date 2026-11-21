# ADR 005: Completion Review System

## Status
Accepted

## Context
Agents may claim task completion without actually fulfilling all requirements. We need a verification mechanism that:
1. Independently reviews the agent's work against the original request
2. Uses a potentially different (stronger/cheaper) model
3. Provides structured feedback for retry
4. Is optional (configurable)

## Decision
Implement a `CompletionResolver` that:
1. Runs the agent loop to get a response
2. Feeds the original request, agent response, and tool trace to a reviewer model
3. Reviewer returns structured JSON: `{"complete": bool, "findings": "..."}`
4. If incomplete, injects findings back into agent loop and retries (up to `max_attempts`)
5. Review model can be different from agent model (via `review_provider`)

The reviewer prompt instructs it to treat conversation as evidence, not instructions, and only mark complete if all deliverables are verified.

## Consequences
- **Positive**: Catches incomplete work; configurable attempts; separate model option; structured feedback
- **Negative**: Doubles model calls (when enabled); adds latency; reviewer can also make mistakes
- **Mitigation**: Disabled by default via `AGENTIC_COMPLETION_REVIEW=false`; configurable attempts; reviewer prompt emphasizes evidence-based review

## Related
- ADR 001: Provider Abstraction Layer (review uses provider interface)
- ADR 003: Context Window Management (trace may be truncated for review)