from __future__ import annotations

import pytest

from src.commands.skills import strip_code_fence
from src.core.agent import AgentLoop
from src.core.completion import CompletionResolver
from src.core.context import ContextManager
from src.core.session import SessionStore
from src.security.permissions import PermissionGate
from src.tools.registry import ToolRegistry
from src.types import (
    Message,
    ModelResponse,
    Role,
    StopReason,
    TextBlock,
    Tool,
    ToolCall,
    ToolResult,
    ToolSchema,
)


class ScriptedProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.received = []

    async def complete(self, system, messages, tools):
        self.received.append(list(messages))
        return self.responses.pop(0)


class EchoTool(Tool):
    def __init__(self, name: str, output: str = "ok"):
        super().__init__(name=name, description=name, schema=ToolSchema(name=name, description=name, parameters={}))
        self.output = output
        self.calls = 0

    async def execute(self, **kwargs):
        self.calls += 1
        return self.output


def tool_turn(call_id: str, output_size: int) -> list[Message]:
    return [
        Message.assistant([ToolCall(id=call_id, name="read_file", arguments={"path": "x"})]),
        Message.tool_result(call_id, "x" * output_size),
    ]


def assert_pairing(messages: list[Message]) -> None:
    """Every tool result must follow an assistant message that issued its call."""
    issued: set[str] = set()
    for message in messages:
        for block in message.content:
            if isinstance(block, ToolCall):
                issued.add(block.id)
            if isinstance(block, ToolResult):
                assert block.call_id in issued, f"orphaned tool result {block.call_id}"


def test_context_manager_compacts_under_budget_and_keeps_pairing():
    manager = ContextManager(context_window_tokens=4000, max_completion_tokens=1000, keep_recent_messages=4)
    messages = [Message.user("original task")]
    for index in range(30):
        messages += tool_turn(f"c{index}", 2000)

    report = manager.compact("system", messages, [])

    assert report.changed
    assert report.after_tokens <= manager.budget_tokens
    assert messages[0].content[0].text == "original task"
    assert messages[1].content[0].text.startswith("[Context note]")
    assert_pairing(messages)


def test_context_manager_leaves_small_history_untouched():
    manager = ContextManager(context_window_tokens=32000, max_completion_tokens=4000)
    messages = [Message.user("hi"), *tool_turn("c1", 100)]
    report = manager.compact("system", messages, [])
    assert not report.changed
    assert len(messages) == 3


def test_budget_handles_completion_tokens_larger_than_window():
    manager = ContextManager(context_window_tokens=200_000, max_completion_tokens=1_000_000)
    assert manager.budget_tokens > 0


@pytest.mark.asyncio
async def test_agent_compacts_history_before_calling_model():
    registry = ToolRegistry()
    registry.register(EchoTool("read_file", output="y" * 5000))
    responses = [
        ModelResponse(
            blocks=[ToolCall(id=f"c{i}", name="read_file", arguments={"path": f"f{i}"})],
            stop_reason=StopReason.TOOL_USE,
        )
        for i in range(12)
    ] + [ModelResponse(blocks=[TextBlock(text="done")], stop_reason=StopReason.END_TURN)]
    provider = ScriptedProvider(responses)
    gate = PermissionGate()
    gate.allow_auto("read_file")
    agent = AgentLoop(
        provider,
        {"agent": provider},
        registry,
        gate,
        "sys",
        max_steps=20,
        context_window_tokens=6000,
        max_completion_tokens=1000,
    )
    agent.add_user_message("read everything")

    assert await agent.run() == "done"
    last_request = provider.received[-1]
    total_chars = sum(len(getattr(b, "output", getattr(b, "text", ""))) for m in last_request for b in m.content)
    assert total_chars < 12 * 5000
    assert_pairing(last_request)


@pytest.mark.asyncio
async def test_agent_returns_malformed_arguments_to_model_as_error():
    registry = ToolRegistry()
    tool = EchoTool("bash")
    registry.register(tool)
    provider = ScriptedProvider(
        [
            ModelResponse(
                blocks=[ToolCall(id="c1", name="bash", arguments={}, parse_error="bad json", raw_arguments="{oops")],
                stop_reason=StopReason.TOOL_USE,
            ),
            ModelResponse(blocks=[TextBlock(text="fixed")], stop_reason=StopReason.END_TURN),
        ]
    )
    agent = AgentLoop(provider, {"agent": provider}, registry, PermissionGate(), "sys")
    agent.add_user_message("go")

    assert await agent.run() == "fixed"
    assert tool.calls == 0
    result = provider.received[1][-1].content[0]
    assert isinstance(result, ToolResult) and result.is_error and "could not parse arguments" in result.output


