#!/bin/bash
set -e

# Function to check if database is ready
function check_db() {
  python -c "
import os
import sys
import time
import psycopg2

# Get database URL from environment variable
db_url = os.getenv('DATABASE_URL', '')
if not db_url:
    print('DATABASE_URL is not set')
    sys.exit(1)

# Extract connection parameters from URL
try:
    # Handle both postgres:// and postgresql:// formats
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    
    # Parse the connection string
    if '@' in db_url:
        auth, rest = db_url.split('@', 1)
        if '://' in auth:
            _, auth = auth.split('://', 1)
        user_pass, host_port_db = rest.split('/', 1)
        host_port, db = host_port_db.split('/', 1)
        
        if ':' in user_pass:
            user, password = user_pass.split(':', 1)
        else:
            user, password = user_pass, ''
            
        if ':' in host_port:
            host, port = host_port.split(':', 1)
        else:
            host, port = host_port, '5432'
        
        # Try to connect to the database
        conn = psycopg2.connect(
            dbname=db,
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.close()
        print('Database connection successful')
        sys.exit(0)
    else:
        print('Invalid DATABASE_URL format')
        sys.exit(1)
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
  sleep 2
  retry_count=$((retry_count+1))
done

if [ $retry_count -eq $max_retries ]; then
  echo "Error: Could not connect to the database after $max_retries attempts"
  exit 1
fi

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Set the port from environment or default to 8000
PORT=${PORT:-8000}
echo "Starting application on port $PORT..."
uvicorn main:app --host 0.0.0.0 --port $PORT
