from __future__ import annotations

import asyncio
import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .agent import AgentLoop
from .agents import AgentLoader
from .commands import build_registry
from .completion import CompletionResolver
from .config import Config
from .logger import (
    log_command,
    log_error,
    log_exception,
    log_info,
    log_permission,
    log_reasoning,
    log_tool_call,
    setup_logging,
)
from .permissions import INTERACTIVE_TOOLS, READ_ONLY_TOOLS, PermissionGate
from .provider import OpenAICompatibleProvider, ProviderAuthenticationError, ProviderTimeoutError
from .session import SessionStore
from .skills import SkillLoader
from .system_prompt import (
    build_system_prompt,
    build_user_input_refurbish_prompt,
    get_tool_descriptions,
)
from .tools import (
    ToolRegistry,
    create_ask_user_tool,
    create_bash_tool,
    create_edit_file_tool,
    create_glob_tool,
    create_grep_tool,
    create_plan_tool,
    create_read_file_tool,
    create_write_file_tool,
)

console = Console()

# Check if running in interactive mode (TTY)
IS_INTERACTIVE = sys.stdin.isatty()

NORMALIZER_SYSTEM_PROMPT = (
    "You normalize user requests for a coding assistant. Return the objective and "
    "actionable tasks in English, regardless of the input language. Preserve intent, "
    "do not invent requirements, and do not ask the user questions or answer the task. "
    "Return only the requested normalized objective and task list."
)


