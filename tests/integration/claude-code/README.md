# Claude Code Integration Tests

This directory contains integration tests that verify claude-proxy compatibility with Claude Code CLI client.

## Overview

These tests start a claude-proxy server and use the actual `claude` CLI command to send requests programmatically, ensuring end-to-end compatibility between claude-proxy and Claude Code.

## Test Categories

### TestClaudeCodeIntegration
Tests basic Claude Code functionality through claude-proxy:

- **test_basic_text_response**: Basic text response handling
- **test_json_output_format**: JSON output format (`--output-format json`)
- **test_streaming_json_output**: Streaming JSON output (`--output-format stream-json`)
- **test_model_specification**: Model specification (`--model`)
- **test_longer_conversation**: Handling longer prompts and responses
- **test_error_handling_invalid_prompt**: Empty prompt handling
- **test_server_connection_error**: Connection error handling
- **test_concurrent_requests**: Concurrent request handling

### TestClaudeCodeAuthentication
Tests authentication scenarios:

- **test_auth_required_no_key**: Request without required auth key
- **test_auth_required_valid_key**: Request with valid auth key
- **test_auth_required_invalid_key**: Request with invalid auth key

## Running Tests

### Quick Start
```bash
# Run all Claude Code integration tests
python -m pytest tests/integration/claude-code/ -v

# Run specific test
python -m pytest tests/integration/claude-code/test_claude_code_integration.py::TestClaudeCodeIntegration::test_basic_text_response -v

# Run tests matching pattern
python -m pytest tests/integration/claude-code/ -k "auth" -v
```

### Using the Test Runner
A convenience script is available at the project root:

```bash
# Run all Claude Code tests
python run_claude_code_tests.py

# Run tests matching pattern
python run_claude_code_tests.py -k "basic"

# List available tests
python run_claude_code_tests.py --list

# Verbose output
python run_claude_code_tests.py -v
```

## Requirements

### Environment Setup
Tests require the same environment variables as other integration tests:
- `OPENAI_API_KEY`: Target API key (or available in `.env`)
- `OPENAI_BASE_URL`: Target API base URL
- `CLAUDE_PROXY_BIG_MODEL`: Model for large requests
- `CLAUDE_PROXY_SMALL_MODEL`: Model for small requests

### Claude Code CLI
Tests require the Claude Code CLI (`claude` command) to be available:

```bash
# Check if Claude Code is installed
claude --version

# If not installed, install it
curl -fsSL https://claude.ai/install.sh | sh
```

## How Tests Work

1. **Server Setup**: Each test starts a claude-proxy server on a random port
2. **Configuration**: Creates temporary settings file pointing to the test server
3. **Execution**: Runs `claude --print` commands programmatically
4. **Validation**: Verifies response content and format
5. **Cleanup**: Stops server and cleans up temporary files

## Test Implementation Details

### Custom Settings Injection
Tests use temporary JSON settings files to override the API base URL:
```json
{
  "apiBaseUrl": "http://localhost:PORT/v1"
}
```

### Command Execution
Tests use Python's `subprocess` to run claude commands:
```bash
claude --print --settings /tmp/settings.json "Your prompt"
```

### Output Formats
Tests verify different Claude Code output formats:
- **Text**: Default plain text output
- **JSON**: Structured JSON response with metadata
- **Stream-JSON**: Real-time streaming JSON events

### Authentication Testing
Authentication tests use different server configurations:
- **No Auth**: Server without `CLAUDE_PROXY_AUTH_KEY`
- **With Auth**: Server requiring proxy authentication
- **Test Keys**: Use known test keys for validation

## Troubleshooting

### Common Issues

1. **Tests timeout**: Increase timeout in test configuration
2. **Claude command not found**: Install Claude Code CLI
3. **Connection refused**: Check if ports are available
4. **Authentication errors**: Verify API keys in environment

### Known Issues

**Tools Compatibility Issue**: Claude Code automatically includes tool definitions in requests, which may not be compatible with all target APIs. This can cause 400 Bad Request errors with messages like "Invalid type for 'tools.15', expected an json object."

This is a legitimate compatibility issue that the tests are designed to discover. The proxy should handle or filter tool definitions to ensure compatibility with target APIs.

### Debug Mode
Run tests with debug output:
```bash
python -m pytest tests/integration/claude-code/ -v --tb=long -s
```

### Test Isolation
Each test uses:
- Random server ports to avoid conflicts
- Temporary settings files for isolation
- Independent server instances
- Proper cleanup in fixtures

## Adding New Tests

### Test Structure
```python
@pytest.mark.integration
class TestClaudeCodeNewFeature:
    @pytest.fixture
    def server_config(self):
        # Setup server with specific configuration
        pass
    
    def test_new_feature(self, server_config):
        result = self._run_claude_command(
            "Test prompt",
            server_config.actual_port,
            output_format='json'
        )
        assert result['success']
        # Add assertions
```

### Helper Method Usage
Use the `_run_claude_command` helper for consistency:
```python
result = self._run_claude_command(
    prompt="Your test prompt",
    server_port=server.actual_port,
    output_format='json',  # optional
    model='claude-3-haiku',  # optional
    timeout=60  # optional
)
```

## Integration with CI/CD

These tests can be integrated into CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run Claude Code Integration Tests
  run: |
    python run_claude_code_tests.py
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    OPENAI_BASE_URL: ${{ secrets.OPENAI_BASE_URL }}
```

## Performance Considerations

- Tests take 5-15 seconds each due to server startup and API calls
- Concurrent tests are limited by API rate limits
- Server ports are randomized to avoid conflicts
- Temporary files are cleaned up automatically

## Security Notes

- Tests use temporary settings files with restricted permissions
- API keys are passed through environment variables only
- Test servers bind to localhost only
- No sensitive data is logged in test output