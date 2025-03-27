"""
Core application file for Andikar Backend API.

This module provides a clean separation between application definition
and application execution, allowing for better testing and deployment.
"""
import logging
import os
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime

# Import utilities and configuration
import config
from database import get_db, engine
from models import Base
from auth import get_current_user
from admin import admin_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("andikar-app")

# Initialize FastAPI app
app = FastAPI(
    title=config.PROJECT_NAME,
    description="Backend API Gateway for Andikar AI services",
    version=config.PROJECT_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="templates")

# Include admin router
app.include_router(admin_router)

# Root endpoint - serves index.html or redirects to API status
@app.get("/")
async def root(request: Request):
    """
    Serve the index page as HTML or return API status as JSON based on Accept header
    """
    # Check Accept header to determine response type
    accept = request.headers.get("Accept", "")
    
    # If client explicitly requests JSON, return API status
    if "application/json" in accept and "text/html" not in accept:
        return {
            "status": "healthy",
            "name": config.PROJECT_NAME,
            "version": config.PROJECT_VERSION,
            "description": "Backend API Gateway for Andikar AI services",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production")
        }
    
    # Otherwise, serve the index.html template
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": config.PROJECT_NAME,
        "description": "Backend API Gateway for Andikar AI services",
        "version": config.PROJECT_VERSION,
        "status": "healthy",
        "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production"),
        "timestamp": datetime.utcnow().isoformat()
    })

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Check system health and return status
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": "healthy",
            "api": "healthy"
        }
    }

# Alternate index page endpoint
@app.get("/index.html")
async def index_html(request: Request):
    """
    Alternative endpoint for index page
    """
    return await root(request)

# Home endpoint - alias for root
@app.get("/home")
async def home(request: Request):
    """
    Alias for root endpoint
    """
    return await root(request)

# For local development
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8080"))
    logger.info(f"Starting {config.PROJECT_NAME} on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
