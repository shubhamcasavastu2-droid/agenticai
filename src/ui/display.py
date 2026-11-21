from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from .theme import create_console


class Display:
    """Centralized Rich display helpers for the agentic CLI.

    All terminal presentation goes through this class so that colors, borders,
    spacing, and layout remain consistent. Accepts an optional Console so tests
    can inject a capture-friendly instance.
    """

    def __init__(self, console: Console | None = None, no_color: bool = False):
        self._console = console or create_console(no_color=no_color)

    @property
    def console(self) -> Console:
        return self._console

    # ------------------------------------------------------------------ status messages

    def info(self, message: str) -> None:
        """Print an INFO status message."""
        self._console.print(f"[status.info]INFO[/status.info]  {message}")

    def success(self, message: str) -> None:
        """Print a SUCCESS status message."""
        self._console.print(f"[status.success]SUCCESS[/status.success]  {message}")

    def warning(self, message: str) -> None:
        """Print a WARNING status message."""
        self._console.print(f"[status.warning]WARNING[/status.warning]  {message}")

    def error(self, message: str) -> None:
        """Print an ERROR status message."""
        self._console.print(f"[status.error]ERROR[/status.error]  {message}")

    # ------------------------------------------------------------------ headers / welcome

    def welcome_header(self, model: str, project_root: str) -> None:
        """Print the professional welcome header."""
        self._console.print()
        self._console.rule("[ui.header]Agentic CLI[/ui.header]", style="ui.border")
        self._console.print(f"[ui.subheader]Model:[/ui.subheader]  {model}")
        self._console.print(f"[ui.subheader]Project:[/ui.subheader]  {project_root}")
        self._console.print("[ui.subheader]Commands:[/ui.subheader]  Type [ui.accent]/help[/ui.accent] for commands")
        self._console.print()

    # ------------------------------------------------------------------ panels

    def panel(self, content: Any, *, title: str, border_style: str = "ui.border") -> None:
        """Print content inside a Rich Panel."""
        self._console.print(Panel(content, title=title, border_style=border_style))

    def markdown_panel(self, markdown_text: str, *, title: str, border_style: str = "ui.border") -> None:
        """Print Markdown text inside a Rich Panel."""
        self.panel(Markdown(markdown_text), title=title, border_style=border_style)

    def agent_response(self, text: str) -> None:
        """Print an agent response in a green-bordered panel."""
        self.markdown_panel(text, title="Agent", border_style="green")

    def task_not_confirmed(self, response: str, attempts: int, findings: str) -> None:
        """Print a task-not-confirmed panel."""
        status = (
            f"Completion not verified after {attempts} attempts. "
            f"Remaining issue: {findings or 'The reviewer could not confirm completion.'}"
        )
        self.markdown_panel(f"{response}\n\n**{status}**", title="Task not confirmed", border_style="yellow")

    def input_normalized(self, normalized: str) -> None:
        """Print the normalized input panel."""
        self.markdown_panel(
            normalized, title="Normalized input sent to coding agent", border_style="cyan"
        )

    def normalization_failed(self, error: str) -> None:
        """Print a normalization failure panel."""
        self.markdown_panel(error, title="Input normalization failed", border_style="red")

    def plan_panel(self, title: str, summary: str, steps: list[str], risks: list[str] | None = None) -> None:
        """Print an implementation plan panel."""
        markdown = f"{summary}\n\n## Steps\n"
        markdown += "\n".join(f"{index}. {step}" for index, step in enumerate(steps, 1))
        if risks:
            markdown += "\n\n## Risks and assumptions\n" + "\n".join(f"- {risk}" for risk in risks)
        self.markdown_panel(markdown, title=f"Plan: {title}", border_style="cyan")

    # ------------------------------------------------------------------ tables

    def todo_table(self, items: list[dict[str, str]]) -> None:
        """Print a todo list table."""
        if not items:
            return
        table = Table(title="Todo List", border_style="ui.border")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Status", style="yellow", width=14)
        table.add_column("Task", style="white")
        for index, item in enumerate(items, 1):
            status = item.get("status", "pending")
            if status == "in_progress":
                status_text = "[todo.in_progress]🔄 In Progress[/todo.in_progress]"
            elif status == "done":
                status_text = "[todo.done]✅ Done[/todo.done]"
            else:
                status_text = "[todo.pending]⏳ Pending[/todo.pending]"
            table.add_row(str(index), status_text, item.get("title", ""))
        self._console.print(table)

    def tool_table(self, tool_name: str, args: dict[str, Any], is_error: bool = False) -> None:
        """Print a tool call parameter table."""
        table = Table(
            title=f"[{'tool.error' if is_error else 'tool.running'}]"
            f"{'❌' if is_error else '▶️'} Running: {tool_name}[/]",
            border_style="red" if is_error else "cyan",
        )
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="white")
        for key, value in args.items():
            table.add_row(key, str(value)[:300])
        self._console.print(table)

    def tool_result_panel(
        self, tool_name: str, output: str, is_error: bool = False, max_chars: int = 500
    ) -> None:
        """Print a tool result panel."""
        title_style = "tool.error" if is_error else "tool.done"
        icon = "❌" if is_error else "✅"
        display_output = output[:max_chars]
        if len(output) > max_chars:
            display_output += f"\n... (truncated, {len(output)} total chars)"
        self._console.print(
            Panel(
                Text(display_output),
                title=f"[{title_style}]{icon} {tool_name} ({'error' if is_error else 'done'})[/]",
                border_style="red" if is_error else "green",
            )
        )

    def sessions_table(self, sessions: list[tuple[str, int, Any]]) -> None:
        """Print a saved sessions table."""
        if not sessions:
            self.warning("No saved sessions")
            return
        table = Table(title="Saved Sessions", border_style="ui.border")
        table.add_column("Session", style="cyan")
        table.add_column("Messages", style="yellow", justify="right")
        table.add_column("Last updated", style="white")
        for session_id, count, modified in sessions[:20]:
            marker = " (current)" if session_id == getattr(self, "_current_session_id", None) else ""
            table.add_row(session_id + marker, str(count), modified.strftime("%Y-%m-%d %H:%M"))
        self._console.print(table)

    # ------------------------------------------------------------------ progress / spinners

    def progress(self, transient: bool = True) -> Progress:
        """Create and return a Progress instance for long-running operations."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=self._console,
            transient=transient,
        )

    def spinner(self, message: str) -> Progress:
        """Create a simple spinner for a single long-running task."""
        return Progress(
            SpinnerColumn(),
            TextColumn(f"[progress.description]{message}"),
            console=self._console,
            transient=True,
        )

    # ------------------------------------------------------------------ streams

    def end_stream(self, stream_open: bool = False) -> bool:
        """Terminate a partially streamed line. Returns False (stream closed)."""
        if stream_open:
            self._console.print()
        return False

    def stream_delta(self, text: str) -> None:
        """Print a streaming text delta."""
        self._console.print(Text(text, style="dim.text"), end="")

    # ------------------------------------------------------------------ prompts

    def prompt(self, message: str, *, choices: list[str] | None = None, default: str | None = None) -> str:
        """Prompt the user with Rich-styled text.

        When `choices` are provided, they are shown as numbered options and the user may
        select one by typing its number, or type the full option text. Free-text input is
        always accepted.
        """
        from rich.prompt import Prompt

        style = "ui.input" if choices else "ui.accent"
        prompt_text = message
        if choices:
            lines = [message]
            for index, choice in enumerate(choices, 1):
                lines.append(f"  [{index}] {choice}")
            if default is not None:
                lines.append(f"  (default: {default})")
            prompt_text = "\n".join(lines)
            prompt_text += "\nSelect an option or type your answer: "
        else:
            prompt_text = message

        while True:
            answer = Prompt.ask(f"[{style}]{prompt_text}[/{style}]", default=default)
            if answer is None or answer == "":
                if default is not None:
                    return default
                continue
            # Numeric selection maps to the choice text.
            if choices:
                try:
                    index = int(answer.strip())
                    if 1 <= index <= len(choices):
                        return choices[index - 1]
                except ValueError:
                    pass
            return answer
