FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    netcat-traditional \
    postgresql-client \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make startup script executable with explicit permissions
RUN chmod +x /app/start.sh && \
    chmod 755 /app/start.sh && \
    ls -la /app/start.sh

# Create a simple status endpoint script as fallback
RUN echo '#!/usr/bin/env python3\nfrom fastapi import FastAPI\nimport uvicorn\napp = FastAPI()\n@app.get("/status")\ndef status():\n    return {"status": "healthy"}\n\nif __name__ == "__main__":\n    uvicorn.run(app, host="0.0.0.0", port=8080)' > /app/status_server.py && \
    chmod +x /app/status_server.py

# Expose port 
ENV PORT=8080
EXPOSE 8080

# Set PYTHONUNBUFFERED to ensure log output is visible
ENV PYTHONUNBUFFERED=1

# Set healthcheck to verify service is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/status || exit 1

# Add a CMD as fallback if ENTRYPOINT fails
ENTRYPOINT ["bash", "/app/start.sh"]
CMD ["python", "-m", "entrypoint"]
