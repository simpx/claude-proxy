"""Utility functions for Claude API Proxy."""

import logging
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


def setup_logging(log_level: str = "INFO") -> None:
    """Setup application logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


def get_current_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"


def extract_api_key_from_headers(headers: Dict[str, Any]) -> Optional[str]:
    """
    Extract API key from request headers for forwarding to provider.
    Priority: x-api-key > Authorization Bearer
    """
    # Check x-api-key header (Claude style)
    if api_key := headers.get("x-api-key"):
        return api_key
    
    # Check Authorization header (OpenAI style)
    auth_header = headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    return None


def extract_proxy_auth_key(headers: Dict[str, Any]) -> Optional[str]:
    """
    Extract proxy authentication key from request headers.
    This is only used for proxy access control (Fixed API Key Mode only).
    Priority: x-api-key > Authorization Bearer
    """
    # Check x-api-key header first
    if auth_key := headers.get("x-api-key"):
        return auth_key
    
    # Fallback to Authorization header
    auth_header = headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    return None


def validate_api_key(client_key: Optional[str], expected_key: Optional[str]) -> bool:
    """Validate client API key against expected key."""
    if expected_key is None:
        # No validation required if no expected key is set
        return True
    
    if client_key is None:
        return False
        
    return client_key == expected_key


def classify_error(error_message: str) -> str:
    """Classify and format error messages."""
    error_lower = error_message.lower()
    
    if "timeout" in error_lower:
        return "Request timeout. Please try again."
    elif "connection" in error_lower:
        return "Connection error. Please check your network."
    elif "api key" in error_lower or "unauthorized" in error_lower:
        return "Invalid API key. Please check your credentials."
    elif "rate limit" in error_lower:
        return "Rate limit exceeded. Please try again later."
    elif "quota" in error_lower:
        return "Quota exceeded. Please check your usage limits."
    else:
        return "An error occurred while processing your request."