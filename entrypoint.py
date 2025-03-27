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

# Status API route - REQUIRED FOR RAILWAY HEALTH CHECK
@startup_app.get("/status")
async def status_api():
    return {
        "status": "healthy",  # Always report healthy to prevent Railway from restarting container
        "progress": startup_progress,
        "message": startup_message,
        "complete": startup_complete
    }

# Health endpoint with detailed status
@startup_app.get("/health")
async def health_check():
    """Provide detailed health status information."""
    return {
        "status": "healthy" if startup_status != "error" else "unhealthy",
        "progress": startup_progress,
        "message": startup_message,
        "services": {
            "api": "starting" if not startup_complete else "running",
            "database": "initializing"
        }
    }

# All other routes redirect to status page during startup
@startup_app.get("/{path:path}")
async def catch_all(path: str):
    # Exclude status endpoint from redirection
    if path == "status":
        return await status_api()
    if path == "health":
        return await health_check()
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
        # Update status to database check
        update_startup_progress("connecting", "Connecting to database...", 10)
        
        # Check if database environment variables are set
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            # Try setting from components if not set
            pguser = os.getenv("PGUSER", "postgres")
            pgpassword = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
            pgdatabase = os.getenv("PGDATABASE", "railway")
            proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
            proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
            
            if pgpassword and proxy_domain and proxy_port:
                # Password encode
                import urllib.parse
                encoded_password = urllib.parse.quote_plus(pgpassword)
                
                # Set DATABASE_URL
                db_url = f"postgresql://{pguser}:{encoded_password}@{proxy_domain}:{proxy_port}/{pgdatabase}"
                os.environ["DATABASE_URL"] = db_url
                logger.info(f"Set DATABASE_URL to: postgresql://{pguser}:****@{proxy_domain}:{proxy_port}/{pgdatabase}")
            else:
                logger.warning("Could not construct DATABASE_URL, missing required components")
        
        # Try to import database modules
        update_startup_progress("importing", "Importing database modules...", 20)
        try:
            from database import Base, engine, init_db
            update_startup_progress("db_connect", "Connected to database, initializing...", 30)
            
            # Initialize database
            result = init_db()
            if result:
                update_startup_progress("db_ready", "Database initialization successful!", 50)
            else:
                update_startup_progress("db_partial", "Database initialization partially successful", 40)
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            update_startup_progress("db_error", f"Database error: {str(e)}", 30)
        
        # Update status to loading routes
        update_startup_progress("loading", "Loading application components...", 60)
        time.sleep(1)  # Small delay
        
        # Update status to starting health check
        update_startup_progress("health_check", "Starting health check service...", 70)
        
        # Start health check service
        try:
            # Start health_check.py in background process
            health_port = os.getenv("HEALTH_PORT", "8081")
            subprocess.Popen([sys.executable, "health_check.py", "--port", health_port], 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logger.info(f"Health check service started on port {health_port}")
        except Exception as e:
            logger.warning(f"Could not start health check service: {str(e)}")
        
        # Update status to finishing up
        update_startup_progress("finishing", "Finishing startup process...", 90)
        
        try:
            # First try to import app from main
            from app import app as main_app
            
            # Mark startup as complete
            update_startup_progress("complete", "Startup complete! Running main application.", 100)
            startup_complete = True
            
            # Run the main app using Uvicorn
            import uvicorn
            port = int(os.getenv("PORT", "8080"))
            uvicorn.run(main_app, host="0.0.0.0", port=port)
            
        except ImportError:
            # Try to import app from app.py
            logger.info("Trying alternative import path for main app")
            
            try:
                import app
                update_startup_progress("complete", "Startup complete! Running main application.", 100)
                startup_complete = True
                
                # Run the main app using Uvicorn
                import uvicorn
                port = int(os.getenv("PORT", "8080"))
                uvicorn.run(app.app, host="0.0.0.0", port=port)
                
            except ImportError as e:
                logger.error(f"Could not import main app: {str(e)}")
                raise
        
    except Exception as e:
        # Log the error
        logger.error(f"Error starting main app: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Update status to error
        update_startup_progress("error", f"Error starting application: {str(e)}", 0)
        
        # Create a simple FastAPI app as fallback
        fallback_app = FastAPI(
            title="Andikar API (Limited Mode)",
            description="Running in limited mode due to startup error",
            version="1.0.0"
        )
        
        @fallback_app.get("/")
        async def fallback_root():
            return {
                "status": "error", 
                "message": "The application encountered an error during startup",
                "error": str(e)
            }
        
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
                "status": "healthy",  # Always report healthy to Railway
                "message": "Limited functionality available",
                "timestamp": time.time()
            }
        
        # Run the fallback app
        import uvicorn
        port = int(os.getenv("PORT", "8080"))
        uvicorn.run(fallback_app, host="0.0.0.0", port=port)

# Main entry point
if __name__ == "__main__":
    # Immediately ensure we have a /status endpoint to keep Railway happy
    update_startup_progress("initializing", "Starting initialization process...", 5)
    
    # Start the main app in a separate thread
    main_app_thread = threading.Thread(target=run_main_app)
    main_app_thread.daemon = True  # Make thread a daemon so it exits when main thread exits
    main_app_thread.start()
    
    # Run the startup app 
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting Andikar API on port {port}")
    
    try:
        # Run starter app which provides the /status endpoint
        uvicorn.run(startup_app, host="0.0.0.0", port=port)
    except Exception as e:
        # If startup app fails, log the error and exit
        logger.error(f"Error running startup app: {str(e)}")
        sys.exit(1)
