FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make startup script executable (more explicit permissions)
RUN chmod 755 start.sh

# Expose port 
ENV PORT=8080
EXPOSE 8080

# Run with bash to avoid permission issues
CMD ["bash", "start.sh"]
