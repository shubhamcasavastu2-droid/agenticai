# Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for the Agentic CLI project.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [001](001-provider-abstraction.md) | Provider Abstraction Layer | Accepted |
| [002](002-tool-registry.md) | Tool Registry Pattern | Accepted |
| [003](003-context-window.md) | Context Window Management | Accepted |
| [004](004-permission-gates.md) | Permission Gates and Shell Safety | Accepted |
| [005](005-completion-review.md) | Completion Review System | Accepted |

## Format

Each ADR follows the format:
- **Status**: Proposed, Accepted, Superseded, Deprecated
- **Context**: The problem being addressed
- **Decision**: The chosen solution
- **Consequences**: Trade-offs and implications
- **Related**: Links to other ADRs

## Creating New ADRs

1. Create a new file with the next number (e.g., `006-new-decision.md`)
2. Use the template above
3. Update this index
4. Link from related ADRs