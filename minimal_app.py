#!/usr/bin/env python3
"""
Minimal FastAPI Application

This is a minimal FastAPI application with no dependencies other than FastAPI and Uvicorn.
It's used as a last resort to diagnose deployment issues.
"""

import os
import sys
import logging
from datetime import datetime
import traceback
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("minimal-app")

# Print diagnostic information
logger.info("Starting Minimal FastAPI Application")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Files in current directory: {os.listdir('.')}")

# Initialize FastAPI app
app = FastAPI(title="Minimal FastAPI App", description="Minimal app for debugging")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.error(f"Could not mount static files: {e}")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint with basic HTML."""
    template_dir_exists = os.path.exists("templates")
    template_contents = os.listdir("templates") if template_dir_exists else []
    admin_dir_exists = os.path.exists("templates/admin")
    admin_contents = os.listdir("templates/admin") if admin_dir_exists else []
    
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Minimal FastAPI App</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 1rem;
            }}
            .info-box {{
                background-color: #d1ecf1;
                border: 1px solid #bee5eb;
                color: #0c5460;
                padding: 1rem;
                border-radius: 0.25rem;
                margin-bottom: 1rem;
            }}
            .success {{
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }}
            .warning {{
                background-color: #fff3cd;
                border: 1px solid #ffeeba;
                color: #856404;
            }}
            .error {{
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }}
            pre {{
                background-color: #f8f9fa;
                padding: 0.5rem;
                border-radius: 0.25rem;
                overflow: auto;
            }}
            .links a {{
                display: inline-block;
                background-color: #007bff;
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 0.25rem;
                text-decoration: none;
                margin-right: 0.5rem;
                margin-bottom: 0.5rem;
            }}
            .links a:hover {{
                background-color: #0069d9;
            }}
        </style>
    </head>
    <body>
        <h1>Minimal FastAPI App</h1>
        
        <div class="info-box success">
            <h2>Server is Running</h2>
            <p>The minimal FastAPI application is running successfully.</p>
            <p>Current time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        
        <div class="info-box {('success' if template_dir_exists else 'error')}">
            <h2>Templates Directory</h2>
            <p>Templates directory exists: {template_dir_exists}</p>
            {('<p>Templates found: ' + str(len(template_contents)) + '</p>') if template_dir_exists else ''}
            {('<pre>' + str(template_contents) + '</pre>') if template_dir_exists and template_contents else ''}
        </div>
        
        <div class="info-box {('success' if admin_dir_exists else 'error')}">
            <h2>Admin Templates</h2>
            <p>Admin templates directory exists: {admin_dir_exists}</p>
            {('<p>Admin templates found: ' + str(len(admin_contents)) + '</p>') if admin_dir_exists else ''}
            {('<pre>' + str(admin_contents) + '</pre>') if admin_dir_exists and admin_contents else ''}
        </div>
        
        <h2>Testing Pages</h2>
        <div class="links">
            <a href="/direct">Direct HTML Page</a>
            <a href="/admin-raw">Raw Admin HTML</a>
            <a href="/info">System Info</a>
            <a href="/status">Status Check</a>
            <a href="/directory">Directory Listing</a>
        </div>
    </body>
    </html>
    """)

@app.get("/direct", response_class=HTMLResponse)
async def direct_html():
    """Serve the direct.html file as a plain HTML response."""
    try:
        file_path = os.path.join("templates", "direct.html")
        if not os.path.exists(file_path):
            return HTMLResponse(f"<h1>Error: File not found</h1><p>The file {file_path} does not exist.</p>")
        
        with open(file_path, "r") as f:
            content = f.read()
        return HTMLResponse(content)
    except Exception as e:
        logger.error(f"Error serving direct.html: {e}")
        return HTMLResponse(f"<h1>Error serving direct.html</h1><pre>{str(e)}</pre><pre>{traceback.format_exc()}</pre>")

@app.get("/admin-raw", response_class=HTMLResponse)
async def admin_raw():
    """Attempt to serve dashboard.html directly without Jinja templating."""
    try:
        file_path = os.path.join("templates", "admin", "dashboard.html")
        if not os.path.exists(file_path):
            return HTMLResponse(
                f"<h1>Error: Admin file not found</h1><p>The file {file_path} does not exist.</p>"
            )
        
        # Read the file content
        with open(file_path, "r") as f:
            content = f.read()
        
        # Create a simplified version without Jinja templating
        simplified_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Raw Admin Dashboard</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
            <style>
                body {{ padding: 2rem; }}
                .alert {{ margin-bottom: 1rem; }}
                pre {{ background: #f8f9fa; padding: 1rem; border-radius: 0.25rem; overflow: auto; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Raw Admin Dashboard Content</h1>
                
                <div class="alert alert-warning">
                    <p><strong>Note:</strong> This is the raw content of the admin dashboard template without Jinja templating.</p>
                    <p>The actual dashboard would have dynamic content and styling from the base template.</p>
                </div>
                
                <div class="alert alert-info">
                    <h4>File Path:</h4>
                    <p>{file_path}</p>
                </div>
                
                <h2>Template Content:</h2>
                <pre>{content}</pre>
                
                <p><a href="/" class="btn btn-primary">Back to Home</a></p>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(simplified_content)
    except Exception as e:
        logger.error(f"Error serving admin raw: {e}")
        return HTMLResponse(f"<h1>Error serving admin dashboard</h1><pre>{str(e)}</pre><pre>{traceback.format_exc()}</pre>")

@app.get("/info")
async def info():
    """Return system information."""
    info_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "python_version": sys.version,
        "environment": {
            "current_directory": os.getcwd(),
            "user": os.environ.get("USER"),
            "home": os.environ.get("HOME"),
            "path": os.environ.get("PATH"),
            "railway_environment": os.environ.get("RAILWAY_ENVIRONMENT_NAME", "unknown")
        },
        "directories": {
            "root": os.listdir("."),
            "templates_exists": os.path.exists("templates"),
            "static_exists": os.path.exists("static"),
            "templates_contents": os.listdir("templates") if os.path.exists("templates") else [],
            "static_contents": os.listdir("static") if os.path.exists("static") else []
        }
    }
    
    if os.path.exists("templates/admin"):
        info_data["directories"]["admin_templates"] = os.listdir("templates/admin")
    
    return info_data

@app.get("/directory")
async def directory(path: str = "."):
    """List the contents of a directory."""
    try:
        contents = os.listdir(path)
        result = []
        
        for item in contents:
            item_path = os.path.join(path, item)
            item_type = "directory" if os.path.isdir(item_path) else "file"
            item_size = os.path.getsize(item_path) if os.path.isfile(item_path) else None
            
            result.append({
                "name": item,
                "type": item_type,
                "size": item_size,
                "path": item_path
            })
        
        return {
            "path": path,
            "contents": result
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/status")
async def status():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Minimal FastAPI App",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/favicon.ico")
async def favicon():
    """Serve favicon."""
    if os.path.exists("static/favicon.ico"):
        return FileResponse("static/favicon.ico")
    else:
        return JSONResponse(status_code=404, content={"error": "Favicon not found"})

# Main entry point
if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=port)
