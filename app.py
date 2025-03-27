#!/usr/bin/env python3
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import logging
import uvicorn
from typing import Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("andikar-api")

# Create app
app = FastAPI(title="Andikar API")

# Try to mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.error(f"Could not mount static files: {e}")

# Try to set up templates
try:
    templates = Jinja2Templates(directory="templates")
    logger.info("Templates initialized successfully")
    TEMPLATES_AVAILABLE = True
except Exception as e:
    logger.error(f"Could not initialize templates: {e}")
    TEMPLATES_AVAILABLE = False

# Try to import database components - but don't fail if they're not available
try:
    from database import get_db, init_db
    from sqlalchemy.orm import Session
    from models import User, Transaction, APILog
    
    # Initialize database
    DB_AVAILABLE = True
    logger.info("Database modules imported successfully")
    
    @app.on_event("startup")
    async def startup_db_event():
        """Initialize database on startup."""
        logger.info("Initializing database...")
        success = init_db()
        if success:
            logger.info("Database initialized successfully")
        else:
            logger.warning("Database initialization failed, some features may be limited")
    
except ImportError as e:
    logger.warning(f"Database modules not available: {e}")
    logger.warning("Running in limited mode without database support")
    DB_AVAILABLE = False
    
    # Define dummy dependencies for routes that expect database
    def get_db():
        return None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Home page route."""
    if TEMPLATES_AVAILABLE:
        try:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "title": "Andikar Backend API"
            })
        except Exception as e:
            logger.error(f"Error rendering index template: {e}")
    
    # Fallback HTML
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Andikar Backend API</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 20px; }
            a.btn { display: inline-block; background: #0066cc; color: white; padding: 10px 15px; 
                   text-decoration: none; border-radius: 4px; margin-right: 10px; }
        </style>
    </head>
    <body>
        <h1>Andikar Backend API</h1>
        
        <div class="card">
            <h2>Quick Access</h2>
            <p>
                <a href="/admin" class="btn">Admin Dashboard</a>
                <a href="/docs" class="btn">API Documentation</a>
                <a href="/status" class="btn">Status Check</a>
            </p>
        </div>
        
        <div class="card">
            <h2>System Status</h2>
            <p>✅ Application is running</p>
            <p>✅ Admin interface is available at <a href="/admin">/admin</a></p>
        </div>
    </body>
    </html>
    """)

@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request, db: Optional[Session] = Depends(get_db)):
    """Admin dashboard route."""
    # Mock data for admin dashboard when database is not available
    mock_data = {
        "users_count": 125,
        "transactions_count": 85,
        "api_requests_count": 1250,
        "recent_users": [
            {"username": "john_doe", "email": "john@example.com", "status": "Active"},
            {"username": "jane_smith", "email": "jane@example.com", "status": "Active"},
            {"username": "bob_jackson", "email": "bob@example.com", "status": "Pending"}
        ]
    }
    
    # Try to get real data from database if available
    data = mock_data
    if DB_AVAILABLE and db is not None:
        try:
            data = {
                "users_count": db.query(User).count(),
                "transactions_count": db.query(Transaction).count(),
                "api_requests_count": db.query(APILog).count(),
                "recent_users": [
                    {
                        "username": user.username,
                        "email": user.email,
                        "status": "Active" if user.is_active else "Inactive"
                    }
                    for user in db.query(User).order_by(User.joined_date.desc()).limit(10).all()
                ]
            }
            logger.info("Successfully retrieved database data for admin dashboard")
        except Exception as e:
            logger.error(f"Error retrieving database data: {e}")
            logger.info("Using mock data for admin dashboard")
    
    if TEMPLATES_AVAILABLE:
        try:
            return templates.TemplateResponse("admin/dashboard.html", {
                "request": request,
                "title": "Admin Dashboard",
                **data
            })
        except Exception as e:
            logger.error(f"Error rendering admin template: {e}")
    
    # Fallback HTML
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ padding: 20px; }}
            .card {{ margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">Admin Dashboard</h1>
            
            <div class="row">
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Users</h5>
                            <p class="card-text display-4">{data['users_count']}</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Transactions</h5>
                            <p class="card-text display-4">{data['transactions_count']}</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">API Requests</h5>
                            <p class="card-text display-4">{data['api_requests_count']}</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header">
                    Recent Users
                </div>
                <div class="card-body">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Username</th>
                                <th>Email</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join([f"""
                            <tr>
                                <td>{user['username']}</td>
                                <td>{user['email']}</td>
                                <td><span class="badge bg-success">{user['status']}</span></td>
                            </tr>
                            """ for user in data['recent_users']])}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="mt-4">
                <a href="/" class="btn btn-primary">Back to Home</a>
            </div>
        </div>
    </body>
    </html>
    """)

@app.get("/status")
async def status():
    """Health check endpoint."""
    template_status = []
    if os.path.exists("templates"):
        template_status = os.listdir("templates")
    
    return {
        "status": "healthy",
        "admin_dashboard": "available",
        "api_version": "1.0.2",
        "database_available": DB_AVAILABLE,
        "templates_available": TEMPLATES_AVAILABLE,
        "template_directories": template_status if template_status else "Not found"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """General startup event handler."""
    logger.info("Application starting up...")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Files in current directory: {os.listdir('.')}")
    if os.path.exists("templates"):
        logger.info(f"Templates directory contents: {os.listdir('templates')}")
        if os.path.exists("templates/admin"):
            logger.info(f"Admin templates directory contents: {os.listdir('templates/admin')}")
    logger.info(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT_NAME', 'unknown')}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port)
