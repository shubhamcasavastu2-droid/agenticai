# ADR 002: Tool Registry Pattern

## Status
Accepted

## Context
The agent needs to invoke various tools (file operations, shell commands, user interaction). We need a uniform way to:
1. Register tools at startup
2. Expose tool schemas to the LLM for function calling
3. Dispatch tool calls to implementations
4. Allow easy extension with new tools

## Decision
Implement a `ToolRegistry` class that:
- Maintains a dictionary of tool name -> Tool instance
- Provides `register()`, `get()`, `all()`, and `schemas()` methods
- Handles async tool execution via `execute(name, **kwargs)`
- Tools implement a base `Tool` class with `name`, `description`, `schema`, and async `execute()`

Each tool defines a `ToolSchema` with JSON Schema parameters for LLM function calling.

## Consequences
- **Positive**: Uniform interface for all tools; easy to add new tools; schema-driven LLM integration; testable with mock tools
- **Negative**: Slight indirection for tool calls; all tools must follow the same pattern
- **Mitigation**: Base class enforces consistency; registry is simple and fast

## Related
- ADR 001: Provider Abstraction Layer
- ADR 004: Permission Gates
