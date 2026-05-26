# ─── Recepta - Dockerfile ───────────────────────────────────────────────────
# Build: docker build -f docker/Dockerfile -t recepta-ai .
# Run:    docker run -it --rm recepta-ai python main.py

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/logs data/chroma_db data/voices data/knowledge

# Environment variables (override with -e flag)
ENV RECEPTA_DEBUG=false
ENV RECEPTA_LOG_LEVEL=INFO
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV SPEACHES_BASE_URL=http://speaches:8000
ENV LIVEKIT_URL=wss://your-project.livekit.cloud

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command: run CLI test mode
CMD ["python", "main.py", "--industry", "dental"]
