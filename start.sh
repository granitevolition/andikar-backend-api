#!/bin/bash

# Andikar Backend API Startup Script
# This script handles the startup process for the Andikar Backend API
# It ensures proper environment setup and database initialization

set -e

echo "========== ANDIKAR BACKEND API STARTUP =========="

# Set up DATABASE_URL explicitly using environment variables or defaults
echo "Setting up database connection..."
PGUSER=${PGUSER:-postgres}
PGDATABASE=${PGDATABASE:-railway}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-ztJggTeesPJYVMHRWuGVbnUinMKwCWyI}
RAILWAY_TCP_PROXY_DOMAIN=${RAILWAY_TCP_PROXY_DOMAIN:-ballast.proxy.rlwy.net}
RAILWAY_TCP_PROXY_PORT=${RAILWAY_TCP_PROXY_PORT:-11148}

# Always use the TCP proxy connection 
export DATABASE_URL="postgresql://$PGUSER:$POSTGRES_PASSWORD@$RAILWAY_TCP_PROXY_DOMAIN:$RAILWAY_TCP_PROXY_PORT/$PGDATABASE"
echo "Database URL set to: postgresql://$PGUSER:****@$RAILWAY_TCP_PROXY_DOMAIN:$RAILWAY_TCP_PROXY_PORT/$PGDATABASE"

# Run database diagnostic
echo "Running database diagnostic..."
python db_diagnostic.py

# Initialize the database - retry if it fails
max_attempts=3
attempt=1
while [ $attempt -le $max_attempts ]; do
    echo "Database initialization attempt $attempt/$max_attempts..."
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
