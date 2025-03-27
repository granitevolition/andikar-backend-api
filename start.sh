#!/bin/bash

# Andikar Backend API Startup Script
# This script handles the startup process for the Andikar Backend API
# It ensures proper environment setup and database initialization

set -e

echo "========== ANDIKAR BACKEND API STARTUP =========="
echo "Running as user: $(whoami)"
echo "Current directory: $(pwd)"
echo "Timestamp: $(date)"

# Set up DATABASE_URL explicitly using environment variables
echo "Setting up database connection..."
# Use the hardcoded password if environment variable isn't set
export PGUSER=${PGUSER:-postgres}
export PGDATABASE=${PGDATABASE:-railway}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-ztJggTeesPJYVMHRWuGVbnUinMKwCWyI}
export PGPASSWORD=${PGPASSWORD:-$POSTGRES_PASSWORD}
export RAILWAY_TCP_PROXY_DOMAIN=${RAILWAY_TCP_PROXY_DOMAIN:-ballast.proxy.rlwy.net}
export RAILWAY_TCP_PROXY_PORT=${RAILWAY_TCP_PROXY_PORT:-11148}

# Always use the TCP proxy connection - encode password for URL safety
ENCODED_PASSWORD=$(echo -n "$POSTGRES_PASSWORD" | python -c "import sys, urllib.parse; print(urllib.parse.quote_plus(sys.stdin.read()))")
export DATABASE_URL="postgresql://$PGUSER:$ENCODED_PASSWORD@$RAILWAY_TCP_PROXY_DOMAIN:$RAILWAY_TCP_PROXY_PORT/$PGDATABASE"
echo "Database URL set to: postgresql://$PGUSER:****@$RAILWAY_TCP_PROXY_DOMAIN:$RAILWAY_TCP_PROXY_PORT/$PGDATABASE"

# Display environment variables (excluding sensitive data)
echo "Environment variables (excluding sensitive data):"
env | grep -v PASSWORD | grep -v SECRET | grep -v KEY | grep -v TOKEN | grep -v PASSWORD | sort

# Run database diagnostic 
echo "Running database diagnostic tool..."
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

# Create health check endpoint
echo "Creating health check endpoint..."
cat > /app/health_check.py << 'EOF'
#!/usr/bin/env python3
from fastapi import FastAPI, Depends
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import text

app = FastAPI()

@app.get("/status")
async def status():
    """Health check endpoint for Railway"""
    return {"status": "healthy"}

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    """Detailed health check endpoint"""
    db_status = "unknown"
    
    try:
        if db is not None:
            db.execute(text("SELECT 1"))
            db_status = "healthy"
        else:
            db_status = "unavailable"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "api": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
EOF

# Start the application using the entrypoint
echo "Starting application on port ${PORT:-8080}..."
exec python -m entrypoint
