"""
Shared fixtures and utilities for integration tests.
"""

import os
import socket
import threading
import time

import pytest
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
        self.temp_env_file = None
        self.original_env_file_content = None
        
    def start(self):
        """Start the test server with custom environment."""
        from pathlib import Path
        
        # Handle .env file if we need to override OPENAI_API_KEY
        project_root = Path(__file__).parent.parent.parent
        env_file = project_root / '.env'
        
        if 'OPENAI_API_KEY' in self.env_overrides and self.env_overrides['OPENAI_API_KEY'] is None:
            # We need to create a temporary .env without OPENAI_API_KEY
            if env_file.exists():
                # Read original content
                self.original_env_file_content = env_file.read_text()
                
                # Create new content without OPENAI_API_KEY
                lines = []
                for line in self.original_env_file_content.splitlines():
                    if not line.strip().startswith('OPENAI_API_KEY='):
                        lines.append(line)
                
                # Write temporary .env
                env_file.write_text('\n'.join(lines))
                self.temp_env_file = env_file
        
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
        for _ in range(max_wait * 10):
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
        
        # Restore original .env file
        if self.temp_env_file and self.original_env_file_content is not None:
            self.temp_env_file.write_text(self.original_env_file_content)
        
        # Restore original environment
        for key, original_value in self.original_env.items():
            if original_value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = original_value


def get_test_env_vars():
    """Get test environment variables from current environment and .env file."""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Load .env file from project root if it exists
    # This will load variables into os.environ if they're not already set
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / '.env'
    
    if env_file.exists():
        load_dotenv(env_file, override=False)  # Don't override existing env vars
    
    return {
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'OPENAI_BASE_URL': os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'CLAUDE_PROXY_BIG_MODEL': os.environ.get('CLAUDE_PROXY_BIG_MODEL', 'gpt-4o'),
        'CLAUDE_PROXY_SMALL_MODEL': os.environ.get('CLAUDE_PROXY_SMALL_MODEL', 'gpt-4o-mini'),
    }


def get_test_env_vars_no_dotenv():
    """Get test environment variables from current environment only (no .env file loading)."""
    import os
    
    return {
        'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
        'OPENAI_BASE_URL': os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'CLAUDE_PROXY_BIG_MODEL': os.environ.get('CLAUDE_PROXY_BIG_MODEL', 'gpt-4o'),
        'CLAUDE_PROXY_SMALL_MODEL': os.environ.get('CLAUDE_PROXY_SMALL_MODEL', 'gpt-4o-mini'),
    }


def should_skip_integration_tests():
    """Check if integration tests should be skipped due to missing required environment variables."""
    env_vars = get_test_env_vars()
    
    # Check if required variables are available
    openai_key = env_vars.get('OPENAI_API_KEY')
    openai_url = env_vars.get('OPENAI_BASE_URL')
    
    # OPENAI_API_KEY is absolutely required
    if not openai_key:
        return True, "OPENAI_API_KEY not found in environment variables or .env file"
    
    # OPENAI_BASE_URL has a default, but let's ensure it's valid
    if not openai_url or not openai_url.startswith(('http://', 'https://')):
        return True, "OPENAI_BASE_URL not found or invalid in environment variables or .env file"
    
    return False, None


@pytest.fixture(scope="session", autouse=True)
def check_integration_requirements():
    """Automatically check if integration tests should be skipped.
    
    This fixture runs once per session and will skip all integration tests
    if required environment variables are not available.
    """
    should_skip, reason = should_skip_integration_tests()
    if should_skip:
        pytest.skip(f"Skipping all integration tests: {reason}")
    
    # Log successful environment detection
    env_vars = get_test_env_vars()
    print(f"\n✅ Integration test environment detected:")
    print(f"   OPENAI_API_KEY: {'✓ Set' if env_vars['OPENAI_API_KEY'] else '✗ Missing'}")
    print(f"   OPENAI_BASE_URL: {env_vars['OPENAI_BASE_URL']}")
    print(f"   BIG_MODEL: {env_vars['CLAUDE_PROXY_BIG_MODEL']}")
    print(f"   SMALL_MODEL: {env_vars['CLAUDE_PROXY_SMALL_MODEL']}")
    print()