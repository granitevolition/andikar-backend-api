#!/bin/bash
set -e

# Print all environment variables (masked) to help debug
echo "Environment variables:"
env | grep -v "_KEY\|_SECRET\|PASSWORD" | sort

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
  echo "WARNING: DATABASE_URL is not set!"
  
  # Check if we have a PostgreSQL service attached in Railway
  if [ ! -z "$PGHOST" ] && [ ! -z "$PGDATABASE" ] && [ ! -z "$PGUSER" ]; then
    echo "Found PostgreSQL environment variables, constructing DATABASE_URL..."
    export DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT:-5432}/${PGDATABASE}"
    echo "DATABASE_URL constructed from PostgreSQL environment variables"
  else
    echo "No PostgreSQL environment variables found either. Using a default in-memory SQLite database for testing."
    export DATABASE_URL="sqlite:///./test.db"
    echo "Set DATABASE_URL to: sqlite:///./test.db"
  fi
fi

# Function to check if database is ready
function check_db() {
  echo "Checking database connection..."
  
  # First, determine what type of database we're using
  if [[ "$DATABASE_URL" == sqlite* ]]; then
    echo "Using SQLite database, no connection check needed"
    return 0
  fi
  
  python -c "
import os
import sys
import time
import socket
import urllib.parse

# Get database URL from environment variable
db_url = os.getenv('DATABASE_URL', '')
if not db_url:
    print('DATABASE_URL is not set')
    sys.exit(1)

try:
    # Handle both postgres:// and postgresql:// formats
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    # Parse the connection string
    parsed = urllib.parse.urlparse(db_url)
    
    if parsed.scheme not in ['postgresql', 'postgres']:
        print(f'Using {parsed.scheme} database, skipping connection check')
        sys.exit(0)
    
    # Extract host and port
    host = parsed.hostname
    port = parsed.port or 5432
    
    # First try a basic socket connection to see if the host is reachable
    print(f'Checking if host {host} is reachable on port {port}...')
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3)
    s.connect((host, port))
    s.close()
    
    # Now try a proper database connection
    print('Host is reachable, attempting database connection...')
    
    # Try to import psycopg2, if it fails, skip the check
    try:
        import psycopg2
    except ImportError:
        print('psycopg2 not installed, skipping database connection check')
        sys.exit(0)
    
    # Extract connection parameters
    user = parsed.username
    password = parsed.password
    dbname = parsed.path[1:]  # Remove leading '/'
    
    # Connect to the database
    conn = psycopg2.connect(
        dbname=dbname,
        user=user,
        password=password,
        host=host,
        port=port,
        connect_timeout=5
    )
    conn.close()
    print('Database connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Database connection failed: {str(e)}')
    sys.exit(1)
"
}

# Wait for the database to be ready
echo "Waiting for database to be ready..."
max_retries=10
retry_count=0

until check_db || [ $retry_count -eq $max_retries ]; do
  echo "Database not ready yet. Waiting..."
  sleep 3
  retry_count=$((retry_count+1))
done

if [ $retry_count -eq $max_retries ]; then
  echo "WARNING: Could not verify database connection after $max_retries attempts"
  echo "Will attempt to continue anyway..."
fi

# Run database migrations
echo "Running database migrations..."
if [[ "$DATABASE_URL" == sqlite* ]]; then
  echo "Creating SQLite database..."
  # For SQLite, let's make sure the directory exists
  mkdir -p $(dirname "${DATABASE_URL#sqlite:///}")
fi

# Run migrations with error handling
if alembic upgrade head; then
  echo "Database migrations completed successfully"
else
  echo "WARNING: Database migrations failed, but will attempt to continue..."
fi

# Set the port from environment or default to 8000
PORT=${PORT:-8000}
echo "Starting application on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT
