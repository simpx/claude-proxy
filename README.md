# Claude API Proxy

A production-ready Claude API proxy server that converts Claude API requests to OpenAI-compatible format. Extremely simple to use - just set environment variables and run.

## Features

- 🔄 **Protocol Conversion**: Complete Claude API to OpenAI API format conversion
- 🚀 **High Performance**: Async FastAPI with connection pooling 
- 📡 **Streaming Support**: Real-time Server-Sent Events streaming
- 🎯 **Smart Model Mapping**: Automatic model routing (Haiku→Small, Sonnet/Opus→Big)
- 🐳 **Docker Ready**: Easy deployment with Docker/Docker Compose
- 🔍 **Observable**: Health checks, logging, and error handling
- ⚡ **Zero Configuration**: Works with any OpenAI-compatible API

## Quick Start

### 🚀 Install and Run

#### Quick Testing (Recommended)
Perfect for local development and testing:

```bash
# Install from PyPI
pip install claude-proxy

# Set your API configuration
export OPENAI_API_KEY=sk-your-api-key
export OPENAI_BASE_URL=https://api.openai.com/v1

# Start the proxy (runs on http://localhost:8085)
claude-proxy
```

#### Production Deployment

**🐳 Docker (Recommended for Production)**

The easiest and most reliable way to run in production:

```bash
# 1. Set environment variables
export OPENAI_API_KEY=sk-your-production-key
export OPENAI_BASE_URL=https://api.openai.com/v1

# 2. Start with docker-compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t claude-proxy .
docker run -p 8085:8085 --env-file .env claude-proxy
```

**⚡ Manual Production Setup**

For environments where Docker isn't available:

```bash
# Install with production dependencies (includes Gunicorn)
pip install claude-proxy[production]

# Set your configuration
export OPENAI_API_KEY=sk-your-production-key
export OPENAI_BASE_URL=https://api.openai.com/v1

# Run with Gunicorn + Uvicorn workers (production-ready)
gunicorn claude_proxy.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8085 \
  --access-logfile - \
  --error-logfile -
```

**🎯 Production Features**

- **Multi-process**: 4 Gunicorn workers with Uvicorn for high concurrency  
- **Health checks**: Built-in monitoring endpoint
- **Security**: Non-root user, minimal attack surface
- **Resource limits**: Configurable CPU/memory constraints
- **Auto-restart**: Automatic recovery from failures

That's it! The proxy is ready to use with Claude Code.

## Supported Providers

### OpenAI (Default)
```bash
export OPENAI_API_KEY=sk-proj-xxx
export OPENAI_BASE_URL=https://api.openai.com/v1
export BIG_MODEL=gpt-4o
export SMALL_MODEL=gpt-4o-mini
claude-proxy
```

### Alibaba Cloud DashScope
```bash
export OPENAI_API_KEY=sk-xxx
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export BIG_MODEL=qwen-plus
export SMALL_MODEL=qwen-plus
claude-proxy
```

### Azure OpenAI
```bash
export OPENAI_API_KEY=your-azure-key
export OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
export BIG_MODEL=gpt-4
export SMALL_MODEL=gpt-35-turbo
claude-proxy
```

### Local Ollama
```bash
export OPENAI_API_KEY=dummy-key
export OPENAI_BASE_URL=http://localhost:11434/v1
export BIG_MODEL=llama3.1:70b
export SMALL_MODEL=llama3.1:8b
claude-proxy
```

### Any OpenAI-Compatible API
```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://your-api-endpoint/v1
export BIG_MODEL=your-big-model
export SMALL_MODEL=your-small-model
claude-proxy
```

## Environment Variables

### Required
- `OPENAI_API_KEY` - API key for your target provider

