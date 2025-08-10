"""
Claude Code integration tests.
Tests claude-proxy compatibility with Claude Code CLI client.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Add parent directories to path to import conftest
sys.path.insert(0, str(Path(__file__).parent.parent))
from conftest import IntegrationTestServer, get_test_env_vars


class ClaudeCodeTestMixin:
    """Mixin class with shared test methods."""
    
    def _run_claude_command(self, prompt, server_port, auth_token=None, **kwargs):
        """
        Run claude command with custom server configuration using environment variables.
        
        Args:
            prompt: The prompt to send to Claude
            server_port: Port of the claude-proxy server
            auth_token: Optional authentication token for proxy
            **kwargs: Additional claude command arguments
        """
        try:
            # Build claude command with minimal configuration to avoid tool issues
            cmd = ['claude', '--print', '--dangerously-skip-permissions']
            
            # Add optional arguments
            if kwargs.get('output_format'):
                cmd.extend(['--output-format', kwargs['output_format']])
                # stream-json format requires --verbose
                if kwargs['output_format'] == 'stream-json':
                    cmd.append('--verbose')
            if kwargs.get('model'):
                cmd.extend(['--model', kwargs['model']])
            if kwargs.get('timeout'):
                timeout = kwargs['timeout']
            else:
                timeout = 30
            
            # Add prompt as final argument
            cmd.append(prompt)
            
            # Set up environment variables
            env = dict(os.environ)
            env['ANTHROPIC_BASE_URL'] = f"http://localhost:{server_port}"
            
            if auth_token:
                env['ANTHROPIC_AUTH_TOKEN'] = auth_token
            
            # Debug: Print the actual command being executed (remove in production)
            # print(f"DEBUG: Executing command: {' '.join(cmd)}")
            # print(f"DEBUG: Environment ANTHROPIC_BASE_URL: {env.get('ANTHROPIC_BASE_URL')}")
            
            # Run command with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            return {
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode,
                'success': result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                'stdout': '',
                'stderr': 'Command timed out',
                'returncode': 124,  # Standard timeout exit code
                'success': False
            }
        except Exception as e:
            return {
                'stdout': '',
                'stderr': f'Error running command: {str(e)}',
                'returncode': 1,
                'success': False
            }


@pytest.mark.integration
class TestClaudeCodeIntegration(ClaudeCodeTestMixin):
    """Test Claude Code CLI integration with claude-proxy."""

    @pytest.fixture
    def server_fixed_key_mode(self):
        """Server in Fixed API Key Mode for Claude Code testing."""
        env_vars = get_test_env_vars()
        server = IntegrationTestServer(
            OPENAI_API_KEY=env_vars['OPENAI_API_KEY'],
            OPENAI_BASE_URL=env_vars['OPENAI_BASE_URL'],
            CLAUDE_PROXY_BIG_MODEL=env_vars['CLAUDE_PROXY_BIG_MODEL'],
            CLAUDE_PROXY_SMALL_MODEL=env_vars['CLAUDE_PROXY_SMALL_MODEL'],
            CLAUDE_PROXY_AUTH_KEY=None  # No proxy auth for simplicity
        )
        server.start()
        yield server
        server.stop()
    
    def test_basic_text_response(self, server_fixed_key_mode):
        """Test basic text response through Claude Code."""
        result = self._run_claude_command(
            "Say 'Hello from Claude Code!' exactly",
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert 'Hello from Claude Code!' in result['stdout']
        assert result['stderr'] == ''  # Should have no errors
    
    def test_json_output_format(self, server_fixed_key_mode):
        """Test JSON output format."""
        result = self._run_claude_command(
            "Respond with just the number 42",
            server_fixed_key_mode.actual_port,
            output_format='json'
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        
        # Parse JSON response
        try:
            response_data = json.loads(result['stdout'])
            # Claude Code JSON format uses 'result' field
            assert 'result' in response_data or 'content' in response_data
            content = response_data.get('result', response_data.get('content', ''))
            assert '42' in str(content)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response: {result['stdout']}")
    
    def test_streaming_json_output(self, server_fixed_key_mode):
        """Test streaming JSON output format."""
        result = self._run_claude_command(
            "Count from 1 to 3, one number per line",
            server_fixed_key_mode.actual_port,
            output_format='stream-json'
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        
        # Verify streaming JSON contains expected events
        output_lines = result['stdout'].strip().split('\n')
        assert len(output_lines) > 0
        
        # Check for Claude API streaming format
        has_content_events = False
        for line in output_lines:
            if line.startswith('event: ') and 'content' in line:
                has_content_events = True
                break
        
        # If not SSE format, should be JSON lines
        if not has_content_events:
            try:
                for line in output_lines:
                    if line.strip():
                        json.loads(line)  # Should be valid JSON
            except json.JSONDecodeError:
                pytest.fail(f"Invalid streaming JSON: {result['stdout']}")
    
    def test_model_specification(self, server_fixed_key_mode):
        """Test specifying Claude model."""
        result = self._run_claude_command(
            "What model are you?",
            server_fixed_key_mode.actual_port,
            model='claude-3-5-haiku-20241022'
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 0
        # Should respond (exact model name may vary in response)
    
    def test_longer_conversation(self, server_fixed_key_mode):
        """Test handling longer prompts."""
        long_prompt = "Write a short poem about programming. Make it exactly 4 lines."
        
        result = self._run_claude_command(
            long_prompt,
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 50  # Should be substantial response
        
        # Check for poem-like structure (multiple lines)
        lines = result['stdout'].strip().split('\n')
        assert len(lines) >= 3  # At least a few lines
    
    def test_error_handling_invalid_prompt(self, server_fixed_key_mode):
        """Test error handling with empty prompt."""
        result = self._run_claude_command(
            "",  # Empty prompt
            server_fixed_key_mode.actual_port
        )
        
        # Claude Code should handle empty prompts gracefully
        # Either succeed with a default response or fail gracefully
        if not result['success']:
            assert result['returncode'] != 0
            assert len(result['stderr']) > 0
    
    def test_server_connection_error(self):
        """Test behavior when claude-proxy is not running."""
        # Use a port that's definitely not in use
        unused_port = 9999
        
        result = self._run_claude_command(
            "This should fail",
            unused_port,
            timeout=10  # Shorter timeout for failure case
        )
        
        assert not result['success']
        # Should have connection error in stderr
        assert any(word in result['stderr'].lower() for word in ['connection', 'error', 'refused', 'timeout'])
    
    def test_concurrent_requests(self, server_fixed_key_mode):
        """Test handling multiple concurrent Claude Code requests."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request(prompt_suffix):
            result = self._run_claude_command(
                f"Say 'Response {prompt_suffix}' exactly",
                server_fixed_key_mode.actual_port
            )
            results.put((prompt_suffix, result))
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)
        
        # Check results
        collected_results = []
        while not results.empty():
            collected_results.append(results.get())
        
        assert len(collected_results) == 3
        
        for suffix, result in collected_results:
            assert result['success'], f"Request {suffix} failed: {result['stderr']}"
            assert f'Response {suffix}' in result['stdout']

