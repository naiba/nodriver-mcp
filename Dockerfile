FROM python:3.11-slim

# Install Chrome and dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set Chrome path for nodriver
ENV CHROME_PATH=/usr/bin/chromium

# Install Python dependencies
RUN pip install --no-cache-dir \
    nodriver \
    fastapi \
    uvicorn[standard] \
    httpx \
    pydantic

# Create downloads directory
RUN mkdir -p /tmp/downloads

# Copy server code
COPY src/nodriver_mcp/container/server.py /app/server.py
WORKDIR /app

# Environment variables
ENV HEADLESS=true
ENV PORT=9000

EXPOSE 9000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:9000/health')" || exit 1

CMD ["python", "server.py"]