@pytest.mark.asyncio
async def test_agent_detects_alternating_tool_call_loop():
    registry = ToolRegistry()
    registry.register(EchoTool("a"))
    registry.register(EchoTool("b"))
    responses = [
        ModelResponse(blocks=[ToolCall(id=str(i), name="ab"[i % 2], arguments={})], stop_reason=StopReason.TOOL_USE)
        for i in range(10)
    ]
    provider = ScriptedProvider(responses)
    gate = PermissionGate()
    gate.allow_auto("a")
    gate.allow_auto("b")
    agent = AgentLoop(provider, {"agent": provider}, registry, gate, "sys", max_steps=10)
    agent.add_user_message("go")

    result = await agent.run()
    assert "keep recurring" in result
    assert agent.state.step_count == 5  # a, b, a, b, a -> third "a" stops it


@pytest.mark.asyncio
async def test_completion_review_can_be_disabled():
    provider = ScriptedProvider([ModelResponse(blocks=[TextBlock(text="answer")], stop_reason=StopReason.END_TURN)])
    agent = AgentLoop(provider, {"agent": provider}, ToolRegistry(), PermissionGate(), "sys")
    agent.add_user_message("q")
    result = await CompletionResolver(provider, enabled=False).run(agent, "q", "q")
    assert result.complete and result.response == "answer" and result.attempts == 1
    assert len(provider.received) == 1  # no review call


def test_completion_trace_is_clipped():
    resolver = CompletionResolver(ScriptedProvider([]), max_trace_chars=2000)
    trace = [resolver._format_message(Message.tool_result(str(i), "z" * 5000)) for i in range(20)]
    fitted = resolver._fit_trace(trace)
    assert fitted[0]["role"] == "note"
    assert all(len(block.get("output", "")) < 1600 for entry in fitted for block in entry["content"])


def test_session_round_trip(tmp_path):
    store = SessionStore(tmp_path)
    messages = [
        Message.user("hello"),
        Message.assistant([TextBlock(text="hi"), ToolCall(id="c1", name="glob", arguments={"pattern": "*"})]),
        Message.tool_result("c1", "a.py", is_error=False),
    ]
    store.save(messages)
    saved_id = store.session_id

    fresh = SessionStore(tmp_path)
    loaded = fresh.load()
    assert fresh.session_id == saved_id
    assert [m.role for m in loaded] == [Role.USER, Role.ASSISTANT, Role.TOOL]
    assert loaded == messages
    assert fresh.list_sessions()[0][1] == 3


def test_strip_code_fence():
    assert strip_code_fence("```markdown\n---\nname: x\n---\nbody\n```") == "---\nname: x\n---\nbody\n"
    assert strip_code_fence("---\nname: x\n---\n") == "---\nname: x\n---\n"


@pytest.mark.asyncio
async def test_cli_slash_commands_dispatch_through_registry(tmp_path, monkeypatch):
    from io import StringIO

    from rich.console import Console

    import src.cli as cli_module
    from src.app import Application
    from src.config import Config

    output = StringIO()
    monkeypatch.setattr(cli_module, "console", Console(file=output, force_terminal=False, width=200))
    app = Application(Config(project_root=tmp_path))
    cli = app.cli
    await app.initialize()
    try:
        await cli.handle_slash_command("/permission deny write_file always")
        assert cli.permission_gate.mode("write_file") == "denied"
        assert cli.permission_gate.mode("read_file") == "auto"

        await cli.handle_slash_command("/nope")
        text = output.getvalue()
        assert "Unknown command: /nope" in text
        assert "/resume" in text  # help is generated from the registry

        await cli.handle_slash_command("/skills create ../escape")
        assert "Invalid skill name" in output.getvalue()
        assert not (tmp_path.parent / "escape").exists()
    finally:
        await app.close()
