"""
Shared fixtures and utilities for integration tests.
"""

import os
import threading
import time
from typing import Optional
import socket

import uvicorn


class IntegrationTestServer:
    """Test server manager for integration tests with custom environment."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 0, **env_overrides):
        self.host = host
        self.requested_port = port
        self.actual_port = None
        self.server = None
        self.server_thread = None
        self.env_overrides = env_overrides
        self.original_env = {}
        
    def start(self):
        """Start the test server with custom environment."""
        # Apply environment overrides
        for key, value in self.env_overrides.items():
            self.original_env[key] = os.environ.get(key)
            if value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = str(value)
        
        # Find available port
        if self.requested_port == 0:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('', 0))
            self.actual_port = sock.getsockname()[1]
            sock.close()
        else:
            self.actual_port = self.requested_port
        
        def run_server():
            # Force reload settings and main module with new environment
            import importlib
            import sys
            
            # Clear cached modules to force reload
            modules_to_reload = [
                'src.claude_proxy.config',
                'src.claude_proxy.main'
            ]
            for mod in modules_to_reload:
                if mod in sys.modules:
                    importlib.reload(sys.modules[mod])
            
            # Re-import the app with new settings
            from src.claude_proxy.main import app
            
            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.actual_port,
                log_level="warning"
            )
            self.server = uvicorn.Server(config)
            self.server.run()
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start
        time.sleep(2)  # Give more time for environment changes to take effect
        max_wait = 15
        for i in range(max_wait * 10):
            try:
                import httpx
                response = httpx.get(f"http://{self.host}:{self.actual_port}/health", timeout=2.0)
                if response.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.1)
        else:
            raise TimeoutError(f"Server failed to start within {max_wait} seconds on port {self.actual_port}")
    
    def stop(self):
        """Stop the test server and restore environment."""
        if self.server:
            self.server.should_exit = True
        
        # Restore original environment
        for key, original_value in self.original_env.items():
            if original_value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = original_value


def get_test_env_vars():
    """Get test environment variables from current environment."""
    return {
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'OPENAI_BASE_URL': os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'CLAUDE_PROXY_BIG_MODEL': os.environ.get('CLAUDE_PROXY_BIG_MODEL', 'gpt-4o'),
        'CLAUDE_PROXY_SMALL_MODEL': os.environ.get('CLAUDE_PROXY_SMALL_MODEL', 'gpt-4o-mini'),
    }