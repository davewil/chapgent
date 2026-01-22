from unittest.mock import AsyncMock, patch

import pytest

from chapgent.core.providers import LLMProvider, LLMResponse, TextBlock
from chapgent.tools.base import ToolCategory, ToolDefinition, ToolRisk


@pytest.fixture
def mock_litellm_completion():
    with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock:
        yield mock


@pytest.mark.asyncio
async def test_complete_text_only(mock_litellm_completion):
    # Setup mock response
    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(finish_reason="stop", message=AsyncMock(content="Hello world", tool_calls=None))]
    mock_litellm_completion.return_value = mock_response

    provider = LLMProvider(model="gpt-4o", api_key="test-key")
    messages = [{"role": "user", "content": "Hi"}]

    response = await provider.complete(messages=messages, tools=[])

    assert isinstance(response, LLMResponse)
    assert len(response.content) == 1
    assert isinstance(response.content[0], TextBlock)
    assert response.content[0].text == "Hello world"
    assert response.stop_reason == "stop"

    # Verify litellm call
    mock_litellm_completion.assert_awaited_once()
    call_kwargs = mock_litellm_completion.await_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["api_key"] == "test-key"
    assert call_kwargs["messages"] == messages


@pytest.mark.asyncio
async def test_complete_with_tools_formatting():
    # Verify tools are correctly formatted for litellm
    with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(finish_reason="stop", message=AsyncMock(content="ok", tool_calls=None))]
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="claude-3")

        async def dummy_tool(x: int):
            pass

        tool_def = ToolDefinition(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
            risk=ToolRisk.LOW,
            category=ToolCategory.SHELL,
            function=dummy_tool,
        )

        await provider.complete(messages=[], tools=[tool_def])

        call_kwargs = mock_completion.await_args.kwargs
        assert "tools" in call_kwargs
        tools_arg = call_kwargs["tools"]
        assert len(tools_arg) == 1
        assert tools_arg[0]["type"] == "function"
        assert tools_arg[0]["function"]["name"] == "test_tool"
        assert tools_arg[0]["function"]["description"] == "A test tool"


@pytest.mark.asyncio
async def test_complete_with_tool_call_response_string_args():
    """Test parsing LLM response with tool calls (string JSON arguments)."""
    with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
        # Mock tool call with string arguments (OpenAI style)
        mock_tool_call = AsyncMock()
        mock_tool_call.id = "call_abc123"
        mock_tool_call.function = AsyncMock()
        mock_tool_call.function.name = "read_file"
        mock_tool_call.function.arguments = '{"path": "/tmp/test.txt"}'  # String JSON

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                finish_reason="tool_use",
                message=AsyncMock(content="Let me read that file", tool_calls=[mock_tool_call]),
            )
        ]
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="gpt-4o")
        response = await provider.complete(messages=[{"role": "user", "content": "Read file"}], tools=[])

        from chapgent.core.providers import ToolUseBlock

        assert len(response.content) == 2  # TextBlock + ToolUseBlock
        tool_block = response.content[1]
        assert isinstance(tool_block, ToolUseBlock)
        assert tool_block.id == "call_abc123"
        assert tool_block.name == "read_file"
        assert tool_block.input == {"path": "/tmp/test.txt"}


@pytest.mark.asyncio
async def test_complete_with_tool_call_response_dict_args():
    """Test parsing LLM response with tool calls (dict arguments - pre-parsed)."""
    with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
        # Mock tool call with dict arguments (some providers return dicts already)
        mock_tool_call = AsyncMock()
        mock_tool_call.id = "call_xyz789"
        mock_tool_call.function = AsyncMock()
        mock_tool_call.function.name = "shell"
        mock_tool_call.function.arguments = {"command": "ls -la", "timeout": 30}  # Already a dict

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(finish_reason="tool_use", message=AsyncMock(content=None, tool_calls=[mock_tool_call]))
        ]
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="claude-3")
        response = await provider.complete(messages=[], tools=[])

        from chapgent.core.providers import ToolUseBlock

        assert len(response.content) == 1  # Only ToolUseBlock (no text)
        tool_block = response.content[0]
        assert isinstance(tool_block, ToolUseBlock)
        assert tool_block.id == "call_xyz789"
        assert tool_block.name == "shell"
        assert tool_block.input == {"command": "ls -la", "timeout": 30}


@pytest.mark.asyncio
async def test_complete_with_tool_call_invalid_json_args():
    """Test parsing LLM response with invalid JSON in arguments (fail-safe)."""
    with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
        # Mock tool call with invalid JSON string
        mock_tool_call = AsyncMock()
        mock_tool_call.id = "call_broken"
        mock_tool_call.function = AsyncMock()
        mock_tool_call.function.name = "some_tool"
        mock_tool_call.function.arguments = "{invalid json here}"  # Invalid JSON

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(finish_reason="tool_use", message=AsyncMock(content=None, tool_calls=[mock_tool_call]))
        ]
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="gpt-4o")
        response = await provider.complete(messages=[], tools=[])

        from chapgent.core.providers import ToolUseBlock

        # Should fall back to empty dict on JSON decode error
        assert len(response.content) == 1
        tool_block = response.content[0]
        assert isinstance(tool_block, ToolUseBlock)
        assert tool_block.input == {}  # Fail-safe empty dict


