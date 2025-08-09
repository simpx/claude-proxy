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

### 🚀 Simple Testing (Recommended)

For quick local testing, just install and run:

```bash
# Install from PyPI
pip install claude-proxy

# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-openai-key

# Start the proxy (default: http://localhost:8085)
claude-proxy
```

That's it! The proxy will start and be ready to use with Claude Code.

### ⚙️ Advanced Configuration

For custom configuration, set environment variables:

```bash
# API Configuration
export OPENAI_API_KEY=sk-your-openai-key
export OPENAI_BASE_URL=https://api.openai.com/v1  # Optional

# Model Mapping
export BIG_MODEL=gpt-4o          # For Claude Sonnet/Opus requests
export SMALL_MODEL=gpt-4o-mini   # For Claude Haiku requests

# Server Settings
export HOST=0.0.0.0
export PORT=8085
export LOG_LEVEL=INFO

# Optional: API key validation
export ANTHROPIC_API_KEY=your-anthropic-key-for-validation

# Then run
claude-proxy
```

### 🏭 Production Deployment

For production use with better performance and reliability:

```bash
# Install with production dependencies
pip install claude-proxy[production]

# Option 1: Run with uvicorn (ASGI server)
uvicorn claude_proxy.main:app --host 0.0.0.0 --port 8085 --workers 4

# Option 2: Run with gunicorn + uvicorn workers (recommended)
gunicorn claude_proxy.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8085

# Option 3: Behind a reverse proxy (nginx/traefik)
uvicorn claude_proxy.main:app --host 127.0.0.1 --port 8085 --workers 4
```

#### Production Environment Variables

```bash
# Required
export OPENAI_API_KEY=sk-your-production-key

# Recommended for production
export ANTHROPIC_API_KEY=your-validation-key  # Enable API key validation
export LOG_LEVEL=WARNING  # Reduce log verbosity
export REQUEST_TIMEOUT=60  # Shorter timeout for production
```

### 🐳 Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# Or build manually
docker build -t claude-proxy .
docker run -p 8085:8085 -e OPENAI_API_KEY=your-key claude-proxy
```

### 🔗 Use with Claude Code

```bash
# Set the proxy URL
export ANTHROPIC_BASE_URL=http://localhost:8085
export ANTHROPIC_API_KEY=any-value  # Or your validation key if set

# Use Claude Code as normal
claude
```

### 🛠️ Development Setup

For development work:

```bash
# Clone the repository
git clone <repository-url>
cd claude-proxy

# Install with uv (recommended)
uv sync

# Run in development mode
uv run python app.py

# Or run the package directly
uv run claude-proxy
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
    "http://localhost:8085/v1/messages",
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
    "http://localhost:8085/v1/messages",
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
    "http://localhost:8085/v1/messages",
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
docker run -p 8085:8085 --env-file .env claude-proxy
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