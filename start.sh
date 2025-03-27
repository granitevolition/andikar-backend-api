#!/bin/bash

# Andikar Backend API Startup Script
# This script handles the startup process for the Andikar Backend API
# It ensures proper environment setup and database initialization

set -e

echo "Environment variables:"
printenv | grep -v PASSWORD | grep -v SECRET | grep -v KEY | sort

# Check database connection
echo "Checking if host postgres.railway.internal is reachable..."
if ping -c 1 postgres.railway.internal &> /dev/null; then
    echo "Host is reachable, attempting database connection..."
    export SQLALCHEMY_DATABASE_URL="postgresql://${PGUSER}:${POSTGRES_PASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}"
    echo "Using internal Railway PostgreSQL connection"
else
    echo "Host postgres.railway.internal is not reachable!"
    echo "Trying with public proxy connection instead..."
    
    # Try using TCP proxy
    export SQLALCHEMY_DATABASE_URL="postgresql://${PGUSER}:${POSTGRES_PASSWORD}@${RAILWAY_TCP_PROXY_DOMAIN}:${RAILWAY_TCP_PROXY_PORT}/${PGDATABASE}"
    echo "Using Railway TCP proxy connection: postgresql://${PGUSER}:****@${RAILWAY_TCP_PROXY_DOMAIN}:${RAILWAY_TCP_PROXY_PORT}/${PGDATABASE}"
fi

echo "Waiting for database to be ready..."
echo "Checking database connection..."

# Initialize the database
echo "Initializing database..."
python initialize_database.py

# Start the application using the new entrypoint
echo "Starting application on port ${PORT:-8080}..."
exec python -m entrypoint