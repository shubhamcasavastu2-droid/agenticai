from __future__ import annotations

import readline
import sys
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .commands import build_registry
from .config import Config
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

NORMALIZER_SYSTEM_PROMPT = """
You are a Requirement Normalizer.

Understand what the user wants, preserve their intent, and convert it into
a clear objective and actionable tasks. Always respond in English.

1. Identify the user's intent and expected outcome.
2. Convert it into a clear, execution-ready objective.
3. Break the objective into ordered tasks with dependencies.
4. Identify missing requirements, ambiguities, conflicts, and constraints.
5. List gaps with their impact and recommended solutions.
6. Ask the user for important missing information and provide your recommendations.
7. Update the objective and tasks based on user input without losing previous decisions.
8. Separate confirmed requirements from assumptions and recommendations.
9. Do not invent requirements or execute the task.

## Output

- User Intent
- Objective
- Requirements
- Tasks (ID, description, dependencies)
- Gaps (missing information, impact, recommendation)
- Updated Objective & Tasks
- Questions for User (only when necessary)
- Readiness (READY, READY_WITH_ASSUMPTIONS, or NEEDS_INPUT)

Keep simple requests concise and complex requests detailed.
Return only the structured analysis.
"""


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
            config.project_root, default_auto_allow=READ_ONLY_TOOLS
        )
        self.agent_loop: AgentLoop | None = None
        self.completion_resolver: Any = None
        self.commands = build_registry()
        self.session = SessionStore(config.sessions_path)
        self.running = True
        self.todos: list[dict[str, str]] = []
        self._stream_open = False
        self.skill_loader: Any = None
        self.agent_loader: Any = None
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

    async def normalize_input(self, user_input: str) -> str:
        """Normalize user input via the model provider. Returns the normalized text."""
        assert self.provider is not None
        response = await self.provider.complete(
            system=NORMALIZER_SYSTEM_PROMPT,
            messages=[Message.user(build_user_input_refurbish_prompt(user_input))],
            tools=[],
        )
        normalized_input = "".join(
            block.text for block in response.blocks if isinstance(block, TextBlock)
        )
        self.end_stream()
        if normalized_input.startswith("Error:"):
            self._ui.normalization_failed(normalized_input)
            return normalized_input
        self._ui.input_normalized(normalized_input)
        return normalized_input

    async def clarify_gaps(self, normalized_input: str) -> str:
        """Use the ask_user tool to ask about any gaps before the final process runs.

        Runs a lightweight agent loop with only the ask_user tool available so the model can
        identify missing/ambiguous information and prompt the user for each gap. Returns the
        clarified request (or the original input when not interactive or no gaps remain).
        """
        if not self.interactive or self.provider is None:
            return normalized_input

        from .core.agent import AgentLoop
        from .tools import ToolRegistry, create_ask_user_tool

        clarify_prompt = (
            "You are a clarification assistant. Your ONLY job is to identify missing information, "
            "ambiguities, or gaps in the user's request and ask the user about them using the "
            "ask_user tool. Do not execute the task. Do not call any tool other than ask_user.\n\n"
            "Process:\n"
            "1. Review the user's request below.\n"
            "2. Identify gaps: missing details, ambiguous requirements, unclear scope, missing files/paths.\n"
            "3. For each gap, call ask_user with a clear question (options when a fixed choice applies).\n"
            "4. Wait for the user's answer, then ask about the next gap.\n"
            "5. When no gaps remain, restate the complete clarified request preserving the "
            "'Tasks to achieve:' list format, then stop.\n\n"
            f"User request:\n{normalized_input}"
        )

        clarify_registry = ToolRegistry()
        clarify_registry.register(create_ask_user_tool(self.ask_user))

        clarify_loop = AgentLoop(
            provider=self.provider,
            providers=self.providers,
            registry=clarify_registry,
            permission_gate=self.permission_gate,
            system_prompt=clarify_prompt,
            max_steps=10,
            tool_callback=self._tool_callback,
            reasoning_callback=self._reasoning_callback,
            context_window_tokens=self.config.context_window_tokens,
            max_completion_tokens=self.config.max_completion_tokens,
        )

        return await clarify_loop.run()

    # ------------------------------------------------------------------ slash commands

    async def handle_slash_command(self, cmd: str) -> None:
        parts = cmd.split()
        log_command(cmd)
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
        self._ui.console.print(
            "\n[y] Allow once  [a] Allow always  [u] Auto-allow  [n] Deny  [d] Deny always"
        )

        choice = self._ui.prompt("Permission", choices=["y", "a", "u", "n", "d"], default="n")
        if choice == "y":
            log_permission(tool_name, True, "Allowed once")
            return True, None
        if choice == "a":
            gate.allow_always(tool_name)
            self._ui.success(f"Always allowed: {tool_name}")
            log_permission(tool_name, True, "Always allowed")
            return True, None
        if choice == "u":
            gate.allow_auto(tool_name)
            self._ui.success(f"Auto-allowed: {tool_name} (no prompts this session)")
            log_permission(tool_name, True, "Auto-allowed")
            return True, None
        if choice == "d":
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
        """Parse tasks from normalized input and show them as a todo list.
        Only sets todos on first call; preserves agent-made status updates."""
        marker = "Tasks to achieve:"
        if marker not in normalized_input:
            return
        # Only create todos if we don't already have them (preserves agent updates)
        if self.todos:
            return
        parsed: list[dict[str, str]] = []
        for line in normalized_input.split(marker, 1)[1].splitlines():
            line = line.strip()
            if line.startswith("- ") and line[2:].strip():
                parsed.append({"title": line[2:].strip(), "status": "pending"})
        if not parsed:
            return
        self.todos = parsed
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
        if in_progress:
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