### Optional  
- `OPENAI_BASE_URL` - API endpoint URL (default: `https://api.openai.com/v1`)
- `BIG_MODEL` - Model for Claude Sonnet/Opus requests (default: `gpt-4o`)
- `SMALL_MODEL` - Model for Claude Haiku requests (default: `gpt-4o-mini`)
- `HOST` - Server host (default: `0.0.0.0`)
- `PORT` - Server port (default: `8085`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `REQUEST_TIMEOUT` - Request timeout in seconds (default: `90`)
- `ANTHROPIC_API_KEY` - Enable API key validation (optional)

## Model Mapping

The proxy automatically maps Claude models to your configured models:

| Claude Request | Environment Variable | Default Value |
|---------------|---------------------|---------------|
| `claude-3-haiku*` | `SMALL_MODEL` | `gpt-4o-mini` |
| `claude-3-sonnet*` | `BIG_MODEL` | `gpt-4o` |
| `claude-3-opus*` | `BIG_MODEL` | `gpt-4o` |
| `claude-sonnet-4*` | `BIG_MODEL` | `gpt-4o` |

## Using with Claude Code

Set the proxy as your Claude endpoint:

```bash
export ANTHROPIC_BASE_URL=http://localhost:8085
export ANTHROPIC_API_KEY=any-value

# Use Claude Code as normal
claude
```

## Configuration Examples

### Create .env file
```bash
# Copy example configuration
cp .env.example .env

# Edit your configuration  
nano .env
```

### Example .env for OpenAI
```env
OPENAI_API_KEY=sk-proj-xxx
OPENAI_BASE_URL=https://api.openai.com/v1
BIG_MODEL=gpt-4o
SMALL_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

### Example .env for DashScope
```env
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  
BIG_MODEL=qwen3-coder-flash
SMALL_MODEL=qwen3-coder-flash
LOG_LEVEL=INFO
```

## Production Deployment

### Basic Production
```bash
# Install with production dependencies
pip install claude-proxy[production]

# Set production environment
export OPENAI_API_KEY=your-production-key
export LOG_LEVEL=WARNING
export REQUEST_TIMEOUT=60

# Run with more workers
gunicorn claude_proxy.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8085
```

### Docker Deployment
```bash
# Using docker-compose (recommended)
docker-compose up -d

# Or build and run manually
docker build -t claude-proxy .
docker run -p 8085:8085 --env-file .env claude-proxy
```

### Behind Reverse Proxy
```bash
# Run on localhost for nginx/traefik
export HOST=127.0.0.1
export PORT=8085
claude-proxy
```

## API Endpoints

- `POST /v1/messages` - Chat completions (Claude API compatible)  
- `POST /v1/messages/count_tokens` - Token counting
- `GET /health` - Health check
- `GET /test-connection` - Test target API connectivity  
- `GET /` - Service information

## Development

### Setup Development Environment
```bash
# Clone repository
git clone <repository-url>
cd claude-proxy

# Install with uv
uv sync

# Set development configuration
cp .env.example .env
nano .env

# Run in development
uv run claude-proxy
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=claude_proxy --cov-report=html

# Test specific functionality
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

## Troubleshooting

### Connection Issues
```bash
# Test target API directly
curl -X POST "$OPENAI_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"test"}],"max_tokens":5}'

# Test proxy health
curl http://localhost:8085/health

# Test proxy connection  
curl http://localhost:8085/test-connection
```

### Common Issues
- **404 Not Found**: Check your `OPENAI_BASE_URL` and model names
- **401 Unauthorized**: Verify your `OPENAI_API_KEY` is valid
- **Model not found**: Ensure `BIG_MODEL` and `SMALL_MODEL` exist in your provider

## Examples

### Basic Chat Request
```bash
curl -X POST http://localhost:8085/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 100,
    "messages": [
      {"role": "user", "content": "Hello, world!"}
    ]
  }'
```

### With System Prompt  
```bash
curl -X POST http://localhost:8085/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-haiku",
    "max_tokens": 100,
    "system": "You are a helpful assistant.",
    "messages": [
      {"role": "user", "content": "Explain quantum computing"}
    ]
  }'
```

### Streaming Request
```bash
curl -X POST http://localhost:8085/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-sonnet",
    "max_tokens": 100,
    "stream": true,
    "messages": [
      {"role": "user", "content": "Tell me a story"}
    ]
  }'
```

## License

MIT License - see LICENSE file for details.