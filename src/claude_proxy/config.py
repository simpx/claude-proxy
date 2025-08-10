"""Configuration management for Claude API Proxy."""

from typing import Dict, Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host", alias="CLAUDE_PROXY_HOST")
    port: int = Field(default=8085, description="Server port", alias="CLAUDE_PROXY_PORT")
    log_level: str = Field(default="INFO", description="Log level", alias="CLAUDE_PROXY_LOG_LEVEL")
    
    # Model mapping
    big_model: str = Field(default="gpt-4o", description="Model for Claude Opus/Sonnet", alias="CLAUDE_PROXY_BIG_MODEL")
    small_model: str = Field(default="gpt-4o-mini", description="Model for Claude Haiku", alias="CLAUDE_PROXY_SMALL_MODEL")
    
    # Provider settings
    openai_api_key: Optional[str] = Field(default=None, description="Target provider API key")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1", 
        description="Target provider API base URL"
    )
    
    # Request settings
    max_tokens_limit: int = Field(default=4096, description="Maximum tokens limit", alias="CLAUDE_PROXY_MAX_TOKENS_LIMIT")
    request_timeout: int = Field(default=90, description="Request timeout in seconds", alias="CLAUDE_PROXY_REQUEST_TIMEOUT")
    
    # Authentication settings
    auth_key: Optional[str] = Field(
        default=None, 
        description="Required API key for proxy access validation",
        alias="CLAUDE_PROXY_AUTH_KEY"
    )
    
    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


def get_model_mapping() -> Dict[str, str]:
    """Get Claude to target model mapping."""
    from .providers.base import BaseProvider
    settings = get_settings()
    return BaseProvider.get_claude_model_mapping(settings.big_model, settings.small_model)


def map_claude_model(claude_model: str) -> str:
    """Map Claude model name to target provider model."""
    from .providers.base import BaseProvider
    settings = get_settings()
    return BaseProvider.map_claude_model(claude_model, settings.big_model, settings.small_model)


# Global settings instance
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get application settings (singleton pattern)."""
    global _settings
    if _settings is None:
        _settings = Settings()
        
        # Validate configuration: Passthrough mode doesn't support auth_key
        if not _settings.openai_api_key and _settings.auth_key:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "CLAUDE_PROXY_AUTH_KEY is set but OPENAI_API_KEY is not configured (Passthrough Mode). "
                "Proxy authentication is not supported in Passthrough Mode. Ignoring CLAUDE_PROXY_AUTH_KEY."
            )
            _settings.auth_key = None
            
    return _settings