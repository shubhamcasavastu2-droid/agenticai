# Impact Analysis

> ID: IA-004 | Status: DRAFT | Risk: HIGH  
> Scope: Backend architectural redesign - multi-command processor system

## 1. Change Summary

| Field | Details |
|---|---|
| Requested Change | Complete architectural redesign of Agentic CLI backend: introduce slash-command processors (/ask, /plan, /agents-default, /session, /schedule, /agent, /skills, /hook, /orchestrator, /job), new directory structure (tools/, processor/, provider/, config/, models/, prompt/), session-based process channels, and a main entry file that loads config and starts app.py |
| Objective | Create a modular, extensible architecture where each slash command has a dedicated processor with its own system prompt, tool restrictions, and session management. All process channels share sessions. |
| Change Type | Feature / Refactor |
| Scope | Backend only |
| Breaking Change | Yes - CLI command routing changes, directory structure changes, Config model changes |

## 2. Impact Matrix

| Component | File / Module | Impact | Change Required |
|---|---|---|---|
| Entry point | `backend/src/main.py` | HIGH | Rewrite to load config and start Application |
| CLI | `backend/src/cli.py` | HIGH | Route slash commands to processors, handle permissions |
| Application | `backend/src/app.py` | HIGH | Refactor to support per-command processors and shared sessions |
| Config | `backend/src/config/config.py` | MEDIUM | Add root_dir/workspace_dir as dataclass fields, add new prompt configs |
| Models | `backend/src/models/` | HIGH | New directory - create data models (ConfigModel, SessionModel, TaskModel, etc.) |
| Tools | `backend/src/tools/` | HIGH | Reorganize into tools/ subdirectory structure |
| Processor | `backend/src/processor/` | HIGH | New directory - create slash command processors |
| Provider | `backend/src/provider/` | HIGH | New directory - provider abstraction |
| Prompt | `backend/src/prompt/` | HIGH | Reorganize into system prompts for each command |
| Security | `backend/src/security/` | MEDIUM | Permission gate for per-command tool restrictions |
| Core | `backend/src/core/` | MEDIUM | Session, agent loop, completion resolver changes |

## 3. Dependency Impact

| Source | Dependency | Relationship | Impact |
|---|---|---|---|
| CLI | Config | Direct | HIGH - CLI reads config for prompts, paths |
| CLI | Processor | Direct | HIGH - CLI routes commands to processors |
| Processor | Provider | Direct | HIGH - Each processor calls provider for LLM |
| Processor | Tools | Direct | HIGH - Each processor has restricted tool set |
| Processor | Session | Direct | HIGH - All processors share session state |
| Config | Project (singleton) | Direct | HIGH - Config reads root_dir/workspace_dir from Project |
| Tool | Security/Permission | Direct | HIGH - Tools check permissions via PermissionGate |
| App | All | Direct | HIGH - Application wires everything together |

## 4. Behaviour Changes

| Existing Behaviour | New Behaviour | Affected Area |
|---|---|---|
| Single monolithic agent loop handles all input | Per-command processors handle specific slash commands | cli.py, processor/ |
| One system prompt for all interactions | Distinct system prompt per command (/ask, /plan, /agents-default, etc.) | prompt/ |
| Tools registered globally | Tools registered per-command with restrictions | tools/, processor/ |
| Sessions stored in JSONL | Sessions shared across all process channels | core/session.py |
| Config loaded from env vars only | Config loaded from env + CLI args (--root-dir, --workspace) | config/ |

## 5. Data & Contract Impact

- Database: None
- API: None
- Events: Session events shared across processors
- Configuration: New `root_dir`, `workspace_dir` fields in Config dataclass; new prompt templates per command
- Backward Compatibility: Breaking - command routing changes, directory restructure

## 6. Risk Analysis

| Risk | Severity | Mitigation |
|---|---|---|
| Breaking existing tests | HIGH | Update tests to match new architecture, keep backward-compatible imports where possible |
| Session state inconsistency across processors | HIGH | Use shared SessionStore with file-based persistence |
| Tool permission bypass in /ask (read-only restriction) | HIGH | Enforce tool allowlist at processor level before permission gate |
| Config migration from old format | MEDIUM | Keep backward-compatible env var loading |

## 7. Test Impact

| Test Type | Required | Coverage |
|---|---|---|
| Unit | Yes | Each processor, config loading, model validation |
| Integration | Yes | CLI command routing, processor-to-provider flow |
| Regression | Yes | All existing tests must pass with new architecture |
| E2E | Yes | Full slash command flow: /ask, /plan, /agents-default, /session, /agent, /skills |

## 8. Implementation Sequence

| Step | Action | Dependency |
|---|---|---|
| 1 | Create impact-analysis.md and story directory | None |
| 2 | Create models/ - data models (ConfigModel, SessionModel, TaskModel, MessageModel) | None |
| 3 | Create config/ - configuration loading from env + CLI args | Step 2 |
| 4 | Create provider/ - provider abstraction layer | Step 3 |
| 5 | Create prompt/ - all system prompts (ask, plan, agents-default, session, agent, skills) | Step 3 |
| 6 | Create tools/ - tool registry and tool implementations | Step 3 |
| 7 | Create processor/ - slash command processors | Steps 3, 4, 5, 6 |
| 8 | Update main.py - main entry file that loads config and starts app.py | Steps 3, 4, 5, 6, 7 |
| 9 | Update CLI.py - route slash commands to processors, handle permissions | Steps 7, 8 |
| 10 | Update app.py - Application wires processors, providers, sessions | Steps 3-9 |
| 11 | Run lint and tests | Steps 1-10 |

## 9. Unresolved Items

| ID | Question / Missing Information | Blocking |
|---|---|---|
| GAP-01 | Should /schedule, /hook, /orchestrator, /job be TODO-only or have basic stubs? | No - user specified TODO only |
| GAP-02 | Exact directory naming: `config/` vs `src/config/` | No - will nest under `src/` |
| GAP-03 | Session serialization format for cross-processor sharing | No - use existing JSONL format |

## 10. Impact Decision

| Check | Result |
|---|---|
| Scope Identified | PASS |
| Dependencies Identified | PASS |
| Breaking Changes Reviewed | PASS |
| Risks Assessed | PASS |
| Tests Identified | PASS |

**Decision:** APPROVED  
**Approval Required:** YES (architectural change)

---

## Related Stories

- IA-001: Package reorganization (core/, security/, capabilities/, prompt/)
- IA-002: Requirement Normalizer and Gap Detector fix
- IA-003: Make system prompts config-driven, add todo completion tracking
- IA-003b: Fix recursive gaps, duplicate questions, scope expansion
- IA-003c: Todo list completion tracking and merge
- IA-003d: Make all system prompts config-driven
- IA-003e: Fix code errors in normalizer gap detection
- IA-003f: Integrate gap clarification into normalize_input
- IA-003g: Make write_user permission system work with click framework
- IA-003h: Config-driven system prompts with env vars
- IA-003i: Match existing skills/agents from agents.md during normalization
- IA-003j: Move agents.md reading into AgentLoader
- IA-003k: Fix CLI prompt to accept numbered selection/free text
- IA-003l: All system prompts config-driven

---

**Story Reference:** docs/stories/STORY-004/  
**Approval:** Required from user before implementation begins.
