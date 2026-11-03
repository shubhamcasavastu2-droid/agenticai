---
name: example-agent
description: Example agent configuration
model: anthropic/claude-sonnet
system_prompt: |
  You are a helpful coding assistant specialized in {{specialty}}.
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
---

# Example Agent

This is an example agent configuration file. Agents follow the same format as skills (markdown with YAML frontmatter).