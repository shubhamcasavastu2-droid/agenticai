---
name: code-reviewer
description: "Specialized in code review"
model: anthropic/claude-sonnet
system_prompt: |
  You are a helpful coding assistant specialized in code-reviewer.
tools:
  - read_file
  - write_file
  - edit_file
  - glob
  - grep
  - bash
permissions:
  read_file: auto
  write_file: prompt
  edit_file: prompt
  glob: auto
  grep: auto
  bash: prompt
metadata:
  version: "1.0"
  agent-author: User
---

# code-reviewer

"Specialized in code review"

## Configuration

This agent is configured with the standard toolset. Modify the frontmatter to customize tools, permissions, and model.
