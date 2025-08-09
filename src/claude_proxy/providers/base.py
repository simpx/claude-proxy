"""Base provider class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional

import httpx

from ..models.claude import ClaudeMessagesRequest, ClaudeMessagesResponse


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(
        self, 
        api_key: str, 
        base_url: str, 
        timeout: int = 90,
        client: Optional[httpx.AsyncClient] = None
    ):
        """Initialize provider with API credentials."""
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()
    
    @abstractmethod
    async def complete(
        self, 
        request: ClaudeMessagesRequest,
        request_id: str
    ) -> ClaudeMessagesResponse:
        """Complete a chat completion request."""
        pass
    
    @abstractmethod
    async def stream_complete(
        self, 
        request: ClaudeMessagesRequest,
        request_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream a chat completion request."""
        pass
    
    @abstractmethod
    def convert_request(self, request: ClaudeMessagesRequest) -> Dict[str, Any]:
        """Convert Claude request to provider-specific format."""
        pass
    
    @abstractmethod
    def convert_response(
        self, 
        response: Dict[str, Any], 
        original_request: ClaudeMessagesRequest
    ) -> ClaudeMessagesResponse:
        """Convert provider response to Claude format."""
        pass
    
    def get_headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        key = api_key or self.api_key
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "claude-proxy/0.1.0"
        }
    
    def classify_error(self, error_message: str, status_code: Optional[int] = None) -> str:
        """Classify error message for better user experience."""
        error_lower = error_message.lower()
        
        if status_code == 401:
            return "Invalid API key. Please check your credentials."
        elif status_code == 429:
            return "Rate limit exceeded. Please try again later."
        elif status_code == 400:
            return "Bad request. Please check your input parameters."
        elif status_code == 500:
            return "Internal server error. Please try again later."
        elif "timeout" in error_lower:
            return "Request timeout. Please try again."
        elif "connection" in error_lower:
            return "Connection error. Please check your network."
        else:
            return f"API Error: {error_message}"