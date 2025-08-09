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

```bash
pip install claude-proxy

# Option 1: Fixed API Key Mode (recommended for single user)
export OPENAI_API_KEY=sk-your-api-key
export OPENAI_BASE_URL=https://api.openai.com/v1
claude-proxy

# Option 2: Passthrough Mode (for multi-user scenarios)  
export OPENAI_BASE_URL=https://api.openai.com/v1
# Don't set OPENAI_API_KEY - proxy will forward each client's API key
claude-proxy
```

## Production Deployment

**🐳 Docker (Recommended for Production)**

The easiest and most reliable way to run in production:

```bash
# 1. Set environment variables (Fixed API Key mode)
export OPENAI_API_KEY=sk-your-production-key
export OPENAI_BASE_URL=https://api.openai.com/v1
export CLAUDE_PROXY_AUTH_KEY=sk-your-own-key

# Or for Passthrough mode, don't set OPENAI_API_KEY and CLAUDE_PROXY_AUTH_KEY:
# export OPENAI_BASE_URL=https://api.openai.com/v1

# 2. Start with docker-compose
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

# Set your configuration (Fixed API Key mode)
export OPENAI_API_KEY=sk-your-production-key
export OPENAI_BASE_URL=https://api.openai.com/v1
export CLAUDE_PROXY_AUTH_KEY=sk-your-own-key

# Or for Passthrough mode, don't set OPENAI_API_KEY and CLAUDE_PROXY_AUTH_KEY

# Run with Gunicorn + Uvicorn workers
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

**API Endpoints**

- `POST /v1/messages` - Chat completions (Claude API compatible)  
- `POST /v1/messages/count_tokens` - Token counting
- `GET /health` - Health check
- `GET /test-connection` - Test target API connectivity  
- `GET /` - Service information

That's it! The proxy is ready to use with Claude Code.

## Supported Providers

### OpenAI
```bash
export OPENAI_BASE_URL=https://api.openai.com/v1
export CLAUDE_PROXY_BIG_MODEL=gpt-4o
export CLAUDE_PROXY_SMALL_MODEL=gpt-4o-mini
claude-proxy
```

### Alibaba Cloud DashScope
```bash
export OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
export CLAUDE_PROXY_BIG_MODEL=qwen3-coder-plus
export CLAUDE_PROXY_SMALL_MODEL=qwen3-coder-flash
claude-proxy
```

### Azure OpenAI
```bash
export OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/deployments/your-deployment
export CLAUDE_PROXY_BIG_MODEL=gpt-4
export CLAUDE_PROXY_SMALL_MODEL=gpt-35-turbo
claude-proxy
```

### Local Ollama
```bash
export OPENAI_BASE_URL=http://localhost:11434/v1
export CLAUDE_PROXY_BIG_MODEL=llama3.1:70b
export CLAUDE_PROXY_SMALL_MODEL=llama3.1:8b
claude-proxy
```

## Environment Variables

- `OPENAI_API_KEY` - API key for your target provider (optional - enables Fixed API Key mode if set)
- `OPENAI_BASE_URL` - API endpoint URL (default: `https://api.openai.com/v1`)

**Mode Selection:**
- **If `OPENAI_API_KEY` is set**: Fixed API Key mode - proxy uses this key for all requests
- **If `OPENAI_API_KEY` is NOT set**: Passthrough mode - proxy forwards each client's API key

- `CLAUDE_PROXY_BIG_MODEL` - Model for Claude Sonnet/Opus requests (default: `gpt-4o`)
- `CLAUDE_PROXY_SMALL_MODEL` - Model for Claude Haiku requests (default: `gpt-4o-mini`)
- `CLAUDE_PROXY_HOST` - Server host (default: `0.0.0.0`)
- `CLAUDE_PROXY_PORT` - Server port (default: `8085`)
- `CLAUDE_PROXY_LOG_LEVEL` - Logging level (default: `INFO`)
- `CLAUDE_PROXY_REQUEST_TIMEOUT` - Request timeout in seconds (default: `90`)
- `CLAUDE_PROXY_AUTH_KEY` - Required API key for proxy access validation (optional, only for Fixed API Key mode)

## Authentication & Security

### Fixed API Key Mode
- **Recommended**: Set `CLAUDE_PROXY_AUTH_KEY` to validate client access
- All requests to target provider use the same `OPENAI_API_KEY`
- Clients provide any API key to the proxy (validated against `CLAUDE_PROXY_AUTH_KEY`)

### Passthrough Mode  
- **Don't set** `CLAUDE_PROXY_AUTH_KEY` - each client uses their own API key
- Client's API key is forwarded directly to the target provider
- No additional proxy-level authentication needed

## Model Mapping

The proxy automatically maps Claude models to your configured models:

| Claude Request | Environment Variable | Default Value |
|---------------|---------------------|---------------|
| `claude-3-haiku*` | `CLAUDE_PROXY_SMALL_MODEL` | `gpt-4o-mini` |
| `claude-3-sonnet*` | `CLAUDE_PROXY_BIG_MODEL` | `gpt-4o` |
| `claude-3-opus*` | `CLAUDE_PROXY_BIG_MODEL` | `gpt-4o` |
| `claude-sonnet-4*` | `CLAUDE_PROXY_BIG_MODEL` | `gpt-4o` |

## Configuration Examples

### Example .env for OpenAI
```env
OPENAI_BASE_URL=https://api.openai.com/v1
CLAUDE_PROXY_BIG_MODEL=gpt-4o
CLAUDE_PROXY_SMALL_MODEL=gpt-4o-mini
CLAUDE_PROXY_LOG_LEVEL=INFO
```

### Example .env for DashScope
```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1  
CLAUDE_PROXY_BIG_MODEL=qwen3-coder-plus
CLAUDE_PROXY_SMALL_MODEL=qwen3-coder-flash
CLAUDE_PROXY_LOG_LEVEL=INFO
```

### Example .env for Fixed API Key Mode
```env
OPENAI_API_KEY=sk-your-production-key # enables Fixed API Key Mode
CLAUDE_PROXY_AUTH_KEY=sk-your-own-key # optional
OPENAI_BASE_URL=https://api.openai.com/v1
CLAUDE_PROXY_BIG_MODEL=gpt-4o
CLAUDE_PROXY_SMALL_MODEL=gpt-4o-mini
CLAUDE_PROXY_LOG_LEVEL=INFO
```

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
vim .env

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
uv run pytest -v
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
- **Model not found**: Ensure `CLAUDE_PROXY_BIG_MODEL` and `CLAUDE_PROXY_SMALL_MODEL` exist in your provider

## License

MIT License - see LICENSE file for details.