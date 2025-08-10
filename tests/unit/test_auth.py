"""
Unit tests for authentication functionality.
Tests the actual authentication functions in main.py and utils.py.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException
from src.claude_proxy.utils import validate_api_key, extract_api_key_from_headers
import importlib
main_module = importlib.import_module('src.claude_proxy.main')
from src.claude_proxy.main import validate_client_api_key, get_provider


class TestAuthUtils:
    """Test authentication utility functions."""
    
    def test_extract_api_key_from_headers_authorization_bearer(self):
        """Test extracting API key from Authorization header with Bearer."""
        headers = {"authorization": "Bearer sk-test-key-123"}
        result = extract_api_key_from_headers(headers)
        assert result == "sk-test-key-123"
    
    def test_extract_api_key_from_headers_x_api_key(self):
        """Test extracting API key from x-api-key header."""
        headers = {"x-api-key": "sk-test-key-456"}
        result = extract_api_key_from_headers(headers)
        assert result == "sk-test-key-456"
    
    def test_extract_api_key_from_headers_no_key(self):
        """Test extracting API key when no key is present."""
        headers = {}
        result = extract_api_key_from_headers(headers)
        assert result is None
    
    def test_extract_api_key_from_headers_malformed_bearer(self):
        """Test extracting API key from malformed Bearer header."""
        headers = {"authorization": "Bearersk-test-key"}  # Missing space
        result = extract_api_key_from_headers(headers)
        assert result is None
    
    def test_extract_api_key_precedence(self):
        """Test that x-api-key takes precedence over Authorization header."""
        headers = {
            "authorization": "Bearer bearer-key",
            "x-api-key": "x-api-key-value"
        }
        result = extract_api_key_from_headers(headers)
        assert result == "x-api-key-value"
    
    def test_validate_api_key_no_expected_key(self):
        """Test validation when no expected key is set (should allow any)."""
        assert validate_api_key("any-key", None) is True
        assert validate_api_key(None, None) is True
    
    def test_validate_api_key_with_expected_key(self):
        """Test validation when expected key is set."""
        expected = "sk-proxy-secret"
        
        # Correct key should pass
        assert validate_api_key("sk-proxy-secret", expected) is True
        
        # Wrong key should fail
        assert validate_api_key("wrong-key", expected) is False
        
        # No key should fail
        assert validate_api_key(None, expected) is False
        
        # Empty string should fail
        assert validate_api_key("", expected) is False


class TestValidateClientApiKey:
    """Test the validate_client_api_key function from main.py."""
    
    @pytest.mark.asyncio
    async def test_validate_client_api_key_no_auth_required(self):
        """Test client validation when no auth key is configured."""
        with patch.object(main_module, 'settings') as mock_settings:
            # Mock settings with no auth key
            mock_settings.auth_key = None
            
            # Mock request with API key
            mock_request = Mock()
            mock_request.headers = {"authorization": "Bearer client-key-123"}
            
            # Should return the client key  
            result = await validate_client_api_key(mock_request, None, "Bearer client-key-123")
            assert result == "client-key-123"
    
    @pytest.mark.asyncio
    async def test_validate_client_api_key_no_auth_no_client_key(self):
        """Test client validation when no auth required and no client key provided."""
        with patch.object(main_module, 'settings') as mock_settings:
            # Mock settings with no auth key
            mock_settings.auth_key = None
            
            # Mock request with no API key
            mock_request = Mock()
            mock_request.headers = {}
            
            # Should return None (no validation required)
            result = await validate_client_api_key(mock_request, None, None)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_validate_client_api_key_auth_required_valid_key(self):
        """Test client validation with auth required and valid key."""
        with patch.object(main_module, 'settings') as mock_settings:
            # Mock settings with auth key
            mock_settings.auth_key = "sk-proxy-auth-key"
            
            # Mock request with correct key
            mock_request = Mock()
            mock_request.headers = {"x-api-key": "sk-proxy-auth-key"}
            
            # Should return the client key
            result = await validate_client_api_key(mock_request, "sk-proxy-auth-key", None)
            assert result == "sk-proxy-auth-key"
    
    @pytest.mark.asyncio
    async def test_validate_client_api_key_auth_required_invalid_key(self):
        """Test client validation with auth required and invalid key."""
        # Mock the settings directly on the main module
        with patch.object(main_module, 'settings') as mock_settings:
            mock_settings.auth_key = "sk-proxy-auth-key"
            
            # Mock request with wrong key
            mock_request = Mock()
            mock_request.headers = {"authorization": "Bearer wrong-key"}
            
            # Should raise HTTPException (function gets key from headers, ignoring the parameters)
            with pytest.raises(HTTPException) as exc_info:
                await validate_client_api_key(mock_request, None, None)
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_client_api_key_auth_required_no_key(self):
        """Test client validation with auth required and no key provided."""
        with patch.object(main_module, 'settings') as mock_settings:
            # Mock settings with auth key
            mock_settings.auth_key = "sk-proxy-auth-key"
            
            # Mock request with no key
            mock_request = Mock()
            mock_request.headers = {}
            
            # Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await validate_client_api_key(mock_request, None, None)
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.detail


class TestGetProvider:
    """Test the get_provider function from main.py."""
    
    def test_get_provider_fixed_api_key_mode(self):
        """Test provider creation in Fixed API Key Mode."""
        with patch.object(main_module, 'settings') as mock_settings, \
             patch.object(main_module, 'OpenAIProvider') as mock_provider_class:
            # Mock settings with fixed API key
            mock_settings.openai_api_key = "sk-server-fixed-key"
            mock_settings.openai_base_url = "https://api.test.com/v1"
            mock_settings.request_timeout = 90
            
            # Call with client key (should be ignored)
            get_provider("sk-client-key")
            
            # Should use server key, not client key
            mock_provider_class.assert_called_once_with(
                api_key="sk-server-fixed-key",
                base_url="https://api.test.com/v1",
                timeout=90
            )
    
    def test_get_provider_fixed_api_key_mode_no_client_key(self):
        """Test provider creation in Fixed API Key Mode without client key."""
        with patch.object(main_module, 'settings') as mock_settings, \
             patch.object(main_module, 'OpenAIProvider') as mock_provider_class:
            # Mock settings with fixed API key
            mock_settings.openai_api_key = "sk-server-fixed-key"
            mock_settings.openai_base_url = "https://api.test.com/v1"
            mock_settings.request_timeout = 90
            
            # Call without client key
            get_provider(None)
            
            # Should still use server key
            mock_provider_class.assert_called_once_with(
                api_key="sk-server-fixed-key",
                base_url="https://api.test.com/v1",
                timeout=90
            )
    
    def test_get_provider_passthrough_mode_with_client_key(self):
        """Test provider creation in Passthrough Mode with client key."""
        with patch.object(main_module, 'settings') as mock_settings, \
             patch.object(main_module, 'OpenAIProvider') as mock_provider_class:
            # Mock settings without fixed API key (passthrough mode)
            mock_settings.openai_api_key = None
            mock_settings.openai_base_url = "https://api.test.com/v1"
            mock_settings.request_timeout = 90
            
            # Call with client key
            get_provider("sk-client-provided-key")
            
            # Should use client key
            mock_provider_class.assert_called_once_with(
                api_key="sk-client-provided-key",
                base_url="https://api.test.com/v1",
                timeout=90
            )
    
    def test_get_provider_passthrough_mode_no_client_key(self):
        """Test provider creation in Passthrough Mode without client key."""
        with patch.object(main_module, 'settings') as mock_settings:
            # Mock settings without fixed API key (passthrough mode)
            mock_settings.openai_api_key = None
            
            # Should raise HTTPException when no client key provided
            with pytest.raises(HTTPException) as exc_info:
                get_provider(None)
            
            assert exc_info.value.status_code == 500
            assert "No API key available" in exc_info.value.detail
    
    def test_get_provider_passthrough_mode_empty_client_key(self):
        """Test provider creation in Passthrough Mode with empty client key."""
        with patch.object(main_module, 'settings') as mock_settings:
            # Mock settings without fixed API key (passthrough mode)
            mock_settings.openai_api_key = None
            
            # Should raise HTTPException when empty client key provided
            with pytest.raises(HTTPException) as exc_info:
                get_provider("")
            
            assert exc_info.value.status_code == 500
            assert "No API key available" in exc_info.value.detail
    
    def test_get_provider_passthrough_mode_empty_string_openai_key(self):
        """Test provider creation when OPENAI_API_KEY is empty string."""
        with patch.object(main_module, 'settings') as mock_settings:
            # Mock settings with empty string (should be treated as passthrough mode)
            mock_settings.openai_api_key = ""
            
            # Should raise HTTPException when no client key provided
            with pytest.raises(HTTPException) as exc_info:
                get_provider(None)
            
            assert exc_info.value.status_code == 500
            assert "No API key available" in exc_info.value.detail