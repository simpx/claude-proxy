"""Anthropic provider implementation (pass-through adapter)."""

import json
from typing import Any, AsyncGenerator, Dict

import httpx

from ..models.claude import ClaudeMessagesRequest, ClaudeMessagesResponse

from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic API provider (direct pass-through)."""
    
    def __init__(self, api_key: str, timeout: int = 90):
        """Initialize Anthropic provider."""
        super().__init__(
            api_key=api_key,
            base_url="https://api.anthropic.com",
            timeout=timeout
        )
    
    def convert_request(self, request: ClaudeMessagesRequest) -> Dict[str, Any]:
        """Convert request (no conversion needed for Anthropic)."""
        return request.model_dump(exclude_none=True)
    
    def convert_response(
        self, 
        response: Dict[str, Any], 
        original_request: ClaudeMessagesRequest
    ) -> ClaudeMessagesResponse:
        """Convert response (no conversion needed for Anthropic)."""
        return ClaudeMessagesResponse(**response)
    
    def get_headers(self, api_key: str = None) -> Dict[str, str]:
        """Get Anthropic-specific headers."""
        key = api_key or self.api_key
        return {
            "x-api-key": key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "User-Agent": "claude-proxy/0.1.0"
        }
    
    async def complete(
        self, 
        request: ClaudeMessagesRequest,
        request_id: str
    ) -> ClaudeMessagesResponse:
        """Complete a non-streaming request."""
        anthropic_request = self.convert_request(request)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/v1/messages",
                json=anthropic_request,
                headers=self.get_headers()
            )
            response.raise_for_status()
            response_data = response.json()
            return self.convert_response(response_data, request)
            
        except httpx.HTTPStatusError as e:
            error_msg = self.classify_error(str(e), e.response.status_code)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = self.classify_error(str(e))
            raise Exception(error_msg) from e
    
    async def stream_complete(
        self, 
        request: ClaudeMessagesRequest,
        request_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream a completion request."""
        anthropic_request = self.convert_request(request)
        anthropic_request["stream"] = True
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                json=anthropic_request,
                headers=self.get_headers()
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip():
                            yield f"data: {data}\n\n"
                    elif line.startswith("event: "):
                        event = line[7:]  # Remove "event: " prefix
                        yield f"event: {event}\n"
                        
        except httpx.HTTPStatusError as e:
            error_msg = self.classify_error(str(e), e.response.status_code)
            error_event = {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": error_msg
                }
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
        except Exception as e:
            error_msg = self.classify_error(str(e))
            error_event = {
                "type": "error",
                "error": {
                    "type": "api_error",
                    "message": error_msg
                }
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"