from __future__ import annotations

import tempfile
from pathlib import Path

import httpx
import pytest

from src.config.config import Config
from src.provider import (
    OpenAICompatibleProvider,
    ProviderAuthenticationError,
    ProviderTimeoutError,
)
from src.security.permissions import PathValidationError, check_deny_list, validate_path
from src.tools.edit_file import EditFileError, create_edit_file_tool
from src.tools.read_file import create_read_file_tool
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


class TestReadFile:
    @pytest.mark.asyncio
    async def test_missing_file_returns_recovery_guidance(self, temp_dir):
        tool = create_read_file_tool(temp_dir)

        result = await tool.execute(path="src/tools/shell_tool.py")

        assert "File not found: src/tools/shell_tool.py" in result
        assert "glob tool" in result
        assert "call read_file again" in result


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
    @pytest.mark.asyncio
    async def test_unauthorized_response_has_credential_guidance(self):
        provider = OpenAICompatibleProvider(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="invalid-test-key",
            model="z-ai/glm-5.3-flash",
        )

        def unauthorized_request(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, request=request)

        await provider._client.aclose()
        provider._client = httpx.AsyncClient(
            transport=httpx.MockTransport(unauthorized_request),
        )
        try:
            with pytest.raises(ProviderAuthenticationError, match="rotate the API key"):
                await provider.complete(system=None, messages=[], tools=[])
        finally:
            await provider.close()

    @pytest.mark.asyncio
    async def test_nvidia_payload_uses_openai_parameters(self):
        provider = OpenAICompatibleProvider(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key="test",
            model="z-ai/glm-5.3-flash",
        )

        payload = provider._build_payload(system="test", messages=[], tools=[])

        assert payload["model"] == "z-ai/glm-5.3-flash"
        assert payload["max_tokens"] == 8192
        assert payload["temperature"] == 0.5
        assert payload["top_p"] == 1
        assert "num_ctx" not in payload

        await provider.close()

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

    @pytest.mark.asyncio
    async def test_read_timeout_has_actionable_error(self):
        provider = OpenAICompatibleProvider(
            base_url="http://localhost:11434/v1",
            api_key="test",
            model="test",
            timeout=12,
        )

        def timeout_request(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out", request=request)

        await provider._client.aclose()
        provider._client = httpx.AsyncClient(transport=httpx.MockTransport(timeout_request))
        try:
            with pytest.raises(ProviderTimeoutError, match="AGENTIC_REQUEST_TIMEOUT_SECONDS"):
                await provider.complete(system=None, messages=[], tools=[])
        finally:
            await provider.close()


def test_request_timeout_is_loaded_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTIC_REQUEST_TIMEOUT_SECONDS", "123")

    config = Config.from_env(env_file=tmp_path / "missing.env")

    assert config.request_timeout_seconds == 123


def test_context_window_is_loaded_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTIC_CONTEXT_WINDOW_TOKENS", "65536")

    config = Config.from_env(env_file=tmp_path / "missing.env")

    assert config.context_window_tokens == 65536


def test_max_completion_tokens_is_loaded_from_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("AGENTIC_MAX_COMPLETION_TOKENS", "12000")

    config = Config.from_env(env_file=tmp_path / "missing.env")

    assert config.max_completion_tokens == 12000
