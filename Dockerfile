# ✅ Google Cloud Run Optimized Dockerfile
# Base image: Python 3.11 slim (lightweight, production-ready)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Python optimization flags for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for PostgreSQL (asyncpg) and SSL
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire application code
COPY . .

# Google Cloud Run injects PORT environment variable
# Default to 8080 if not set (Cloud Run standard)
ENV PORT=8080

# Expose port (Cloud Run will override this, but good practice)
EXPOSE 8080

# Use exec form for proper signal handling (important for Cloud Run)
# Cloud Run sends SIGTERM for graceful shutdown
# Run uvicorn with production settings:
# - --host 0.0.0.0: Listen on all interfaces
# - --port ${PORT}: Use Cloud Run's PORT env var
# - --workers 1: Single worker (Cloud Run handles scaling)
# - --timeout-keep-alive 5: Keep connections alive for 5 seconds
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1 --timeout-keep-alive 5