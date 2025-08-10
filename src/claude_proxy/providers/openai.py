"""OpenAI provider implementation."""

import json
import time
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import httpx

from ..config import map_claude_model, get_settings
from ..models.claude import (
    ClaudeMessage,
    ClaudeMessagesRequest,
    ClaudeMessagesResponse,
    ClaudeTextContent,
    ClaudeToolUseContent,
    ClaudeToolResultContent,
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
            
            # Check if this message contains tool_use content (assistant with tool calls)
            has_tool_use = False
            tool_calls = []
            
            # Check if this message contains tool_result content (user with tool results)  
            has_tool_results = False
            
            if isinstance(msg.content, str):
                openai_msg["content"] = msg.content
            elif isinstance(msg.content, list):
                # Handle multi-modal content and tool calls
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
                        elif part.get("type") == "tool_use":
                            # Convert Claude tool_use to OpenAI tool_calls
                            has_tool_use = True
                            tool_calls.append({
                                "id": part.get("id", ""),
                                "type": "function",
                                "function": {
                                    "name": part.get("name", ""),
                                    "arguments": json.dumps(part.get("input", {}))
                                }
                            })
                        elif part.get("type") == "tool_result":
                            # Convert Claude tool_result to OpenAI format
                            has_tool_results = True
                            tool_result_content = part.get("content", "")
                            if isinstance(tool_result_content, list):
                                # Extract text from content list
                                text_content = ""
                                for item in tool_result_content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_content += item.get("text", "")
                                tool_result_content = text_content
                            
                            content_parts.append({
                                "type": "text",
                                "text": str(tool_result_content)
                            })
                    elif hasattr(part, "type") and hasattr(part, "text"):
                        # Handle Pydantic models
                        if part.type == "text":
                            content_parts.append({
                                "type": "text", 
                                "text": part.text
                            })
                        elif part.type == "tool_use":
                            # Handle Pydantic tool_use models
                            has_tool_use = True
                            tool_calls.append({
                                "id": part.id,
                                "type": "function",
                                "function": {
                                    "name": part.name,
                                    "arguments": json.dumps(part.input)
                                }
                            })
                    elif hasattr(part, "type"):
                        # Handle Pydantic models without text attribute
                        if part.type == "tool_use":
                            has_tool_use = True
                            tool_calls.append({
                                "id": part.id,
                                "type": "function", 
                                "function": {
                                    "name": part.name,
                                    "arguments": json.dumps(part.input)
                                }
                            })
                        elif part.type == "tool_result":
                            # Handle Pydantic tool_result models  
                            has_tool_results = True
                            result_content = part.content
                            if isinstance(result_content, list):
                                text_content = ""
                                for item in result_content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_content += item.get("text", "")
                                result_content = text_content
                            
                            content_parts.append({
                                "type": "text",
                                "text": str(result_content)
                            })
                
                # Set message content and tool_calls
                if has_tool_use:
                    # Assistant message with tool calls
                    openai_msg["tool_calls"] = tool_calls
                    # For assistant messages with tool calls, content should be null or text-only
                    text_parts = [part for part in content_parts if part.get("type") == "text"]
                    if text_parts and text_parts[0].get("text"):
                        openai_msg["content"] = text_parts[0]["text"]
                    else:
                        openai_msg["content"] = None
                elif has_tool_results:
                    # Handle tool_result messages - convert each to separate tool message
                    for part in msg.content:
                        if isinstance(part, dict) and part.get("type") == "tool_result":
                            tool_result_content = part.get("content", "")
                            if isinstance(tool_result_content, list):
                                # Extract text from content list
                                text_content = ""
                                for item in tool_result_content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_content += item.get("text", "")
                                tool_result_content = text_content
                            
                            # Create separate tool message
                            tool_msg = {
                                "role": "tool",
                                "content": str(tool_result_content),
                                "tool_call_id": part.get("tool_use_id", "unknown")
                            }
                            messages.append(tool_msg)
                        elif hasattr(part, "type") and part.type == "tool_result":
                            # Handle Pydantic tool_result models
                            result_content = part.content
                            if isinstance(result_content, list):
                                text_content = ""
                                for item in result_content:
                                    if isinstance(item, dict) and item.get("type") == "text":
                                        text_content += item.get("text", "")
                                result_content = text_content
                            
                            # Create separate tool message
                            tool_msg = {
                                "role": "tool", 
                                "content": str(result_content),
                                "tool_call_id": part.tool_use_id
                            }
                            messages.append(tool_msg)
                    # Skip the original user message since we've converted tool_results to tool messages
                    continue
                else:
                    # Regular content
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
        
        # Handle tools
        if request.tools and self._should_include_tools(request.tools):
            openai_request["tools"] = self._convert_tools(request.tools)
        if request.tool_choice and request.tools:
            openai_request["tool_choice"] = self._convert_tool_choice(request.tool_choice)
            
        return openai_request
    
    def convert_response(
        self, 
        response: Dict[str, Any], 
        original_request: Optional[ClaudeMessagesRequest] = None
    ) -> ClaudeMessagesResponse:
        """Convert OpenAI response to Claude format."""
        choice = response["choices"][0]
        message = choice["message"]
        
        # Convert content
        content = []
        # Only add text content if it's not empty
        if message.get("content") and message["content"].strip():
            content.append(ClaudeTextContent(text=message["content"]))
        
        # Handle tool calls
        if tool_calls := message.get("tool_calls"):
            for tool_call in tool_calls:
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}
                    
                content.append(ClaudeToolUseContent(
                    id=tool_call["id"],
                    name=tool_call["function"]["name"],
                    input=arguments
                ))
        
        # Convert usage
        usage_data = response.get("usage", {})
        usage = ClaudeUsage(
            input_tokens=usage_data.get("prompt_tokens", 0),
            output_tokens=usage_data.get("completion_tokens", 0)
        )
        
        # Determine model from original request or guess from response
        settings = get_settings()
        model = original_request.model if original_request else BaseProvider.guess_claude_model(
            response.get("model"), 
            settings.big_model, 
            settings.small_model
        )
        
        return ClaudeMessagesResponse(
            id=response["id"],
            model=model,
            content=content,
            stop_reason=self._convert_finish_reason(choice.get("finish_reason")),
            usage=usage
        )
    
    def _should_include_tools(self, tools: List[Dict[str, Any]]) -> bool:
        """Determine if tools should be included in the request to avoid compatibility issues."""
        if not tools:
            return False
        
        logging.debug(f"Converting {len(tools)} Claude tools to OpenAI format")
        
        # Always try to include tools, but convert them properly
        return True
    
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert Claude tools format to OpenAI tools format."""
        openai_tools = []
        
        for tool in tools:
            # Convert Claude tool format to OpenAI format
            # Claude: {"name": "...", "description": "...", "input_schema": {...}}
            # OpenAI: {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
            
            if not isinstance(tool, dict):
                logging.warning(f"Skipping non-dict tool: {tool}")
                continue
                
            if "name" not in tool:
                logging.warning(f"Skipping tool without name: {tool}")
                continue
            
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                }
            }
            
            # Convert input_schema to parameters
            if "input_schema" in tool and isinstance(tool["input_schema"], dict):
                # Remove Claude-specific fields from schema
                parameters = dict(tool["input_schema"])
                # Remove $schema as it's not needed in OpenAI format
                parameters.pop("$schema", None)
                openai_tool["function"]["parameters"] = parameters
            else:
                # Provide empty parameters if no schema
                openai_tool["function"]["parameters"] = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            
            openai_tools.append(openai_tool)
        
        logging.debug(f"Successfully converted {len(tools)} Claude tools to {len(openai_tools)} OpenAI tools")
        return openai_tools
    
    def _convert_tool_choice(self, tool_choice: Dict[str, Any]) -> Union[str, Dict[str, Any]]:
        """Convert Claude tool_choice format to OpenAI format."""
        if not tool_choice:
            return "auto"
        
        # Claude format: {"type": "auto"} or {"type": "tool", "name": "function_name"}
        # OpenAI format: "auto", "none", or {"type": "function", "function": {"name": "function_name"}}
        
        if isinstance(tool_choice, dict):
            choice_type = tool_choice.get("type", "auto")
            
            if choice_type == "auto":
                return "auto"
            elif choice_type == "none":
                return "none"
            elif choice_type == "tool" and "name" in tool_choice:
                # Convert specific tool choice
                return {
                    "type": "function",
                    "function": {
                        "name": tool_choice["name"]
                    }
                }
        
        # Default to auto
        return "auto"
    
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
        logging.info(f"=== NON-STREAMING REQUEST START [{request_id}] ===")
        logging.info(f"Original Claude request: {request.model_dump()}")
        openai_request = self.convert_request(request)
        logging.info(f"Converted OpenAI request: {openai_request}")
        logging.info(f"=== NON-STREAMING REQUEST END [{request_id}] ===")
        
        # Log the exact URL and headers being used
        url = f"{self.base_url}/chat/completions"
        headers = self.get_headers()
        logging.debug(f"Request URL: {url}")
        logging.debug(f"Request headers: {headers}")
        logging.debug(f"Base URL: {self.base_url}")
        logging.debug(f"Client base URL: {self.client.base_url}")
        
        try:
            logging.debug(f"About to send POST request to: {url}")
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=openai_request,
                headers=self.get_headers()
            )
            logging.debug(f"HTTP response received: {response.status_code}")
            logging.debug(f"Response headers: {response.headers}")
            response.raise_for_status()
            response_data = response.json()
            logging.debug(f"Response data: {response_data}")
            claude_response = self.convert_response(response_data, request)
            logging.info(f"=== NON-STREAMING RESPONSE START [{request_id}] ===")
            logging.info(f"OpenAI response data: {response_data}")
            logging.info(f"Final Claude response: {claude_response.model_dump()}")
            logging.info(f"=== NON-STREAMING RESPONSE END [{request_id}] ===")
            return claude_response
            
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTPStatusError occurred: {e.response.status_code}, {str(e)}")
            logging.error(f"Response text: {e.response.text}")
            logging.error(f"Request URL was: {e.request.url}")
            logging.error(f"Request headers were: {e.request.headers}")
            error_msg = self.classify_error(str(e), e.response.status_code)
            raise Exception(error_msg) from e
        except Exception as e:
            logging.error(f"General exception occurred: {str(e)}")
            error_msg = self.classify_error(str(e))
            raise Exception(error_msg) from e
            
    
    async def stream_complete(
        self, 
        request: ClaudeMessagesRequest,
        request_id: str
    ) -> AsyncGenerator[str, None]:
        """Stream a completion request."""
        logging.info(f"=== STREAMING REQUEST START [{request_id}] ===")
        logging.info(f"Original Claude request: {request.model_dump()}")
        openai_request = self.convert_request(request)
        logging.info(f"Converted OpenAI request: {openai_request}")
        logging.info(f"=== STREAMING REQUEST END [{request_id}] ===")
        openai_request["stream"] = True
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json=openai_request,
                headers=self.get_headers()
            ) as response:
                logging.debug(f"Streaming HTTP response status: {response.status_code}")
                response.raise_for_status()
                
                input_tokens = 0
                tool_calls_accumulator = {}  # Track tool calls across chunks
                has_text_content = False
                has_tool_content = False
                text_block_started = False
                
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
                        "usage": {"input_tokens": input_tokens, "output_tokens": 0}
                    }
                }
                start_event_str = f"event: message_start\ndata: {json.dumps(start_event)}\n\n"
                logging.info(f"[{request_id}] STREAMING RESPONSE: {start_event_str.strip()}")
                yield start_event_str
                async for line in response.aiter_lines():
                    logging.debug(f"Streaming line received: {line}")
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        if data.strip() == "[DONE]":
                            logging.debug("Streaming completed with [DONE] signal.")
                            break
                        
                        try:
                            chunk = json.loads(data)
                            logging.debug(f"Parsed chunk: {chunk}")
                            
                            # Check if chunk has choices array
                            if not chunk.get("choices") or not isinstance(chunk["choices"], list):
                                logging.debug("Chunk has no choices array, skipping")
                                continue
                                
                            choice = chunk["choices"][0] if len(chunk["choices"]) > 0 else None
                            if not choice or not isinstance(choice, dict):
                                logging.debug("Choice is None, empty, or not a dict, skipping")
                                continue
                                
                            delta = choice.get("delta", {}) if choice else {}
                            
                            if chunk.get("usage") and isinstance(chunk["usage"], dict):
                                input_tokens = chunk["usage"].get("prompt_tokens", input_tokens)
                            
                            # Handle text content deltas
                            if content := delta.get("content"):
                                if not text_block_started:
                                    # Send text content_block_start event
                                    block_start_event = {
                                        "type": "content_block_start",
                                        "index": 0,
                                        "content_block": {
                                            "type": "text",
                                            "text": ""
                                        }
                                    }
                                    yield f"event: content_block_start\ndata: {json.dumps(block_start_event)}\n\n"
                                    text_block_started = True
                                    
                                has_text_content = True
                                delta_event = {
                                    "type": "content_block_delta",
                                    "index": 0,
                                    "delta": {
                                        "type": "text_delta",
                                        "text": content
                                    }
                                }
                                delta_event_str = f"event: content_block_delta\ndata: {json.dumps(delta_event)}\n\n"
                                logging.info(f"[{request_id}] STREAMING RESPONSE: {delta_event_str.strip()}")
                                yield delta_event_str
                            
                            # Handle tool calls in streaming
                            if tool_calls := delta.get("tool_calls"):
                                for tool_call in tool_calls:
                                    call_index = tool_call.get("index", 0)
                                    call_id = tool_call.get("id", "")
                                    
                                    # Initialize tool call if we haven't seen it
                                    if call_index not in tool_calls_accumulator:
                                        tool_calls_accumulator[call_index] = {
                                            "id": call_id,
                                            "name": "",
                                            "arguments": "",
                                            "started": False
                                        }
                                        
                                    acc = tool_calls_accumulator[call_index]
                                    
                                    # Update ID if provided
                                    if call_id:
                                        acc["id"] = call_id
                                    
                                    # Handle function info
                                    if func := tool_call.get("function"):
                                        # Update function name if provided
                                        if name := func.get("name"):
                                            acc["name"] = name
                                            
                                        # Update arguments if provided
                                        if args := func.get("arguments"):
                                            acc["arguments"] += args
                                    
                                    # Send content_block_start if this is the first time we see this tool call with a name
                                    if acc["name"] and not acc["started"]:
                                        content_index = 1 if has_text_content else 0
                                        tool_start_event = {
                                            "type": "content_block_start",
                                            "index": content_index,
                                            "content_block": {
                                                "type": "tool_use",
                                                "id": acc["id"],
                                                "name": acc["name"],
                                                "input": {}
                                            }
                                        }
                                        tool_start_event_str = f"event: content_block_start\ndata: {json.dumps(tool_start_event)}\n\n"
                                        logging.info(f"[{request_id}] STREAMING RESPONSE: {tool_start_event_str.strip()}")
                                        yield tool_start_event_str
                                        acc["started"] = True
                                        has_tool_content = True
                                        
                                    # Send arguments delta if we have new arguments
                                    if func and func.get("arguments"):
                                        content_index = 1 if has_text_content else 0
                                        tool_delta_event = {
                                            "type": "content_block_delta",
                                            "index": content_index,
                                            "delta": {
                                                "type": "input_json_delta",
                                                "partial_json": func["arguments"]
                                            }
                                        }
                                        yield f"event: content_block_delta\ndata: {json.dumps(tool_delta_event)}\n\n"
                            
                            if choice and choice.get("finish_reason"):
                                usage_info = chunk.get("usage", {}) if chunk.get("usage") and isinstance(chunk.get("usage"), dict) else {}
                                output_tokens = usage_info.get("completion_tokens", 0)
                                
                                # Send content_block_stop events for any active blocks
                                if has_tool_content:
                                    content_index = 1 if has_text_content else 0
                                    tool_stop_event = {
                                        "type": "content_block_stop",
                                        "index": content_index
                                    }
                                    yield f"event: content_block_stop\ndata: {json.dumps(tool_stop_event)}\n\n"
                                
                                if has_text_content:
                                    block_stop_event = {
                                        "type": "content_block_stop",
                                        "index": 0
                                    }
                                    yield f"event: content_block_stop\ndata: {json.dumps(block_stop_event)}\n\n"
                                
                                # Send message_delta event
                                stop_event = {
                                    "type": "message_delta",
                                    "delta": {
                                        "stop_reason": self._convert_finish_reason(choice.get("finish_reason")),
                                        "stop_sequence": None
                                    },
                                    "usage": {
                                        "output_tokens": output_tokens
                                    }
                                }
                                yield f"event: message_delta\ndata: {json.dumps(stop_event)}\n\n"
                                
                                stop_event = {"type": "message_stop"}
                                stop_event_str = f"event: message_stop\ndata: {json.dumps(stop_event)}\n\n"
                                logging.info(f"[{request_id}] STREAMING RESPONSE: {stop_event_str.strip()}")
                                logging.info(f"=== STREAMING COMPLETE [{request_id}] ===")
                                yield stop_event_str
                                break
                        except json.JSONDecodeError as e:
                            logging.error(f"JSONDecodeError occurred: {str(e)}")
                            continue
                            
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTPStatusError occurred during streaming: {e.response.status_code}, {str(e)}")
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
            logging.error(f"General exception occurred during streaming: {str(e)}")
            error_msg = self.classify_error(str(e))
            error_event = {
                "type": "error",
                "error": {
                    "type": "api_error", 
                    "message": error_msg
                }
            }
            yield f"event: error\ndata: {json.dumps(error_event)}\n\n"