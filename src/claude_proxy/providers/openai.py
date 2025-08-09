"""OpenAI provider implementation."""

import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

from ..config import map_claude_model
from ..models.claude import (
    ClaudeMessage,
    ClaudeMessagesRequest,
    ClaudeMessagesResponse,
    ClaudeTextContent,
    ClaudeUsage,
)
from ..models.openai import OpenAIMessage, OpenAIMessagesRequest
from ..utils import generate_request_id, get_current_timestamp

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI API provider."""
    
    def convert_request(self, request: ClaudeMessagesRequest) -> Dict[str, Any]:
        """Convert Claude request to OpenAI format."""
        messages = []
        
        # Add system message if present
        if request.system:
            system_content = request.system
            if isinstance(system_content, list):
                # Convert system blocks to string
                system_text = ""
                for block in system_content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        system_text += block.get("text", "")
                system_content = system_text
            
            messages.append({
                "role": "system",
                "content": system_content
            })
        
        # Convert Claude messages to OpenAI format
        for msg in request.messages:
            openai_msg = {"role": msg.role}
            
            if isinstance(msg.content, str):
                openai_msg["content"] = msg.content
            elif isinstance(msg.content, list):
                # Handle multi-modal content
                content_parts = []
                for part in msg.content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            content_parts.append({
                                "type": "text",
                                "text": part.get("text", "")
                            })
                        elif part.get("type") == "image":
                            # Convert Claude image format to OpenAI
                            source = part.get("source", {})
                            if source.get("type") == "base64":
                                content_parts.append({
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{source.get('media_type', 'image/jpeg')};base64,{source.get('data', '')}"
                                    }
                                })
                    elif hasattr(part, "type") and hasattr(part, "text"):
                        # Handle Pydantic models
                        if part.type == "text":
                            content_parts.append({
                                "type": "text", 
                                "text": part.text
                            })
                
                openai_msg["content"] = content_parts if content_parts else ""
            
            messages.append(openai_msg)
        
        # Build OpenAI request
        openai_request = {
            "model": map_claude_model(request.model),
            "messages": messages,
            "max_tokens": request.max_tokens,
            "stream": request.stream or False
        }
        
        # Add optional parameters
        if request.temperature is not None:
            openai_request["temperature"] = request.temperature
        if request.top_p is not None:
            openai_request["top_p"] = request.top_p
        if request.stop_sequences:
            openai_request["stop"] = request.stop_sequences
        if request.tools:
            openai_request["tools"] = request.tools
        if request.tool_choice:
            openai_request["tool_choice"] = request.tool_choice
            
        return openai_request
    
    def convert_response(
        self, 
        response: Dict[str, Any], 
        original_request: ClaudeMessagesRequest
    ) -> ClaudeMessagesResponse:
        """Convert OpenAI response to Claude format."""
        choice = response["choices"][0]
        message = choice["message"]
        
        # Convert content
        content = []
        if message.get("content"):
            content.append(ClaudeTextContent(text=message["content"]))
        
        # Handle tool calls
        if tool_calls := message.get("tool_calls"):
            for tool_call in tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tool_call["id"],
                    "name": tool_call["function"]["name"],
                    "input": json.loads(tool_call["function"]["arguments"])
                })
        
        # Convert usage
        usage_data = response.get("usage", {})
        usage = ClaudeUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0)
        )
        
        return ClaudeMessagesResponse(
            id=response["id"],
            model=original_request.model,
            content=content,
            stop_reason=self._convert_finish_reason(choice.get("finish_reason")),
            usage=usage
        )
    
    def _convert_finish_reason(self, openai_reason: Optional[str]) -> Optional[str]:
        """Convert OpenAI finish reason to Claude format."""
        if openai_reason is None:
            return None
        
        mapping = {
            "stop": "end_turn",
            "length": "max_tokens",
            "function_call": "tool_use",
            "tool_calls": "tool_use",
            "content_filter": "stop_sequence"
        }
        return mapping.get(openai_reason, "end_turn")
    
    async def complete(
        self, 
        request: ClaudeMessagesRequest,
        request_id: str
    ) -> ClaudeMessagesResponse:
        """Complete a non-streaming request."""
        openai_request = self.convert_request(request)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=openai_request,
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
        openai_request = self.convert_request(request)
        openai_request["stream"] = True
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=openai_request,
                headers=self.get_headers()
            ) as response:
                response.raise_for_status()
                
                # Send initial message_start event
                start_event = {
                    "type": "message_start",
                    "message": {
                        "id": f"msg_{generate_request_id()}",
                        "type": "message",
                        "role": "assistant",
                        "model": request.model,
                        "content": [],
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0}
                    }
                }
                yield f"event: message_start\ndata: {json.dumps(start_event)}\n\n"
                
                # Send content_block_start event
                block_start_event = {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "text",
                        "text": ""
                    }
                }
                yield f"event: content_block_start\ndata: {json.dumps(block_start_event)}\n\n"
                
                total_tokens = 0
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip() == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            choice = chunk["choices"][0]
                            delta = choice.get("delta", {})
                            
                            if content := delta.get("content"):
                                # Send content delta
                                delta_event = {
                                    "type": "content_block_delta",
                                    "index": 0,
                                    "delta": {
                                        "type": "text_delta",
                                        "text": content
                                    }
                                }
                                yield f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n"
                                total_tokens += len(content.split())  # Rough token count
                            
                            if choice.get("finish_reason"):
                                # Send content_block_stop event
                                block_stop_event = {
                                    "type": "content_block_stop",
                                    "index": 0
                                }
                                yield f"event: content_block_stop\ndata: {json.dumps(block_stop_event)}\n\n"
                                
                                # Send message_stop event
                                stop_event = {
                                    "type": "message_delta",
                                    "delta": {
                                        "stop_reason": self._convert_finish_reason(choice["finish_reason"]),
                                        "stop_sequence": None
                                    },
                                    "usage": {
                                        "output_tokens": total_tokens
                                    }
                                }
                                yield f"event: message_delta\ndata: {json.dumps(stop_event)}\n\n"
                                
                                stop_event = {"type": "message_stop"}
                                yield f"event: message_stop\ndata: {json.dumps(stop_event)}\n\n"
                                break
                        except json.JSONDecodeError:
                            continue
                            
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