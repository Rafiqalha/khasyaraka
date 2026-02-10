# ✅ Google Cloud Run Optimized Dockerfile
# Base image: Python 3.11 slim (lightweight, production-ready)
FROM python:3.11-slim

# Mencegah Python menulis file .pyc & buffering stdout (agar log muncul di Cloud Run)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies sistem (diperlukan untuk asyncpg/PostgreSQL)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements dan install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sisa kode
COPY . .

# Pastikan port 8080 terekspos (Cloud Run default)
ENV PORT=8080
EXPOSE 8080

# COMMAND STARTUP YANG BENAR
# Menggunakan 0.0.0.0 adalah WAJIB untuk Cloud Run (bukan 127.0.0.1)
# Format exec form untuk proper signal handling
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}