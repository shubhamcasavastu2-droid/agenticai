---
name: my-test-skill
description: Auto-generated skill
license: MIT
compatibility: Python 3.11+
metadata:
  version: "1.0"
  skill-author: Agent Designer
---

```markdown
---
name: my-test-skill
description: A planning skill that asks clarifying questions
license: MIT
compatibility:
  - agent-base-schema
metadata:
  author: test-contributor
  version: 1.0.0
  categories:
    - planning
    - clarification
---

# my-test-skill

## When to use

Use this skill when:
- The user provides a vague or incomplete request
- You need additional information to complete a task effectively
- Planning or strategy discussions require context gathering
- The conversation indicates the need for questions before proceeding

Trigger conditions:
- User requests that are too broad or lack specific details
- Context suggests clarification is needed before action
- Task planning requires understanding user constraints and preferences

## Workflow

1. **Analyze the user request** - Review the incoming message for clarity, specificity, and missing information
2. **Identify knowledge gaps** - Determine what additional information would help complete the task effectively
3. **Formulate clarifying questions** - Generate relevant, focused questions to gather necessary context
4. **Present questions to user** - Ask the questions in a clear, non-intrusive manner
5. **Wait for response** - Pause and await user clarification before proceeding
6. **Document gathered information** - Record the clarified details for future reference
7. **Proceed with task** - Once sufficient context is gathered, continue with the main workflow

## Tools required

- none (This skill operates purely through dialogue)

## Inputs/Outputs

### Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| user_request | string | The initial user request or context message that triggers this skill |

### Outputs
| Output | Type | Description |
|--------|------|-------------|
| clarifying_questions | list[string] | A collection of questions to ask the user for clarification |
| suggested_context | dict[object] | Additional context suggestions based on the request analysis |

## References

### Related skills
- information-extraction - For extracting structured data once clarification is complete
- task-planning - The next skill in the workflow after questions are answered

### Standard patterns
This skill follows the standard clarification pattern for agent workflows where:
1. Input analysis informs question generation
2. Questions are asked without overwhelming the user
3. Context gathering happens before tool invocation

## Scripts

None required for this skill.

## Assets

none
```The user wants me to create a complete SKILL.md file for a skill named "my-test-skill". Let me analyze the requirements:

1. Skill name: "my-test-skill"
2. Trigger: "A planning skill that asks clarifying questions"
3. Inputs: User request
4. Outputs: Generated skill file
5. Tools: all
6. Workflow: Generate skill from description
7. Constraints: Follow standard skill format

The output should include:
1. YAML frontmatter (name, description, license, compatibility, metadata)
2. Markdown content with sections for:
   - ## When to use (trigger conditions)
   - ## Workflow (step-by-step)
   - ## Tools required
   - ## Inputs/Outputs
   - Any references/scripts/assets sections if needed

I need to output ONLY the skill file content, nothing else. Let me create a well-structured skill file.