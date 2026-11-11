# Architecture Diagrams Documentation

This directory contains architectural diagrams for the AI Agent CLI codebase, generated in Mermaid format for easy viewing and editing.

## Diagram Files

| File | Description | Type |
|------|-------------|------|
| `class_diagram.mermaid` | Complete class diagram showing all classes, interfaces, enums, and relationships | Class Diagram |
| `package_layer_diagram.mermaid` | Package/layer architecture showing module organization and dependencies | Package/Layer Diagram |
| `responsibility_matrix.mermaid` | Responsibility assignment matrix with tabular view | Responsibility Matrix |
| `crc_cards.mermaid` | Class-Responsibility-Collaborator (CRC) cards for each major component | CRC Cards |
| `sequence_diagrams.mermaid` | Sequence diagrams for key flows (agent loop, tool execution, completion review, input normalization) | Sequence Diagrams |

## Viewing the Diagrams

### Option 1: VS Code / GitHub / GitLab
Mermaid diagrams render natively in:
- VS Code (with Markdown Preview)
- GitHub/GitLab markdown files
- Any Mermaid-compatible viewer

### Option 2: Mermaid Live Editor
1. Go to https://mermaid.live/
2. Copy the content of any `.mermaid` file
3. Paste into the editor for interactive viewing

### Option 3: CLI Tools
```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Generate SVG/PNG/PDF
mmdc -i class_diagram.mermaid -o class_diagram.svg
mmdc -i package_layer_diagram.mermaid -o package_layer_diagram.png
```

### Option 4: Python
```bash
pip install mermaid-py
# Or use playwright-based rendering
```

## Diagram Overview

### 1. Class Diagram (`class_diagram.mermaid`)
Shows the complete object-oriented structure:
- **Core Types**: Role, StopReason, Block hierarchy, Message, ToolSchema, ModelResponse, Tool interface
- **Agent Layer**: AgentState, AgentLoop with all methods
- **Provider Layer**: Provider interface, OpenAICompatibleProvider, stub providers
- **Tools Layer**: ToolRegistry, all 7 tool implementations
- **Permissions**: PermissionGate, validation, deny list, truncation
- **Skills & Agents**: Skill, SkillLoader, Agent, AgentLoader
- **Config, Completion, CLI, Logging**

Key relationships: inheritance, composition, dependency, interface implementation

### 2. Package/Layer Diagram (`package_layer_diagram.mermaid`)
Shows the layered architecture:
- **CLI Layer** → orchestrates everything
- **Core Agent Layer** → AgentLoop, CompletionResolver
- **Provider Layer** → Abstract Provider + implementations
- **Types Layer** → Core data structures (foundation)
- **Tools Layer** → ToolRegistry + 7 tool implementations
- **Permissions Layer** → Gate, validation, deny list, truncation
- **Configuration Layer** → Config
- **Skills & Agents Layer** → Discovery and loading
- **System Prompt Layer** → Prompt building
- **Logging Layer** → Structured logging

External dependencies shown with dashed lines.

### 3. Responsibility Matrix (`responsibility_matrix.mermaid`)
Two views:
- **Graph view**: Each component with numbered responsibilities (R1, R2...) and key collaborations
- **Tabular view**: Component | Primary Responsibilities | Key Collaborators

Useful for understanding ownership and for code reviews.

### 4. CRC Cards (`crc_cards.mermaid`)
Class-Responsibility-Collaborator cards for each major class:
- **Responsibilities**: What the class does
- **Collaborators**: What other classes it works with

Organized by layer with color coding.

### 5. Sequence Diagrams (`sequence_diagrams.mermaid`)
Four key flows:
1. **Main Agent Loop Flow** - Complete user interaction from startup to completion review
2. **Tool Execution Flow** - Detailed tool execution with permission checks, path validation
3. **Completion Review Flow** - How the reviewer verifies task completion
4. **Input Normalization Flow** - How user input is normalized before main agent

## Architecture Summary

### Layer Dependencies (Bottom-Up)
```
Types (foundation)
    ↑
Permissions, Config
    ↑
Provider, Tools, Skills/Agents, SystemPrompt, Logger
    ↑
Core Agent (AgentLoop, CompletionResolver)
    ↑
CLI (orchestration)
```

### Key Design Patterns
1. **Interface Segregation**: `Provider` abstract base, `Tool` interface
2. **Dependency Injection**: AgentLoop receives Provider, ToolRegistry, PermissionGate
3. **Callback Pattern**: AgentLoop uses callbacks for permission, reasoning, tool events
4. **Registry Pattern**: ToolRegistry manages tool lifecycle
5. **Factory Functions**: `create_*_tool()` functions for tool creation
6. **Dataclass-based DTOs**: All data structures use `@dataclass`
7. **Async/Await**: All I/O operations are asynchronous

### Security Boundaries
- **PathValidation**: All file operations validate paths stay within project root
- **DenyList**: Bash commands checked against dangerous patterns
- **PermissionGate**: Write tools require explicit user permission
- **Non-interactive Mode**: Safe defaults (deny by default)

## Updating Diagrams

When the codebase changes:
1. Update the relevant `.mermaid` file(s)
2. Commit changes with descriptive messages
3. Diagrams in `docs/architecture/` are version-controlled with code

## Exporting for Documentation

```bash
# Generate all as SVG for web documentation
for f in *.mermaid; do
    mmdc -i "$f" -o "${f%.mermaid}.svg" --backgroundColor white
done

# Or generate PDF for printing
mmdc -i class_diagram.mermaid -o class_diagram.pdf
```