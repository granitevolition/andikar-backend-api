"""
Main application module for Andikar Backend API.
This is separate from app.py to avoid circular imports.
"""
import logging
import os
import sys
from fastapi import FastAPI, Request, Response, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
try:
    from fastapi.templating import Jinja2Templates
    TEMPLATES_AVAILABLE = True
except (ImportError, AssertionError):
    TEMPLATES_AVAILABLE = False
import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text

# Ensure we're in the correct working directory
if os.path.exists("main.py") and not os.path.samefile("main.py", __file__):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Create necessary directories
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("andikar-main")

# Try to import database and models
try:
    from database import get_db, engine
    import models
    from models import Base
    import schemas
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database modules not available: {e}")
    DATABASE_AVAILABLE = False

# Try to import auth utils
try:
    from auth import get_current_user, get_current_active_user
    AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Auth modules not available: {e}")
    AUTH_AVAILABLE = False

# Try to import admin router
try:
    from admin import admin_router
    ADMIN_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Admin module not available: {e}")
    ADMIN_AVAILABLE = False

# Try to import config
try:
    import config
    PROJECT_NAME = config.PROJECT_NAME
    PROJECT_VERSION = config.PROJECT_VERSION
except ImportError:
    PROJECT_NAME = "Andikar Backend API"
    PROJECT_VERSION = "1.0.0"

# Create FastAPI app
app = FastAPI(
    title=PROJECT_NAME,
    description="Backend API Gateway for Andikar AI services",
    version=PROJECT_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Set up templates if available
if TEMPLATES_AVAILABLE:
    templates = Jinja2Templates(directory="templates")
    
    # Create a basic index.html if it doesn't exist
    index_path = os.path.join("templates", "index.html")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Andikar Backend API</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container {
            max-width: 800px;
            margin: 50px auto;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo i {
            font-size: 48px;
            color: #0d6efd;
        }
        .card {
            border: none;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
            transition: transform 0.3s;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .card-header {
            background-color: #fff;
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            font-weight: bold;
        }
        .list-group-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .btn-primary {
            background-color: #0d6efd;
            border: none;
            padding: 10px 20px;
            transition: all 0.3s;
        }
        .btn-primary:hover {
            background-color: #0b5ed7;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }
        .system-status {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .system-status.healthy {
            background-color: #198754;
        }
        .system-status.unhealthy {
            background-color: #dc3545;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <i class="fas fa-robot"></i>
            <h1>Andikar Backend API</h1>
            <p class="text-muted">Backend API Gateway for Andikar AI services</p>
        </div>
        
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-link me-2"></i> Quick Links
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <a href="/admin" class="btn btn-primary w-100">
                                    <i class="fas fa-tachometer-alt me-2"></i> Admin Dashboard
                                </a>
                            </div>
                            <div class="col-md-6 mb-3">
                                <a href="/docs" class="btn btn-secondary w-100">
                                    <i class="fas fa-book me-2"></i> API Documentation
                                </a>
                            </div>
                            <div class="col-md-6 mb-3">
                                <a href="/health" class="btn btn-info w-100 text-white">
                                    <i class="fas fa-heartbeat me-2"></i> Health Check
                                </a>
                            </div>
                            <div class="col-md-6 mb-3">
                                <a href="/redoc" class="btn btn-success w-100">
                                    <i class="fas fa-file-alt me-2"></i> ReDoc Documentation
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-info-circle me-2"></i> API Information
                    </div>
                    <div class="card-body">
                        <div class="list-group">
                            <div class="list-group-item">
                                <strong>Version</strong>
                                <span id="api-version">1.0.6</span>
                            </div>
                            <div class="list-group-item">
                                <strong>Environment</strong>
                                <span id="api-environment">Production</span>
                            </div>
                            <div class="list-group-item">
                                <strong>Status</strong>
                                <span>
                                    <span class="system-status healthy"></span>
                                    <span id="api-status">Up and running</span>
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <i class="fas fa-server me-2"></i> Available Endpoints
                    </div>
                    <div class="card-body">
                        <div class="list-group">
                            <div class="list-group-item">
                                <strong>Authentication</strong>
                                <code>/token</code>
                            </div>
                            <div class="list-group-item">
                                <strong>User Management</strong>
                                <code>/users/register</code>, <code>/users/me</code>
                            </div>
                            <div class="list-group-item">
                                <strong>Text Services</strong>
                                <code>/api/humanize</code>, <code>/api/detect</code>
                            </div>
                            <div class="list-group-item">
                                <strong>Payment Processing</strong>
                                <code>/api/payments/mpesa/initiate</code>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>© 2025 Andikar. All rights reserved.</p>
            <p>Powered by FastAPI, PostgreSQL, and Railway.</p>
        </div>
    </div>
</body>
</html>""")

# Include admin router if available
if ADMIN_AVAILABLE:
    try:
        app.include_router(admin_router)
        logger.info("Admin router included successfully")
    except Exception as e:
        logger.error(f"Error including admin router: {e}")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    
    logger.error(f"Unexpected error: {str(exc)}")
    import traceback
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if os.getenv("DEBUG") == "1" else "An unexpected error occurred"
        }
    )

# Root endpoint (index page)
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if TEMPLATES_AVAILABLE:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "title": PROJECT_NAME,
            "description": "Backend API Gateway for Andikar AI services",
            "version": PROJECT_VERSION,
            "status": "healthy",
            "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production"),
            "timestamp": datetime.utcnow().isoformat()
        })
    else:
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Andikar Backend API</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 20px; }
                h1 { color: #333; }
            </style>
        </head>
        <body>
            <h1>Andikar Backend API</h1>
            <p>API is running in limited mode.</p>
            <p>To access API documentation, visit <a href="/docs">/docs</a></p>
        </body>
        </html>
        """)

# JSON status for API clients
@app.get("/api/status")
async def api_status():
    return {
        "status": "healthy",
        "name": PROJECT_NAME,
        "version": PROJECT_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production")
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    db_status = "unknown"
    
    if DATABASE_AVAILABLE:
        try:
            db = next(get_db())
            db.execute(text("SELECT 1"))
            db_status = "healthy"
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            db_status = f"unhealthy: {str(e)}"
    else:
        db_status = "unavailable"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": db_status,
            "api": "healthy"
        }
    }

# Status endpoint for healthcheck
@app.get("/status")
async def status_check():
    return {
        "status": "healthy",
        "message": "Application is running",
        "progress": 100,
        "complete": True
    }

# Alternative index page routes
@app.get("/index.html", response_class=HTMLResponse)
async def index_html(request: Request):
    return await root(request)

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request):
    return await root(request)

# Main entry point
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting {PROJECT_NAME} server on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
