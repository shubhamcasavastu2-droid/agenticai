"""Loadable capabilities: skills and agents.

Responsibility: discover and load user-defined skills (SKILL.md) and agents (.md with YAML
frontmatter) so they can be referenced in prompts and slash commands. Objective: extend agent
behaviour without changing code.
"""

from .agents import Agent, AgentLoader
from .skills import Skill, SkillLoader

__all__ = ["Agent", "AgentLoader", "Skill", "SkillLoader"]
