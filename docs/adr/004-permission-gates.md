# ADR 004: Permission Gates and Shell Safety

## Status
Accepted

## Context
The agent can execute arbitrary shell commands and modify files. We need a security model that:
1. Prevents path traversal outside the project root
2. Blocks dangerous shell commands (sudo, rm -rf, curl | sh, etc.)
3. Requires user approval for write operations
4. Works in both interactive and non-interactive (CI) environments

## Decision
Implement a layered security approach:

1. **Path Validation** (`validate_path()`): Resolves symlinks with `os.path.realpath()`, uses `os.path.commonpath()` to verify target is within project root. Runs on every file operation.

2. **Shell Safety** (`find_denied_reason()`): Tokenizes commands with `shlex`, splits on shell operators, recursively unwraps wrappers (`bash -c`, `eval`, `env`, `nohup`), applies deny rules to each simple command. Rules cover:
   - Privilege escalation (sudo, su, doas)
   - System power commands (shutdown, reboot)
   - Disk operations (fdisk, wipefs)
   - Recursive destructive ops outside project (rm -rf, chmod -R, chown -R)
   - Download-and-execute (curl | sh, wget | python)
   - Git force push
   - Fork bombs, raw device writes

3. **Permission Gate**: Classifies tools as read-only (auto-allow) or write (ask). Interactive prompt: `y` (once), `a`/`u` (session), `n` (deny), `d` (deny session). Non-interactive: auto-deny write tools.

4. **Defense in Depth**: Safety rules checked BEFORE allow-lists in both bash tool and permission gate.

## Consequences
- **Positive**: Strong default security; works in CI; defense in depth; user control
- **Negative**: Some legitimate commands blocked; symlink TOCTOU race condition (low risk)
- **Mitigation**: Users can allow commands per session; TOCTOU is low risk for local CLI tool

## Related
- ADR 002: Tool Registry Pattern (tools integrate with permission gate)
