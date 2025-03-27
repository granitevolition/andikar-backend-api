#!/bin/bash

# Andikar Backend API Startup Script
# This script handles the startup process for the Andikar Backend API
# It ensures proper environment setup and database initialization

set -e

echo "========== ANDIKAR BACKEND API STARTUP =========="
echo "Environment variables:"
printenv | grep -v PASSWORD | grep -v SECRET | grep -v KEY | sort

# Run database diagnostic tool
echo "Running database diagnostic tool..."
python db_diagnostic.py

# Wait for database to be ready
echo "Waiting for database to be ready..."

# Set connection variables for export
if [ -n "$RAILWAY_TCP_PROXY_DOMAIN" ] && [ -n "$RAILWAY_TCP_PROXY_PORT" ]; then
    echo "Using Railway TCP proxy for database connection"
    export SQLALCHEMY_DATABASE_URL="postgresql://${PGUSER}:${POSTGRES_PASSWORD}@${RAILWAY_TCP_PROXY_DOMAIN}:${RAILWAY_TCP_PROXY_PORT}/${PGDATABASE}"
    echo "Connection URL set to: postgresql://${PGUSER}:****@${RAILWAY_TCP_PROXY_DOMAIN}:${RAILWAY_TCP_PROXY_PORT}/${PGDATABASE}"
elif [ -n "$DATABASE_URL" ]; then
    echo "Using DATABASE_URL environment variable"
    export SQLALCHEMY_DATABASE_URL="${DATABASE_URL}"
    echo "Connection URL set from DATABASE_URL"
else
    echo "Using direct internal connection"
    export SQLALCHEMY_DATABASE_URL="postgresql://${PGUSER}:${POSTGRES_PASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}"
    echo "Connection URL set to: postgresql://${PGUSER}:****@${PGHOST}:${PGPORT}/${PGDATABASE}"
fi

# Initialize the database - retry if it fails
max_attempts=5
attempt=1
while [ $attempt -le $max_attempts ]; do
    echo "Initializing database (attempt $attempt/$max_attempts)..."
    if python initialize_database.py; then
        echo "✅ Database initialization successful!"
        break
    else
        echo "❌ Database initialization failed!"
        
        if [ $attempt -lt $max_attempts ]; then
            backoff=$((2 ** attempt))
            echo "Retrying in $backoff seconds..."
            sleep $backoff
        else
            echo "Maximum attempts reached. Starting application anyway..."
        fi
    fi
    attempt=$((attempt + 1))
done

# Start the application using the entrypoint
echo "Starting application on port ${PORT:-8080}..."
exec python -m entrypoint