class CLI:
    """Terminal front end: owns the providers, agent loops and session; slash commands live in
    `src/commands/`."""

    def __init__(self, config: Config):
        self.config = config
        self.provider: OpenAICompatibleProvider | None = None
        self.review_provider: OpenAICompatibleProvider | None = None
        self.registry = ToolRegistry()
        self.permission_gate = PermissionGate(config.project_root, default_auto_allow=READ_ONLY_TOOLS)
        self.agent_loop: AgentLoop | None = None
        self.input_normalizer_loop: AgentLoop | None = None
        self.completion_resolver: CompletionResolver | None = None
        self.commands = build_registry()
        self.session = SessionStore(config.sessions_path)
        self.running = True
        self.todos: list[dict[str, str]] = []
        self._stream_open = False

    # ------------------------------------------------------------------ properties

    @property
    def console(self) -> Console:
        # Looked up at call time so tests can swap the module-level console.
        return console

    @property
    def interactive(self) -> bool:
        return IS_INTERACTIVE

    # ------------------------------------------------------------------ setup

    def _make_provider(self, model: str, stream: bool) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            base_url=self.config.base_url,
            api_key=self.config.api_key,
            model=model,
            timeout=self.config.request_timeout_seconds,
            max_completion_tokens=self.config.max_completion_tokens,
            max_retries=self.config.max_retries,
            stream=stream,
            on_text_delta=self.on_text_delta if stream else None,
        )

    async def rebuild_providers(self) -> None:
        """(Re)create the agent and review providers from the current config."""
        await self.close()
        self.provider = self._make_provider(self.config.model, self.config.stream)
        # The reviewer returns JSON, so it never streams to the terminal.
        self.review_provider = self._make_provider(self.config.review_model or self.config.model, False)
        for loop in (self.agent_loop, self.input_normalizer_loop):
            if loop:
                loop.provider = self.provider
        if self.completion_resolver:
            self.completion_resolver.provider = self.provider
            self.completion_resolver.review_provider = self.review_provider

    async def close(self) -> None:
        for provider in (self.provider, self.review_provider):
            if provider:
                await provider.close()

    async def initialize(self) -> None:
        await self.rebuild_providers()
        assert self.provider is not None
        self.completion_resolver = CompletionResolver(
            self.provider,
            max_attempts=self.config.max_completion_attempts,
            review_provider=self.review_provider,
            enabled=self.config.completion_review,
        )

        root = self.config.project_root
        max_output = self.config.max_output_size
        self.registry.register(create_read_file_tool(root, max_output))
        self.registry.register(create_write_file_tool(root))
        self.registry.register(create_edit_file_tool(root))
        self.registry.register(create_glob_tool(root, max_output))
        self.registry.register(create_grep_tool(root, max_output))
        self.registry.register(create_bash_tool(root, max_output))
        self.registry.register(create_ask_user_tool(self.ask_user))
        self.registry.register(create_plan_tool(self.present_plan))

        self.skill_loader = SkillLoader(root / ".agents" / "skills")
        self.skill_loader.discover()
        self.agent_loader = AgentLoader(root / ".agents" / "agents", root / "agents" / "agents.md")
        self.agent_loader.discover()

        system_prompt = build_system_prompt(
            root,
            get_tool_descriptions(self.registry.all()),
            root / "AGENT.md",
            self.skill_loader.format_for_prompt(),
            self.agent_loader.format_for_prompt(),
        )
        self.agent_loop = AgentLoop(
            provider=self.provider,
            registry=self.registry,
            permission_gate=self.permission_gate,
            system_prompt=system_prompt,
            max_steps=self.config.max_steps,
            permission_callback=self._permission_callback,
            reasoning_callback=self._reasoning_callback,
            tool_callback=self._tool_callback,
            clarification_callback=self._clarify_empty_response,
            context_window_tokens=self.config.context_window_tokens,
            max_completion_tokens=self.config.max_completion_tokens,
        )
        self.input_normalizer_loop = AgentLoop(
            provider=self.provider,
            registry=ToolRegistry(),
            permission_gate=PermissionGate(),
            system_prompt=NORMALIZER_SYSTEM_PROMPT,
            max_steps=3,
            reasoning_callback=self._reasoning_callback,
            clarification_callback=self._clarify_empty_response,
            context_window_tokens=self.config.context_window_tokens,
            max_completion_tokens=self.config.max_completion_tokens,
        )

        self.console.print("[green]Agent initialized[/green]")
        self.console.print(f"Model: [cyan]{self.config.model}[/cyan]")
        if self.config.review_model:
            self.console.print(f"Review model: [cyan]{self.config.review_model}[/cyan]")
        self.console.print(f"Max output tokens per response: [cyan]{self.config.max_completion_tokens}[/cyan]")
        self.console.print(f"Context window budget: [cyan]{self.config.context_window_tokens}[/cyan]")
        self.console.print(f"Project: [cyan]{root}[/cyan]")
        if self.skill_loader.all():
            self.console.print(f"Skills loaded: [cyan]{len(self.skill_loader.all())}[/cyan]")
        if self.agent_loader.all():
            self.console.print(f"Agents loaded: [cyan]{len(self.agent_loader.all())}[/cyan]")
        self.console.print("Type [bold]/help[/bold] for commands\n")

    # ------------------------------------------------------------------ main loop

    async def run(self) -> None:
        await self.initialize()
        while self.running:
            try:
                user_input = Prompt.ask("[bold blue]>>[/bold blue]")
                await self.handle_input(user_input.strip())
            except (KeyboardInterrupt, EOFError):
                self.end_stream()
                self.console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
            except ProviderAuthenticationError as e:
                self.end_stream()
                self.console.print(f"[red]Authentication error: {e}[/red]")
                log_error(str(e))
            except ProviderTimeoutError as e:
                self.end_stream()
                self.console.print(
                    "[red]Model request timed out.[/red] "
                    "The model server did not respond within the configured timeout. "
                    "Check that the model server is running and responsive, or increase "
                    "AGENTIC_REQUEST_TIMEOUT_SECONDS (current: "
                    f"{self.config.request_timeout_seconds}s)."
                )
                log_error(str(e))
            except Exception as e:
                self.end_stream()
                detail = str(e).strip() or repr(e)
                self.console.print(f"[red]Error ({type(e).__name__}): {detail}[/red]")
                log_exception(e)
            finally:
                self._save_session()

    async def handle_input(self, user_input: str) -> None:
        if not user_input:
            return
        if user_input.startswith("/"):
            await self.handle_slash_command(user_input)
            return
        if not (self.agent_loop and self.input_normalizer_loop):
            return

        self.input_normalizer_loop.add_user_message(build_user_input_refurbish_prompt(user_input))
        normalized_input = await self.input_normalizer_loop.run()
        self.input_normalizer_loop.clear_history()
        self.end_stream()
        if normalized_input.startswith("Error:"):
            self.console.print(
                Panel(Markdown(normalized_input), title="Input normalization failed", border_style="red")
            )
            return
        self.console.print(
            Panel(Markdown(normalized_input), title="Normalized input sent to coding agent", border_style="cyan")
        )
        self.agent_loop.add_user_message(normalized_input)
        self._create_todos_from_normalized(normalized_input)
        if self.completion_resolver is None:
            raise RuntimeError("Completion resolver is not initialized")
        completion = await self.completion_resolver.run(
            self.agent_loop,
            original_request=user_input,
            normalized_request=normalized_input,
        )
        self.end_stream()

        if completion.complete:
            self.console.print(Panel(Markdown(completion.response), title="Assistant", border_style="green"))
        else:
            status = (
                f"Completion not verified after {completion.attempts} attempts. "
                f"Remaining issue: {completion.findings or 'The reviewer could not confirm completion.'}"
            )
            self.console.print(
                Panel(
                    Markdown(f"{completion.response}\n\n**{status}**"),
                    title="Task not confirmed",
                    border_style="yellow",
                )
            )

    async def handle_slash_command(self, cmd: str) -> None:
        parts = cmd.split()
        log_command(cmd)
        command = self.commands.get(parts[0])
        if command is None:
            self.console.print(f"[red]Unknown command: {parts[0]}[/red]")
            help_command = self.commands.get("help")
            if help_command:
                await help_command.handler(self, [])
            return
        await command.handler(self, parts[1:])

    def _save_session(self) -> None:
        if not isinstance(self.agent_loop, AgentLoop) or not self.agent_loop.state.messages:
            return
        try:
            path = self.session.save(self.agent_loop.state.messages)
            log_info(f"SESSION_SAVED: {path}")
        except OSError as error:
            log_error(f"SESSION_SAVE_FAILED: {error}")

    # ------------------------------------------------------------------ streaming / display callbacks

    async def on_text_delta(self, text: str) -> None:
        self._stream_open = True
        self.console.print(Text(text, style="dim"), end="")

    def end_stream(self) -> None:
        """Terminate a partially streamed line before printing panels or prompts."""
        if self._stream_open:
            self.console.print()
            self._stream_open = False

    async def on_reasoning(self, reasoning: str) -> None:
        self.end_stream()
        self.console.print(Panel(Markdown(reasoning), title="🤔 Reasoning", border_style="magenta", style="dim"))
        log_reasoning(reasoning)

    async def on_tool(self, tool_name: str, args: dict[str, Any], output: str, is_error: bool) -> None:
        self.end_stream()
        if output == "started":
            table = Table(title=f"▶️  Running: {tool_name}", border_style="cyan")
            table.add_column("Parameter", style="cyan")
            table.add_column("Value", style="white")
            for key, value in args.items():
                table.add_row(key, str(value)[:300])
            self.console.print(table)
        else:
            title = f"❌ {tool_name} (error)" if is_error else f"✅ {tool_name} (done)"
            display_output = output[:500]
            if len(output) > 500:
                display_output += f"\n... (truncated, {len(output)} total chars)"
            self.console.print(Panel(Text(display_output), title=title, border_style="red" if is_error else "green"))
        log_tool_call(tool_name, args, output, is_error)

    # Names used by AgentLoop wiring and existing tests.
    _reasoning_callback = on_reasoning
    _tool_callback = on_tool

    # ------------------------------------------------------------------ permission / user interaction

    async def _permission_callback(self, tool_name: str, args: dict[str, Any]) -> tuple[bool, str | None]:
        """Interactive permission prompt. Safety rules were already applied by AgentLoop."""
        self.end_stream()
        gate = self.permission_gate
        if tool_name in INTERACTIVE_TOOLS:
            log_permission(tool_name, True, "Tool performs its own user interaction")
            return True, None
        violation = gate.safety_violation(tool_name, args)
        if violation:
            log_permission(tool_name, False, violation)
            return False, violation
        if gate.is_preapproved(tool_name):
            log_permission(tool_name, True, f"Pre-approved ({gate.mode(tool_name)})")
            return True, None

        if not self.interactive:
            self.console.print(
                f"[yellow]Non-interactive: denying {tool_name} "
                "(use /permission allow <tool> auto to pre-allow)[/yellow]"
            )
            log_permission(tool_name, False, "Non-interactive mode: tool not pre-allowed")
            return False, "Non-interactive mode: tool not pre-allowed"

        table = Table(title=f"Tool Call: {tool_name}", border_style="yellow")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")
        for key, value in args.items():
            table.add_row(key, str(value)[:200])
        self.console.print(table)
        self.console.print("\n[y] Allow once  [a] Allow always  [u] Auto-allow  [n] Deny  [d] Deny always")

        choice = Prompt.ask("Permission", choices=["y", "a", "u", "n", "d"], default="n")
        if choice == "y":
            log_permission(tool_name, True, "Allowed once")
            return True, None
        if choice == "a":
            gate.allow_always(tool_name)
            self.console.print(f"[green]Always allowed: {tool_name}[/green]")
            log_permission(tool_name, True, "Always allowed")
            return True, None
        if choice == "u":
            gate.allow_auto(tool_name)
            self.console.print(f"[green]Auto-allowed: {tool_name} (no prompts this session)[/green]")
            log_permission(tool_name, True, "Auto-allowed")
            return True, None
        if choice == "d":
            gate.deny(tool_name)
            self.console.print(f"[red]Always denied: {tool_name}[/red]")
            log_permission(tool_name, False, "Denied always")
            return False, "User denied permission permanently"
        log_permission(tool_name, False, "Denied once")
        return False, "User denied permission"

    async def ask_user(self, question: str, options: list[str] | None) -> str:
        self.end_stream()
        if not self.interactive:
            raise RuntimeError("ask_user requires an interactive terminal")
        if options:
            return Prompt.ask(f"[bold cyan]{question}[/bold cyan]", choices=options)
        return Prompt.ask(f"[bold cyan]{question}[/bold cyan]")

    async def _clarify_empty_response(self, question: str) -> str:
        return await self.ask_user(question, None)

    async def present_plan(self, title: str, summary: str, steps: list[str], risks: list[str]) -> str:
        self.end_stream()
        if not self.interactive:
            raise RuntimeError("plan approval requires an interactive terminal")
        plan_markdown = f"{summary}\n\n## Steps\n"
        plan_markdown += "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
        if risks:
            plan_markdown += "\n\n## Risks and assumptions\n" + "\n".join(f"- {risk}" for risk in risks)
        self.console.print(Panel(Markdown(plan_markdown), title=f"Plan: {title}", border_style="cyan"))

        decision = Prompt.ask("Plan decision", choices=["approve", "revise", "reject"], default="reject")
        if decision == "approve":
            return "APPROVED: You may proceed with this plan."
        if decision == "revise":
            feedback = Prompt.ask("What should change?", default="Please revise the plan")
            return f"REVISION REQUESTED: {feedback}"
        return "REJECTED: Do not proceed with implementation."

    # ------------------------------------------------------------------ todo list

    def _create_todos_from_normalized(self, normalized_input: str) -> None:
        """Parse tasks from normalized input and show them as a todo list."""
        self.todos = []
        marker = "Tasks to achieve:"
        if marker not in normalized_input:
            return
        for line in normalized_input.split(marker, 1)[1].splitlines():
            line = line.strip()
            if line.startswith("- ") and line[2:].strip():
                self.todos.append({"title": line[2:].strip(), "status": "pending"})
        if not self.todos:
            return
        table = Table(title="Todo List", border_style="blue")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Status", style="yellow", width=10)
        table.add_column("Task", style="white")
        for index, todo in enumerate(self.todos, 1):
            table.add_row(str(index), "✅ Done" if todo["status"] == "done" else "⏳ Pending", todo["title"])
        self.console.print(table)


async def main() -> None:
    config = Config.from_env()
    setup_logging(config.log_dir)
    cli = CLI(config)
    try:
        await cli.run()
    finally:
        await cli.close()


def main_sync() -> None:
    """Synchronous entry point for console script."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main_sync()
