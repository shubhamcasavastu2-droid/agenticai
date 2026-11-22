"""
Agents System for Agentic CLI.

This module implements the agents loading mechanism. Agents are markdown files with
YAML frontmatter that define specialized agent configurations including:
- Model selection
- Custom system prompts
- Tool allow/deny lists
- Permission overrides
- Additional context/content

Agents can be loaded and selected via:
- Slash commands (/agents)
- Configuration
- Direct invocation

Structure:
.agents/agents/<agent_name>.md  # Agent definition with YAML frontmatter
agents/agents.md                # Global agents registry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Agent:
    name: str
    description: str = ""
    model: str = "anthropic/claude-sonnet"
    system_prompt: str = ""
    tools: list[str] = field(default_factory=list)
    permissions: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str = ""
    path: str = ""  # Path to the agent file

    @classmethod
    def load(cls, agent_file: Path) -> Agent:
        content = agent_file.read_text()

        # Parse YAML frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
            else:
                frontmatter = {}
                body = content
        else:
            frontmatter = {}
            body = content

        return cls(
            name=frontmatter.get("name", agent_file.stem),
            description=frontmatter.get("description", ""),
            model=frontmatter.get("model", "anthropic/claude-sonnet"),
            system_prompt=frontmatter.get("system_prompt", ""),
            tools=frontmatter.get("tools", []),
            permissions=frontmatter.get("permissions", {}),
            metadata=frontmatter.get("metadata", {}),
            content=body,
            path=str(agent_file),
        )

    def format_for_prompt(self) -> str:
        """Format agent for inclusion in system prompt."""
        lines = [f"## Agent: {self.name}"]
        if self.description:
            lines.append(f"Description: {self.description}")
        if self.model:
            lines.append(f"Model: {self.model}")
        if self.tools:
            lines.append(f"Tools: {', '.join(self.tools)}")
        if self.permissions:
            lines.append(f"Permissions: {self.permissions}")
        if self.system_prompt:
            lines.append(f"System Prompt: {self.system_prompt[:200]}...")
        return "\n".join(lines)


class AgentLoader:
    def __init__(self, agents_dir: Path, default_agents_md: Path | None = None):
        self.agents_dir = agents_dir
        self.default_agents_md = default_agents_md
        self._agents: dict[str, Agent] = {}

    def discover(self) -> dict[str, Agent]:
        """Discover all agents in the agents directory."""
        self._agents.clear()

        # Load default agents.md if exists
        if self.default_agents_md and self.default_agents_md.exists():
            self._load_agents_md(self.default_agents_md)

        # Load individual agent files (.md with frontmatter)
        if not self.agents_dir.exists():
            return self._agents

        for agent_file in self.agents_dir.iterdir():
            if agent_file.suffix == ".md":
                try:
                    agent = Agent.load(agent_file)
                    self._agents[agent.name] = agent
                except Exception as e:
                    print(f"Warning: Failed to load agent {agent_file.name}: {e}")
        return self._agents

    def _load_agents_md(self, path: Path):
        """Load agents from agents.md file (markdown with frontmatter)."""
        content = path.read_text()
        # Extract YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    data = yaml.safe_load(parts[1])
                    if data and "agents" in data:
                        for agent_data in data["agents"]:
                            agent = Agent(
                                name=agent_data.get("name", ""),
                                description=agent_data.get("description", ""),
                                model=agent_data.get("model", "anthropic/claude-sonnet"),
                                system_prompt=agent_data.get("system_prompt", ""),
                                tools=agent_data.get("tools", []),
                                permissions=agent_data.get("permissions", {}),
                                metadata=agent_data.get("metadata", {}),
                            )
                            if agent.name:
                                self._agents[agent.name] = agent
                except Exception:
                    pass

    def get(self, name: str) -> Agent | None:
        return self._agents.get(name)

    def all(self) -> list[Agent]:
        return list(self._agents.values())

    def format_for_prompt(self) -> str:
        """Format agents for inclusion in system prompt."""
        if not self._agents:
            return ""

        lines = ["## Available Agents"]
        for agent in self._agents.values():
            lines.append(f"- **{agent.name}**: {agent.description or 'No description'}")
        return "\n".join(lines)

    def read_agents_md_content(self) -> str:
        """Read the raw agents.md content from common project locations.

        Checks the configured default path first, then common fallback locations.
        Returns the raw text (empty string when not found).
        """
        candidates: list[Path] = []
        if self.default_agents_md is not None:
            candidates.append(self.default_agents_md)
        candidates.extend(
            [
                Path.cwd() / "AGENT.md",
                Path.cwd() / "agents.md",
                Path.cwd() / ".agents" / "agents.md",
            ]
        )
        seen: set[Path] = set()
        for path in candidates:
            if path in seen or not path.exists():
                continue
            seen.add(path)
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                pass
        return ""
