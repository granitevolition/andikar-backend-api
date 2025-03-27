#!/usr/bin/env python3
"""
Railway Entry Point

This script serves as a direct Python entry point for Railway deployment.
It ensures that the /status endpoint is immediately available and then
launches the main application.
"""
import os
import sys
import logging
import threading
import time

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("railway-entry")

# Create a simple FastAPI app with a /status endpoint
app = FastAPI(
    title="Andikar API",
    description="Andikar Backend API Gateway",
    version="1.0.0"
)

@app.get("/status")
async def status():
    """Health check endpoint for Railway."""
    return {"status": "healthy", "message": "Service is operational"}

@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "api": "running",
            "database": "initializing"
        }
    }

def launch_main_app():
    """Launch the main application in a subprocess."""
    logger.info("Starting initialization...")
    
    # Execute the start.sh script with bash
    try:
        import subprocess
        # Set environment variables for database connection
        env_vars = os.environ.copy()
        pguser = env_vars.get("PGUSER", "postgres")
        pgpassword = env_vars.get("PGPASSWORD") or env_vars.get("POSTGRES_PASSWORD")
        pgdatabase = env_vars.get("PGDATABASE", "railway")
        proxy_domain = env_vars.get("RAILWAY_TCP_PROXY_DOMAIN")
        proxy_port = env_vars.get("RAILWAY_TCP_PROXY_PORT")
        
        if pgpassword and proxy_domain and proxy_port:
            # Set DATABASE_URL
            import urllib.parse
            encoded_password = urllib.parse.quote_plus(pgpassword)
            env_vars["DATABASE_URL"] = f"postgresql://{pguser}:{encoded_password}@{proxy_domain}:{proxy_port}/{pgdatabase}"
            logger.info(f"Set DATABASE_URL for database connection")
        
        # Start the main application using database.py's init_db function
        try:
            logger.info("Importing database modules...")
            from database import engine, init_db
            
            if engine:
                logger.info("Database engine created successfully")
                
                # Initialize database
                result = init_db()
                if result:
                    logger.info("Database initialization successful")
                else:
                    logger.warning("Database initialization partially successful")
            else:
                logger.error("Failed to create database engine")
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            
        # Launch main application logic directly
        logger.info("Starting main application process...")
        try:
            from app import app as main_app
            # We're already running the FastAPI server,
            # so we don't need to start another one
            # Just incorporate the routes from main_app
            app.mount("/api", main_app)
            logger.info("Main application mounted successfully")
        except Exception as e:
            logger.error(f"Failed to start main application: {e}")
            
    except Exception as e:
        logger.error(f"Error in launch_main_app: {e}")
        import traceback
        logger.error(traceback.format_exc())

# Start the main app in a background thread
main_app_thread = threading.Thread(target=launch_main_app)
main_app_thread.daemon = True

if __name__ == "__main__":
    # Set up environment
    port = int(os.environ.get("PORT", "8080"))
    
    # Start the background thread
    main_app_thread.start()
    
    # Run the FastAPI app
    logger.info(f"Starting Railway entry point on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
