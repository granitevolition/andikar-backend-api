#!/usr/bin/env python3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("andikar-api")

# Create app
app = FastAPI(title="Andikar API")

# Try to mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.error(f"Could not mount static files: {e}")

@app.get("/", response_class=HTMLResponse)
async def root():
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
async def admin():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { padding: 20px; }
            .card { margin-bottom: 20px; }
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
                            <p class="card-text display-4">125</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">Transactions</h5>
                            <p class="card-text display-4">85</p>
                        </div>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">API Requests</h5>
                            <p class="card-text display-4">1,250</p>
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
                            <tr>
                                <td>john_doe</td>
                                <td>john@example.com</td>
                                <td><span class="badge bg-success">Active</span></td>
                            </tr>
                            <tr>
                                <td>jane_smith</td>
                                <td>jane@example.com</td>
                                <td><span class="badge bg-success">Active</span></td>
                            </tr>
                            <tr>
                                <td>bob_jackson</td>
                                <td>bob@example.com</td>
                                <td><span class="badge bg-warning text-dark">Pending</span></td>
                            </tr>
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
    return {
        "status": "healthy",
        "admin_dashboard": "available",
        "api_version": "1.0.2",
        "template_directories": os.listdir("templates") if os.path.exists("templates") else "Not found"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Files in current directory: {os.listdir('.')}")
    if os.path.exists("templates"):
        logger.info(f"Templates directory contents: {os.listdir('templates')}")
    logger.info(f"Environment: {os.environ.get('RAILWAY_ENVIRONMENT_NAME', 'unknown')}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port)
