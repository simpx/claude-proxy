"""Tests for data models."""

import pytest
from pydantic import ValidationError

from src.claude_proxy.models.claude import (
    ClaudeMessage,
    ClaudeMessagesRequest,
    ClaudeMessagesResponse,
    ClaudeTextContent,
    ClaudeUsage,
)
from src.claude_proxy.models.openai import OpenAIMessage, OpenAIMessagesRequest


def test_claude_message_creation():
    """Test Claude message model creation."""
    # Simple text message
    message = ClaudeMessage(role="user", content="Hello")
    assert message.role == "user"
    assert message.content == "Hello"
    
    # Message with content blocks
    message = ClaudeMessage(
        role="user",
        content=[
            ClaudeTextContent(type="text", text="Hello")
        ]
    )
    assert message.role == "user"
    assert len(message.content) == 1
    assert message.content[0].text == "Hello"


def test_claude_messages_request_validation():
    """Test Claude messages request validation."""
    # Valid request
    request = ClaudeMessagesRequest(
        model="claude-3-haiku",
        max_tokens=100,
        messages=[
            ClaudeMessage(role="user", content="Hello")
        ]
    )
    assert request.model == "claude-3-haiku"
    assert request.max_tokens == 100
    assert len(request.messages) == 1
    
    # Missing required fields should raise error
    with pytest.raises(ValidationError):
        ClaudeMessagesRequest(
            model="claude-3-haiku",
            # Missing max_tokens and messages
        )


def test_claude_messages_request_with_options():
    """Test Claude request with optional parameters."""
    request = ClaudeMessagesRequest(
        model="claude-3-sonnet",
        max_tokens=200,
        messages=[ClaudeMessage(role="user", content="Test")],
        system="You are a helpful assistant",
        temperature=0.7,
        top_p=0.9,
        stream=True,
        stop_sequences=["END"],
        tools=[{"name": "calculator", "description": "A calculator"}]
    )
    
    assert request.system == "You are a helpful assistant"
    assert request.temperature == 0.7
    assert request.top_p == 0.9
    assert request.stream is True
    assert request.stop_sequences == ["END"]
    assert len(request.tools) == 1


def test_claude_messages_response():
    """Test Claude response model."""
    response = ClaudeMessagesResponse(
        id="msg_test",
        model="claude-3-haiku",
        content=[ClaudeTextContent(text="Hello!")],
        stop_reason="end_turn",
        usage=ClaudeUsage(input_tokens=10, output_tokens=5)
    )
    
    assert response.id == "msg_test"
    assert response.type == "message"
    assert response.role == "assistant"
    assert response.model == "claude-3-haiku"
    assert len(response.content) == 1
    assert response.content[0].text == "Hello!"
    assert response.stop_reason == "end_turn"
    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 5


def test_openai_message_creation():
    """Test OpenAI message model creation."""
    message = OpenAIMessage(role="user", content="Hello")
    assert message.role == "user"
    assert message.content == "Hello"
    
    # Message with multimodal content
    message = OpenAIMessage(
        role="user",
        content=[
            {"type": "text", "text": "Hello"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
    )
    assert message.role == "user"
    assert len(message.content) == 2


def test_openai_messages_request():
    """Test OpenAI request model."""
    request = OpenAIMessagesRequest(
        model="gpt-4o",
        messages=[
            OpenAIMessage(role="system", content="You are helpful"),
            OpenAIMessage(role="user", content="Hello")
        ],
        max_tokens=100,
        temperature=0.7,
        stream=False
    )
    
    assert request.model == "gpt-4o"
    assert len(request.messages) == 2
    assert request.max_tokens == 100
    assert request.temperature == 0.7
    assert request.stream is False


def test_temperature_validation():
    """Test temperature parameter validation."""
    # Valid temperature for Claude (0.0-1.0)
    request = ClaudeMessagesRequest(
        model="claude-3-haiku",
        max_tokens=100,
        messages=[ClaudeMessage(role="user", content="Test")],
        temperature=0.5
    )
    assert request.temperature == 0.5
    
    # Invalid temperature should raise error
    with pytest.raises(ValidationError):
        ClaudeMessagesRequest(
            model="claude-3-haiku",
            max_tokens=100,
            messages=[ClaudeMessage(role="user", content="Test")],
            temperature=2.0  # Too high for Claude API
        )