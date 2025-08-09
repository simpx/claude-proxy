"""Tests for provider implementations."""

import pytest
from unittest.mock import AsyncMock, patch

from src.claude_proxy.models.claude import ClaudeMessage, ClaudeMessagesRequest
from src.claude_proxy.providers.openai import OpenAIProvider
from src.claude_proxy.config import map_claude_model


@pytest.fixture
def claude_request():
    """Sample Claude request."""
    return ClaudeMessagesRequest(
        model="claude-3-haiku",
        max_tokens=100,
        messages=[
            ClaudeMessage(role="user", content="Hello, world!")
        ]
    )


@pytest.fixture
def openai_provider():
    """OpenAI provider instance."""
    return OpenAIProvider(
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        timeout=30
    )


def test_model_mapping():
    """Test Claude model to OpenAI model mapping."""
    assert map_claude_model("claude-3-haiku") == "gpt-4o-mini"
    assert map_claude_model("claude-3-sonnet") == "gpt-4o"
    assert map_claude_model("claude-3-opus") == "gpt-4o"
    assert map_claude_model("claude-sonnet-4-20250514") == "gpt-4o"
    assert map_claude_model("unknown-model") == "gpt-4o"  # Default to big model


def test_openai_request_conversion(openai_provider, claude_request):
    """Test conversion of Claude request to OpenAI format."""
    openai_request = openai_provider.convert_request(claude_request)
    
    assert openai_request["model"] == "gpt-4o-mini"
    assert openai_request["max_tokens"] == 100
    assert openai_request["stream"] is False
    assert len(openai_request["messages"]) == 1
    assert openai_request["messages"][0]["role"] == "user"
    assert openai_request["messages"][0]["content"] == "Hello, world!"


def test_openai_request_conversion_with_system(openai_provider):
    """Test conversion with system message."""
    claude_request = ClaudeMessagesRequest(
        model="claude-3-sonnet",
        max_tokens=100,
        system="You are a helpful assistant.",
        messages=[
            ClaudeMessage(role="user", content="Hello")
        ]
    )
    
    openai_request = openai_provider.convert_request(claude_request)
    
    assert len(openai_request["messages"]) == 2
    assert openai_request["messages"][0]["role"] == "system"
    assert openai_request["messages"][0]["content"] == "You are a helpful assistant."
    assert openai_request["messages"][1]["role"] == "user"


def test_openai_response_conversion(openai_provider, claude_request):
    """Test conversion of OpenAI response to Claude format."""
    openai_response = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 8,
            "total_tokens": 18
        }
    }
    
    claude_response = openai_provider.convert_response(openai_response, claude_request)
    
    assert claude_response.id == "chatcmpl-test"
    assert claude_response.model == "claude-3-haiku"
    assert len(claude_response.content) == 1
    assert claude_response.content[0].text == "Hello! How can I help you?"
    assert claude_response.stop_reason == "end_turn"
    assert claude_response.usage.input_tokens == 10
    assert claude_response.usage.output_tokens == 8


def test_finish_reason_conversion(openai_provider):
    """Test OpenAI finish reason to Claude format conversion."""
    assert openai_provider._convert_finish_reason("stop") == "end_turn"
    assert openai_provider._convert_finish_reason("length") == "max_tokens"
    assert openai_provider._convert_finish_reason("function_call") == "tool_use"
    assert openai_provider._convert_finish_reason("tool_calls") == "tool_use"
    assert openai_provider._convert_finish_reason("content_filter") == "stop_sequence"
    assert openai_provider._convert_finish_reason("unknown") == "end_turn"
    assert openai_provider._convert_finish_reason(None) is None


def test_openai_complete_preparation(openai_provider, claude_request):
    """Test OpenAI completion preparation (without actual HTTP call)."""
    # Test that the request is properly converted
    openai_request = openai_provider.convert_request(claude_request)
    assert openai_request["model"] == "gpt-4o-mini"
    assert openai_request["max_tokens"] == 100
    
    # Test response conversion
    mock_response_data = {
        "id": "chatcmpl-test",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 2,
            "total_tokens": 7
        }
    }
    
    response = openai_provider.convert_response(mock_response_data, claude_request)
    assert response.id == "chatcmpl-test"
    assert len(response.content) == 1
    assert response.content[0].text == "Test response"


@pytest.mark.asyncio 
async def test_openai_complete_error(openai_provider, claude_request):
    """Test OpenAI completion error handling."""
    import httpx
    
    with patch.object(openai_provider.client, 'post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 401
        mock_post.side_effect = httpx.HTTPStatusError(
            "Unauthorized",
            request=AsyncMock(),
            response=mock_response
        )
        
        with pytest.raises(Exception) as exc_info:
            await openai_provider.complete(claude_request, "test-id")
        
        assert "Invalid API key" in str(exc_info.value)