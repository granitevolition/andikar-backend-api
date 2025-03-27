#!/usr/bin/env python3
"""
Railway Start Script

This script handles the startup of the Andikar Backend API.
"""

import os
import sys
import logging
import importlib.util
import traceback
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

# Check if templates directory exists
if os.path.exists("templates"):
    logger.info(f"Templates directory found with contents: {os.listdir('templates')}")
    if os.path.exists("templates/admin"):
        logger.info(f"Admin templates found with contents: {os.listdir('templates/admin')}")
else:
    logger.warning("Templates directory not found")

# Check if static directory exists
if os.path.exists("static"):
    logger.info(f"Static directory found with contents: {os.listdir('static')}")
else:
    logger.warning("Static directory not found")

# Run the test script to diagnose import issues
try:
    from test_import import logger as test_logger
    logger.info("Test import script executed successfully")
except Exception as e:
    logger.error(f"Failed to run test import script: {e}")
    logger.error(traceback.format_exc())

try:
    logger.info("Importing main application from app.py")
    # Try to import the main application from app.py
    from app import app as main_app
    logger.info("Successfully imported main application")
    
    # List available routes
    routes = [{"path": route.path, "name": route.name} for route in main_app.routes]
    logger.info(f"Available routes: {routes}")
    
    # Test if the admin routes are available
    admin_routes = [r for r in routes if '/admin' in r['path']]
    if admin_routes:
        logger.info(f"Admin routes found: {admin_routes}")
    else:
        logger.warning("No admin routes found in the imported app")
    
    # Use the main application from app.py
    app = main_app
    
except Exception as e:
    logger.error(f"Failed to import main application: {e}")
    logger.error(traceback.format_exc())
    
    # Fall back to a simple status server if the main app can't be loaded
    logger.warning("Falling back to simple status server")
    app = FastAPI(title="Andikar API Status Server", version="1.0.0")
    
    # Try to serve static files
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
        logger.info("Static files mounted successfully")
    except Exception as e:
        logger.warning(f"Could not mount static files: {e}")
    
    # Try to set up templates
    try:
        templates = Jinja2Templates(directory="templates")
        logger.info("Templates initialized successfully")
    except Exception as e:
        logger.warning(f"Could not initialize templates: {e}")
        templates = None
    
    @app.get("/status")
    async def status():
        """Health check endpoint for Railway."""
        return {
            "service": "Andikar API Status Server",
            "version": "1.0.0",
            "health_endpoint": "/status"
        }
    
    @app.get("/", response_class=HTMLResponse)
    async def root(request: Request):
        """Root endpoint with basic info."""
        if templates:
            try:
                logger.info("Rendering index template")
                return templates.TemplateResponse("index.html", {
                    "request": request,
                    "title": "Andikar API Status Server",
                })
            except Exception as e:
                logger.error(f"Error rendering template: {e}")
        
        # Fallback HTML if templates aren't working
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Andikar API Status Server</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 1rem;
                }}
                .error-box {{
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                    padding: 1rem;
                    border-radius: 0.25rem;
                    margin-bottom: 1rem;
                }}
                .debug-info {{
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    padding: 1rem;
                    border-radius: 0.25rem;
                    margin-top: 1rem;
                    white-space: pre-wrap;
                    font-family: monospace;
                    font-size: 0.875rem;
                }}
            </style>
        </head>
        <body>
            <h1>Andikar API Status Server</h1>
            <p>This is a fallback server because the main application could not be loaded.</p>
            
            <div class="error-box">
                <h2>Error Information</h2>
                <p>The main application could not be loaded due to an error.</p>
                <p>Error: {str(e) if 'e' in locals() else "Unknown error"}</p>
            </div>
            
            <div>
                <h2>Available Endpoints</h2>
                <ul>
                    <li><a href="/status">/status</a> - Health check endpoint</li>
                    <li><a href="/debug">/debug</a> - System diagnostic information</li>
                </ul>
            </div>
        </body>
        </html>
        """)
    
    @app.get("/debug")
    async def debug():
        """Debug endpoint with system information."""
        try:
            # Execute pip list to check installed packages
            import subprocess
            pip_output = subprocess.check_output(['pip', 'list']).decode('utf-8')
        except Exception as e:
            pip_output = f"Error running pip list: {e}"
        
        # Get environment variables (excluding sensitive ones)
        env_vars = {}
        for key, value in os.environ.items():
            if any(sensitive in key.lower() for sensitive in ['secret', 'password', 'token', 'key']):
                env_vars[key] = '********'
            else:
                env_vars[key] = value
        
        # Check template directory
        template_info = {}
        if os.path.exists("templates"):
            template_info["exists"] = True
            template_info["files"] = os.listdir("templates")
            
            # Check admin templates
            if os.path.exists("templates/admin"):
                template_info["admin_exists"] = True
                template_info["admin_files"] = os.listdir("templates/admin")
            else:
                template_info["admin_exists"] = False
        else:
            template_info["exists"] = False
        
        return {
            "service": "Andikar API Debug Information",
            "python_version": sys.version,
            "current_directory": os.getcwd(),
            "directory_contents": os.listdir('.'),
            "template_info": template_info,
            "pip_packages": pip_output,
            "environment_variables": env_vars
        }

# Main entry point
if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=port)
