#!/usr/bin/env python
import os
import time
import subprocess
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

print("Starting Andikar Backend API...")

# Check if DATABASE_URL or DATABASE_PUBLIC_URL environment variable is set
if os.environ.get("DATABASE_PUBLIC_URL"):
    print("Using DATABASE_PUBLIC_URL.")
    os.environ["DATABASE_URL"] = os.environ["DATABASE_PUBLIC_URL"]
elif not os.environ.get("DATABASE_URL"):
    print("Warning: No DATABASE_URL or DATABASE_PUBLIC_URL provided. Using default SQLite database.")
    os.environ["DATABASE_URL"] = "sqlite:///./andikar.db"

# Check database connection
print("Checking database connection...")
db_url = os.environ.get("DATABASE_URL")
max_retries = 5
retry_interval = 3

for i in range(max_retries):
    try:
        engine = create_engine(db_url)
        conn = engine.connect()
        conn.close()
        print("Database connection successful")
        break
    except OperationalError as e:
        if i < max_retries - 1:
            print(f"Database connection failed, retrying in {retry_interval} seconds... ({i+1}/{max_retries})")
            print(f"Error: {str(e)}")
            time.sleep(retry_interval)
        else:
            print("Failed to connect to the database after multiple retries")
            raise

# Run database migrations
print("Checking if database tables already exist...")
try:
    engine = create_engine(db_url)
    conn = engine.connect()
    try:
        # Check if 'users' table exists as a basic check
        result = conn.execute(text("SELECT 1 FROM information_schema.tables WHERE table_name='users'")).fetchone()
        if result:
            print("Database tables already exist, skipping migrations")
        else:
            print("Creating database tables...")
            from models import Base
            Base.metadata.create_all(engine)
            print("Database tables created successfully")
    except Exception as e:
        print(f"Error checking database: {str(e)}")
        print("Creating database tables as fallback...")
        from models import Base
        Base.metadata.create_all(engine)
        print("Database tables created successfully")
    conn.close()
except Exception as e:
    print(f"Error during database initialization: {str(e)}")
    # Continue anyway, the app might handle this properly

# Start the application
port = os.environ.get("PORT", "8080")
print(f"Starting application on port {port}...")

if os.environ.get("DEBUG") == "1":
    os.execvp("uvicorn", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", port, "--reload"])
else:
    os.execvp("uvicorn", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", port])
