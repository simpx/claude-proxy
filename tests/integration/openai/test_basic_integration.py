"""
Basic integration test for claude-proxy with OpenAI API.
Tests the full flow: start proxy server -> make Claude API calls -> verify responses.
"""

import asyncio
import os
import threading
import time
from typing import Optional

import pytest
import uvicorn
from anthropic import Anthropic
from anthropic.types import Message

from src.claude_proxy.main import app
from src.claude_proxy.config import get_settings


class ProxyTestServer:
    """Test server manager for integration tests."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self.requested_port = port
        self.actual_port = None
        self.server = None
        self.server_thread = None
        
    def start(self):
        """Start the test server in a separate thread."""
        import socket
        
        # If port is 0, find an available port first
        if self.requested_port == 0:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            self.actual_port = sock.getsockname()[1]
            sock.close()
        else:
            self.actual_port = self.requested_port
        
        def run_server():
            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.actual_port,
                log_level="warning"  # Reduce log noise in tests
            )
            self.server = uvicorn.Server(config)
            self.server.run()
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(1)  # Give server initial time to start
        max_wait = 15
        for i in range(max_wait * 10):
            try:
                import httpx
                response = httpx.get(f"http://{self.host}:{self.actual_port}/health", timeout=2.0)
                if response.status_code == 200:
                    break
            except Exception as e:
                pass
            time.sleep(0.1)
        else:
            raise TimeoutError(f"Server failed to start within {max_wait} seconds on port {self.actual_port}")
    
    def stop(self):
        """Stop the test server."""
        if self.server:
            self.server.should_exit = True


@pytest.fixture(scope="module")
def test_server():
    """Fixture to start and stop test server for the entire module."""
    server = ProxyTestServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def anthropic_client(test_server):
    """Fixture to create Anthropic client pointing to our test server."""
    # Use environment variable for API key, or skip test
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set - skipping integration test")
    
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