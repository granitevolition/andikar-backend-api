#!/bin/bash
set -e

echo "Starting Andikar Backend API..."

# Check if DATABASE_URL or DATABASE_PUBLIC_URL environment variable is set
if [ -n "$DATABASE_PUBLIC_URL" ]; then
  echo "Using DATABASE_PUBLIC_URL."
  export DATABASE_URL="$DATABASE_PUBLIC_URL"
elif [ -z "$DATABASE_URL" ]; then
  echo "Warning: No DATABASE_URL or DATABASE_PUBLIC_URL provided. Using default SQLite database."
  export DATABASE_URL="sqlite:///./andikar.db"
fi

# Check database connection
echo "Checking database connection..."
python -c "
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
import os

db_url = os.environ.get('DATABASE_URL')
max_retries = 5
retry_interval = 3

for i in range(max_retries):
    try:
        engine = create_engine(db_url)
        conn = engine.connect()
        conn.close()
        print('Database connection successful')
        break
    except OperationalError as e:
        if i < max_retries - 1:
            print(f'Database connection failed, retrying in {retry_interval} seconds... ({i+1}/{max_retries})')
            print(f'Error: {str(e)}')
            time.sleep(retry_interval)
        else:
            print('Failed to connect to the database after multiple retries')
            raise
"

# Run database migrations
echo "Running database migrations..."
python -c "
from sqlalchemy import create_engine, text
from models import Base
import os

db_url = os.environ.get('DATABASE_URL')
engine = create_engine(db_url)

# Check if tables already exist
try:
    conn = engine.connect()
    # Check if 'users' table exists as a basic check
    result = conn.execute(text(\"SELECT 1 FROM information_schema.tables WHERE table_name='users'\")).fetchone()
    if result:
        print('Database tables already exist, skipping migrations')
    else:
        print('Creating database tables...')
        Base.metadata.create_all(engine)
        print('Database tables created successfully')
    conn.close()
except Exception as e:
    print(f'Error checking database: {str(e)}')
    print('Creating database tables as fallback...')
    Base.metadata.create_all(engine)
    print('Database tables created successfully')
"

# Start the application
echo "Starting application on port ${PORT:-8080}..."
if [ -n "$DEBUG" ] && [ "$DEBUG" = "1" ]; then
  uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}" --reload
else
  uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"
fi
