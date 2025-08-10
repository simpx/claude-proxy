"""
Basic integration test for claude-proxy with OpenAI API.
Tests the full flow: start proxy server -> make Claude API calls -> verify responses.
"""

import pytest
from anthropic import Anthropic
from anthropic.types import Message

from ..conftest import IntegrationTestServer, get_test_env_vars


@pytest.fixture(scope="module")
def test_server():
    """Fixture to start and stop test server for the entire module."""
    env_vars = get_test_env_vars()
    server = IntegrationTestServer(
        OPENAI_API_KEY=env_vars['OPENAI_API_KEY'],
        OPENAI_BASE_URL=env_vars['OPENAI_BASE_URL'],
        CLAUDE_PROXY_BIG_MODEL=env_vars['CLAUDE_PROXY_BIG_MODEL'],
        CLAUDE_PROXY_SMALL_MODEL=env_vars['CLAUDE_PROXY_SMALL_MODEL'],
        CLAUDE_PROXY_AUTH_KEY=None  # No auth for basic tests
    )
    server.start()
    yield server
    server.stop()


@pytest.fixture
def anthropic_client(test_server):
    """Fixture to create Anthropic client pointing to our test server."""
    env_vars = get_test_env_vars()
    api_key = env_vars['OPENAI_API_KEY']
    
    return Anthropic(
        api_key=api_key,  # This will be forwarded through proxy
        base_url=f"http://{test_server.host}:{test_server.actual_port}",
    )


@pytest.mark.integration
class TestBasicIntegration:
    """Basic integration tests for claude-proxy."""
    
    def test_simple_message(self, anthropic_client: Anthropic):
        """Test basic message completion through proxy."""
        message = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "Say hello in exactly 3 words."}
            ]
        )
        
        assert isinstance(message, Message)
        assert message.content
        assert len(message.content) > 0
        assert message.content[0].type == "text"
        assert len(message.content[0].text.split()) <= 10  # Should be short response
    
    def test_system_message(self, anthropic_client: Anthropic):
        """Test message with system prompt through proxy.""" 
        message = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=30,
            system="You are a helpful assistant that always responds with 'OK' followed by exactly one word.",
            messages=[
                {"role": "user", "content": "How are you?"}
            ]
        )
        
        assert isinstance(message, Message)
        assert message.content
        response_text = message.content[0].text.lower()
        assert "ok" in response_text
        assert len(response_text.split()) <= 5  # Should be very short
    
    def test_multi_turn_conversation(self, anthropic_client: Anthropic):
        """Test multi-turn conversation through proxy."""
        message = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022", 
            max_tokens=100,
            messages=[
                {"role": "user", "content": "What's 2+2?"},
                {"role": "assistant", "content": "2+2 equals 4."},
                {"role": "user", "content": "What about 4+4?"}
            ]
        )
        
        assert isinstance(message, Message)
        assert message.content
        response_text = message.content[0].text.lower()
        assert "8" in response_text or "eight" in response_text
    
    def test_model_mapping(self, anthropic_client: Anthropic):
        """Test that different Claude models get mapped correctly."""
        # Test small model (should map to settings.small_model)
        message1 = anthropic_client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=20,
            messages=[{"role": "user", "content": "Hi"}]
        )
        
        # Test big model (should map to settings.big_model)
        message2 = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=20,
            messages=[{"role": "user", "content": "Hi"}]
        )
        
        assert isinstance(message1, Message)
        assert isinstance(message2, Message)
        # Both should succeed - actual model mapping verification would need API introspection
    
    @pytest.mark.asyncio
    async def test_token_counting(self, anthropic_client: Anthropic):
        """Test token counting endpoint through proxy."""
        import httpx
        
        # Get server details from the client
        base_url = str(anthropic_client._base_url)
        api_key = anthropic_client.api_key
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/messages/count_tokens",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "messages": [
                        {"role": "user", "content": "Hello world, this is a test message."}
                    ]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "input_tokens" in data
        assert isinstance(data["input_tokens"], int)
        assert data["input_tokens"] > 0


@pytest.mark.integration 
class TestHealthAndStatus:
    """Integration tests for health and status endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, test_server):
        """Test health check endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{test_server.host}:{test_server.actual_port}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "config" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, test_server):
        """Test root information endpoint."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://{test_server.host}:{test_server.actual_port}/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "running"
        assert "endpoints" in data
        assert "/v1/messages" in data["endpoints"]["messages"]