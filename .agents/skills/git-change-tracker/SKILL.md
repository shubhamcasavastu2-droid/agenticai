---
name: git-change-tracker
description: Track and document code changes with git commit IDs. Use this skill to record what was changed, why, and link it to specific commits for audit trails and debugging.
license: MIT
compatibility: Requires git. Works with any git repository.
metadata:
  version: "1.0"
  skill-author: Kilo
---

# Git Change Tracker

## When to use

Use this skill when you need to:
- Record what changes were made in a commit
- Create a changelog entry from commit history
- Track the relationship between issues/tasks and commits
- Generate a summary of changes for a PR or release

## Workflow

1. **Get commit details** - Use `git show` or `git log` to extract commit info
2. **Categorize changes** - Classify as feature, fix, refactor, docs, test, chore
3. **Record in tracking file** - Append to CHANGELOG.md or similar
4. **Link to issues** - Reference issue numbers if available

## Commands

```bash
# Show last commit with full details
git show --stat HEAD

# Show last N commits with stats
git log --oneline --stat -5

# Show changes since a tag
git log v1.0..HEAD --oneline

# Get diff for a specific commit
git show <commit-hash>

# Show files changed in commit
git show --name-only <commit-hash>
```

## Example: Recording a change

```bash
# After making changes and committing
COMMIT_ID=$(git rev-parse HEAD)
echo "## [$COMMIT_ID] - $(date +%Y-%m-%d)" >> CHANGELOG.md
echo "- **Type**: Feature/Fix/Refactor" >> CHANGELOG.md
echo "- **Description**: What was changed" >> CHANGELOG.md
echo "- **Files**: $(git show --name-only --format= HEAD)" >> CHANGELOG.md
echo "" >> CHANGELOG.md
```

## Tracking template

| Commit ID | Date | Type | Description | Files Changed |
|-----------|------|------|-------------|---------------|
| `8d2cdbc` | 2026-11-03 | feat | Initial Agentic CLI with 6 tools, agent loop, permissions, CLI | 60 files |

## Integration with agent workflow

When the agent makes changes:
1. Run `git status` to see what's modified
2. Run `git diff` to review changes
3. Commit with descriptive message
4. Run `git log --oneline -1` to get commit ID
5. Record in tracking document