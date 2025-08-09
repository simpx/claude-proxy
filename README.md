# Claude API Proxy

A production-ready Claude API proxy server that enables seamless integration with OpenAI-compatible API providers.

## Features

- 🔄 **Protocol Conversion**: Complete Claude API to OpenAI API format conversion
- 🚀 **High Performance**: Async FastAPI with connection pooling 
- 📡 **Streaming Support**: Real-time Server-Sent Events streaming
- 🎯 **Smart Model Mapping**: Configurable model routing (Haiku→Small, Sonnet/Opus→Big)
- 🔒 **Secure**: Optional API key validation and request authentication
- 🐳 **Docker Ready**: Easy deployment with Docker/Docker Compose
- 🔍 **Observable**: Health checks, logging, and error handling
- 🛠️ **Developer Friendly**: Type-safe with Pydantic models

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd claude-proxy

# Install dependencies with uv (recommended)
uv sync

# Or install directly
uv pip install -e .

# Or with pip (traditional method)
pip install -e .
```

### 2. Configuration

Create a `.env` file:

```bash
# Required: Your OpenAI API key
OPENAI_API_KEY=sk-your-openai-key

# Optional: API configuration
OPENAI_BASE_URL=https://api.openai.com/v1

# Model mapping
BIG_MODEL=gpt-4o          # For Claude Sonnet/Opus requests
SMALL_MODEL=gpt-4o-mini   # For Claude Haiku requests

# Server settings
HOST=0.0.0.0
PORT=8082
LOG_LEVEL=INFO

# Optional: API key validation
ANTHROPIC_API_KEY=your-anthropic-key-for-validation
```

### 3. Run the Server

```bash
# With uv
uv run python app.py

# Or directly (after installing dependencies)
python app.py

# With Docker Compose
docker-compose up -d
```

### 4. Use with Claude Code

```bash
# Set the proxy URL and API key
export ANTHROPIC_BASE_URL=http://localhost:8082
export ANTHROPIC_API_KEY=any-value  # Or your validation key

# Use Claude Code as normal
claude
```

## API Endpoints

### Main Endpoints

- `POST /v1/messages` - Chat completions (compatible with Claude API)
- `POST /v1/messages/count_tokens` - Token counting
- `GET /health` - Health check
- `GET /test-connection` - Test connectivity to target API
- `GET /` - API information

### Model Mapping

The proxy automatically maps Claude models to your configured models:

| Claude Model | Maps To | Environment Variable |
|--------------|---------|---------------------|
| `claude-3-haiku*` | `SMALL_MODEL` | Default: `gpt-4o-mini` |
| `claude-3-sonnet*` | `BIG_MODEL` | Default: `gpt-4o` |
| `claude-3-opus*` | `BIG_MODEL` | Default: `gpt-4o` |
| `claude-sonnet-4*` | `BIG_MODEL` | Default: `gpt-4o` |

## Usage Examples

### Basic Chat Completion

```python
import httpx

response = httpx.post(
    "http://localhost:8082/v1/messages",
    headers={"x-api-key": "your-api-key"},  # Optional if validation disabled
    json={
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 100,
        "messages": [
            {"role": "user", "content": "Hello, world!"}
        ]
    }
)
print(response.json())
```

### Streaming Chat

```python
import httpx

with httpx.stream(
    "POST",
    "http://localhost:8082/v1/messages",
    headers={"x-api-key": "your-api-key"},
    json={
        "model": "claude-3-haiku",
        "max_tokens": 100,
        "stream": True,
        "messages": [
            {"role": "user", "content": "Tell me a story"}
        ]
    }
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            print(line[6:])  # Remove "data: " prefix
```

### With System Prompt and Tools

```python
response = httpx.post(
    "http://localhost:8082/v1/messages",
    headers={"x-api-key": "your-api-key"},
    json={
        "model": "claude-3-sonnet",
        "max_tokens": 200,
        "system": "You are a helpful assistant.",
        "messages": [
            {"role": "user", "content": "What's the weather like?"}
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get current weather",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        }
                    }
                }
            }
        ]
    }
)
```

## Provider Configuration

### OpenAI

```bash
OPENAI_API_KEY=sk-your-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini
```

### Azure OpenAI

```bash
OPENAI_API_KEY=your-azure-key
OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
BIG_MODEL=gpt-4
SMALL_MODEL=gpt-35-turbo
```

### Local Models (Ollama)

```bash
OPENAI_API_KEY=dummy-key  # Required but can be dummy
OPENAI_BASE_URL=http://localhost:11434/v1
BIG_MODEL=llama3.1:70b
SMALL_MODEL=llama3.1:8b
```

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=. --cov-report=html

# Run specific test file
uv run pytest tests/test_app.py -v
```

### Code Quality

```bash
# Format code
uv run black .

# Lint code
uv run ruff check .

# Type checking
uv run mypy .
```

### Project Structure

```
claude-proxy/
├── app.py                 # FastAPI application
├── config.py             # Configuration management
├── utils.py              # Utility functions
├── models/               # Data models
│   ├── claude.py         # Claude API models
│   └── openai.py         # OpenAI API models
├── providers/            # LLM provider implementations
│   ├── base.py          # Base provider class
│   ├── openai.py        # OpenAI provider
│   └── anthropic.py     # Anthropic provider (pass-through)
└── tests/               # Test suite
```

## Deployment

### Docker

```bash
# Build image
docker build -t claude-proxy .

# Run container
docker run -p 8082:8082 --env-file .env claude-proxy
```

### Docker Compose

```bash
# Create .env file with your configuration
cp .env.example .env

# Start services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Production Considerations

- Use a reverse proxy (Nginx/Traefik) for HTTPS termination
- Set up monitoring and logging
- Configure resource limits and health checks
- Use secrets management for API keys
- Enable API key validation in production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details.