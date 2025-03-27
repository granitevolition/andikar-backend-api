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
    export SQLALCHEMY_DATABASE_URL="${DATABASE_URL}"
else
    echo "Host postgres.railway.internal is not reachable!"
    echo "Trying with DATABASE_PUBLIC_URL instead..."
    
    # Extract host and port from DATABASE_PUBLIC_URL
    if [[ -n "$DATABASE_PUBLIC_URL" ]]; then
        DB_HOST=$(echo $DATABASE_PUBLIC_URL | sed -E 's/.*@([^:]+):.*/\1/')
        DB_PORT=$(echo $DATABASE_PUBLIC_URL | sed -E 's/.*:([0-9]+).*/\1/')
        
        echo "Checking if host $DB_HOST is reachable on port $DB_PORT..."
        if nc -z -w 5 $DB_HOST $DB_PORT; then
            echo "Public database host $DB_HOST is reachable! Using DATABASE_PUBLIC_URL."
            export SQLALCHEMY_DATABASE_URL="${DATABASE_PUBLIC_URL}"
        else
            echo "Error: Neither postgres.railway.internal nor $DB_HOST:$DB_PORT are reachable!"
            echo "Using SQLite fallback database..."
            export SQLALCHEMY_DATABASE_URL="sqlite:///./andikar.db"
        fi
    else
        echo "No DATABASE_PUBLIC_URL set, using SQLite fallback database..."
        export SQLALCHEMY_DATABASE_URL="sqlite:///./andikar.db"
    fi
fi

echo "Waiting for database to be ready..."
echo "Checking database connection..."

# Start the application using the new entrypoint
echo "Starting application on port ${PORT:-8080}..."
exec python -m entrypoint
