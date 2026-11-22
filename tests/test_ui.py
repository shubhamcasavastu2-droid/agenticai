from __future__ import annotations

from datetime import datetime
from io import StringIO

import pytest
from rich.console import Console

from src.ui import Display, create_console
from src.ui.theme import AGENTIC_THEME
from src.ui.theme import console as module_console


class TestTheme:
    """Tests for the Rich theme and console configuration."""

    def test_theme_has_expected_styles(self):
        """The theme defines all expected style keys."""
        expected_styles = {
            "status.info",
            "status.success",
            "status.warning",
            "status.error",
            "ui.header",
            "ui.subheader",
            "ui.border",
            "ui.accent",
            "user.input",
            "agent.output",
            "tool.running",
            "tool.done",
            "tool.error",
            "todo.pending",
            "todo.in_progress",
            "todo.done",
            "code.block",
            "dim.text",
        }
        for style in expected_styles:
            assert style in AGENTIC_THEME.styles, f"Missing theme style: {style}"

    def test_create_console_works(self):
        """create_console returns a working Console."""
        c = create_console()
        assert c is not None
        # Can print without error
        c.print("test")

    def test_create_console_no_color(self):
        """create_console with no_color=True disables color output."""
        c = create_console(no_color=True)
        assert c is not None
        c.print("test")

    def test_create_console_force_terminal(self):
        """create_console respects force_terminal parameter."""
        c = create_console(force_terminal=True)
        assert c is not None
        c.print("test")

    def test_module_console_works(self):
        """The module-level console can print without error."""
        module_console.print("test")


