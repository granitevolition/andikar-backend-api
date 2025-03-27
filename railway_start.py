#!/usr/bin/env python3
"""
Railway Start Script

This script handles the startup of the Andikar Backend API.
"""

import os
import sys
import logging
import importlib.util
import uvicorn

# Set up logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("railway-start")

# Print diagnostic information
logger.info("Starting Andikar Backend API deployment process")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Files in current directory: {os.listdir('.')}")

try:
    logger.info("Importing main application from app.py")
    # Try to import the main application from app.py
    from app import app as main_app
    logger.info("Successfully imported main application")
    
    # List available routes
    routes = [{"path": route.path, "name": route.name} for route in main_app.routes]
    logger.info(f"Available routes: {routes}")
    
    # Use the main application from app.py
    app = main_app
    
except Exception as e:
    logger.error(f"Failed to import main application: {e}")
    import traceback
    logger.error(traceback.format_exc())
    
    # Fall back to a simple status server if the main app can't be loaded
    logger.warning("Falling back to simple status server")
    from fastapi import FastAPI
    app = FastAPI(title="Andikar API Status Server", version="1.0.0")
    
    @app.get("/status")
    async def status():
        """Health check endpoint for Railway."""
        return {
            "service": "Andikar API Status Server",
            "version": "1.0.0",
            "health_endpoint": "/status"
        }
    
    @app.get("/")
    async def root():
        """Root endpoint with basic info."""
        return {
            "service": "Andikar API Status Server",
            "message": "Main application could not be loaded. Using fallback server.",
            "error": str(e) if 'e' in locals() else "Unknown error"
        }

# Main entry point
if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=port)
