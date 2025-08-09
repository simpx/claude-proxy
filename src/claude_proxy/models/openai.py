"""OpenAI API data models."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class OpenAIMessage(BaseModel):
    """OpenAI API message format."""
    role: str = Field(..., description="Message role: system, user, assistant")
    content: Optional[Union[str, List[Dict[str, Any]]]] = Field(
        default=None, description="Message content"
    )
    name: Optional[str] = Field(default=None, description="Message name")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)


class OpenAIUsage(BaseModel):
    """OpenAI API usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class OpenAIChoice(BaseModel):
    """OpenAI API response choice."""
    index: int
    message: OpenAIMessage
    logprobs: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class OpenAIMessagesRequest(BaseModel):
    """OpenAI API /v1/chat/completions request format."""
    model: str = Field(..., description="Model name")
    messages: List[OpenAIMessage] = Field(..., description="Conversation messages")
    max_tokens: Optional[int] = Field(default=None)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    n: Optional[int] = Field(default=1, ge=1)
    stream: Optional[bool] = Field(default=False)
    stop: Optional[Union[str, List[str]]] = Field(default=None)
    presence_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    frequency_penalty: Optional[float] = Field(default=None, ge=-2.0, le=2.0)
    logit_bias: Optional[Dict[str, float]] = Field(default=None)
    user: Optional[str] = Field(default=None)
    tools: Optional[List[Dict[str, Any]]] = Field(default=None)
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(default=None)
    response_format: Optional[Dict[str, Any]] = Field(default=None)
    seed: Optional[int] = Field(default=None)


class OpenAIMessagesResponse(BaseModel):
    """OpenAI API /v1/chat/completions response format."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[OpenAIChoice]
    usage: Optional[OpenAIUsage] = None
    system_fingerprint: Optional[str] = None


class OpenAIStreamChoice(BaseModel):
    """OpenAI API streaming response choice."""
    index: int
    delta: OpenAIMessage
    logprobs: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class OpenAIStreamResponse(BaseModel):
    """OpenAI API streaming response format."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[OpenAIStreamChoice]
    usage: Optional[OpenAIUsage] = None
    system_fingerprint: Optional[str] = None