class TestDisplay:
    """Tests for the Display class - terminal rendering and non-interactive output."""

    @pytest.fixture
    def capture_console(self):
        """Create a Display with a StringIO capture console that has the agentic theme."""
        output = StringIO()
        c = Console(file=output, force_terminal=False, width=200, no_color=True)
        c.push_theme(AGENTIC_THEME)
        return Display(console=c), output

    def test_info_message(self, capture_console):
        """INFO status message renders with correct prefix."""
        display, output = capture_console
        display.info("Operation completed")
        text = output.getvalue()
        assert "INFO" in text
        assert "Operation completed" in text

    def test_success_message(self, capture_console):
        """SUCCESS status message renders with correct prefix."""
        display, output = capture_console
        display.success("Task finished")
        text = output.getvalue()
        assert "SUCCESS" in text
        assert "Task finished" in text

    def test_warning_message(self, capture_console):
        """WARNING status message renders with correct prefix."""
        display, output = capture_console
        display.warning("Low memory")
        text = output.getvalue()
        assert "WARNING" in text
        assert "Low memory" in text

    def test_error_message(self, capture_console):
        """ERROR status message renders with correct prefix."""
        display, output = capture_console
        display.error("File not found")
        text = output.getvalue()
        assert "ERROR" in text
        assert "File not found" in text

    def test_agent_response_panel(self, capture_console):
        """Agent response renders in a panel with correct title."""
        display, output = capture_console
        display.agent_response("Hello, world!")
        text = output.getvalue()
        assert "Agent" in text
        assert "Hello, world!" in text

    def test_task_not_confirmed_panel(self, capture_console):
        """Task-not-confirmed panel includes attempts and findings."""
        display, output = capture_console
        display.task_not_confirmed("partial output", 3, "Missing file verification")
        text = output.getvalue()
        assert "Task not confirmed" in text
        assert "3 attempts" in text
        assert "Missing file verification" in text
        assert "partial output" in text

    def test_input_normalized_panel(self, capture_console):
        """Normalized input panel renders correctly."""
        display, output = capture_console
        display.input_normalized("Do X then Y")
        text = output.getvalue()
        assert "Normalized input sent to coding agent" in text
        assert "Do X then Y" in text

    def test_normalization_failed_panel(self, capture_console):
        """Normalization failure panel renders correctly."""
        display, output = capture_console
        display.normalization_failed("Error: model returned empty")
        text = output.getvalue()
        assert "Input normalization failed" in text
        assert "Error: model returned empty" in text

    def test_plan_panel(self, capture_console):
        """Plan panel renders title, summary, steps, and risks."""
        display, output = capture_console
        display.plan_panel(
            title="Add feature",
            summary="Implement the feature",
            steps=["Step 1", "Step 2"],
            risks=["Risk A"],
        )
        text = output.getvalue()
        assert "Plan: Add feature" in text
        assert "Implement the feature" in text
        assert "Step 1" in text
        assert "Step 2" in text
        assert "Risk A" in text

    def test_todo_table_pending(self, capture_console):
        """Todo table renders pending items correctly."""
        display, output = capture_console
        display.todo_table([{"title": "Task A", "status": "pending"}])
        text = output.getvalue()
        assert "Todo List" in text
        assert "Task A" in text
        assert "Pending" in text

    def test_todo_table_in_progress(self, capture_console):
        """Todo table renders in-progress items correctly."""
        display, output = capture_console
        display.todo_table([{"title": "Task B", "status": "in_progress"}])
        text = output.getvalue()
        assert "Task B" in text
        assert "In Progress" in text

    def test_todo_table_done(self, capture_console):
        """Todo table renders done items correctly."""
        display, output = capture_console
        display.todo_table([{"title": "Task C", "status": "done"}])
        text = output.getvalue()
        assert "Task C" in text
        assert "Done" in text

    def test_todo_table_empty(self, capture_console):
        """Todo table with no items produces no output."""
        display, output = capture_console
        display.todo_table([])
        assert output.getvalue() == ""

    def test_tool_table_started(self, capture_console):
        """Tool table renders for a started tool call."""
        display, output = capture_console
        display.tool_table("write_file", {"path": "test.py", "content": "print('hi')"})
        text = output.getvalue()
        assert "Running:" in text
        assert "write_file" in text
        assert "path" in text
        assert "test.py" in text

    def test_tool_table_error(self, capture_console):
        """Tool table renders with error styling for failed calls."""
        display, output = capture_console
        display.tool_table("bash", {"cmd": "rm -rf /"}, is_error=True)
        text = output.getvalue()
        assert "Running:" in text
        assert "bash" in text

    def test_tool_result_panel_done(self, capture_console):
        """Tool result panel renders success styling."""
        display, output = capture_console
        display.tool_result_panel("read_file", "file contents here")
        text = output.getvalue()
        assert "read_file" in text
        assert "done" in text.lower()
        assert "file contents here" in text

    def test_tool_result_panel_error(self, capture_console):
        """Tool result panel renders error styling."""
        display, output = capture_console
        display.tool_result_panel("bash", "Command not found", is_error=True)
        text = output.getvalue()
        assert "bash" in text
        assert "error" in text.lower()
        assert "Command not found" in text

    def test_sessions_table_empty(self, capture_console):
        """Sessions table with no items shows warning."""
        display, output = capture_console
        display.sessions_table([])
        text = output.getvalue()
        assert "No saved sessions" in text

    def test_sessions_table_with_items(self, capture_console):
        """Sessions table renders session list."""
        now = datetime.now()
        display, output = capture_console
        display._current_session_id = "sess-1"
        display.sessions_table([("sess-1", 5, now), ("sess-2", 3, now)])
        text = output.getvalue()
        assert "Saved Sessions" in text
        assert "sess-1" in text
        assert "sess-2" in text

    def test_end_stream(self, capture_console):
        """end_stream terminates stream and returns False."""
        display, output = capture_console
        result = display.end_stream(stream_open=True)
        assert result is False

    def test_stream_delta(self, capture_console):
        """stream_delta prints text without newline."""
        display, output = capture_console
        display.stream_delta("hello")
        display.stream_delta(" world")
        text = output.getvalue()
        assert "hello world" in text

    def test_prompt_choices(self, capture_console, monkeypatch):
        """prompt with choices renders correctly."""
        display, output = capture_console
        monkeypatch.setattr("rich.prompt.Prompt.ask", lambda *a, **k: "y")
        result = display.prompt("Continue?", choices=["y", "n"], default="n")
        assert result == "y"

    def test_no_color_console(self):
        """Display works with no_color=True for non-color terminals."""
        output = StringIO()
        c = Console(file=output, force_terminal=False, width=200, no_color=True)
        c.push_theme(AGENTIC_THEME)
        display = Display(console=c, no_color=True)
        display.info("Test message")
        text = output.getvalue()
        assert "INFO" in text
        assert "Test message" in text

    def test_progress_creation(self, capture_console):
        """Progress instance is created for long-running operations."""
        display, output = capture_console
        progress = display.progress()
        assert progress is not None
        assert progress.console is display.console

    def test_spinner_creation(self, capture_console):
        """Spinner instance is created for single long-running task."""
        display, output = capture_console
        spinner = display.spinner("Loading...")
        assert spinner is not None
        assert spinner.console is display.console
