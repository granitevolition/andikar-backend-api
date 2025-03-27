#!/usr/bin/env python3
"""
Railway Start Script

Ultra-minimal Python script designed specifically for Railway deployment.
This script handles the startup of the simple status server.
"""

import os
import sys
import logging
from fastapi import FastAPI
import uvicorn

# Set up logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("railway-start")

# Print diagnostic information
logger.info("Starting Railway deployment process")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Files in current directory: {os.listdir('.')}")

# Set up a very simple FastAPI app
app = FastAPI()

@app.get("/status")
async def status():
    """Health check endpoint for Railway."""
    return {"status": "healthy"}

@app.get("/health")
async def health():
    """More detailed health check."""
    return {
        "status": "healthy",
        "message": "Service is running",
        "environment": os.environ.get("RAILWAY_ENVIRONMENT_NAME", "unknown")
    }

@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "service": "Andikar Backend API",
        "status": "running",
        "check": "/status",
        "health": "/health"
    }

# Main entry point
if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=port)
