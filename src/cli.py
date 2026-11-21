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
        # Confirmed gap decisions preserved across normalize_input calls so
        # resolved questions are not asked again.
        self.confirmed_decisions: dict[str, str] = {}
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

    async def normalize_input(self, user_input: str) -> str:
        """Normalize user input end-to-end.

        1. Refurbish the raw request via the model provider.
        2. Split the result into objective + tasks.
        3. Detect gaps in each task and ask the user (with suggestions) via ask_user.
        4. Take user input once all gaps are filled.
        5. Preserve the original input, refurbish the requirement, build a task object,
           and return it all as the normalized user input string.
        """
        assert self.provider is not None
        self.end_stream()

        # Step 1: refurbish / normalize via the provider.
        response = await self.provider.complete(
            system=self.config.normalizer_system_prompt,
            messages=[
                Message.user(
                    build_user_input_refurbish_prompt(
                        user_input, user_input_refurbish_prompt=self.config.user_input_refurbish_prompt
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

        # Non-interactive: return the refurbished text as-is.
        if not self.interactive:
            self._ui.input_normalized(normalized_text)
            return normalized_text

        # Step 2: split into objective + tasks.
        objective, tasks = self._split_normalized(normalized_text)
        if not tasks:
            self._ui.input_normalized(normalized_text)
            return normalized_text

        # Step 3: skip tasks whose gap was already confirmed in a prior call
        # (don't ask resolved questions again).
        pending_tasks = [
            t for t in tasks if t not in self.confirmed_decisions
        ]
        if not pending_tasks:
            self._ui.input_normalized(normalized_text)
            return normalized_text

        # Step 4: detect actual gaps only across pending tasks.
        gaps: list[dict[str, Any]] = []
        for task in pending_tasks:
            gap, suggestions = await self._detect_gap(objective, task)
            if gap:
                gaps.append({"task": task, "gap": gap, "suggestions": suggestions})

        # Step 5: if no real gaps, continue with normalized input unchanged.
        if not gaps:
            self._ui.input_normalized(normalized_text)
            return normalized_text

        # Step 6: show out-of-scope items on screen.
        self._ui.console.print("\n[ui.header]Out of scope[/ui.header]")
        self._ui.console.print(
            "Items outside the current objective will be ignored unless you add them:"
        )
        self._ui.console.print()

        # Step 7: clarify each gap one-by-one with suggestions.
        clarified_tasks: list[dict[str, str]] = []
        for task in tasks:
            matching_gap = None
            for g in gaps:
                if g["task"] == task:
                    matching_gap = g
                    break
            if matching_gap is None:
                clarified_tasks.append({"title": task, "status": "pending"})
                continue

            gap = matching_gap["gap"]
            suggestions = matching_gap["suggestions"]
            self._ui.console.print(f"\n[ui.subheader]Gap found for task:[/ui.subheader] {task}")
            self._ui.console.print(f"[status.warning]Missing/unclear:[/status.warning] {gap}")
            if suggestions:
                self._ui.console.print(f"Suggestions: {', '.join(suggestions)}")

            suggestion_text = ", ".join(suggestions) if suggestions else "please clarify"
            question = (
                f"Task '{task}' has a gap: {gap}. "
                f"Did you mean {suggestion_text}? Or provide more details."
            )
            answer = await self.ask_user(question, suggestions or None)
            # Preserve the confirmed decision so this question is not asked again.
            self.confirmed_decisions[task] = (answer or "").strip()
            enriched = f"{task} — {answer}" if answer and answer.strip() else task
            clarified_tasks.append({"title": enriched, "status": "pending"})

        # Step 8: reference the normalized input with answers again.
        # Step 9: check existing skills/agents (from agents.md) to load for each task.
        matched_capabilities = await self._match_existing_capabilities(objective, tasks)
        final_text = self._assemble_normalized(
            user_input, objective, clarified_tasks, matched_capabilities
        )
        self._ui.input_normalized(final_text)
        return final_text

    def _split_normalized(self, text: str) -> tuple[str, list[str]]:
        """Split normalized text into (objective, [tasks])."""
        objective = ""
        tasks: list[str] = []
        marker = "Tasks to achieve:"
        if marker in text:
            parts = text.split(marker, 1)
            objective = parts[0].replace("User wants to achieve:", "").strip()
            for line in parts[1].splitlines():
                line = line.strip()
                if line.startswith("- ") and line[2:].strip():
                    tasks.append(line[2:].strip())
        return objective, tasks

    async def _detect_gap(self, objective: str, task: str) -> tuple[str | None, list[str]]:
        """Use the provider to detect gaps in a task and suggest clarifications.

        Returns (gap_description_or_None, [suggestions]).
        Only returns a gap if one actually exists; otherwise returns (None, []).
        """
        if not self.interactive or self.provider is None:
            return None, []

        detect_prompt = (
        "You are a requirement gap detector. Identify only missing information "
        "that is essential to fulfilling the user's actual objective.\n\n"

        f"Overall objective: {objective}\n"
        f"Task to review: {task}\n\n"

        "Rules:\n"
        "- Detect only gaps that materially affect the requested outcome.\n"
        "- Do not flag routine implementation, execution, or verification details.\n"
        "- Do not flag information that can be reasonably inferred from context.\n"
        "- Do not flag implementation choices the agent can decide with reasonable defaults.\n"
        "- Do not suggest additional features or expand the task scope.\n"
        "- Do not treat optional improvements or preferences as required information.\n"
        "- If the user asks to create/edit a file but did not specify its content or "
        "purpose, flag that as a GAP (do not invent content).\n"
        "- If the task can be completed correctly using reasonable defaults, "
        "consider it COMPLETE.\n"
        "- Ask for clarification only when missing information could lead to "
        "a materially incorrect result.\n\n"

        "If no critical gap exists, reply exactly:\n"
        "COMPLETE\n\n"

        "If a critical gap exists, reply exactly:\n"
        "GAP: <what is essential and missing>\n"
        "SUGGEST: <recommended option> | <alternative 1> | <alternative 2>\n\n"

        "Keep the response concise. Return only COMPLETE or the GAP format."
    )
        try:
            response = await self.provider.complete(
                system="You are a precise gap-detection assistant. Reply only in the requested format.",
                messages=[Message.user(detect_prompt)],
                tools=[],
            )
            result = "".join(
                block.text for block in response.blocks if isinstance(block, TextBlock)
            ).strip()
        except Exception:
            return None, []

        if result == "COMPLETE" or not result:
            return None, []
        if result.startswith("GAP:"):
            lines = result.splitlines()
            gap = lines[0][len("GAP:"):].strip()
            suggestions: list[str] = []
            for line in lines[1:]:
                if line.startswith("SUGGEST:"):
                    raw = line[len("SUGGEST:"):]
                    suggestions = [s.strip() for s in raw.split("|") if s.strip()]
                    break
            return gap, suggestions
        return None, []

    async def _match_existing_capabilities(
        self, objective: str, tasks: list[str]
    ) -> list[dict[str, Any]]:
        """Check existing skills and agents (from agents.md) against the tasks.

        Uses the provider to determine which discovered skill or agent can help
        complete each task. Returns a list of matches with type, name, and the
        task indices they apply to.
        """
        if not self.interactive or self.provider is None:
            return []

        agents_md = self.agent_loader.read_agents_md_content() if self.agent_loader else ""

        # Gather discovered skills and agents.
        skills: list[Any] = []
        agents: list[Any] = []
        if self.skill_loader is not None:
            try:
                skills = self.skill_loader.all()
            except Exception:
                skills = []
        if self.agent_loader is not None:
            try:
                agents = self.agent_loader.all()
            except Exception:
                agents = []

        if not skills and not agents and not agents_md:
            return []

        skill_list = "\n".join(
            f"- {s.name}: {s.description}" for s in skills
        ) or "(none discovered)"
        agent_list = "\n".join(
            f"- {a.name}: {a.description}" for a in agents
        ) or "(none discovered)"

        tasks_text = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(tasks))

        match_prompt = (
            "You are a capability-matching assistant. Given a user objective, a list of tasks, "
            "and the available skills/agents (from agents.md and discovered skill/agent files), "
            "decide which skill or agent should be loaded to help complete each task.\n\n"
            f"Objective: {objective}\n\n"
            f"Tasks:\n{tasks_text}\n\n"
            f"Available Skills:\n{skill_list}\n\n"
            f"Available Agents:\n{agent_list}\n\n"
            f"agents.md content:\n{agents_md or '(none found)'}\n\n"
            "For each task, reply with exactly one line per task in this format:\n"
            "TASK <index>: LOAD <type> <name>\n"
            "or if no capability helps:\n"
            "TASK <index>: NONE\n"
            "Only match when the skill/agent name or description clearly applies to the task. "
            "Do not invent capabilities. type is either 'skill' or 'agent'."
        )
        try:
            response = await self.provider.complete(
                system="You are a precise capability-matching assistant. Reply only in the requested format.",
                messages=[Message.user(match_prompt)],
                tools=[],
            )
            result = "".join(
                block.text for block in response.blocks if isinstance(block, TextBlock)
            ).strip()
        except Exception:
            return []

        matches: list[dict[str, Any]] = []
        skill_by_name = {s.name: s for s in skills}
        agent_by_name = {a.name: a for a in agents}

        for line in result.splitlines():
            line = line.strip()
            if not line.startswith("TASK "):
                continue
            try:
                prefix, rest = line.split(":", 1)
                idx_str = prefix[len("TASK "):].strip()
                task_index = int(idx_str) - 1
                rest = rest.strip()
                if rest == "NONE":
                    continue
                if rest.startswith("LOAD "):
                    parts = rest[len("LOAD "):].split(None, 1)
                    if len(parts) != 2:
                        continue
                    ctype, cname = parts[0], parts[1].strip()
                    capability = None
                    if ctype == "skill":
                        capability = skill_by_name.get(cname)
                    elif ctype == "agent":
                        capability = agent_by_name.get(cname)
                    if capability is not None:
                        matches.append(
                            {
                                "type": ctype,
                                "name": cname,
                                "task_index": task_index,
                                "description": getattr(capability, "description", ""),
                            }
                        )
            except (ValueError, IndexError):
                continue
        return matches

    def _assemble_normalized(
        self,
        original_input: str,
        objective: str,
        tasks: list[dict[str, str]],
        matched_capabilities: list[dict[str, Any]] | None = None,
    ) -> str:
        """Reference the normalized input with answers included.

        Preserves original input, refurbished requirement, builds the clarified
        task object, and adds load tasks for matched skills/agents so downstream
        todo creation still works.
        """
        matched_capabilities = matched_capabilities or []
        task_lines = "\n".join(f"- {t['title']}" for t in tasks)

        capability_lines: list[str] = []
        load_task_lines: list[str] = []
        for m in matched_capabilities:
            ctype = m["type"]
            cname = m["name"]
            desc = m.get("description", "")
            capability_lines.append(
                f"- [{ctype}] {cname}: {desc} (applies to task index {m['task_index'] + 1})"
            )
            load_task_lines.append(f"- Load {ctype} '{cname}' to help complete its task")

        return (
            f"Original user input: {original_input}\n\n"
            f"User wants to achieve: {objective}\n"
            f"Tasks to achieve:\n{task_lines}"
            + (
                "\n\nExisting capabilities to load:\n" + "\n".join(capability_lines)
                if capability_lines
                else ""
            )
            + (
                "\n\nAdditional tasks to load capabilities:\n" + "\n".join(load_task_lines)
                if load_task_lines
                else ""
            )
        )

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
