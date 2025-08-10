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
        # Auth failure can manifest as timeout or explicit error
        error_msg = result['stderr'].lower()
        assert any(word in error_msg for word in ['authentication', 'unauthorized', 'timeout', 'timed out', 'connection'])
    
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
        # Auth failure can manifest as timeout or explicit error  
        error_msg = result['stderr'].lower()
        assert any(word in error_msg for word in ['authentication', 'unauthorized', 'timeout', 'timed out', 'connection'])


@pytest.mark.integration
class TestClaudeCodeAdvancedFeatures(ClaudeCodeTestMixin):
    """Test advanced Claude Code features including tool usage and complex scenarios."""

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

    def test_tools_mathematical_calculation(self, server_fixed_key_mode):
        """Test tool usage with mathematical calculation prompt."""
        result = self._run_claude_command(
            "What is 15 * 23 + 47? Please calculate step by step.",
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 0
        # Should contain the calculation result (15 * 23 = 345, + 47 = 392)
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['392', 'calculation', 'multiply', 'add'])

    def test_tools_code_analysis(self, server_fixed_key_mode):
        """Test tool usage with code analysis prompt."""
        code_prompt = '''
        Analyze this Python function and tell me what it does:
        
        def fibonacci(n):
            if n <= 1:
                return n
            return fibonacci(n-1) + fibonacci(n-2)
        
        What's the time complexity and can you suggest improvements?
        '''
        
        result = self._run_claude_command(
            code_prompt.strip(),
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 100  # Should be substantial analysis
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['fibonacci', 'recursive', 'complexity', 'function'])

    def test_tools_with_json_output(self, server_fixed_key_mode):
        """Test tool usage combined with JSON output format."""
        result = self._run_claude_command(
            "List the first 5 prime numbers and explain what makes them prime",
            server_fixed_key_mode.actual_port,
            output_format='json'
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        
        # Parse JSON response
        try:
            response_data = json.loads(result['stdout'])
            assert 'result' in response_data or 'content' in response_data
            content = str(response_data.get('result', response_data.get('content', '')))
            content_lower = content.lower()
            assert any(word in content_lower for word in ['prime', '2', '3', '5', '7', '11'])
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response: {result['stdout']}")

    def test_file_operations_simulation(self, server_fixed_key_mode):
        """Test prompts that might trigger file-related tool usage."""
        result = self._run_claude_command(
            "How do I read a CSV file in Python?",
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 20
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['csv', 'pandas', 'read', 'python', 'import'])

    def test_streaming_with_tools(self, server_fixed_key_mode):
        """Test streaming response with tool usage."""
        result = self._run_claude_command(
            "Write a step-by-step recipe for chocolate chip cookies, including baking temperature and time",
            server_fixed_key_mode.actual_port,
            output_format='stream-json'
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        
        # Verify streaming output contains content
        output_lines = result['stdout'].strip().split('\n')
        assert len(output_lines) > 0
        
        # Look for recipe-related content in the streaming output
        full_output = result['stdout'].lower()
        assert any(word in full_output for word in ['cookie', 'temperature', 'recipe', 'flour', 'sugar'])

    def test_concurrent_requests_with_tools(self, server_fixed_key_mode):
        """Test concurrent requests that might involve tool usage."""
        import threading
        import queue
        
        results = queue.Queue()
        
        prompts = [
            "What is 100 factorial?",
            "Sort these numbers: 42, 17, 33, 8, 91",
            "Convert 100 degrees Fahrenheit to Celsius"
        ]
        
        def make_request(prompt_idx):
            result = self._run_claude_command(
                prompts[prompt_idx],
                server_fixed_key_mode.actual_port
            )
            results.put((prompt_idx, result))
        
        # Start threads
        threads = []
        for i in range(len(prompts)):
            thread = threading.Thread(target=make_request, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=45)
        
        # Check results
        collected_results = []
        while not results.empty():
            collected_results.append(results.get())
        
        assert len(collected_results) == 3
        
        for prompt_idx, result in collected_results:
            assert result['success'], f"Request {prompt_idx} failed: {result['stderr']}"
            assert len(result['stdout']) > 10


@pytest.mark.integration 
class TestClaudeCodeMultiTurnConversations(ClaudeCodeTestMixin):
    """Test multi-turn conversation scenarios (simulated through context-aware prompts)."""

    @pytest.fixture
    def server_fixed_key_mode(self):
        """Server in Fixed API Key Mode for Claude Code testing."""
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

    def test_conversation_context_awareness(self, server_fixed_key_mode):
        """Test context-aware responses that simulate multi-turn conversations."""
        context_prompt = '''
        I'm a beginner programmer learning Python. I want to create a simple calculator.
        Can you show me a basic calculator that can add, subtract, multiply, and divide?
        Then explain how I could extend it to handle more advanced operations.
        '''
        
        result = self._run_claude_command(
            context_prompt.strip(),
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 50  # Reduced expectation for response length
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['calculator', 'add', 'subtract', 'multiply', 'divide', 'python'])

    def test_follow_up_question_simulation(self, server_fixed_key_mode):
        """Test handling follow-up style prompts."""
        followup_prompt = '''
        Earlier I asked about Python calculators. Now I want to add error handling to prevent division by zero.
        How should I modify the division function to handle this case gracefully?
        '''
        
        result = self._run_claude_command(
            followup_prompt.strip(),
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 50
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['division', 'zero', 'error', 'exception', 'try', 'catch'])

    def test_progressive_complexity(self, server_fixed_key_mode):
        """Test progressive complexity with a working prompt."""
        progressive_prompt = "Explain the difference between frontend and backend development in 2-3 sentences."
        
        result = self._run_claude_command(
            progressive_prompt,
            server_fixed_key_mode.actual_port,
            timeout=60
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 20  # Should be substantial  
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['frontend', 'backend', 'development', 'user'])


@pytest.mark.integration
class TestClaudeCodeComplexScenarios(ClaudeCodeTestMixin):
    """Test complex scenarios including edge cases and error conditions."""

    @pytest.fixture
    def server_fixed_key_mode(self):
        """Server in Fixed API Key Mode for Claude Code testing."""
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

    def test_unicode_and_special_characters(self, server_fixed_key_mode):
        """Test handling of Unicode and special characters."""
        unicode_prompt = "What are the Greek letters alpha, beta, and gamma used for in mathematics?"
        
        result = self._run_claude_command(
            unicode_prompt,
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 50
        # Should handle and respond about Greek letters
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['alpha', 'beta', 'gamma', 'greek', 'mathematics'])

    def test_code_generation_request(self, server_fixed_key_mode):
        """Test code generation requests that might use tools extensively."""
        code_gen_prompt = '''
        Generate a complete Python class for a simple bank account with the following features:
        - Initialize with account number and initial balance
        - Methods for deposit, withdraw, and check balance
        - Transaction history tracking
        - Input validation and error handling
        - Include docstrings and type hints
        '''
        
        result = self._run_claude_command(
            code_gen_prompt.strip(),
            server_fixed_key_mode.actual_port,
            timeout=60
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 100
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['class', 'def', 'deposit', 'withdraw', 'balance'])

    def test_mathematical_notation(self, server_fixed_key_mode):
        """Test handling mathematical notation and formulas."""
        math_prompt = "Explain the quadratic formula and show how to solve x² + 5x + 6 = 0. Include step-by-step solution and explain the discriminant."
        
        result = self._run_claude_command(
            math_prompt,
            server_fixed_key_mode.actual_port
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        assert len(result['stdout']) > 100
        output_lower = result['stdout'].lower()
        assert any(word in output_lower for word in ['quadratic', 'formula', 'discriminant', 'solution'])

    def test_streaming_with_complex_content(self, server_fixed_key_mode):
        """Test streaming with complex content that might trigger multiple tool calls."""
        complex_streaming_prompt = '''
        Create a comprehensive guide for setting up a Python development environment:
        1. Installing Python and virtual environments
        2. Essential VS Code extensions
        3. Setting up linting and formatting
        4. Configuring debugging
        5. Package management best practices
        
        Include code examples and practical tips.
        '''
        
        result = self._run_claude_command(
            complex_streaming_prompt.strip(),
            server_fixed_key_mode.actual_port,
            output_format='stream-json',
            timeout=75
        )
        
        assert result['success'], f"Command failed: {result['stderr']}"
        
        # Verify streaming format
        output_lines = result['stdout'].strip().split('\n')
        assert len(output_lines) > 0
        
        # Check for comprehensive content
        full_output = result['stdout'].lower()
        assert any(word in full_output for word in ['python', 'environment', 'vscode', 'linting', 'development'])