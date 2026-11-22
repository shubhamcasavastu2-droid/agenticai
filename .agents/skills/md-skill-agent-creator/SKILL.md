---
name: md-skill-agent-creator
description: "Use this skill ALWAYS when the user wants to create or update a skill or agent. It works inside the MAIN context window: based on the user's justified input it builds a system prompt for the new skill/agent, loads that skill into the main system prompt so the agent can use it immediately, and extends the main context window. It does NOT run as a standalone create-skill-file function — creation happens through the main agent loop and the result is fed back into the main context window."
compatibility: ["ask_tool"]
---

# md-skill-agent-creator

This skill creates or updates skills and agents directly inside the MAIN context window. When the user justifies what they want (object, purpose, tools, workflow), the skill builds a system prompt for the new skill/agent, then loads it into the main system prompt so the agent can use it right away — extending the main context window. One skill created = one skill loaded back into the main context window.

## When to trigger

ALWAYS trigger this skill when:
- The user wants to create a new skill or agent (via /skill, /agent, or natural language).
- The user wants to update an existing skill or agent.
- The user describes an objective that implies defining a reusable skill or agent behavior.

Do NOT create a skill/agent as a separate standalone file-write function. Always go through the main context window: justify input → build system prompt → load into main context → agent can use it.

## Workflow (inside main context window)

### Step 1: Capture the user's justified input
Ask the user to justify what they want:
- What object/name should the skill or agent have?
- What is its purpose? When should it trigger?
- What inputs does it need?
- What should it produce (outputs)?
- What tools does it need? (read_file, write_file, edit_file, glob, grep, bash — or 'all')
- What is the step-by-step workflow? (3-5 steps)
- Any constraints or example use cases?

### Step 2: Build a system prompt from the justified input
Convert the user's justified input into a system prompt for the new skill/agent:
- The system prompt defines when the skill triggers, what it does, and how it behaves.
- Include trigger conditions, workflow, tools required, inputs/outputs, and constraints.
- Keep it concise and pushy (describe when to use it clearly).

### Step 3: Load into the main context window
- Check whether the skill/agent already exists.
  - If it exists: update its system prompt/content with the new justified input.
  - If it does not exist: create it using the standard format.
- Immediately reload the skill/agent loader so the new/updated skill is available.
- Rebuild the main system prompt to include the new skill — this extends the main context window.
- The agent in the main context window can now use the skill right away.

### Step 4: Confirm back to the main context window
- Report to the user what was created/updated and that it is now loaded in the main context window.
- The skill is now part of the main system prompt and available to the agent.

## Standard formats

### Skill format (`backend/.agents/skills/<name>/SKILL.md`)
```markdown
---
name: <skill-name>
description: <pushy description of when to trigger and what it does>
compatibility: [<list of required tools>]
---

# <skill-name>

## When to use
<trigger conditions>

## Workflow
<step-by-step>

## Tools required
<tools>

## Inputs / Outputs
<inputs> → <outputs>

## Constraints
<constraints>
```

### Agent format (`backend/.agents/agents/<name>.md`)
```markdown
---
name: <agent-name>
description: <agent description>
model: <model name>
system_prompt: <system prompt>
tools: [<list of tools>]
permissions: <permissions object>
metadata: <metadata object>
---

<agent content>
```

## How it extends the main context window

Skills and agents are loaded into the system prompt at session start via `build_system_prompt()`. When this skill creates or updates a skill/agent during a session, it:

1. Writes the skill/agent file to disk.
2. Re-runs `skill_loader.discover()` / `agent_loader.discover()` to pick up the change.
3. Rebuilds the main system prompt with `build_system_prompt(..., skills_info=..., agents_info=...)`, which includes the new skill's description in the agent's system prompt.
4. The main agent loop now sees the new skill in its context window and can invoke it.

This means: one skill created → immediately loaded into the main context window → the agent can use it without restarting.

## Examples

**Example 1: Create a new skill in the main context window**
- User: "Create a skill for reviewing code quality."
- Skill asks: "What should the skill be called? When should it trigger? What tools does it need? What's the workflow?"
- User justifies: "name: code-reviewer, triggers when user asks to review code, tools: read_file+grep, workflow: read file → grep issues → report."
- Skill builds a system prompt for code-reviewer, creates `backend/.agents/skills/code-reviewer/SKILL.md`, reloads into the main context window.
- The agent can now invoke the code-reviewer skill in the main conversation.

**Example 2: Update an existing skill**
- User: "Update the diagram skill to support mermaid charts."
- Skill finds `backend/.agents/skills/diagram/SKILL.md` exists.
- Asks for the new justification: "add mermaid chart generation to workflow."
- Updates the skill file, reloads into main context window.
- The updated skill is now available in the main agent context.

## Principles

- Work inside the main context window — never a standalone create-file function.
- Justify user input → build system prompt → load into main context.
- One skill created = one skill loaded back into the main context window.
- Check existence before creating — update if exists, create if not.
- Reload skill/agent loaders and rebuild the main system prompt after every change.
- Preserve existing content when updating.
