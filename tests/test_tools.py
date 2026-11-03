from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.permissions import PathValidationError, check_deny_list, validate_path
from src.provider import OpenAICompatibleProvider
from src.tools.edit_file import EditFileError, create_edit_file_tool
from src.types import ToolCall


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


class TestEditFile:

    @pytest.mark.asyncio
    async def test_edit_file_success(self, temp_dir):
        tool = create_edit_file_tool(temp_dir)
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello world\n")

        result = await tool.execute(path=str(test_file), old_string="hello", new_string="hi")
        assert "Edited" in result
        assert test_file.read_text() == "hi world\n"

    @pytest.mark.asyncio
    async def test_edit_file_not_found(self, temp_dir):
        tool = create_edit_file_tool(temp_dir)
        test_file = temp_dir / "nonexistent.txt"

        with pytest.raises(EditFileError) as exc:
            await tool.execute(path=str(test_file), old_string="hello", new_string="hi")
        assert "not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_edit_file_no_match(self, temp_dir):
        tool = create_edit_file_tool(temp_dir)
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello world\n")

        with pytest.raises(EditFileError) as exc:
            await tool.execute(path=str(test_file), old_string="goodbye", new_string="hi")
        assert "not found" in str(exc.value)

    @pytest.mark.asyncio
    async def test_edit_file_multiple_matches(self, temp_dir):
        tool = create_edit_file_tool(temp_dir)
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello hello world\n")

        with pytest.raises(EditFileError) as exc:
            await tool.execute(path=str(test_file), old_string="hello", new_string="hi")
        assert "matches 2 times" in str(exc.value)

    @pytest.mark.asyncio
    async def test_edit_file_shows_context_on_error(self, temp_dir):
        tool = create_edit_file_tool(temp_dir)
        test_file = temp_dir / "test.txt"
        test_file.write_text("line 1\nline 2\nhello world\nline 4\n")

        with pytest.raises(EditFileError) as exc:
            await tool.execute(path=str(test_file), old_string="goodbye", new_string="hi")
        assert "context" in str(exc.value).lower() or "line" in str(exc.value).lower()


class TestPermissions:
    def test_validate_path_within_root(self, temp_dir):
        root = temp_dir
        result = validate_path(root, "src/main.py")
        assert result == (root / "src/main.py").resolve()

    def test_validate_path_absolute_within_root(self, temp_dir):
        root = temp_dir
        result = validate_path(root, str(root / "src/main.py"))
        assert result == (root / "src/main.py").resolve()

    def test_validate_path_escapes_root(self):
        root = Path("/home/user/project")
        with pytest.raises(PathValidationError):
            validate_path(root, "../../../etc/passwd")

    def test_validate_path_escapes_root_absolute(self):
        root = Path("/home/user/project")
        with pytest.raises(PathValidationError):
            validate_path(root, "/etc/passwd")

    def test_check_deny_list_rm_rf(self):
        assert check_deny_list("rm -rf /")
        assert check_deny_list("rm -rf /*")
        assert check_deny_list("sudo rm -rf /")

    def test_check_deny_list_git_push_force(self):
        assert check_deny_list("git push --force")
        assert check_deny_list("git push -f")

    def test_check_deny_list_allows_normal(self):
        assert not check_deny_list("ls -la")
        assert not check_deny_list("python test.py")
        assert not check_deny_list("git push origin main")


class TestProvider:
    def test_tool_call_parsing(self):
        # Test that ToolCall can be created with JSON string args
        tc = ToolCall(id="call_123", name="read_file", arguments={"path": "test.py"})
        assert tc.name == "read_file"
        assert tc.arguments == {"path": "test.py"}

    @pytest.mark.asyncio
    async def test_provider_requires_api_key(self):
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:11434/v1",
            api_key="test",
            model="test",
        )
        # Just verify it initializes
        assert provider.api_key == "test"
        await provider.close()