@pytest.mark.integration
class TestClaudeCodeAuthentication(ClaudeCodeTestMixin):
    """Test Claude Code authentication scenarios."""
    
    @pytest.fixture
    def server_with_auth(self):
        """Server requiring proxy authentication."""
        env_vars = get_test_env_vars()
        server = IntegrationTestServer(
            OPENAI_API_KEY=env_vars['OPENAI_API_KEY'],
            OPENAI_BASE_URL=env_vars['OPENAI_BASE_URL'],
            CLAUDE_PROXY_BIG_MODEL=env_vars['CLAUDE_PROXY_BIG_MODEL'],
            CLAUDE_PROXY_SMALL_MODEL=env_vars['CLAUDE_PROXY_SMALL_MODEL'],
            CLAUDE_PROXY_AUTH_KEY="test-proxy-auth-key"
        )
        server.start()
        yield server
        server.stop()
    
    def _run_claude_with_auth(self, prompt, server_port, auth_key=None):
        """Run claude command with authentication using environment variables."""
        return self._run_claude_command(
            prompt,
            server_port,
            auth_token=auth_key
        )
    
    def test_auth_required_no_key(self, server_with_auth):
        """Test request without required auth key."""
        result = self._run_claude_with_auth(
            "This should fail",
            server_with_auth.actual_port
        )
        
        assert not result['success']
        assert 'authentication' in result['stderr'].lower() or 'unauthorized' in result['stderr'].lower()
    
    def test_auth_required_valid_key(self, server_with_auth):
        """Test request with valid auth key."""
        result = self._run_claude_with_auth(
            "Say 'Authenticated!' exactly",
            server_with_auth.actual_port,
            auth_key="test-proxy-auth-key"
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert 'Authenticated!' in result['stdout']
    
    def test_auth_required_invalid_key(self, server_with_auth):
        """Test request with invalid auth key."""
        result = self._run_claude_with_auth(
            "This should fail",
            server_with_auth.actual_port,
            auth_key="wrong-key"
        )
        
        assert not result['success']
        assert 'authentication' in result['stderr'].lower() or 'unauthorized' in result['stderr'].lower()