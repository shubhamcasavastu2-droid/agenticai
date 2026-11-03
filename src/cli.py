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
from .config import Config
from .provider import OpenAICompatibleProvider
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
from .permissions import PermissionGate


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

        # Build system prompt
        tool_descriptions = get_tool_descriptions(self.registry.all())
        agent_md_path = self.config.project_root / "AGENT.md"
        system_prompt = build_system_prompt(
            self.config.project_root,
            tool_descriptions,
            agent_md_path,
        )

        # Create agent loop
        self.agent_loop = AgentLoop(
            provider=self.provider,
            registry=self.registry,
            permission_gate=self.permission_gate,
            system_prompt=system_prompt,
            max_steps=self.config.max_steps,
        )

        console.print(f"[green]Agent initialized[/green]")
        console.print(f"Model: [cyan]{self.config.model}[/cyan]")
        console.print(f"Project: [cyan]{self.config.project_root}[/cyan]")
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

            with console.status("[bold green]Thinking...[/bold green]"):
                result = await self.agent_loop.run()

            console.print(Panel(Markdown(result), title="Assistant", border_style="green"))

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
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            self.show_help()

    def show_help(self):
        help_text = """
**Slash Commands:**
- `/help` - Show this help
- `/clear` - Clear conversation history
- `/model [name]` - Show or change model
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
        """
        console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))


async def main():
    config = Config.from_env()
    cli = CLI(config)
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())