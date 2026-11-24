# Story STORY-004: Architectural Redesign - Multi-Command Processor System

## Objective
Redesign the Agentic CLI backend into a modular architecture with dedicated slash-command processors, new directory structure (tools/, processor/, provider/, config/, models/, prompt/), and shared session-based process channels.

## Requirements

### Core Architecture
- [ ] Main entry file loads config and starts app.py
- [ ] CLI responsible for all CLI inputs and permissions
- [ ] User input associated with user input context
- [ ] Input starting with `/` routes to separate processor
- [ ] All process channels share session
- [ ] Session can be created/switched via /session command

### Slash Commands

#### /ask
- [ ] Load input to ask processor
- [ ] Add ask system prompt
- [ ] Add normalized user input based on ask standard
- [ ] Only pass read tools: read_file, bash (read-only)
- [ ] Ensure full understanding of user input before processing
- [ ] Only process after user input is objectified
- [ ] Send agent response and stay in terminal

#### /plan
- [ ] Same format system prompt for planning only
- [ ] Use ask or read_file tool, bash only for read purpose
- [ ] Once plan ready, create .md file in docs/plans/* folder
- [ ] Only proceed to code once output full plan is ready

#### /agents-default
- [ ] Default system prompt
- [ ] First normalize user input
- [ ] Split into tasks
- [ ] Create todo list
- [ ] Process todo list items one by one
- [ ] Update todo list after each completion
- [ ] Publish task: read skills, agent ready, workspace read files, then process task by task

#### /session
- [ ] Use ask to check from user
- [ ] Split session or create new one if new
- [ ] Save session
+ Create new one if user wants to switch
- [ ] Option to switch sessions
- [ ] User can pass prompt, identify which session, create one or switch

#### /schedule
- [ ] TODO placeholder only

#### /agent
- [ ] Create agent as per user prompt
- [ ] Create agent from provider
- [ ] System prompt for this
- [ ] Normalized user input
- [ ] Check if exists, then update with findings
- [ ] If not existing, create new

#### /skills
- [ ] Same as agent
- [ ] System prompt and structure changed
- [ ] Location to create - check if user provided local path
- [ ] If yes, prefer that one

#### /hook
- [ ] TODO placeholder only

#### /orchestrator
- [ ] TODO placeholder only

#### /job
- [ ] Create process channel based on this input

### Directory Structure
- [ ] backend/src/tools/ - tool registry and implementations
- [ ] backend/src/processor/ - slash command processors
- [ ] backend/src/provider/ - provider abstraction
- [ ] backend/src/config/ - configuration loading
- [ ] backend/src/models/ - data models (config model, data models)
- [ ] backend/src/prompt/ - all system prompts and normalization

### Session Management
- [ ] All process channels share session
- [ ] Session can be created new based on /session command
- [ ] Session switching support

## Acceptance Criteria
- [ ] All slash commands work as specified
- [ ] New directory structure is in place
- [ ] Session sharing works across process channels
- [ ] Permissions handled by CLI
- [ ] System prompts are command-specific
- [ ] Tests pass (158+ tests)
- [ ] Ruff lint passes

## Dependencies
- IA-001 through IA-003l (previous architecture changes)
