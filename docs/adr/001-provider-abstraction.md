# ADR 001: Provider Abstraction Layer

## Status
Accepted

## Context
The Agentic CLI needs to work with multiple LLM providers (OpenAI, Ollama, NVIDIA NIM, Anthropic, OpenRouter) that all expose OpenAI-compatible APIs. We need a clean abstraction to:
1. Allow swapping providers without changing agent logic
2. Handle provider-specific quirks (streaming formats, parameter names)
3. Centralize retry logic, error handling, and token usage tracking

## Decision
Create an abstract `Provider` base class with an `OpenAICompatibleProvider` implementation. The provider interface exposes a single `complete()` method that takes system prompt, messages, and tool schemas, returning a `ModelResponse`.

Key design choices:
- Use `httpx.AsyncClient` for HTTP operations
- Support streaming with SSE parsing
- Implement retry logic with exponential backoff and `Retry-After` header support
- Classify errors into specific exception types (timeout, auth, HTTP)
- Track token usage for context window management

## Consequences
- **Positive**: Clean separation between agent logic and provider details; easy to add new providers; centralized error handling
- **Negative**: Additional abstraction layer; OpenAI-compatible assumption may not fit all future providers
- **Mitigation**: Keep interface minimal; can add provider-specific subclasses if needed

## Related
- ADR 002: Tool Registry Pattern
- ADR 003: Context Window Management
