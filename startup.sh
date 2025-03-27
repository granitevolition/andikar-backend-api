#!/bin/bash

# Andikar Backend API Startup Script
# This script handles the startup process for the Andikar Backend API
# It ensures proper environment setup and database initialization

set -e

echo "Starting Andikar Backend API..."
echo ""

# Print non-sensitive environment variables
echo "Environment variables:"
printenv | grep -v PASSWORD | grep -v SECRET | grep -v KEY | sort

# Wait for PostgreSQL to be ready (if using Railway PostgreSQL)
if [[ -n "$DATABASE_URL" || -n "$DATABASE_PUBLIC_URL" ]]; then
    echo "Checking database connection..."
    
    # Extract host and port
    if [[ -n "$DATABASE_URL" ]]; then
        DB_URL="$DATABASE_URL"
    else
        DB_URL="$DATABASE_PUBLIC_URL"
    fi
    
    # Parse the URL to extract host and port
    if [[ "$DB_URL" =~ .*@([^:]+):([0-9]+)/([^?]+).* ]]; then
        DB_HOST="${BASH_REMATCH[1]}"
        DB_PORT="${BASH_REMATCH[2]}"
        DB_NAME="${BASH_REMATCH[3]}"
        
        echo "Database details:"
        echo "  - Host: $DB_HOST"
        echo "  - Port: $DB_PORT"
        echo "  - Database: $DB_NAME"
        
        # Try to connect using timeout to avoid hanging
        echo "Waiting for database to be ready..."
        
        MAX_RETRIES=5
        RETRY_COUNT=0
        BACKOFF_TIME=2
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            if nc -z -w 5 "$DB_HOST" "$DB_PORT"; then
                echo "Database is ready!"
                break
            else
                RETRY_COUNT=$((RETRY_COUNT+1))
                if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
                    echo "Warning: Could not connect to database after $MAX_RETRIES attempts."
                    echo "Proceeding with application startup, but database features may not work."
                    break
                fi
                
                WAIT_TIME=$((BACKOFF_TIME ** RETRY_COUNT))
                echo "Database not ready yet. Retrying in $WAIT_TIME seconds... (Attempt $RETRY_COUNT/$MAX_RETRIES)"
                sleep $WAIT_TIME
            fi
        done
    else
        echo "Warning: Could not parse database URL. Will continue without database connection check."
    fi
fi

# Create static and templates directories if they don't exist
mkdir -p templates
mkdir -p static

# Start the application
echo "Starting application on port ${PORT:-8080}..."
exec python -m app
