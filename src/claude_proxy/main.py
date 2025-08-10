"""Claude API Proxy - Main FastAPI application."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from .config import get_settings
from .models.claude import (
    ClaudeMessagesRequest,
    ClaudeMessagesResponse,
    ClaudeTokenCountRequest,
    ClaudeTokenCountResponse,
)
# from .providers.anthropic import AnthropicProvider  # Not used currently
from .providers.openai import OpenAIProvider
from .utils import (
    extract_api_key_from_headers,
    extract_proxy_auth_key,
    generate_request_id,
    get_current_timestamp,
    setup_logging,
    validate_api_key,
)

# Initialize settings
settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Claude API Proxy starting up...")
    logger.info(f"   Server: {settings.host}:{settings.port}")
    logger.info(f"   Target API: {settings.openai_base_url}")
    logger.info(f"   Big Model: {settings.big_model}")
    logger.info(f"   Small Model: {settings.small_model}")
    logger.info(f"   API Key Validation: {'Enabled' if settings.auth_key else 'Disabled'}")
    logger.info(f"   Mode: {'Fixed API Key' if settings.openai_api_key else 'Passthrough'}")
    yield
    logger.info("👋 Claude API Proxy shutting down...")


# Create FastAPI app
app = FastAPI(
    title="Claude API Proxy",
    description="A production-ready Claude API proxy server",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_provider(client_api_key: Optional[str] = None) -> OpenAIProvider:
    """Get the configured LLM provider with automatic passthrough mode."""
    # Simple logic: if OPENAI_API_KEY is set, use it; otherwise use client's key
    if settings.openai_api_key:
        # Use configured API key
        api_key = settings.openai_api_key
    else:
        # Passthrough mode: use client's API key
        if not client_api_key:
            raise HTTPException(
                status_code=500,
                detail="No API key available. Either set OPENAI_API_KEY or provide API key in request."
            )
        api_key = client_api_key
    
    return OpenAIProvider(
        api_key=api_key,
        base_url=settings.openai_base_url,
        timeout=settings.request_timeout
    )


async def validate_client_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """
    Validate proxy access permissions and return API key for provider.
    
    In Fixed API Key Mode: validates proxy auth and returns server's API key.
    In Passthrough Mode: no proxy auth, returns client's API key.
    """
    headers = dict(request.headers)
    
    # Step 1: Proxy authentication (Fixed API Key Mode only)
    if settings.auth_key:
        proxy_auth_key = extract_proxy_auth_key(headers)
        if not validate_api_key(proxy_auth_key, settings.auth_key):
            logger.warning("Invalid proxy authentication key provided by client")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key. Please provide a valid proxy authentication key."
            )
    
    # Step 2: Extract API key for provider
    client_api_key = extract_api_key_from_headers(headers)
    
    # Return the key to use for provider calls
    return client_api_key


@app.post("/v1/messages", response_model=ClaudeMessagesResponse)
async def create_message(
    request: ClaudeMessagesRequest,
    http_request: Request,
    client_key: Optional[str] = Depends(validate_client_api_key)  # API key validation
):
    """Handle Claude API /v1/messages requests."""
    request_id = generate_request_id()
    
    logger.info(
        f"Processing request {request_id}: model={request.model}, "
        f"stream={request.stream}, max_tokens={request.max_tokens}"
    )
    
    try:
        # Check if client disconnected
        if await http_request.is_disconnected():
            raise HTTPException(status_code=499, detail="Client disconnected")
        
        # Create provider with client API key (automatic passthrough mode)
        provider = get_provider(client_key)
        
        if request.stream:
            # For streaming, we need to keep the provider open during the entire response
            # The provider will be closed when the generator is exhausted
            async def stream_with_cleanup():
                async with provider:
                    async for chunk in provider.stream_complete(request, request_id):
                        yield chunk
            
            return StreamingResponse(
                stream_with_cleanup(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                }
            )
        else:
            # Non-streaming response
            async with provider:
                response = await provider.complete(request, request_id)
                logger.info(f"Request {request_id} completed successfully")
                return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request {request_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/messages/count_tokens", response_model=ClaudeTokenCountResponse)
async def count_tokens(
    request: ClaudeTokenCountRequest,
    _: str = Depends(validate_client_api_key)  # API key validation
):
    """Handle token counting requests."""
    try:
        total_chars = 0
        
        # Count system message characters
        if request.system:
            if isinstance(request.system, str):
                total_chars += len(request.system)
            elif isinstance(request.system, list):
                for block in request.system:
                    if isinstance(block, dict) and "text" in block:
                        total_chars += len(block["text"])
        
        # Count message characters
        for msg in request.messages:
            if isinstance(msg.content, str):
                total_chars += len(msg.content)
            elif isinstance(msg.content, list):
                for block in msg.content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        total_chars += len(block.get("text", ""))
                    elif hasattr(block, "text"):
                        total_chars += len(block.text)
        
        # Rough estimation: 4 characters per token
        estimated_tokens = max(1, total_chars // 4)
        
        return ClaudeTokenCountResponse(input_tokens=estimated_tokens)
    
    except Exception as e:
        logger.error(f"Token counting failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": get_current_timestamp(),
        "version": "0.1.0",
        "config": {
            "openai_api_configured": bool(settings.openai_api_key),
            "api_key_validation": bool(settings.auth_key),
            "big_model": settings.big_model,
            "small_model": settings.small_model,
            "max_tokens_limit": settings.max_tokens_limit,
        }
    }


@app.get("/test-connection") 
async def test_connection():
    """Test connectivity to the target API."""
    try:
        from .models.claude import ClaudeMessage, ClaudeMessagesRequest
        
        test_request = ClaudeMessagesRequest(
            model="claude-3-5-haiku-20241022",
            max_tokens=5,
            messages=[ClaudeMessage(role="user", content="Hello")]
        )
        
        # Create provider (no passthrough for test)
        provider = get_provider()
        
        async with provider:
            await provider.complete(test_request, "test-connection")
        
        return {
            "status": "success",
            "message": "Successfully connected to target API",
            "model_used": settings.small_model,
            "timestamp": get_current_timestamp(),
        }
    
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "failed",
                "error": str(e),
                "timestamp": get_current_timestamp(),
                "suggestions": [
                    "Check your OPENAI_API_KEY is valid",
                    "Verify API key permissions",
                    "Check rate limits and quotas"
                ]
            }
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Claude API Proxy v0.1.0",
        "status": "running",
        "config": {
            "openai_base_url": settings.openai_base_url,
            "max_tokens_limit": settings.max_tokens_limit,
            "api_key_configured": bool(settings.openai_api_key),
            "api_key_validation": bool(settings.auth_key),
            "big_model": settings.big_model,
            "small_model": settings.small_model,
        },
        "endpoints": {
            "messages": "/v1/messages",
            "count_tokens": "/v1/messages/count_tokens",
            "health": "/health",
            "test_connection": "/test-connection",
        }
    }


def main():
    """Main entry point for simple testing and development."""
    print("🚀 Starting Claude API Proxy...")
    print(f"📡 Server will start at http://{settings.host}:{settings.port}")
    print("💡 For production use, please use: uvicorn claude_proxy.main:app --host 0.0.0.0 --port 8085")
    print()
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()