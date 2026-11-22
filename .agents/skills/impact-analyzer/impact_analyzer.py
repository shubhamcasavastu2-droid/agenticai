"""Impact Analyzer Skill Implementation.

This skill monitors changes in src/ and test/ folders, analyzes impact,
creates story documentation, maintains process log, and updates agent registry.
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class FileChange:
    """Represents a single file change."""
    path: str
    change_type: str  # "created", "modified", "deleted"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    size: int = 0


@dataclass
class ImpactAnalysis:
    """Results of impact analysis for a set of changes."""
    story_number: str
    changed_files: list[FileChange]
    affected_components: list[str]
    risk_level: str  # "low", "medium", "high"
    summary: str
    recommendations: list[str]
    test_implications: list[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class StoryRecord:
    """A story record in the process log."""
    story_number: str
    timestamp: str
    changed_files: list[str]
    impact_summary: str
    risk_level: str
    approval_status: str  # "approved", "denied", "pending", "auto-approved"
    outcome: str = ""


class ImpactAnalyzer:
    """Main impact analyzer skill implementation."""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.src_dir = self.project_root / "src"
        self.test_dir = self.project_root / "tests"
        self.docs_dir = self.project_root / "docs"
        self.stories_dir = self.docs_dir / "stories"
        self.process_file = self.docs_dir / "process.md"
        self.agents_file = self.project_root / ".agents" / "agents.md"
        self.agents_dir = self.project_root / ".agents" / "agents"
        self.skills_dir = self.project_root / ".agents" / "skills"

        # Ensure directories exist
        self.stories_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def get_next_story_number(self) -> str:
        """Get the next sequential story number."""
        existing_stories = []
        if self.stories_dir.exists():
            for item in self.stories_dir.iterdir():
                if item.is_dir() and item.name.startswith("STORY-"):
                    try:
                        num = int(item.name.split("-")[1])
                        existing_stories.append(num)
                    except (IndexError, ValueError):
                        continue

        next_num = max(existing_stories, default=0) + 1
        return f"STORY-{next_num:03d}"

    def detect_changes(self, since_commit: str | None = None) -> list[FileChange]:
        """Detect changes in src/ and test/ folders using git diff."""
        changes = []

        # Use git to detect changes
        try:
            if since_commit:
                cmd = ["git", "diff", "--name-status", since_commit, "--", "src/", "tests/"]
            else:
                # Check uncommitted changes
                cmd = ["git", "status", "--porcelain", "--", "src/", "tests/"]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split(maxsplit=1)
                    if len(parts) >= 2:
                        status, filepath = parts[0], parts[1]

                        # Map git status to change type
                        if status.startswith("A"):
                            change_type = "created"
                        elif status.startswith("M"):
                            change_type = "modified"
                        elif status.startswith("D"):
                            change_type = "deleted"
                        elif status.startswith("R"):
                            change_type = "renamed"
                        else:
                            change_type = "modified"

                        full_path = self.project_root / filepath
                        size = full_path.stat().st_size if full_path.exists() else 0

                        changes.append(FileChange(
                            path=filepath,
                            change_type=change_type,
                            size=size
                        ))
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            # Fallback: scan directories for recent changes
            changes = self._scan_directories_for_changes()

        return changes

    def _scan_directories_for_changes(self) -> list[FileChange]:
        """Fallback: scan directories for recently modified files."""
        changes = []
        cutoff_time = time.time() - 3600  # Last hour

        for dir_path in [self.src_dir, self.test_dir]:
            if not dir_path.exists():
                continue
            for file_path in dir_path.rglob("*"):
                if file_path.is_file():
                    try:
                        mtime = file_path.stat().st_mtime
                        if mtime > cutoff_time:
                            rel_path = file_path.relative_to(self.project_root)
                            changes.append(FileChange(
                                path=str(rel_path),
                                change_type="modified",
                                size=file_path.stat().st_size
                            ))
                    except OSError:
                        continue
        return changes

    def analyze_impact(self, changes: list[FileChange]) -> ImpactAnalysis:
        """Analyze the impact of detected changes."""
        if not changes:
            return ImpactAnalysis(
                story_number=self.get_next_story_number(),
                changed_files=[],
                affected_components=[],
                risk_level="low",
                summary="No changes detected",
                recommendations=[],
                test_implications=[]
            )

        story_number = self.get_next_story_number()
        affected_components = set()
        test_implications = set()
        recommendations = []
        risk_factors = []

        for change in changes:
            path = change.path

            # Determine affected components based on file path
            if path.startswith("src/agent.py"):
                affected_components.add("Agent Loop")
                affected_components.add("Completion Review")
                risk_factors.append("Core agent logic modified")
                test_implications.add("Run full agent test suite")
            elif path.startswith("src/provider.py"):
                affected_components.add("Provider Abstraction")
                affected_components.add("Streaming")
                affected_components.add("Retry Logic")
                risk_factors.append("Provider interface changed")
                test_implications.add("Test all provider implementations")
            elif path.startswith("src/tools/"):
                tool_name = Path(path).stem
                affected_components.add(f"Tool: {tool_name}")
                risk_factors.append(f"Tool {tool_name} modified")
                test_implications.add(f"Test {tool_name} functionality")
            elif path.startswith("src/commands/"):
                affected_components.add("Slash Commands")
                risk_factors.append("Command interface changed")
            elif path.startswith("src/cli.py"):
                affected_components.add("CLI Interface")
                affected_components.add("User Interaction")
                risk_factors.append("Main CLI modified")
            elif path.startswith("src/context.py"):
                affected_components.add("Context Management")
                affected_components.add("Token Estimation")
                risk_factors.append("Context compaction logic changed")
            elif path.startswith("src/completion.py"):
                affected_components.add("Completion Review")
                risk_factors.append("Review logic modified")
            elif path.startswith("src/permissions.py") or path.startswith("src/shell_safety.py"):
                affected_components.add("Security/Permissions")
                risk_factors.append("Security logic modified - HIGH RISK")
                risk_factors.append("Requires security review")
            elif path.startswith("src/config.py"):
                affected_components.add("Configuration")
                risk_factors.append("Configuration schema changed")
            elif path.startswith("src/types.py"):
                affected_components.add("Type Definitions")
                risk_factors.append("Core types modified - may affect all modules")
            elif path.startswith("tests/"):
                affected_components.add("Test Suite")
                test_implications.add("New/modified tests - verify they pass")
            elif path.startswith("src/"):
                affected_components.add(f"Module: {Path(path).stem}")

        # Determine risk level
        risk_level = "low"
        if any("HIGH RISK" in f for f in risk_factors):
            risk_level = "high"
        elif any("Core" in f or "security" in f.lower() or "type" in f.lower() for f in risk_factors):
            risk_level = "high"
        elif len(affected_components) > 3 or len(changes) > 5:
            risk_level = "medium"
        elif any("modified" in f for f in risk_factors):
            risk_level = "medium"

        # Generate summary
        summary_lines = [
            f"Detected {len(changes)} file change(s) in {len(affected_components)} component(s).",
            f"Risk Level: {risk_level.upper()}",
            "",
            "Changed Files:"
        ]
        for change in changes:
            summary_lines.append(f"  - {change.path} ({change.change_type})")

        if affected_components:
            summary_lines.append("\nAffected Components:")
            for comp in sorted(affected_components):
                summary_lines.append(f"  - {comp}")

        if risk_factors:
            summary_lines.append("\nRisk Factors:")
            for factor in risk_factors:
                summary_lines.append(f"  - {factor}")

        # Recommendations
        if risk_level == "high":
            recommendations.append("Require explicit user approval before proceeding")
            recommendations.append("Run full test suite including integration tests")
            recommendations.append("Consider code review by security-aware reviewer")
        elif risk_level == "medium":
            recommendations.append("Request user confirmation for significant changes")
            recommendations.append("Run affected module tests")
        else:
            recommendations.append("Low risk - can auto-approve in non-interactive mode")
            recommendations.append("Run related unit tests")

        if test_implications:
            recommendations.extend([f"Test: {t}" for t in test_implications])

        return ImpactAnalysis(
            story_number=story_number,
            changed_files=changes,
            affected_components=sorted(affected_components),
            risk_level=risk_level,
            summary="\n".join(summary_lines),
            recommendations=recommendations,
            test_implications=sorted(test_implications)
        )

    def create_story_document(self, analysis: ImpactAnalysis) -> Path:
        """Create the story analysis document."""
        story_dir = self.stories_dir / analysis.story_number
        story_dir.mkdir(parents=True, exist_ok=True)

        analysis_file = story_dir / "analysis.md"

        content = f"""# Impact Analysis: {analysis.story_number}

