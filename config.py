"""Configuration management for Claude API Proxy."""

import os
from typing import Dict, Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8082, description="Server port")
    log_level: str = Field(default="INFO", description="Log level")
    
    # Model mapping
    big_model: str = Field(default="gpt-4o", description="Model for Claude Opus/Sonnet")
    small_model: str = Field(default="gpt-4o-mini", description="Model for Claude Haiku")
    
    # Provider settings
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", 
        description="OpenAI API base URL"
    )
    
    # Request settings
    max_tokens_limit: int = Field(default=4096, description="Maximum tokens limit")
    request_timeout: int = Field(default=90, description="Request timeout in seconds")
    
    # Optional API key validation
    anthropic_api_key: Optional[str] = Field(
        default=None, 
        description="Expected Anthropic API key for validation"
    )
    
    model_config = {"env_file": ".env", "case_sensitive": False}


def get_model_mapping() -> Dict[str, str]:
    """Get Claude to target model mapping."""
    settings = get_settings()
    return {
        # Claude Haiku models -> Small model
        "claude-3-haiku": settings.small_model,
        "claude-3-haiku-20240307": settings.small_model,
        
        # Claude Sonnet/Opus models -> Big model  
        "claude-3-sonnet": settings.big_model,
        "claude-3-sonnet-20240229": settings.big_model,
        "claude-3-5-sonnet": settings.big_model,
        "claude-3-5-sonnet-20241022": settings.big_model,
        "claude-3-opus": settings.big_model,
        "claude-3-opus-20240229": settings.big_model,
        
        # Claude 4 models
        "claude-sonnet-4-20250514": settings.big_model,
    }


def map_claude_model(claude_model: str) -> str:
    """Map Claude model name to target provider model."""
    model_mapping = get_model_mapping()
    
    # Direct mapping
    if claude_model in model_mapping:
        return model_mapping[claude_model]
    
    # Fuzzy matching for model families
    if "haiku" in claude_model.lower():
        return get_settings().small_model
    elif any(x in claude_model.lower() for x in ["sonnet", "opus"]):
        return get_settings().big_model
    
    # Default to big model
    return get_settings().big_model


# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings