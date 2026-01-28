FROM python:3.11-slim

# Install Chrome, Xvfb and dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    xvfb \
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
ENV DISPLAY=:99

EXPOSE 9000

# Create startup script
RUN echo '#!/bin/bash\n\
# Start Xvfb with 1920x1080 resolution\n\
Xvfb :99 -screen 0 1920x1080x24 &\n\
sleep 1\n\
# Start the server\n\
exec python server.py\n\
' > /app/start.sh && chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:9000/health')" || exit 1

CMD ["/app/start.sh"]
