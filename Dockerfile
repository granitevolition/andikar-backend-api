FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    netcat-traditional \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x /app/startup.sh

# Expose port 
ENV PORT=8080
EXPOSE 8080

# Set PYTHONUNBUFFERED to ensure log output is visible
ENV PYTHONUNBUFFERED=1

# Use our startup script as the entrypoint
ENTRYPOINT ["/app/startup.sh"]
