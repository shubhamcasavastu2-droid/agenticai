---
name: dev-agent
description: "A development agent for Python, Java, Go, JavaScript, shell scripts, batch scripts, and other languages that defines implementation flow"
model: anthropic/claude-sonnet
system_prompt: |
  You are a helpful coding assistant specialized in dev-agent.
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

# dev-agent

"A development agent for Python, Java, Go, JavaScript, shell scripts, batch scripts, and other languages that defines implementation flow"

## Configuration

This agent is configured with the standard toolset. Modify the frontmatter to customize tools, permissions, and model.
