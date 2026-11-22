#!/usr/bin/env python3
"""Check whether a skill or agent already exists in the backend/.agents directory.

Usage:
    python scripts/check-existence.py skill <name>
    python scripts/check-existence.py agent <name>

Exits with code 0 if the skill/agent exists, code 1 if it does not.
Prints the path if it exists.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent
SKILLS_DIR = BACKEND_DIR / "backend" / ".agents" / "skills"
AGENTS_DIR = BACKEND_DIR / "backend" / ".agents" / "agents"
AGENTS_MD = BACKEND_DIR / "backend" / ".agents" / "agents.md"


def skill_exists(name: str) -> bool:
    return (SKILLS_DIR / name / "SKILL.md").exists()


def agent_exists(name: str) -> bool:
    if (AGENTS_DIR / f"{name}.md").exists():
        return True
    if AGENTS_MD.exists():
        content = AGENTS_MD.read_text(encoding="utf-8")
        return f"name: {name}" in content or f'name: "{name}"' in content
    return False


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python check-existence.py <skill|agent> <name>", file=sys.stderr)
        sys.exit(2)

    kind, name = sys.argv[1].lower(), sys.argv[2]

    if kind == "skill":
        exists = skill_exists(name)
        path = SKILLS_DIR / name / "SKILL.md"
    elif kind == "agent":
        exists = agent_exists(name)
        path = AGENTS_DIR / f"{name}.md"
    else:
        print(f"Unknown kind: {kind}. Use 'skill' or 'agent'.", file=sys.stderr)
        sys.exit(2)

    if exists:
        print(str(path))
        sys.exit(0)
    else:
        print(f"{kind} '{name}' does not exist", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
