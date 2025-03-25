#!/bin/bash
set -e

# Print all environment variables (masked) to help debug
echo "Environment variables:"
env | grep -v "_KEY\|_SECRET\|_PASSWORD\|_PASS" | sort

# Try to export DATABASE_PUBLIC_URL as DATABASE_URL if needed
if [ -z "$DATABASE_URL" ] && [ ! -z "$DATABASE_PUBLIC_URL" ]; then
  echo "DATABASE_URL is not set but DATABASE_PUBLIC_URL is available. Using DATABASE_PUBLIC_URL instead."
  export DATABASE_URL="$DATABASE_PUBLIC_URL"
  echo "Set DATABASE_URL to: ${DATABASE_PUBLIC_URL//:*@/:****@}"
fi

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

# Simple function to extract host from URL
get_host_from_url() {
  local url=$1
  if [[ $url == *"@"* ]]; then
    echo $url | sed -e 's/.*@\([^:]*\).*/\1/'
  else
    echo ""
  fi
}

# Simple function to check if host is reachable
is_host_reachable() {
  local host=$1
  local port=$2
  nc -z -w3 $host $port 2>/dev/null
  return $?
}

# Try to check if DATABASE_URL points to a reachable host
db_host=$(get_host_from_url "$DATABASE_URL")
if [ ! -z "$db_host" ]; then
  echo "Checking if host $db_host is reachable..."
  if ! is_host_reachable $db_host 5432; then
    echo "Host $db_host is not reachable!"
    
    # Try with DATABASE_PUBLIC_URL if it exists and is different
    if [ ! -z "$DATABASE_PUBLIC_URL" ] && [ "$DATABASE_URL" != "$DATABASE_PUBLIC_URL" ]; then
      echo "Trying with DATABASE_PUBLIC_URL instead..."
      public_db_host=$(get_host_from_url "$DATABASE_PUBLIC_URL")
      if [ ! -z "$public_db_host" ]; then
        if is_host_reachable $public_db_host ${DATABASE_PUBLIC_URL##*:}; then
          echo "Public database host $public_db_host is reachable! Using DATABASE_PUBLIC_URL."
          export DATABASE_URL="$DATABASE_PUBLIC_URL"
        else
          echo "Public database host $public_db_host is also not reachable."
        fi
      fi
    fi
  else
    echo "Host $db_host is reachable."
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
    
    # Host is reachable, now try a proper database connection
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
    
    # Try a public DATABASE_URL if available and different from the current one
    try:
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
    except Exception as e1:
        public_url = os.getenv('DATABASE_PUBLIC_URL')
        if public_url and public_url != db_url:
            print(f'Primary connection failed: {str(e1)}')
            print('Trying with DATABASE_PUBLIC_URL...')
            try:
                if public_url.startswith('postgres://'):
                    public_url = public_url.replace('postgres://', 'postgresql://', 1)
                
                parsed = urllib.parse.urlparse(public_url)
                host = parsed.hostname
                port = parsed.port or 5432
                user = parsed.username
                password = parsed.password
                dbname = parsed.path[1:]
                
                # Connect using the public URL
                conn = psycopg2.connect(
                    dbname=dbname,
                    user=user,
                    password=password,
                    host=host,
                    port=port,
                    connect_timeout=5
                )
                conn.close()
                print('Database connection successful using DATABASE_PUBLIC_URL')
                # Set this as the primary URL for future use
                os.environ['DATABASE_URL'] = public_url
                sys.exit(0)
            except Exception as e2:
                print(f'Public connection also failed: {str(e2)}')
                sys.exit(1)
        else:
            print(f'Database connection failed: {str(e1)}')
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
  sleep 3
  retry_count=$((retry_count+1))
done

if [ $retry_count -eq $max_retries ]; then
  echo "WARNING: Could not verify database connection after $max_retries attempts"
  echo "Checking if we have DATABASE_PUBLIC_URL to try instead..."
  
  if [ ! -z "$DATABASE_PUBLIC_URL" ] && [ "$DATABASE_URL" != "$DATABASE_PUBLIC_URL" ]; then
    echo "Trying with DATABASE_PUBLIC_URL instead..."
    export DATABASE_URL="$DATABASE_PUBLIC_URL"
    
    # Reset retry counter and try again with public URL
    retry_count=0
    until check_db || [ $retry_count -eq $max_retries ]; do
      echo "Database not ready yet (using public URL). Waiting..."
      sleep 3
      retry_count=$((retry_count+1))
    done
    
    if [ $retry_count -eq $max_retries ]; then
      echo "WARNING: Could not verify database connection with public URL either"
      echo "Will attempt to continue with SQLite fallback..."
      export DATABASE_URL="sqlite:///./fallback.db"
    fi
  else
    echo "No alternative DATABASE_PUBLIC_URL available or already tried"
    echo "Will attempt to continue with SQLite fallback..."
    export DATABASE_URL="sqlite:///./fallback.db"
  fi
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
