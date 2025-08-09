FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies (production includes gunicorn)
RUN uv pip install --system -e .[production]

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8085

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8085/health || exit 1

# Production command: Gunicorn with Uvicorn workers
CMD ["gunicorn", "claude_proxy.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8085", "--access-logfile", "-", "--error-logfile", "-"]