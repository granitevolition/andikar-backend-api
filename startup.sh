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
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-"eLsHIpQoaRgtqGUMXAGzDXcIKLsIsRSf"}

# Hard-coded PostgreSQL information (from screenshots)
export PGUSER=postgres
export PGDATABASE=railway
export PGPORT=5432

# Check if PostgreSQL is reachable via internal network
echo "Checking if host postgres.railway.internal is reachable..."
if nc -z -w 5 postgres.railway.internal 5432; then
    echo "Host postgres.railway.internal is reachable!"
    
    # Set DATABASE_URL
    export DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD}@postgres.railway.internal:5432/railway"
    echo "Set DATABASE_URL using internal network"
else
    echo "Host postgres.railway.internal is not reachable!"
    
    # Try using TCP proxy if available
    if [ ! -z "$RAILWAY_TCP_PROXY_DOMAIN" ] && [ ! -z "$RAILWAY_TCP_PROXY_PORT" ]; then
        echo "Using TCP proxy for database connection"
        export DATABASE_PUBLIC_URL="postgresql://postgres:${POSTGRES_PASSWORD}@${RAILWAY_TCP_PROXY_DOMAIN}:${RAILWAY_TCP_PROXY_PORT}/railway"
        echo "Set DATABASE_PUBLIC_URL using TCP proxy"
    else
        echo "No TCP proxy information available, will try direct connection"
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

# Run database diagnostic tool first
echo "Running database diagnostic tool..."
python db_diagnostic.py

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
