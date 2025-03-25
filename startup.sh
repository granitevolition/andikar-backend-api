#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Extract port from environment variable or use default
python -c "import os; print(f'PORT={os.environ.get(\"PORT\", 8000)}')" > .env.port

# Start the application
PORT=$(cat .env.port | cut -d= -f2)
echo "Starting application on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT