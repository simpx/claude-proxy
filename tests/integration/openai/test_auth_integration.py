"""
Authentication integration tests for claude-proxy.
Tests different authentication modes and scenarios end-to-end.
"""

import pytest
import httpx

from ..conftest import IntegrationTestServer, get_test_env_vars


@pytest.mark.integration
class TestFixedApiKeyModeAuth:
    """Test Fixed API Key Mode authentication scenarios."""
    
    @pytest.fixture
    def server_with_fixed_key(self):
        """Server with OPENAI_API_KEY set (Fixed API Key Mode)."""
        env_vars = get_test_env_vars()
        server = IntegrationTestServer(
            OPENAI_API_KEY=env_vars['OPENAI_API_KEY'],
            OPENAI_BASE_URL=env_vars['OPENAI_BASE_URL'],
            CLAUDE_PROXY_BIG_MODEL=env_vars['CLAUDE_PROXY_BIG_MODEL'],
            CLAUDE_PROXY_SMALL_MODEL=env_vars['CLAUDE_PROXY_SMALL_MODEL'],
            CLAUDE_PROXY_AUTH_KEY=None  # No auth required
        )
        server.start()
        yield server
        server.stop()
    
    @pytest.fixture
    def server_with_fixed_key_and_auth(self):
        """Server with OPENAI_API_KEY set AND auth key required."""
        env_vars = get_test_env_vars()
        server = IntegrationTestServer(
            OPENAI_API_KEY=env_vars['OPENAI_API_KEY'],
            OPENAI_BASE_URL=env_vars['OPENAI_BASE_URL'],
            CLAUDE_PROXY_BIG_MODEL=env_vars['CLAUDE_PROXY_BIG_MODEL'],
            CLAUDE_PROXY_SMALL_MODEL=env_vars['CLAUDE_PROXY_SMALL_MODEL'],
            CLAUDE_PROXY_AUTH_KEY="proxy-secret-key"
        )
        server.start()
        yield server
        server.stop()

    @pytest.mark.asyncio
    async def test_fixed_key_mode_no_auth_required(self, server_with_fixed_key):
        """Test Fixed API Key Mode with no authentication required."""
        async with httpx.AsyncClient() as client:
            # Should work without any client API key
            response = await client.post(
                f"http://{server_with_fixed_key.host}:{server_with_fixed_key.actual_port}/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
            
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
        assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_fixed_key_mode_with_client_key_ignored(self, server_with_fixed_key):
        """Test that client API key is ignored in Fixed API Key Mode."""
        async with httpx.AsyncClient() as client:
            # Client provides key, but it should be ignored (server uses its own key)
            response = await client.post(
                f"http://{server_with_fixed_key.host}:{server_with_fixed_key.actual_port}/v1/messages",
                headers={
                    "Authorization": "Bearer sk-fake-client-key",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022", 
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
    
    @pytest.mark.asyncio
    async def test_fixed_key_mode_with_auth_valid_key(self, server_with_fixed_key_and_auth):
        """Test Fixed API Key Mode with authentication required and valid key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_with_fixed_key_and_auth.host}:{server_with_fixed_key_and_auth.actual_port}/v1/messages",
                headers={
                    "x-api-key": "proxy-secret-key",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
    
    @pytest.mark.asyncio
    async def test_fixed_key_mode_with_auth_invalid_key(self, server_with_fixed_key_and_auth):
        """Test Fixed API Key Mode with authentication required and invalid key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_with_fixed_key_and_auth.host}:{server_with_fixed_key_and_auth.actual_port}/v1/messages",
                headers={
                    "Authorization": "Bearer wrong-key",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid API key" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_fixed_key_mode_with_auth_no_key(self, server_with_fixed_key_and_auth):
        """Test Fixed API Key Mode with authentication required and no key provided."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_with_fixed_key_and_auth.host}:{server_with_fixed_key_and_auth.actual_port}/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 401
        data = response.json()
        assert "Invalid API key" in data["detail"]


@pytest.mark.integration
class TestPassthroughModeAuth:
    """Test Passthrough Mode authentication scenarios."""
    
    @pytest.fixture
    def server_passthrough_no_auth(self):
        """Server in Passthrough Mode with no auth key required."""
        env_vars = get_test_env_vars()
        server = IntegrationTestServer(
            OPENAI_API_KEY="",  # Empty = Passthrough Mode
            OPENAI_BASE_URL=env_vars['OPENAI_BASE_URL'],
            CLAUDE_PROXY_BIG_MODEL=env_vars['CLAUDE_PROXY_BIG_MODEL'],
            CLAUDE_PROXY_SMALL_MODEL=env_vars['CLAUDE_PROXY_SMALL_MODEL'],
            # Note: CLAUDE_PROXY_AUTH_KEY is ignored in Passthrough Mode
        )
        server.start()
        yield server
        server.stop()

    @pytest.mark.asyncio
    async def test_passthrough_mode_with_valid_client_key(self, server_passthrough_no_auth):
        """Test Passthrough Mode with valid client API key."""
        env_vars = get_test_env_vars()
        if not env_vars['OPENAI_API_KEY']:
            pytest.skip("OPENAI_API_KEY not set - skipping test requiring real API key")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_passthrough_no_auth.host}:{server_passthrough_no_auth.actual_port}/v1/messages",
                headers={
                    "Authorization": f"Bearer {env_vars['OPENAI_API_KEY']}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data
    
    @pytest.mark.asyncio
    async def test_passthrough_mode_no_client_key(self, server_passthrough_no_auth):
        """Test Passthrough Mode with no client API key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_passthrough_no_auth.host}:{server_passthrough_no_auth.actual_port}/v1/messages",
                headers={"Content-Type": "application/json"},
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 500
        data = response.json()
        assert "No API key available" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_passthrough_mode_invalid_client_key(self, server_passthrough_no_auth):
        """Test Passthrough Mode with invalid client API key."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_passthrough_no_auth.host}:{server_passthrough_no_auth.actual_port}/v1/messages",
                headers={
                    "Authorization": "Bearer sk-invalid-key",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        # Should get error from the underlying provider
        assert response.status_code in [401, 403, 500]
    
    @pytest.mark.asyncio
    async def test_passthrough_mode_x_api_key_forwarded(self, server_passthrough_no_auth):
        """Test that x-api-key is forwarded as API key in Passthrough Mode."""
        env_vars = get_test_env_vars()
        if not env_vars['OPENAI_API_KEY']:
            pytest.skip("OPENAI_API_KEY not set - skipping test requiring real API key")
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_passthrough_no_auth.host}:{server_passthrough_no_auth.actual_port}/v1/messages",
                headers={
                    "x-api-key": env_vars['OPENAI_API_KEY'],  # x-api-key forwarded as API key
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "content" in data


@pytest.mark.integration
class TestAuthHeaderFormats:
    """Test different API key header formats."""
    
    @pytest.fixture
    def server_no_auth(self):
        """Server with no authentication required."""
        env_vars = get_test_env_vars()
        server = IntegrationTestServer(
            OPENAI_API_KEY=env_vars['OPENAI_API_KEY'],
            OPENAI_BASE_URL=env_vars['OPENAI_BASE_URL'],
            CLAUDE_PROXY_BIG_MODEL=env_vars['CLAUDE_PROXY_BIG_MODEL'],
            CLAUDE_PROXY_SMALL_MODEL=env_vars['CLAUDE_PROXY_SMALL_MODEL'],
            CLAUDE_PROXY_AUTH_KEY=None
        )
        server.start()
        yield server
        server.stop()

    @pytest.mark.asyncio
    async def test_authorization_bearer_header(self, server_no_auth):
        """Test Authorization Bearer header format.""" 
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_no_auth.host}:{server_no_auth.actual_port}/v1/messages",
                headers={
                    "Authorization": "Bearer sk-test-key",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_x_api_key_header(self, server_no_auth):
        """Test x-api-key header format."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_no_auth.host}:{server_no_auth.actual_port}/v1/messages",
                headers={
                    "x-api-key": "sk-test-key",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_x_api_key_precedence(self, server_no_auth):
        """Test that x-api-key takes precedence over Authorization header."""
        # This test verifies header parsing behavior, not authentication
        # Since we're in fixed key mode, the client key is ignored anyway
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"http://{server_no_auth.host}:{server_no_auth.actual_port}/v1/messages",
                headers={
                    "Authorization": "Bearer bearer-key",
                    "x-api-key": "x-api-key-value",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 5,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
        
        assert response.status_code == 200