#!/usr/bin/env python3
"""
Health Check Service for Andikar Backend API

This module provides a simple HTTP service for health checks.
Railway uses the /status endpoint to determine if the service is healthy.
"""

import os
import sys
import logging
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("health-check")

try:
    # Import database utils
    from database import get_db, engine
    from models import Base
except ImportError as e:
    logger.error(f"Error importing database modules: {e}")
    logger.error("Health check will run with limited functionality")
    get_db = None
    engine = None
    Base = None

# Create FastAPI app
app = FastAPI(
    title="Andikar Health Check",
    description="Health check service for Andikar Backend API",
    version="1.0.0"
)

@app.get("/status")
async def status():
    """Simple status endpoint for Railway health checks."""
    return {
        "status": "healthy",
        "message": "Service is operational"
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db) if get_db else None):
    """Detailed health check endpoint providing system status."""
    # Basic service check
    status_info = {
        "service": "healthy",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }
    
    # Database check
    if db is not None:
        try:
            db.execute(text("SELECT 1"))
            status_info["database"] = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            status_info["database"] = f"error: {str(e)}"
            status_info["status"] = "degraded"
    else:
        status_info["database"] = "unavailable"
        status_info["status"] = "degraded"
    
    # Environment info
    status_info["environment"] = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
    
    # Overall status
    if "status" not in status_info:
        status_info["status"] = "healthy"
    
    return status_info

def main():
    """Run the health check service."""
    import uvicorn
    port = int(os.getenv("HEALTH_PORT", "8081"))
    logger.info(f"Starting health check service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
