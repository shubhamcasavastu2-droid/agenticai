---
name: my-test-skill
description: A planning skill that asks clarifying questions to generate a complete skill from user descriptions.
license: MIT
compatibility: all
metadata:
  category: planning
  tags: [planning, clarification, generative]
  author: System
  version: 1.0.0
---

## When to use

Use this skill when you need to generate a complete SKILL.md file from user descriptions or requirements. This skill is triggered by planning workflows where clarifying questions are needed to gather necessary information before generating the final output.

**Trigger conditions:**
- User provides a description of what skill they want created
- Planning phase requires clarifying questions about skill parameters
- Need standardized skill format with YAML frontmatter and markdown sections
- Skill development or documentation generation task

## Workflow

1. **Receive user request**: Analyze the user's input describing the skill they want to create.

2. **Generate clarifying questions**: Ask questions needed to fully define the skill:
   - What functions/tools will this skill use?
   - Are there specific constraints or requirements?
   - What output format is expected?
   - Any particular license or compatibility requirements?

3. **Collect information**: Gather responses to clarifying questions and compile all necessary metadata.

4. **Draft content sections**: Create each section of the SKILL.md file:
   - YAML frontmatter with metadata
   - When to use documentation
   - Step-by-step workflow
   - Tools required list
   - Inputs and outputs specification

5. **Review and validate**: Check against standard skill format requirements:
   - Verify all required fields are present
   - Ensure consistent formatting
   - Validate YAML syntax is correct

6. **Generate final output**: Create the complete SKILL.md file ready for use.

## Tools required

### All Available Tools
This skill may utilize any of the following tools depending on requirements:
- `read_file`: For accessing existing files or documentation
- `write_file`: For creating and saving the generated SKILL.md file
- `glob`: For finding related files or patterns
- `grep`: For searching content within files

### Standard Skill Format Tools
- File system operations (read/write)
- Pattern matching (glob)
- Text search capabilities (grep)
- Shell command execution (bash)

## Inputs/Outputs

| Type | Description | Example |
|------|-------------|---------|
| Input | user request | "Create a skill for code analysis" |
| Output | Generated SKILL.md file | Complete markdown file with YAML frontmatter |

### Detailed Input Schema
```yaml
- name: request
  type: string
  description: User's description of the skill to generate
  required: true
```

### Detailed Output Schema
```yaml
- name: skill_file
  type: file
  description: Complete SKILL.md file ready for deployment
  format: markdown
  includes:
    - YAML frontmatter
    - When to use section
    - Workflow section
    - Tools required section
    - Inputs/Outputs section
    - References/scripts/assets (if applicable)
```

## References

- Standard skill documentation guidelines
- File system conventions for SKILL.md files
- YAML frontmatter specification
- Markdown formatting standards

## Scripts

N/A - This skill generates content rather than executing scripts.

## Assets

None currently required, but may include:
- Template SKILL.md files
- Style guides for skill creation
- Example completed skills for reference
