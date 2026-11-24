"""
Command-Line Interface for Agentic CLI.

This module implements the terminal front-end including:
- REPL (Read-Eval-Print Loop) for user interaction
- Slash command registry and execution (/help, /clear, /model, /resume, /permission, /skills, /agents, /plan, /ask, /exit)
- Permission callbacks for tool approval
- Display formatting with Rich
- Session management and resumption
- Input normalization via provider
- Agent loop integration

The CLI class is initialized by Application and coordinates all user-facing interactions.
"""

from __future__ import annotations

import readline
import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .commands import build_registry
from .config.config import Config
from .core.agent import CONTINUATION_STEPS, AgentLoop
from .core.session import SessionStore
from .logger import (
    log_command,
    log_error,
    log_info,
    log_permission,
    log_reasoning,
    log_tool_call,
)
from .prompt.system_prompt import build_user_input_refurbish_prompt
from .provider import (
    OpenAICompatibleProvider,
)
from .security.permissions import INTERACTIVE_TOOLS, READ_ONLY_TOOLS, PermissionGate
from .tools import ToolRegistry
from .types import Message, TextBlock
from .ui import Display, console

# Check if running in interactive mode (TTY)
IS_INTERACTIVE = sys.stdin.isatty()


class CLI:
    """Terminal front end: owns user input, permissions, display, and slash commands.
    Initialized components (provider, agent loop, registry, etc.) are wired in by
    `Application`. The agent loop execution lives in `Application.run()`."""

    def __init__(self, config: Config):
        self.config = config
        self.provider: OpenAICompatibleProvider | None = None
        self.providers: dict[str, OpenAICompatibleProvider] = {}
        self.review_provider: OpenAICompatibleProvider | None = None
        self.registry: ToolRegistry = ToolRegistry()
        self.permission_gate = PermissionGate(
            config.root_dir, default_auto_allow=READ_ONLY_TOOLS
        )
        self.agent_loop: AgentLoop | None = None
        self.completion_resolver: Any = None
        self.commands = build_registry()
        self.session = SessionStore(config.sessions_path)
        self.running = True
        self.todos: list[dict[str, str]] = []
        self._stream_open = False
        self._setup_readline()

    # ------------------------------------------------------------------ properties

    @property
    def console(self) -> Console:
        # Looked up at call time so tests can swap the module-level console.
        return console

    @property
    def _ui(self) -> Display:
        """Lazy UI display using the current module-level console (allows test monkeypatching)."""
        return Display(console=console)

    @property
    def interactive(self) -> bool:
        return IS_INTERACTIVE

    # ------------------------------------------------------------------ readline autocomplete

    def _setup_readline(self) -> None:
        """Configure readline tab completion for slash commands."""
        try:
            readline.set_completer_delims(" \t\n;")
            readline.parse_and_bind("tab: complete")
            readline.set_completer(self._slash_completer)
        except (ImportError, AttributeError):
            # readline not available on this platform (e.g. Windows without pyreadline)
            pass

    def _slash_completer(self, text: str, state: int) -> str | None:
        """Tab-complete slash commands when user types '/'.

        Returns the state-th matching command, or None when no more matches.
        """
        if not text.startswith("/"):
            return None
        matches = [
            f"/{cmd.name}"
            for cmd in self.commands.all()
            if cmd.name.startswith(text.lstrip("/"))
        ]
        if state < len(matches):
            return matches[state]
        return None

    # ------------------------------------------------------------------ user input

    async def prompt_user(self) -> str | None:
        """Prompt the user for input. Returns None on interrupt/EOF."""
        try:
            user_input = self._ui.prompt(">>")
        except (KeyboardInterrupt, EOFError):
            self.end_stream()
            self.console.print("\n[yellow]Interrupted. Type /exit to quit.[/yellow]")
            return None
        return user_input.strip()

    # ------------------------------------------------------------------ normalization / gap clarification



    # ------------------------------------------------------------------ slash commands

    async def handle_slash_command(self, cmd: str) -> None:
        """Route slash commands to the appropriate processor via Application.

        If input starts with '/', it's routed to the command processor.
        Otherwise, it's treated as normal agent input (handled by Application.run()).
        """
        parts = cmd.split()
        cmd_name = parts[0].lstrip("/")
        log_command(cmd)

        # Delegate to Application's processor routing
        app = getattr(self, "app", None)
        if app is not None:
            await app._handle_slash_command(cmd)
        else:
            # Fallback: try old commands registry
            command = self.commands.get(parts[0])
            if command is None:
                self._ui.console.print(f"[status.error]Unknown command:[/status.error] {parts[0]}")
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
        self._ui.stream_delta(text)

    def end_stream(self) -> None:
        """Terminate a partially streamed line before printing panels or prompts."""
        self._stream_open = self._ui.end_stream(self._stream_open)

    async def on_reasoning(self, reasoning: str) -> None:
        self.end_stream()
        self._ui.console.print(
            Panel(Markdown(reasoning), title="🤔 Reasoning", border_style="magenta", style="dim")
        )
        log_reasoning(reasoning)

    async def on_tool(self, tool_name: str, args: dict[str, Any], output: str, is_error: bool) -> None:
        self.end_stream()
        if output == "started":
            self._ui.tool_table(tool_name, args, is_error=False)
        else:
            self._ui.tool_result_panel(tool_name, output, is_error=is_error)
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
            self._ui.warning(
                f"Non-interactive: denying {tool_name} "
                "(use /permission allow <tool> auto to pre-allow)"
            )
            log_permission(tool_name, False, "Non-interactive mode: tool not pre-allowed")
            return False, "Non-interactive mode: tool not pre-allowed"

        self._ui.tool_table(tool_name, args, is_error=False)

        from .security.permission_prompt import prompt_permission

        choice = prompt_permission(tool_name, args)
        if choice == "allow_once":
            self._ui.success(f"Allowed once: {tool_name}")
            log_permission(tool_name, True, "Allowed once")
            return True, None
        if choice == "allow_always":
            gate.allow_always(tool_name)
            self._ui.success(f"Always allowed: {tool_name}")
            log_permission(tool_name, True, "Always allowed")
            return True, None
        if choice == "auto_allow":
            gate.allow_auto(tool_name)
            self._ui.success(f"Auto-allowed: {tool_name} (no prompts this session)")
            log_permission(tool_name, True, "Auto-allowed")
            return True, None
        if choice == "deny_always":
            gate.deny(tool_name)
            self._ui.error(f"Always denied: {tool_name}")
            log_permission(tool_name, False, "Denied always")
            return False, "User denied permission permanently"
        log_permission(tool_name, False, "Denied once")
        return False, "User denied permission"

    async def ask_user(self, question: str, options: list[str] | None) -> str:
        self.end_stream()
        if not self.interactive:
            raise RuntimeError("ask_user requires an interactive terminal")
        if options:
            return self._ui.prompt(question, choices=options)
        return self._ui.prompt(question)

    async def normalize_input(self, user_input: str) -> str:
        """Normalize user input via the model provider."""
        assert self.provider is not None
        self.end_stream()
        response = await self.provider.complete(
            system=self.config.normalizer_system_prompt,
            messages=[
                Message.user(
                    build_user_input_refurbish_prompt(
                        user_input,
                        prompt_template=self.config.user_input_refurbish_prompt,
                    )
                )
            ],
            tools=[],
        )
        normalized_text = "".join(
            block.text for block in response.blocks if isinstance(block, TextBlock)
        )
        self.end_stream()
        if normalized_text.startswith("Error:"):
            self._ui.normalization_failed(normalized_text)
            return normalized_text
        self._ui.input_normalized(normalized_text)
        return normalized_text



    async def _clarify_empty_response(self, question: str) -> str:
        return await self.ask_user(question, None)

    async def present_plan(self, title: str, summary: str, steps: list[str], risks: list[str]) -> str:
        self.end_stream()
        if not self.interactive:
            raise RuntimeError("plan approval requires an interactive terminal")
        self._ui.plan_panel(title, summary, steps, risks)

        decision = self._ui.prompt("Plan decision", choices=["approve", "revise", "reject"], default="reject")
        if decision == "approve":
            return "APPROVED: You may proceed with this plan."
        if decision == "revise":
            feedback = self._ui.prompt("What should change?", default="Please revise the plan")
            return f"REVISION REQUESTED: {feedback}"
        return "REJECTED: Do not proceed with implementation."

    async def _ask_continue(self, current_max_steps: int) -> bool:
        """Ask the user whether to continue for more steps after max steps are reached."""
        self.end_stream()
        if not self.interactive:
            return False
        choice = self._ui.prompt(
            f"Maximum steps ({current_max_steps}) reached. Continue for {CONTINUATION_STEPS} more steps?",
            choices=["y", "n"],
            default="n",
        )
        return choice == "y"

    # ------------------------------------------------------------------ todo list

    def _todo_callback(self, action: str, items: list[dict[str, str]]) -> str:
        """Handle todo tool calls: create or update todo items and display progress."""
        if action == "create":
            self.todos = [{"title": item["title"], "status": item["status"]} for item in items]
        elif action == "update":
            for item in items:
                title = item["title"]
                status = item["status"]
                for todo in self.todos:
                    if todo["title"] == title:
                        todo["status"] = status
                        break
                else:
                    self.todos.append({"title": title, "status": status})
        self._display_todos()
        return "Todo list updated."

    def _create_todos_from_normalized(self, normalized_input: str) -> None:
        """Parse tasks from normalized input and merge into the todo list.

        Preserves existing agent-made status updates while adding any new tasks
        that haven't been seen before. Shows the updated list every time.
        """
        marker = "Tasks to achieve:"
        if marker not in normalized_input:
            return
        parsed: list[dict[str, str]] = []
        for line in normalized_input.split(marker, 1)[1].splitlines():
            line = line.strip()
            if line.startswith("- ") and line[2:].strip():
                title = line[2:].strip()
                # Preserve existing status if we already have this task.
                existing = next((t for t in self.todos if t["title"] == title), None)
                parsed.append(
                    {"title": title, "status": existing["status"] if existing else "pending"}
                )
        if not parsed:
            return
        # Append any brand-new tasks; keep existing statuses for known ones.
        existing_titles = {t["title"] for t in self.todos}
        for item in parsed:
            if item["title"] not in existing_titles:
                self.todos.append(item)
        self._display_todos()

    def _display_todos(self) -> None:
        """Render the todo list with Rich status badges. Shows current in-progress step."""
        if not self.todos:
            return
        # Build a compact single-line summary + detailed table
        pending = [t for t in self.todos if t["status"] == "pending"]
        in_progress = [t for t in self.todos if t["status"] == "in_progress"]
        done = [t for t in self.todos if t["status"] == "done"]

        total = len(self.todos)
        done_count = len(done)

        # Header line with progress
        progress_text = f"{done_count}/{total} complete"
        if done_count == total and total > 0:
            progress_text += " | [todo.done]✅ All tasks completed[/todo.done]"
        elif in_progress:
            progress_text += f" | [todo.in_progress]🔄 {in_progress[0]['title']}[/todo.in_progress]"
        elif pending:
            progress_text += f" | [todo.pending]⏳ Next: {pending[0]['title']}[/todo.pending]"
        else:
            progress_text += " | [todo.done]✅ All done[/todo.done]"

        self._ui.console.print(f"[ui.subheader]Todo:[/ui.subheader]  {progress_text}")

        # Detailed table
        table = Table(title="Todo List", border_style="ui.border", show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Status", style="yellow", width=16)
        table.add_column("Task", style="white")
        for index, item in enumerate(self.todos, 1):
            status = item.get("status", "pending")
            title = item.get("title", "")
            if status == "in_progress":
                status_text = "[todo.in_progress]🔄 In Progress[/todo.in_progress]"
            elif status == "done":
                status_text = "[todo.done]✅ Done[/todo.done]"
            else:
                status_text = "[todo.pending]⏳ Pending[/todo.pending]"
            table.add_row(str(index), status_text, title)
        self._ui.console.print(table)
