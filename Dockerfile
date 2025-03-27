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

# Make all Python files executable
RUN find . -name "*.py" -exec chmod +x {} \; && \
    chmod +x /app/start.sh && \
    chmod 755 /app/start.sh /app/railway_entry.py /app/status_server.py

# Expose port
ENV PORT=8080
EXPOSE 8080

# Set PYTHONUNBUFFERED to ensure log output is visible
ENV PYTHONUNBUFFERED=1

# Set healthcheck to verify service is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/status || exit 1

# Run Python directly
CMD ["python", "status_server.py"]