**Timestamp:** {analysis.timestamp}
**Risk Level:** {analysis.risk_level.upper()}
**Status:** Pending Approval

---

## Summary

{analysis.summary}

---

## Changed Files

| File | Change Type | Size (bytes) |
|------|-------------|--------------|
"""
        for change in analysis.changed_files:
            content += f"| {change.path} | {change.change_type} | {change.size} |\n"

        content += """

---

## Affected Components

"""
        for comp in analysis.affected_components:
            content += f"- {comp}\n"

        content += f"""

---

## Risk Assessment

**Level:** {analysis.risk_level.upper()}

"""
        if analysis.risk_level == "high":
            content += "**HIGH RISK** - Changes affect core functionality, security, or type definitions. "
            content += "Requires explicit approval and comprehensive testing.\n"
        elif analysis.risk_level == "medium":
            content += "**MEDIUM RISK** - Changes affect multiple components or significant functionality. "
            content += "Requires user confirmation and targeted testing.\n"
        else:
            content += "**LOW RISK** - Changes are localized or additive. "
            content += "Can be auto-approved in non-interactive mode.\n"

        content += """

---

## Recommendations

"""
        for i, rec in enumerate(analysis.recommendations, 1):
            content += f"{i}. {rec}\n"

        content += """

---

## Test Implications

