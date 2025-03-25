#!/usr/bin/env python
import os
import sys
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("startup")

def main():
    # Get port from environment variable or use default
    try:
        port = int(os.environ.get("PORT", 8080))
        logger.info(f"Using port: {port}")
    except ValueError:
        port = 8080
        logger.warning(f"Invalid PORT value, using default: {port}")
    
    # Print environment variables for debugging (excluding sensitive ones)
    logger.info("Environment variables:")
    for key, value in os.environ.items():
        if not ("key" in key.lower() or "secret" in key.lower() or "password" in key.lower()):
            logger.info(f"  {key}: {value}")
    
    # Start uvicorn with the specified port
    logger.info(f"Starting uvicorn on port {port}")
    cmd = ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(port)]
    
    try:
        subprocess.run(cmd)
    except Exception as e:
        logger.error(f"Error starting uvicorn: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
