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
    
    @staticmethod
    def get_claude_model_mapping(big_model: str, small_model: str) -> Dict[str, str]:
        """Get Claude to target model mapping."""
        return {
            # Claude Haiku models -> Small model
            "claude-3-haiku": small_model,
            "claude-3-haiku-20240307": small_model,
            "claude-3-5-haiku": small_model,
            "claude-3-5-haiku-20241022": small_model,
            
            # Claude Sonnet models -> Big model
            "claude-3-sonnet": big_model,
            "claude-3-sonnet-20240229": big_model,
            "claude-3-5-sonnet": big_model,
            "claude-3-5-sonnet-20241022": big_model,
            "claude-3-7-sonnet": big_model,
            "claude-3-7-sonnet-20250219": big_model,
            
            # Claude Opus models -> Big model
            "claude-3-opus": big_model,
            "claude-3-opus-20240229": big_model,
            
            # Claude 4 models -> Big model
            "claude-sonnet-4": big_model,
            "claude-sonnet-4-20250514": big_model,
            "claude-opus-4": big_model,
            "claude-opus-4-20250514": big_model,
            "claude-opus-4-1": big_model,
            "claude-opus-4-1-20250805": big_model,
        }
    
    @staticmethod
    def map_claude_model(claude_model: str, big_model: str, small_model: str) -> str:
        """Map Claude model name to target provider model."""
        model_mapping = BaseProvider.get_claude_model_mapping(big_model, small_model)
        
        # Direct mapping
        if claude_model in model_mapping:
            return model_mapping[claude_model]
        
        # Fuzzy matching for model families
        if "haiku" in claude_model.lower():
            return small_model
        elif any(x in claude_model.lower() for x in ["sonnet", "opus"]):
            return big_model
        
        # Default to user-specified model
        return big_model
    
    @staticmethod
    def guess_claude_model(provider_model: Optional[str], big_model: str, small_model: str) -> str:
        """Guess Claude model from provider model response.
        
        This is used when converting responses back to Claude format.
        It provides a reverse mapping from provider models to Claude models.
        
        Args:
            provider_model: The model name returned by the provider (e.g., "gpt-4o")
            big_model: The configured big model name
            small_model: The configured small model name
            
        Returns:
            A Claude model name for compatibility
            
        Note:
            Returns legacy model names for backward compatibility with tests.
            The actual model used for requests supports all latest Claude models.
        """
        if not provider_model:
            return "claude-3-haiku-20240307"  # Default fallback for compatibility
        
        # Reverse mapping from provider models to Claude models
        if provider_model == big_model:
            return "claude-3-opus-20240229"  # Default big model for compatibility
        elif provider_model == small_model:
            return "claude-3-haiku-20240307"  # Default small model for compatibility
        else:
            # For custom/unknown models, default to haiku
            return "claude-3-haiku-20240307"