"""
        for impl in analysis.test_implications:
            content += f"- {impl}\n"

        if not analysis.test_implications:
            content += "No specific test implications identified.\n"

        content += """

---

## Approval

- [ ] **Approved** - Proceed with changes
- [ ] **Denied** - Reject changes, revert if necessary
- [ ] **Deferred** - Postpone decision

**Approver:** ________________
**Date:** ________________
**Notes:** ________________

---

*Generated by Impact Analyzer Skill*
"""

        analysis_file.write_text(content, encoding="utf-8")
        return analysis_file

    def update_process_log(self, analysis: ImpactAnalysis, approval_status: str, outcome: str = "") -> None:
        """Update the process.md log file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Read existing process log
        existing_content = ""
        if self.process_file.exists():
            existing_content = self.process_file.read_text(encoding="utf-8")

        # Create new entry
        entry = f"""## {analysis.story_number} - {timestamp}

**Changed Files:**
"""
        for change in analysis.changed_files:
            entry += f"- {change.path} ({change.change_type})\n"

        entry += f"""
**Impact Summary:** {analysis.summary.split(chr(10))[0] if analysis.summary else 'N/A'}

**Risk Level:** {analysis.risk_level.upper()}

**Approval Status:** {approval_status}

**Outcome:** {outcome or 'Pending'}

---

"""

        # Prepend new entry (most recent first)
        if existing_content and not existing_content.startswith("# Process Log"):
            # Add header if missing
            existing_content = "# Process Log\n\n" + existing_content
        elif not existing_content:
            existing_content = "# Process Log\n\n"

        new_content = existing_content.replace("# Process Log\n\n", f"# Process Log\n\n{entry}")
        if new_content == existing_content:
            # Header not found, prepend
            new_content = f"# Process Log\n\n{entry}{existing_content}"

        self.process_file.write_text(new_content, encoding="utf-8")

    def update_agents_registry(self, analysis: ImpactAnalysis | None = None) -> None:
        """Update the agents.md registry file."""
        # Gather current project state
        agents = []
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("*.md"):
                agents.append(agent_file.stem)

        skills = []
        if self.skills_dir.exists():
            for skill_dir in self.skills_dir.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    skills.append(skill_dir.name)

        # Get recent stories
        recent_stories = []
        if self.stories_dir.exists():
            for story_dir in sorted(self.stories_dir.iterdir(), reverse=True)[:10]:
                if story_dir.is_dir() and story_dir.name.startswith("STORY-"):
                    analysis_file = story_dir / "analysis.md"
                    if analysis_file.exists():
                        content = analysis_file.read_text(encoding="utf-8")
                        # Extract risk level
                        risk = "unknown"
                        for line in content.split("\n"):
                            if "**Risk Level:**" in line:
                                risk = line.split("**Risk Level:**")[1].strip()
                                break
                        recent_stories.append({
                            "number": story_dir.name,
                            "risk": risk
                        })

        # Get recent process entries
        recent_process = []
        if self.process_file.exists():
            content = self.process_file.read_text(encoding="utf-8")
            # Parse last 5 entries
            entries = content.split("## ")[1:6]
            for entry in entries:
                lines = entry.strip().split("\n")
                if lines:
                    story_line = lines[0]
                    status = "unknown"
                    for line in lines:
                        if "**Approval Status:**" in line:
                            status = line.split("**Approval Status:**")[1].strip()
                            break
                    recent_process.append({
                        "story": story_line,
                        "status": status
                    })

        # Generate agents.md
        content = f"""# Agent Registry

**Last Updated:** {datetime.now().isoformat()}
**Project Root:** {self.project_root}

---

## Project Overview

This is the Agentic CLI - a provider-agnostic agentic coding tool built from scratch.
It uses tools to read, edit, and run code until tasks are complete.

### Key Components

- **Agent Loop** (`src/agent.py`) - Core execution loop with step management
- **Provider Abstraction** (`src/provider.py`) - OpenAI-compatible provider interface
- **Tool System** (`src/tools/`) - 8 built-in tools (read, write, edit, glob, grep, bash, ask_user, plan, todo)
- **Context Management** (`src/context.py`) - Token estimation and compaction
- **Completion Review** (`src/completion.py`) - Optional second-pass verification
- **Security** (`src/permissions.py`, `src/shell_safety.py`) - Path validation and command safety
- **CLI** (`src/cli.py`) - Terminal interface with slash commands
- **Skills System** (`src/skills.py`) - Extensible skill framework
- **Agents System** (`src/agents.py`) - Specialized agent configurations

---

## Loaded Agents ({len(agents)})

"""
        for agent in sorted(agents):
            content += f"- **{agent}**\n"

        content += f"""

---

## Loaded Skills ({len(skills)})

"""
        for skill in sorted(skills):
            content += f"- **{skill}**\n"

        content += f"""

---

## Recent Stories ({len(recent_stories)})

| Story | Risk Level |
|-------|------------|
"""
        for story in recent_stories:
            content += f"| {story['number']} | {story['risk'].upper()} |\n"

        content += f"""

---

## Recent Process Entries ({len(recent_process)})

| Story | Status |
|-------|--------|
"""
        for entry in recent_process:
            content += f"| {entry['story']} | {entry['status']} |\n"

        if analysis:
            content += f"""

---

## Latest Analysis: {analysis.story_number}

**Risk Level:** {analysis.risk_level.upper()}
**Components Affected:** {len(analysis.affected_components)}
**Files Changed:** {len(analysis.changed_files)}

"""

        content += """

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (cli.py)                           │
│  REPL, Slash Commands, Display, Permission Callbacks        │
├─────────────────────────────────────────────────────────────┤
│                    Agent Loop (agent.py)                    │
│  Step execution, Loop guards, Context compaction, Completion│
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Provider   │  │    Tools     │  │   Permissions    │  │
│  │  (provider)  │  │ (tools/*.py) │  │  (permissions)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Context │ Session │ Logger │ Config │ Shell Safety │ Types │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

- **Model:** Configurable via `AGENTIC_MODEL` env var
- **Base URL:** Configurable via `AGENTIC_BASE_URL` env var
- **Context Window:** Default 128k tokens (configurable)
- **Max Completion:** Default 8192 tokens (configurable)
- **Completion Review:** Enabled by default (configurable)
- **Max Review Attempts:** Default 3 (configurable)

---

## Test Status

- **Total Tests:** 129
- **Test Files:** 8
- **Coverage:** Unit tests for agent, provider, tools, safety, context, completion, UI, interaction

---

*Auto-generated by Impact Analyzer Skill*
"""

        self.agents_file.write_text(content, encoding="utf-8")

    async def request_approval(self, analysis: ImpactAnalysis, cli_ask_user) -> tuple[bool, str]:
        """Request user approval for the changes."""
        # Format the analysis for user
        prompt = f"""## Impact Analysis: {analysis.story_number}

**Risk Level:** {analysis.risk_level.upper()}

{analysis.summary}

### Recommendations:
"""
        for i, rec in enumerate(analysis.recommendations, 1):
            prompt += f"{i}. {rec}\n"

        prompt += "\n**Do you approve proceeding with these changes?**"

        try:
            response = await cli_ask_user(prompt, options=["approve", "deny", "defer"])
            if response.lower() == "approve":
                return True, "approved"
            elif response.lower() == "deny":
                return False, "denied"
            else:
                return False, "deferred"
        except RuntimeError:
            # Non-interactive mode
            if analysis.risk_level == "low":
                return True, "auto-approved"
            else:
                return False, "pending (non-interactive)"

    async def run_analysis(self, cli_ask_user=None, since_commit: str | None = None) -> dict[str, Any]:
        """Run the full impact analysis workflow."""
        # Step 1: Detect changes
        changes = self.detect_changes(since_commit)

        if not changes:
            return {
                "success": True,
                "message": "No changes detected in src/ or tests/",
                "story_number": None
            }

        # Step 2: Analyze impact
        analysis = self.analyze_impact(changes)

        # Step 3: Create story document
        story_file = self.create_story_document(analysis)

        # Step 4: Request approval
        approval_status = "pending"
        approved = False

        if cli_ask_user:
            approved, approval_status = await self.request_approval(analysis, cli_ask_user)
        else:
            # Non-interactive: auto-approve low risk
            if analysis.risk_level == "low":
                approved = True
                approval_status = "auto-approved"
            else:
                approved = False
                approval_status = "pending (requires interactive approval)"

        # Step 5: Update process log
        outcome = "Approved - proceeding" if approved else f"Approval: {approval_status}"
        self.update_process_log(analysis, approval_status, outcome)

        # Step 6: Update agents registry
        self.update_agents_registry(analysis)

        return {
            "success": True,
            "story_number": analysis.story_number,
            "analysis_file": str(story_file),
            "risk_level": analysis.risk_level,
            "approved": approved,
            "approval_status": approval_status,
            "changed_files": [c.path for c in changes],
            "affected_components": analysis.affected_components
        }


# Skill entry point for the skill system
class ImpactAnalyzerSkill:
    """Skill wrapper for the skill loader."""

    def __init__(self, project_root: Path):
        self.analyzer = ImpactAnalyzer(project_root)
        self.name = "impact-analyzer"
        self.description = "Monitors changes in src/ and test/ folders, analyzes impact, creates story documentation"

    async def execute(self, cli_ask_user=None, since_commit: str | None = None, **kwargs) -> dict[str, Any]:
        """Execute the impact analysis."""
        return await self.analyzer.run_analysis(cli_ask_user, since_commit)

    def get_schema(self) -> dict[str, Any]:
        """Return the tool schema for this skill."""
        return {
            "name": "impact_analyzer",
            "description": "Analyze impact of changes in src/ and test/ folders",
            "parameters": {
                "type": "object",
                "properties": {
                    "since_commit": {
                        "type": "string",
                        "description": "Git commit to compare against (optional)"
                    }
                }
            }
        }
