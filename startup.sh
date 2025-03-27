#!/bin/bash
# Railway startup script for Andikar Backend API

echo "Starting Andikar Backend API initialization..."

# Set default environment variables if not set
export PORT=${PORT:-8080}
export DEBUG=${DEBUG:-0}
export SECRET_KEY=${SECRET_KEY:-"09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"}
export ADMIN_USERNAME=${ADMIN_USERNAME:-"admin"}
export ADMIN_PASSWORD=${ADMIN_PASSWORD:-"adminpassword"}
export ADMIN_EMAIL=${ADMIN_EMAIL:-"admin@example.com"}

# Check if PostgreSQL is reachable via internal network
echo "Checking if host postgres.railway.internal is reachable..."
if nc -z -w 5 postgres.railway.internal 5432; then
    echo "Host postgres.railway.internal is reachable!"
    
    # Set DATABASE_URL if not already set
    if [ -z "$DATABASE_URL" ]; then
        export DATABASE_URL="postgresql://${PGUSER}:${POSTGRES_PASSWORD}@postgres.railway.internal:5432/${PGDATABASE}"
        echo "Set DATABASE_URL using internal network"
    fi
else
    echo "Host postgres.railway.internal is not reachable!"
    echo "Trying with DATABASE_PUBLIC_URL instead..."
    
    # If DATABASE_PUBLIC_URL is not set but we have the necessary components, construct it
    if [ -z "$DATABASE_PUBLIC_URL" ] && [ ! -z "$RAILWAY_TCP_PROXY_DOMAIN" ] && [ ! -z "$RAILWAY_TCP_PROXY_PORT" ]; then
        export DATABASE_PUBLIC_URL="postgresql://${PGUSER}:${POSTGRES_PASSWORD}@${RAILWAY_TCP_PROXY_DOMAIN}:${RAILWAY_TCP_PROXY_PORT}/${PGDATABASE}"
        echo "Constructed DATABASE_PUBLIC_URL from environment variables"
    elif [ -z "$DATABASE_PUBLIC_URL" ]; then
        echo "No DATABASE_PUBLIC_URL set, using SQLite fallback database..."
    fi
fi

# Print environment details (without sensitive info)
echo "Environment Configuration:"
echo "- RAILWAY_ENVIRONMENT: ${RAILWAY_ENVIRONMENT}"
echo "- RAILWAY_PROJECT_ID: ${RAILWAY_PROJECT_ID}"
echo "- RAILWAY_SERVICE_NAME: ${RAILWAY_SERVICE_NAME}"
echo "- DATABASE_URL: [REDACTED]"
echo "- DATABASE_PUBLIC_URL: [REDACTED]"
echo "- PORT: ${PORT}"

# Initialize database
echo "Waiting for database to be ready..."
python -c "
import time
import sys
from database import init_db
for attempt in range(5):
    print(f'Database initialization attempt {attempt+1}/5...')
    if init_db():
        print('Database initialized successfully!')
        sys.exit(0)
    if attempt < 4:
        print(f'Retrying in {2**attempt} seconds...')
        time.sleep(2**attempt)
print('Failed to initialize database after 5 attempts')
# Continue anyway, app will use fallback mechanisms
"

# Start the application
echo "Starting application on port ${PORT}..."
exec python app.py
