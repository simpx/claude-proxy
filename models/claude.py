"""Claude API data models."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ClaudeTextContent(BaseModel):
    """Claude text content block."""
    type: str = "text"
    text: str


class ClaudeImageContent(BaseModel):
    """Claude image content block."""
    type: str = "image"
    source: Dict[str, Any]


class ClaudeMessage(BaseModel):
    """Claude API message format."""
    role: str = Field(..., description="Message role: user, assistant")
    content: Union[str, List[Union[ClaudeTextContent, ClaudeImageContent]]] = Field(
        ..., description="Message content"
    )


class ClaudeUsage(BaseModel):
    """Claude API usage statistics."""
    input_tokens: int
    output_tokens: int


class ClaudeMessagesRequest(BaseModel):
    """Claude API /v1/messages request format."""
    model: str = Field(..., description="Claude model name")
    max_tokens: int = Field(..., description="Maximum tokens to generate")
    messages: List[ClaudeMessage] = Field(..., description="Conversation messages")
    system: Optional[Union[str, List[Dict[str, Any]]]] = Field(
        default=None, description="System prompt"
    )
    temperature: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    stream: Optional[bool] = Field(default=False, description="Enable streaming")
    stop_sequences: Optional[List[str]] = Field(default=None)
    tools: Optional[List[Dict[str, Any]]] = Field(default=None)
    tool_choice: Optional[Dict[str, Any]] = Field(default=None)


class ClaudeMessagesResponse(BaseModel):
    """Claude API /v1/messages response format."""
    id: str
    type: str = "message"
    role: str = "assistant"
    model: str
    content: List[Union[ClaudeTextContent, Dict[str, Any]]]
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: ClaudeUsage


class ClaudeTokenCountRequest(BaseModel):
    """Claude API token count request format."""
    model: str
    system: Optional[Union[str, List[Dict[str, Any]]]] = None
    messages: List[ClaudeMessage]


class ClaudeTokenCountResponse(BaseModel):
    """Claude API token count response format."""
    input_tokens: int


class ClaudeStreamEvent(BaseModel):
    """Claude API streaming event format."""
    type: str
    index: Optional[int] = None
    delta: Optional[Dict[str, Any]] = None
    content_block: Optional[Dict[str, Any]] = None
    message: Optional[Dict[str, Any]] = None
    usage: Optional[ClaudeUsage] = None