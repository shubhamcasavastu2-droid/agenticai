from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


@dataclass
class Skill:
    name: str
    description: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)
    content: str = ""

    @classmethod
    def load(cls, skill_dir: Path) -> "Skill":
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            raise ValueError(f"SKILL.md not found in {skill_dir}")
        
        content = skill_file.read_text()
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2].strip()
        else:
            frontmatter = {}
            body = content
        
        return cls(
            name=frontmatter.get("name", skill_dir.name),
            description=frontmatter.get("description", ""),
            path=skill_dir,
            metadata=frontmatter.get("metadata", {}),
            content=body,
        )


class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}

    def discover(self) -> dict[str, Skill]:
        """Discover all skills in the skills directory."""
        self._skills.clear()
        if not self.skills_dir.exists():
            return self._skills
        
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                try:
                    skill = Skill.load(skill_dir)
                    self._skills[skill.name] = skill
                except Exception as e:
                    print(f"Warning: Failed to load skill {skill_dir.name}: {e}")
        return self._skills

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def all(self) -> list[Skill]:
        return list(self._skills.values())

    def format_for_prompt(self) -> str:
        """Format skills for inclusion in system prompt."""
        if not self._skills:
            return ""
        
        lines = ["## Available Skills"]
        for skill in self._skills.values():
            lines.append(f"- **{skill.name}**: {skill.description}")
        return "\n".join(lines)