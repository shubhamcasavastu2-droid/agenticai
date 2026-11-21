from __future__ import annotations

import pytest

from src.tools.todo_tool import create_todo_tool


@pytest.mark.asyncio
async def test_todo_tool_create_returns_updated_list():
    """Test that creating a todo list returns the updated list."""
    received = {}

    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        received.update(action=action, items=items)
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)
    result = await tool.execute(
        action="create",
        items=[
            {"title": "Task 1", "status": "pending"},
            {"title": "Task 2", "status": "in_progress"},
        ],
    )

    assert tool.name == "todo"
    assert result == "Todo list updated."
    assert received == {
        "action": "create",
        "items": [
            {"title": "Task 1", "status": "pending"},
            {"title": "Task 2", "status": "in_progress"},
        ],
    }


@pytest.mark.asyncio
async def test_todo_tool_update_returns_updated_list():
    """Test that updating a todo list returns the updated list."""
    received = {}

    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        received.update(action=action, items=items)
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)
    result = await tool.execute(
        action="update",
        items=[
            {"title": "Task 1", "status": "done"},
            {"title": "Task 3", "status": "pending"},
        ],
    )

    assert tool.name == "todo"
    assert result == "Todo list updated."
    assert received == {
        "action": "update",
        "items": [
            {"title": "Task 1", "status": "done"},
            {"title": "Task 3", "status": "pending"},
        ],
    }


@pytest.mark.asyncio
async def test_todo_tool_create_validates_empty_items():
    """Test that creating a todo list with empty items raises ValueError."""
    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)

    with pytest.raises(ValueError, match="items cannot be empty"):
        await tool.execute(action="create", items=[])


@pytest.mark.asyncio
async def test_todo_tool_update_validates_empty_items():
    """Test that updating a todo list with empty items raises ValueError."""
    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)

    with pytest.raises(ValueError, match="items cannot be empty"):
        await tool.execute(action="update", items=[])


@pytest.mark.asyncio
async def test_todo_tool_create_validates_empty_title():
    """Test that creating a todo list with empty title raises ValueError."""
    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)

    with pytest.raises(ValueError, match="todo item title cannot be empty"):
        await tool.execute(action="create", items=[{"title": "", "status": "pending"}])


@pytest.mark.asyncio
async def test_todo_tool_update_validates_empty_title():
    """Test that updating a todo list with empty title raises ValueError."""
    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)

    with pytest.raises(ValueError, match="todo item title cannot be empty"):
        await tool.execute(action="update", items=[{"title": "  ", "status": "pending"}])


@pytest.mark.asyncio
async def test_todo_tool_create_validates_invalid_status():
    """Test that creating a todo list with invalid status raises ValueError."""
    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)

    with pytest.raises(ValueError, match="todo item status must be pending, in_progress, or done"):
        await tool.execute(action="create", items=[{"title": "Task 1", "status": "invalid"}])


@pytest.mark.asyncio
async def test_todo_tool_update_validates_invalid_status():
    """Test that updating a todo list with invalid status raises ValueError."""
    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)

    with pytest.raises(ValueError, match="todo item status must be pending, in_progress, or done"):
        await tool.execute(action="update", items=[{"title": "Task 1", "status": "invalid"}])


@pytest.mark.asyncio
async def test_todo_tool_all_valid_statuses():
    """Test that all valid statuses are accepted."""
    received = {}

    async def todo_callback(action: str, items: list[dict[str, str]]) -> str:
        received.update(action=action, items=items)
        return "Todo list updated."

    tool = create_todo_tool(todo_callback)

    # Test all valid statuses
    for status in ["pending", "in_progress", "done"]:
        received.clear()
        result = await tool.execute(
            action="create",
            items=[{"title": f"Task {status}", "status": status}],
        )
        assert result == "Todo list updated."
        assert received["items"][0]["status"] == status


@pytest.mark.asyncio
async def test_cli_registers_todo_tool(tmp_path):
    """Test that the CLI registers the todo tool."""
    from src.app import Application
    from src.config import Config

    app = Application(Config(project_root=tmp_path))
    await app.initialize()

    try:
        cli = app.cli
        schemas = {schema.name for schema in cli.registry.schemas()}
        assert "todo" in schemas
    finally:
        assert app.provider is not None
        await app.provider.close()
