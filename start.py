#!/usr/bin/env python
import os
import sys
import logging
import time
import threading
import uvicorn
import asyncio
from fastapi import FastAPI

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("startup")

# Create a minimal FastAPI app that responds immediately to health checks
minimal_app = FastAPI()

@minimal_app.get("/health")
async def minimal_health():
    """Simple health check that responds immediately"""
    return {"status": "healthy"}

@minimal_app.get("/")
async def minimal_root():
    """Simple root endpoint that responds immediately"""
    return {"status": "Andikar API is starting up, please wait..."}

def start_minimal_app():
    """Start the minimal app on a separate port"""
    minimal_port = int(os.environ.get("MINIMAL_PORT", 8081))
    logger.info(f"Starting minimal app on port {minimal_port}")
    
    # Configure uvicorn to run the minimal app
    minimal_config = uvicorn.Config(
        app=minimal_app,
        host="0.0.0.0",
        port=minimal_port,
        log_level="info"
    )
    minimal_server = uvicorn.Server(minimal_config)
    
    # Start the minimal server
    asyncio.run(minimal_server.serve())

def start_main_app():
    """Start the main app after a short delay"""
    time.sleep(3)  # Brief delay to ensure minimal app is running
    
    # Get port from environment variable or use default
    try:
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Starting main app on port {port}")
    except ValueError:
        port = 8080
        logger.warning(f"Invalid PORT value, using default: {port}")
    
    # Print environment variables for debugging (excluding sensitive ones)
    logger.info("Environment variables:")
    for key, value in os.environ.items():
        if not any(sensitive in key.lower() for sensitive in ["key", "secret", "password", "token"]):
            logger.info(f"  {key}: {value}")
    
    # Start the main app
    try:
        # Use os.system for simplicity and to avoid blocking issues
        os.system(f"uvicorn main:app --host 0.0.0.0 --port {port}")
    except Exception as e:
        logger.error(f"Error starting main app: {e}")
        sys.exit(1)

def main():
    # Configure the reverse proxy for Railway
    os.environ["MINIMAL_PORT"] = "8081"
    
    # Configure PORT to be used by Railway healthchecks
    if "PORT" in os.environ:
        os.environ["MAIN_PORT"] = os.environ["PORT"]
    
    # Start the minimal app in a separate thread
    minimal_thread = threading.Thread(target=start_minimal_app)
    minimal_thread.daemon = True
    minimal_thread.start()
    
    # Start the main app in the main thread
    start_main_app()

if __name__ == "__main__":
    main()
