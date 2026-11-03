from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from .agent import AgentLoop
from .agents import AgentLoader
from .config import Config
from .provider import OpenAICompatibleProvider
from .skills import SkillLoader
from .system_prompt import build_system_prompt, get_tool_descriptions
from .tools import (
    ToolRegistry,
    create_bash_tool,
    create_edit_file_tool,
    create_glob_tool,
    create_grep_tool,
    create_read_file_tool,
    create_write_file_tool,
)
from .permissions import PermissionGate, check_deny_list


console = Console()


class CLI:
    def __init__(self, config: Config):
        self.config = config
        self.provider: OpenAICompatibleProvider | None = None
        self.registry = ToolRegistry()
        self.permission_gate = PermissionGate()
        self.agent_loop: AgentLoop | None = None
        self.running = True

    async def initialize(self):
        # Create provider
        self.provider = OpenAICompatibleProvider(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=self.config.model,
        )

        # Register tools
        self.registry.register(create_read_file_tool(self.config.project_root))
        self.registry.register(create_write_file_tool(self.config.project_root))
        self.registry.register(create_edit_file_tool(self.config.project_root))
        self.registry.register(create_glob_tool(self.config.project_root))
        self.registry.register(create_grep_tool(self.config.project_root))
        self.registry.register(create_bash_tool(self.config.project_root))

        # Load skills
        skills_dir = self.config.project_root / ".agents" / "skills"
        self.skill_loader = SkillLoader(skills_dir)
        self.skill_loader.discover()

        # Load agents
        agents_dir = self.config.project_root / ".agents" / "agents"
        default_agents_md = self.config.project_root / "agents" / "agents.md"
        self.agent_loader = AgentLoader(agents_dir, default_agents_md)
        self.agent_loader.discover()

        # Build system prompt with skills and agents
        tool_descriptions = get_tool_descriptions(self.registry.all())
        agent_md_path = self.config.project_root / "AGENT.md"
        system_prompt = build_system_prompt(
            self.config.project_root,
            tool_descriptions,
            agent_md_path,
            self.skill_loader.format_for_prompt(),
            self.agent_loader.format_for_prompt(),
        )

        # Create agent loop with permission callback
        self.agent_loop = AgentLoop(
            provider=self.provider,
            registry=self.registry,
            permission_gate=self.permission_gate,
            system_prompt=system_prompt,
            max_steps=self.config.max_steps,
            permission_callback=self._permission_callback,
            reasoning_callback=self._reasoning_callback,
        )

        console.print(f"[green]Agent initialized[/green]")
        console.print(f"Model: [cyan]{self.config.model}[/cyan]")
        console.print(f"Project: [cyan]{self.config.project_root}[/cyan]")
        if self.skill_loader._skills:
            console.print(f"Skills loaded: [cyan]{len(self.skill_loader._skills)}[/cyan]")
        if self.agent_loader._agents:
            console.print(f"Agents loaded: [cyan]{len(self.agent_loader._agents)}[/cyan]")
        console.print("Type [bold]/help[/bold] for commands\n")

    async def run(self):
        await self.initialize()

        while self.running:
            try:
                user_input = Prompt.ask("[bold blue]>>[/bold blue]")
                await self.handle_input(user_input.strip())
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    async def handle_input(self, user_input: str):
        if not user_input:
            return

        # Slash commands
        if user_input.startswith("/"):
            await self.handle_slash_command(user_input)
            return

        # Regular message to agent
        if self.agent_loop:
            self.agent_loop.add_user_message(user_input)

            result = await self.agent_loop.run()

            console.print(Panel(Markdown(result), title="Assistant", border_style="green"))

    async def _reasoning_callback(self, reasoning: str) -> None:
        """Display model reasoning in console."""
        from rich.panel import Panel
        from rich.markdown import Markdown
        console.print(Panel(Markdown(reasoning), title="🤔 Reasoning", border_style="magenta", style="dim"))

    async def _permission_callback(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, str | None]:
        """Interactive permission prompt for tool execution."""
        # Check if already allowed
        if tool_name in self.permission_gate._always_allow:
            return True, None
        if tool_name in self.permission_gate._auto_allow:
            return True, None

        # Check deny list for bash
        if tool_name == "bash":
            command = args.get("command", "")
            if check_deny_list(command):
                return False, f"Command matches deny list: {command}"

        # Show tool call info
        from rich.table import Table
        from rich.prompt import Prompt
        
        table = Table(title=f"Tool Call: {tool_name}", border_style="yellow")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")
        for k, v in args.items():
            table.add_row(k, str(v)[:200])
        console.print(table)

        # Show permission options
        console.print("\n[y] Allow once  [a] Allow always  [u] Auto-allow  [n] Deny  [d] Deny always")
        
        while True:
            choice = Prompt.ask("Permission", choices=["y", "a", "u", "n", "d"], default="n")
            
            if choice == "y":
                return True, None
            elif choice == "a":
                self.permission_gate.allow_always(tool_name)
                console.print(f"[green]Always allowed: {tool_name}[/green]")
                return True, None
            elif choice == "u":
                self.permission_gate.allow_auto(tool_name)
                console.print(f"[green]Auto-allowed: {tool_name} (no prompts this session)[/green]")
                return True, None
            elif choice == "n":
                return False, "User denied permission"
            elif choice == "d":
                self.permission_gate.deny(tool_name)
                console.print(f"[red]Always denied: {tool_name}[/red]")
                return False, "User denied permission permanently"

    async def handle_slash_command(self, cmd: str):
        parts = cmd.split()
        command = parts[0].lower()

        if command == "/help":
            self.show_help()
        elif command == "/clear":
            if self.agent_loop:
                self.agent_loop.clear_history()
                self.permission_gate.reset()
            console.print("[green]History cleared[/green]")
        elif command == "/model":
            if len(parts) > 1:
                new_model = parts[1]
                self.config.model = new_model
                if self.provider:
                    await self.provider.close()
                    self.provider = OpenAICompatibleProvider(
                        base_url=self.config.base_url,
                        api_key=self.config.api_key,
                        model=new_model,
                    )
                    if self.agent_loop:
                        self.agent_loop.provider = self.provider
                console.print(f"[green]Model changed to: {new_model}[/green]")
            else:
                console.print(f"Current model: [cyan]{self.config.model}[/cyan]")
                console.print("Usage: /model <model-name>")
        elif command == "/exit":
            console.print("[yellow]Goodbye![/yellow]")
            self.running = False
            if self.provider:
                await self.provider.close()
        elif command == "/permission":
            await self.handle_permission_command(parts[1:] if len(parts) > 1 else [])
        elif command == "/skills":
            await self.handle_skills_command(parts[1:] if len(parts) > 1 else [])
        elif command == "/agents":
            await self.handle_agents_command(parts[1:] if len(parts) > 1 else [])
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            self.show_help()

    async def handle_skills_command(self, args: list[str]):
        """Handle /skills command to list, show, or create skills."""
        if not args:
            self.show_skills()
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.show_skills()
        elif subcommand == "show":
            if len(args) < 2:
                console.print("[red]Usage: /skills show <skill-name>[/red]")
                return
            skill_name = args[1]
            skill = self.skill_loader.get(skill_name)
            if skill:
                self.show_skill_detail(skill)
            else:
                console.print(f"[red]Skill not found: {skill_name}[/red]")
        elif subcommand == "create":
            if len(args) < 2:
                console.print("[red]Usage: /skills create <skill-name> [description][/red]")
                return
            skill_name = args[1]
            description = " ".join(args[2:]) if len(args) > 2 else f"Skill: {skill_name}"
            self.create_skill(skill_name, description)
        else:
            console.print(f"[red]Unknown skills subcommand: {subcommand}[/red]")
            self.show_skills_help()

    async def handle_agents_command(self, args: list[str]):
        """Handle /agents command to list, show, or create agents."""
        if not args:
            self.show_agents()
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.show_agents()
        elif subcommand == "show":
            if len(args) < 2:
                console.print("[red]Usage: /agents show <agent-name>[/red]")
                return
            agent_name = args[1]
            agent = self.agent_loader.get(agent_name)
            if agent:
                self.show_agent_detail(agent)
            else:
                console.print(f"[red]Agent not found: {agent_name}[/red]")
        elif subcommand == "create":
            if len(args) < 2:
                console.print("[red]Usage: /agents create <agent-name> [description][/red]")
                return
            agent_name = args[1]
            description = " ".join(args[2:]) if len(args) > 2 else f"Agent: {agent_name}"
            self.create_agent(agent_name, description)
        else:
            console.print(f"[red]Unknown agents subcommand: {subcommand}[/red]")
            self.show_agents_help()

    def show_skills(self):
        """Display all loaded skills."""
        from rich.table import Table
        
        skills = self.skill_loader.all()
        if not skills:
            console.print("[yellow]No skills loaded[/yellow]")
            return
        
        table = Table(title="Loaded Skills", border_style="blue")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Version", style="yellow")
        
        for skill in skills:
            version = skill.metadata.get("version", "1.0")
            table.add_row(skill.name, skill.description, version)
        
        console.print(table)

    def show_skill_detail(self, skill):
        """Display detailed skill information."""
        from rich.panel import Panel
        from rich.markdown import Markdown
        
        content = f"**Name**: {skill.name}\n"
        content += f"**Description**: {skill.description}\n"
        if skill.metadata:
            content += f"**Metadata**: {skill.metadata}\n"
        if skill.content:
            content += f"\n---\n{skill.content}"
        
        console.print(Panel(Markdown(content), title=f"Skill: {skill.name}", border_style="cyan"))

    def create_skill(self, name: str, description: str):
        """Create a new skill file."""
        skills_dir = self.config.project_root / ".agents" / "skills" / name
        skills_dir.mkdir(parents=True, exist_ok=True)
        
        skill_file = skills_dir / "SKILL.md"
        if skill_file.exists():
            console.print(f"[red]Skill already exists: {name}[/red]")
            return
        
        content = f"""---
name: {name}
description: {description}
license: MIT
compatibility: Python 3.11+
metadata:
  version: "1.0"
  skill-author: User
---

# {name}

## When to use

{description}

## Workflow

1. 
2. 
3. 
"""
        skill_file.write_text(content)
        console.print(f"[green]Created skill: {name}[/green]")
        console.print(f"Path: {skill_file}")
        
        # Reload skills
        self.skill_loader.discover()

    def show_skills_help(self):
        help_text = """
**Skills Commands:**
- `/skills` - List all skills
- `/skills list` - List all skills
- `/skills show <name>` - Show skill details
- `/skills create <name> [description]` - Create new skill

**Examples:**
- `/skills create my-skill "A custom skill for my project"`
- `/skills show my-skill`
        """
        console.print(Panel(Markdown(help_text), title="Skills Help", border_style="cyan"))

    async def handle_permission_command(self, args: list[str]):
        """Handle /permission command to view and set tool permissions."""
        tools = self.registry.all()
        tool_names = [t.name for t in tools]
        
        if not args:
            # Show current permissions
            self.show_permissions(tool_names)
            return
        
        subcommand = args[0].lower()
        
        if subcommand == "list":
            self.show_permissions(tool_names)
        elif subcommand == "allow":
            if len(args) < 2:
                console.print("[red]Usage: /permission allow <tool-name> [always|auto][/red]")
                return
            tool_name = args[1]
            if tool_name not in tool_names:
                console.print(f"[red]Unknown tool: {tool_name}. Available: {', '.join(tool_names)}[/red]")
                return
            mode = args[2].lower() if len(args) > 2 else "once"
            if mode == "always":
                self.permission_gate.allow_always(tool_name)
                console.print(f"[green]Permission set: {tool_name} = always[/green]")
            elif mode == "auto":
                self.permission_gate.allow_auto(tool_name)
                console.print(f"[green]Permission set: {tool_name} = auto (no prompts)[/green]")
            else:
                console.print(f"[green]Permission set: {tool_name} = prompt (will ask each time)[/green]")
        elif subcommand == "deny":
            if len(args) < 2:
                console.print("[red]Usage: /permission deny <tool-name> [always][/red]")
                return
            tool_name = args[1]
            if tool_name not in tool_names:
                console.print(f"[red]Unknown tool: {tool_name}. Available: {', '.join(tool_names)}[/red]")
                return
            always = len(args) > 2 and args[2].lower() == "always"
            if always:
                self.permission_gate.deny(tool_name)
                console.print(f"[red]Permission set: {tool_name} = denied always[/red]")
            else:
                self.permission_gate._always_allow.discard(tool_name)
                self.permission_gate._auto_allow.discard(tool_name)
                console.print(f"[yellow]Permission set: {tool_name} = prompt (will ask each time)[/yellow]")
        elif subcommand == "reset":
            self.permission_gate.reset()
            console.print("[green]All permissions reset to defaults[/green]")
        else:
            console.print(f"[red]Unknown subcommand: {subcommand}[/red]")
            self.show_permission_help()

    def show_permissions(self, tool_names: list[str]):
        """Display current permission status for all tools."""
        from rich.table import Table
        
        table = Table(title="Tool Permissions", border_style="blue")
        table.add_column("Tool", style="cyan")
        table.add_column("Default", style="yellow")
        table.add_column("Current", style="green")
        table.add_column("Description", style="white")
        
        for tool in self.registry.all():
            name = tool.name
            # Default is prompt for all tools (they all ask now)
            default = "prompt"
            
            if name in self.permission_gate._always_allow:
                current = "always"
            elif name in self.permission_gate._auto_allow:
                current = "auto"
            else:
                current = "prompt"
            
            table.add_row(name, default, current, tool.description)
        
        console.print(table)
        console.print("\n[y] Allow once  [a] Always allow  [u] Auto-allow  [n] Deny  [d] Deny always")

    def show_permission_help(self):
        help_text = """
**Permission Commands:**
- `/permission` - Show current permissions
- `/permission list` - Show current permissions
- `/permission allow <tool> [always|auto]` - Allow tool (once/always/auto)
- `/permission deny <tool> [always]` - Deny tool (prompt/always)
- `/permission reset` - Reset all permissions to defaults

**Examples:**
- `/permission allow bash always` - Always allow bash without prompting
- `/permission allow read_file auto` - Auto-allow read_file (no prompts)
- `/permission deny write_file always` - Always deny write_file
- `/permission reset` - Reset to defaults

**Interactive Prompt Options:**
- `y` - Allow once for this tool call
- `a` - Allow always for this session
- `u` - Auto-allow (no prompts for this tool this session)
- `n` - Deny this tool call
- `d` - Deny always for this session
        """
        console.print(Panel(Markdown(help_text), title="Permission Help", border_style="blue"))
        help_text = """
**Slash Commands:**
- `/help` - Show this help
- `/clear` - Clear conversation history
- `/model [name]` - Show or change model
- `/permission [list|allow|deny|reset]` - View/set tool permissions
- `/exit` - Exit the CLI

**Tools available to the agent:**
- `read_file` - Read a file (with optional offset/limit)
- `write_file` - Write content to a file
- `edit_file` - Edit a file by exact string replacement
- `glob` - Find files matching a pattern
- `grep` - Search for regex pattern in files
- `bash` - Execute shell commands

**Permission model:**
- Read-only tools (read_file, glob, grep) run automatically
- Write tools (write_file, edit_file, bash) ask for permission
- Type `y` to allow once, `a` to always allow for this session, `n` to deny
- Use `/permission` to manage permissions without prompts
        """
        console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))

    def show_help(self):
        help_text = """
**Slash Commands:**
- `/help` - Show this help
- `/clear` - Clear conversation history
- `/model [name]` - Show or change model
- `/permission [list|allow|deny|reset]` - View/set tool permissions
- `/skills [list|show|create]` - Manage skills
- `/agents [list|show|create]` - Manage agents
- `/exit` - Exit the CLI

**Tools available to the agent:**
- `read_file` - Read a file (with optional offset/limit)
- `write_file` - Write content to a file
- `edit_file` - Edit a file by exact string replacement
- `glob` - Find files matching a pattern
- `grep` - Search for regex pattern in files
- `bash` - Execute shell commands

**Permission model:**
- Read-only tools (read_file, glob, grep) run automatically
- Write tools (write_file, edit_file, bash) ask for permission
- Type `y` to allow once, `a` to always allow for this session, `n` to deny
- Use `/permission` to manage permissions without prompts

**Skills & Agents:**
- Skills in `.agents/skills/<name>/SKILL.md` (auto-loaded)
- Agents in `.agents/agents/<name>.md` (auto-loaded)
- Default agents config in `agents/agents.md` (auto-loaded if exists)
        """
        console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))

    def show_permission_help(self):
        help_text = """
**Permission Commands:**
- `/permission` - Show current permissions
- `/permission list` - Show current permissions
- `/permission allow <tool> [always]` - Allow tool (once or always)
- `/permission deny <tool>` - Deny tool (will prompt each time)
- `/permission reset` - Reset all permissions to defaults

**Examples:**
- `/permission allow bash always` - Always allow bash without prompting
- `/permission deny write_file` - Require prompt for write_file
- `/permission reset` - Reset to defaults
        """
        console.print(Panel(Markdown(help_text), title="Permission Help", border_style="blue"))

    def show_agents(self):
        """Display all loaded agents."""
        from rich.table import Table
        
        agents = self.agent_loader.all()
        if not agents:
            console.print("[yellow]No agents loaded[/yellow]")
            return
        
        table = Table(title="Loaded Agents", border_style="blue")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Model", style="yellow")
        
        for agent in agents:
            table.add_row(agent.name, agent.description or "No description", agent.model)
        
        console.print(table)

    def show_agent_detail(self, agent):
        """Display detailed agent information."""
        from rich.panel import Panel
        from rich.markdown import Markdown
        
        content = f"**Name**: {agent.name}\n"
        content += f"**Description**: {agent.description}\n"
        content += f"**Model**: {agent.model}\n"
        if agent.tools:
            content += f"**Tools**: {', '.join(agent.tools)}\n"
        if agent.permissions:
            content += f"**Permissions**: {agent.permissions}\n"
        if agent.system_prompt:
            content += f"\n**System Prompt**:\n{agent.system_prompt[:300]}..."
        
        console.print(Panel(Markdown(content), title=f"Agent: {agent.name}", border_style="cyan"))

    def create_agent(self, name: str, description: str):
        """Create a new agent file."""
        agents_dir = self.config.project_root / ".agents" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_file = agents_dir / f"{name}.md"
        if agent_file.exists():
            console.print(f"[red]Agent already exists: {name}[/red]")
            return
        
        content = f"""---
name: {name}
description: {description}
model: anthropic/claude-sonnet
system_prompt: |
  You are a helpful coding assistant specialized in {name}.
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
  agent-author: User
---

# {name}

{description}

## Configuration

This agent is configured with the standard toolset. Modify the frontmatter to customize tools, permissions, and model.
"""
        agent_file.write_text(content)
        console.print(f"[green]Created agent: {name}[/green]")
        console.print(f"Path: {agent_file}")
        
        # Reload agents
        self.agent_loader.discover()

    def show_agents_help(self):
        help_text = """
**Agents Commands:**
- `/agents` - List all agents
- `/agents list` - List all agents
- `/agents show <name>` - Show agent details
- `/agents create <name> [description]` - Create new agent

**Examples:**
- `/agents create code-reviewer "Specialized in code review"`
- `/agents show code-reviewer`
        """
        console.print(Panel(Markdown(help_text), title="Agents Help", border_style="cyan"))


async def main():
    config = Config.from_env()
    cli = CLI(config)
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())