"""
Enhanced startup script for Andikar Backend API.

This script provides a two-phase startup process:
1. A simple FastAPI app that serves a status page while the main app is starting
2. Graceful transition to the main application once initialization is complete

This ensures users always get a response, even during startup/initialization.
"""
import asyncio
import os
import time
import threading
import logging
import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
try:
    from fastapi.templating import Jinja2Templates
    TEMPLATES_AVAILABLE = True
except (ImportError, AssertionError):
    TEMPLATES_AVAILABLE = False
from fastapi.staticfiles import StaticFiles

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("andikar-entrypoint")

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Global variables
startup_complete = False
startup_progress = 0
startup_status = "initializing"
startup_message = "Andikar Backend API is starting up..."

# Create a simple startup app
startup_app = FastAPI(
    title="Andikar Backend API Startup",
    description="Starting up Andikar Backend API",
    version="1.0.0"
)

# Set up templates if available
if TEMPLATES_AVAILABLE:
    templates = Jinja2Templates(directory="templates")

    # Create status page HTML template if it doesn't exist
    status_template_path = os.path.join("templates", "status.html")
    if not os.path.exists(status_template_path):
        with open(status_template_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Andikar Backend API - Starting Up</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <meta http-equiv="refresh" content="5">
    <style>
        body {
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .startup-container {
            max-width: 600px;
            text-align: center;
            padding: 2rem;
        }
        .logo i {
            font-size: 48px;
            color: #0d6efd;
            margin-bottom: 1rem;
        }
        .progress {
            height: 10px;
            margin: 1.5rem 0;
        }
        .status-message {
            margin: 1rem 0;
            font-size: 1.1rem;
        }
        .spinner-border {
            width: 3rem;
            height: 3rem;
            color: #0d6efd;
        }
        .footer {
            margin-top: 2rem;
            color: #6c757d;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <div class="startup-container">
        <div class="logo">
            <i class="fas fa-robot"></i>
            <h1>Andikar Backend API</h1>
            <p class="lead text-muted">System is starting up</p>
        </div>
        
        <div class="spinner-border mb-4" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        
        <div class="progress">
            <div class="progress-bar progress-bar-striped progress-bar-animated" 
                role="progressbar" 
                style="width: {{ progress }}%;" 
                aria-valuenow="{{ progress }}" 
                aria-valuemin="0" 
                aria-valuemax="100">
                {{ progress }}%
            </div>
        </div>
        
        <div class="status-message">
            <strong>Status:</strong> {{ status }}
            <p>{{ message }}</p>
        </div>
        
        <div class="footer">
            <p>This page will automatically refresh every 5 seconds</p>
            <p>© 2025 Andikar. All rights reserved.</p>
        </div>
    </div>
</body>
</html>""")

# Mount static files
try:
    startup_app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {str(e)}")

# Status page route
@startup_app.get("/", response_class=HTMLResponse)
async def status_page(request: Request):
    if TEMPLATES_AVAILABLE:
        return templates.TemplateResponse("status.html", {
            "request": request,
            "progress": startup_progress,
            "status": startup_status,
            "message": startup_message
        })
    else:
        # Fallback HTML if templates not available
        html_content = f"""
        <html>
            <head>
                <title>Andikar Backend API - Starting Up</title>
                <meta http-equiv="refresh" content="5">
            </head>
            <body>
                <h1>Andikar Backend API</h1>
                <p>Status: {startup_status}</p>
                <p>Progress: {startup_progress}%</p>
                <p>{startup_message}</p>
                <p>This page will automatically refresh every 5 seconds</p>
            </body>
        </html>
        """
        return HTMLResponse(content=html_content)

# Status API route
@startup_app.get("/status")
async def status_api():
    return {
        "status": startup_status,
        "progress": startup_progress,
        "message": startup_message,
        "complete": startup_complete
    }

# All other routes redirect to status page during startup
@startup_app.get("/{path:path}")
async def catch_all(path: str):
    return RedirectResponse(url="/")

def update_startup_progress(status, message, progress):
    global startup_status, startup_message, startup_progress
    startup_status = status
    startup_message = message
    startup_progress = progress
    logger.info(f"Startup progress: {progress}% - {status}: {message}")

def run_main_app():
    global startup_complete, startup_status, startup_message, startup_progress
    
    try:
        # Update status to connecting to database
        update_startup_progress("database_check", "Checking database connection...", 10)
        time.sleep(1)  # Simulate database connection time
        
        # Update status to initializing database
        update_startup_progress("database_init", "Initializing database...", 30)
        time.sleep(1)  # Simulate database initialization time
        
        # Update status to loading routes
        update_startup_progress("loading_routes", "Loading API routes...", 50)
        time.sleep(1)  # Simulate route loading time
        
        # Update status to loading templates
        update_startup_progress("loading_templates", "Loading templates...", 70)
        time.sleep(1)  # Simulate template loading time
        
        # Update status to finishing up
        update_startup_progress("finishing", "Finishing startup process...", 90)
        time.sleep(1)  # Simulate final startup tasks
        
        try:
            # Import main app here to avoid circular imports
            from main import app as main_app
            
            # Mark startup as complete
            update_startup_progress("complete", "Startup complete! Redirecting to main application...", 100)
            startup_complete = True
            
            # Run the main app using Uvicorn
            import uvicorn
            port = int(os.getenv("PORT", "8080"))
            uvicorn.run(main_app, host="0.0.0.0", port=port)
        except ImportError:
            logger.error("Could not import main app, falling back to simple app")
            raise
        
    except Exception as e:
        # Log the error
        logger.error(f"Error starting main app: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Update status to error
        update_startup_progress("error", f"Error starting application: {str(e)}", 0)
        
        # Create basic index.html if it doesn't exist
        if not os.path.exists("templates/index.html"):
            os.makedirs("templates", exist_ok=True)
            with open("templates/index.html", "w") as f:
                f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Andikar Backend API</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding: 2rem; font-family: system-ui, sans-serif; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { margin-bottom: 1rem; }
        .card { margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Andikar Backend API</h1>
        <div class="alert alert-warning">
            The application is experiencing difficulties starting up. Basic navigation is available below.
        </div>
        
        <div class="card">
            <div class="card-header">Navigation</div>
            <div class="card-body">
                <ul>
                    <li><a href="/docs">API Documentation</a></li>
                    <li><a href="/redoc">ReDoc Documentation</a></li>
                    <li><a href="/health">Health Check</a></li>
                </ul>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">Status</div>
            <div class="card-body">
                <p>Status: Error</p>
                <p>Message: The application encountered an error during startup.</p>
            </div>
        </div>
    </div>
</body>
</html>""")
        
        # Create a simple FastAPI app as fallback
        fallback_app = FastAPI(
            title="Andikar API (Limited Mode)",
            description="Running in limited mode due to startup error",
            version="1.0.0"
        )
        
        if TEMPLATES_AVAILABLE:
            fallback_templates = Jinja2Templates(directory="templates")
            
            @fallback_app.get("/", response_class=HTMLResponse)
            async def fallback_root(request: Request):
                return fallback_templates.TemplateResponse("index.html", {"request": request})
        else:
            @fallback_app.get("/")
            async def fallback_root():
                return {"status": "error", "message": "The application encountered an error during startup"}
        
        @fallback_app.get("/health")
        async def fallback_health():
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        
        @fallback_app.get("/status")
        async def fallback_status():
            return {
                "status": "error",
                "message": str(e),
                "timestamp": time.time()
            }
        
        # Run the fallback app
        import uvicorn
        port = int(os.getenv("PORT", "8080"))
        uvicorn.run(fallback_app, host="0.0.0.0", port=port)

# Main entry point
if __name__ == "__main__":
    # Start the main app in a separate thread
    main_app_thread = threading.Thread(target=run_main_app)
    main_app_thread.start()
    
    # Run the startup app while waiting for the main app to start
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    try:
        uvicorn.run(startup_app, host="0.0.0.0", port=port)
    except Exception as e:
        # If startup app fails, log the error and exit
        logger.error(f"Error running startup app: {str(e)}")
        sys.exit(1)
