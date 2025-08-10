# Testing Guide

This directory contains tests for claude-proxy, organized into unit and integration tests.

## Directory Structure

```
tests/
├── conftest.py              # Shared test configuration
├── unit/                   # Unit tests (fast, isolated)
│   ├── test_auth.py        # Authentication unit tests
│   ├── test_convert.py     # Conversion unit tests
│   ├── test_models.py      # Model unit tests
│   └── test_providers.py   # Provider unit tests
└── integration/            # Integration tests (slower, end-to-end)
    ├── conftest.py         # Shared integration test utilities
    └── openai/
        ├── test_basic_integration.py    # Basic API integration tests
        └── test_auth_integration.py     # Authentication integration tests
```

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only (fast)
```bash
pytest -m "not integration"
# or
pytest tests/unit/
```

### Integration Tests Only
```bash
pytest -m integration
# or  
pytest tests/integration/
```

### Specific Test File
```bash
pytest tests/unit/test_auth.py
pytest tests/integration/openai/test_basic_integration.py
```

## Environment Setup

### For Unit Tests
Unit tests use mocks and don't require external services. They should run without any environment configuration.

### For Integration Tests
Integration tests require a valid OpenAI-compatible API key and use the same configuration as your main application:

1. **Use existing `.env` file**: Tests automatically load from the project root `.env` file
2. **Or set environment variables directly**:
   ```bash
   export OPENAI_API_KEY=your-api-key-here
   export OPENAI_BASE_URL=https://api.openai.com/v1  # or your provider URL
   ```

This approach allows you to reuse the same configuration for both testing and normal operation. Integration tests will be skipped automatically if required environment variables are not available.

**Important**: All API keys and sensitive configuration are read from environment variables - no secrets are hardcoded in test files.

## Test Types

### Unit Tests
- Fast execution (< 1 second)
- Test individual functions and classes in isolation
- Use mocks to avoid external dependencies
- Run in parallel safely

### Integration Tests  
- Slower execution (few seconds)
- Test full API workflows end-to-end
- Start actual proxy server with custom configurations
- Use real HTTP clients and Anthropic client against the proxy
- Verify complete request/response flow
- Test different authentication modes (Fixed API Key, Passthrough)
- Test various authentication scenarios (valid/invalid keys, missing auth, etc.)

## Development

When adding new tests:

1. **Unit tests** for new functions/classes go in `tests/unit/`
2. **Integration tests** for new API endpoints/workflows go in `tests/integration/`
3. Mark integration tests with `@pytest.mark.integration`
4. Use descriptive test names that explain the scenario being tested
5. **Never hardcode API keys or secrets** - always use environment variables
6. Use shared utilities from `tests/integration/conftest.py` for integration tests