@pytest.mark.asyncio
async def test_complete_multiple_tool_calls():
    """Test parsing response with multiple tool calls."""
    with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_completion:
        mock_tool_call_1 = AsyncMock()
        mock_tool_call_1.id = "call_1"
        mock_tool_call_1.function = AsyncMock()
        mock_tool_call_1.function.name = "read_file"
        mock_tool_call_1.function.arguments = '{"path": "a.txt"}'

        mock_tool_call_2 = AsyncMock()
        mock_tool_call_2.id = "call_2"
        mock_tool_call_2.function = AsyncMock()
        mock_tool_call_2.function.name = "read_file"
        mock_tool_call_2.function.arguments = '{"path": "b.txt"}'

        mock_response = AsyncMock()
        mock_response.choices = [
            AsyncMock(
                finish_reason="tool_use",
                message=AsyncMock(content="Reading both files", tool_calls=[mock_tool_call_1, mock_tool_call_2]),
            )
        ]
        mock_completion.return_value = mock_response

        provider = LLMProvider(model="gpt-4o")
        response = await provider.complete(messages=[], tools=[])

        from chapgent.core.providers import ToolUseBlock

        assert len(response.content) == 3  # TextBlock + 2 ToolUseBlocks
        assert isinstance(response.content[1], ToolUseBlock)
        assert isinstance(response.content[2], ToolUseBlock)
        assert response.content[1].input == {"path": "a.txt"}
        assert response.content[2].input == {"path": "b.txt"}


# =============================================================================
# LiteLLM Gateway / Proxy Support Tests
# =============================================================================


class TestLLMProviderGatewaySupport:
    """Tests for LiteLLM Gateway / base_url / extra_headers support."""

    def _mock_response(self):
        """Create a mock LiteLLM response."""
        response = AsyncMock()
        response.choices = [
            AsyncMock(
                finish_reason="stop",
                message=AsyncMock(content="Test response", tool_calls=None),
            )
        ]
        response.usage = AsyncMock()
        response.usage.prompt_tokens = 10
        response.usage.completion_tokens = 5
        response.usage.total_tokens = 15
        return response

    @pytest.mark.asyncio
    async def test_base_url_passed_to_litellm(self):
        """Verify base_url is passed as api_base to litellm."""
        provider = LLMProvider(
            model="test-model",
            api_key="test-key",
            base_url="http://localhost:4000",
        )

        with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = self._mock_response()

            await provider.complete(
                messages=[{"role": "user", "content": "test"}],
                tools=[],
            )

            mock_complete.assert_called_once()
            call_kwargs = mock_complete.call_args.kwargs
            assert call_kwargs["api_base"] == "http://localhost:4000"

    @pytest.mark.asyncio
    async def test_extra_headers_passed_to_litellm(self):
        """Verify extra_headers are passed to litellm."""
        headers = {"x-litellm-api-key": "Bearer sk-test", "x-custom": "value"}
        provider = LLMProvider(
            model="test-model",
            extra_headers=headers,
        )

        with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = self._mock_response()

            await provider.complete(
                messages=[{"role": "user", "content": "test"}],
                tools=[],
            )

            call_kwargs = mock_complete.call_args.kwargs
            assert call_kwargs["extra_headers"] == headers

    @pytest.mark.asyncio
    async def test_none_values_passed_correctly(self):
        """Verify None values for base_url and extra_headers are passed."""
        provider = LLMProvider(model="test-model")

        with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = self._mock_response()

            await provider.complete(
                messages=[{"role": "user", "content": "test"}],
                tools=[],
            )

            call_kwargs = mock_complete.call_args.kwargs
            assert call_kwargs.get("api_base") is None
            assert call_kwargs.get("extra_headers") is None

    @pytest.mark.asyncio
    async def test_full_gateway_config(self):
        """Test provider with full gateway configuration."""
        provider = LLMProvider(
            model="anthropic-claude",
            api_key="sk-test-key",
            base_url="http://localhost:4000",
            extra_headers={
                "x-litellm-api-key": "Bearer sk-litellm",
                "Authorization": "Bearer oauth-token",
            },
        )

        with patch("chapgent.core.providers.litellm.acompletion", new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = self._mock_response()

            response = await provider.complete(
                messages=[{"role": "user", "content": "test"}],
                tools=[],
            )

            # Verify response is still parsed correctly
            assert isinstance(response, LLMResponse)
            assert len(response.content) == 1
            assert isinstance(response.content[0], TextBlock)

            # Verify all params passed correctly
            call_kwargs = mock_complete.call_args.kwargs
            assert call_kwargs["model"] == "anthropic-claude"
            assert call_kwargs["api_key"] == "sk-test-key"
            assert call_kwargs["api_base"] == "http://localhost:4000"
            assert call_kwargs["extra_headers"]["x-litellm-api-key"] == "Bearer sk-litellm"
