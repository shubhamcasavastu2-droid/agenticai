---
name: impact-analyzer
description: Monitors changes in src/ and test/ folders, analyzes impact, creates story documentation, maintains process log, and manages agent registry
license: MIT
metadata:
  version: "1.0"
  skill-author: Agent Designer
  trigger: "file-change"
  tools: ["read_file", "write_file", "edit_file", "glob", "grep", "bash", "ask_user", "plan", "todo"]
---

# Impact Analyzer Skill

## When to Use

This skill is triggered automatically when changes are detected in the `src/` or `test/` folders. It analyzes the impact of changes, creates story documentation, maintains a process log, and updates the agent registry.

**Trigger Conditions:**
- Any file creation, modification, or deletion in `src/` folder
- Any file creation, modification, or deletion in `test/` folder
- Can also be invoked manually via `/skills impact-analyzer run`

## Workflow

### Step 1: Detect Changes
- Monitor `src/` and `test/` directories for changes
- Use file system watching or git diff to identify modified files
- Categorize changes by type (new file, modification, deletion)

### Step 2: Analyze Impact
- For each changed file, determine:
  - What functionality it affects
  - Which other files might be impacted (imports, dependencies)
  - Test coverage implications
  - Breaking change potential
- Generate impact summary with risk level (low/medium/high)

### Step 3: Create Story Documentation
- Generate a unique story number (incremental: STORY-001, STORY-002, etc.)
- Create folder: `docs/stories/STORY-XXX/`
- Create `analysis.md` with:
  - Changed files list
  - Impact analysis
  - Risk assessment
  - Affected components
  - Recommended testing

### Step 4: Request User Approval
- Present impact analysis to user
- Ask for approval to proceed with the change
- If denied, log rejection and stop
- If approved, continue to next step

### Step 5: Update Process Log
- Append entry to `docs/process.md` with:
  - Timestamp
  - Story number
  - Changed files
  - Impact summary
  - Approval status
  - Outcome

### Step 6: Update Agent Registry
- Update `.agents/agents.md` with:
  - Current project state
  - Active stories
  - Recent changes
  - Agent capabilities summary

## Tools Required

- `read_file` - Read changed files and existing documentation
- `write_file` - Create story analysis, process log, agent registry
- `edit_file` - Update existing process.md and agents.md
- `glob` - Find files in src/ and test/
- `grep` - Search for imports and dependencies
- `bash` - Run git diff, file watching commands
- `ask_user` - Request approval for changes
- `plan` - Present impact analysis plan
- `todo` - Track analysis steps

## Inputs

- Changed file paths (from file watcher or git)
- Project root directory
- Current story counter (from process.md or new)

## Outputs

- `docs/stories/STORY-XXX/analysis.md` - Impact analysis document
- `docs/process.md` - Updated process log
- `.agents/agents.md` - Updated agent registry

## Constraints

- Must run in interactive mode for approval prompts
- Story numbers must be sequential and unique
- Process.md must maintain chronological order
- Agents.md must reflect current project state
- Non-interactive mode: auto-approve low-risk changes, log high-risk for later review

## Example Use Cases

1. **Developer modifies `src/agent.py`** → Skill detects change, analyzes impact on agent loop, creates STORY-001, requests approval, updates logs
2. **New test added in `tests/test_new_feature.py`** → Skill detects, analyzes coverage impact, creates STORY-002, auto-approves (low risk), updates logs
3. **File deleted from `src/tools/`** → Skill detects, analyzes breaking change risk (high), creates STORY-003, requires explicit approval