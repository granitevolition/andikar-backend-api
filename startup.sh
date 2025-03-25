#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Set the port from environment or default to 8000
PORT=${PORT:-8000}
echo "Starting application on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT
