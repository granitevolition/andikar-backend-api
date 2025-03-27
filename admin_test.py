#!/usr/bin/env python3
"""
Standalone Admin Dashboard Tester

This script provides a simple FastAPI application that serves the admin
dashboard templates without authentication, for testing purposes.
"""

import os
import sys
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("admin-test")

# Print diagnostic information
logger.info("Starting Admin Dashboard Test Server")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")

# Create required directories
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="Andikar Admin Test", description="Test server for admin dashboard")

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("Static files mounted successfully")
except Exception as e:
    logger.error(f"Could not mount static files: {e}")

# Set up templates
try:
    templates = Jinja2Templates(directory="templates")
    logger.info("Templates initialized successfully")
    if os.path.exists("templates/admin"):
        logger.info(f"Admin templates found: {os.listdir('templates/admin')}")
    else:
        logger.error("Admin templates directory not found")
except Exception as e:
    logger.error(f"Could not initialize templates: {e}")
    templates = None

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint with links to test pages."""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Andikar Admin Test Server</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 1rem;
            }}
            .card {{
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 1rem;
                border-radius: 0.25rem;
                margin-bottom: 1rem;
            }}
            .btn {{
                display: inline-block;
                background-color: #0d6efd;
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 0.25rem;
                text-decoration: none;
                margin-right: 0.5rem;
                margin-bottom: 0.5rem;
            }}
            .btn-secondary {{
                background-color: #6c757d;
            }}
            .btn:hover {{
                background-color: #0a58ca;
            }}
            .btn-secondary:hover {{
                background-color: #5a6268;
            }}
        </style>
    </head>
    <body>
        <h1>Andikar Admin Test Server</h1>
        <p>This server is used to test the admin dashboard templates.</p>
        
        <div class="card">
            <h2>Admin Dashboard Pages</h2>
            <p>
                <a href="/admin" class="btn">Admin Dashboard</a>
                <a href="/admin-dashboard" class="btn">Alternative Admin Dashboard</a>
                <a href="/admin-users" class="btn">User Management</a>
                <a href="/admin-transactions" class="btn">Transactions</a>
                <a href="/admin-logs" class="btn">API Logs</a>
                <a href="/admin-settings" class="btn">Settings</a>
            </p>
        </div>
        
        <div class="card">
            <h2>Basic Template Tests</h2>
            <p>
                <a href="/test" class="btn btn-secondary">Basic Template Test</a>
                <a href="/test-simple" class="btn btn-secondary">Simple HTML Template</a>
            </p>
            <p>These tests use simple templates to verify that template rendering is working.</p>
        </div>
        
        <div class="card">
            <h2>Debugging Information</h2>
            <p>
                <a href="/debug" class="btn">View Debug Info</a>
                <a href="/templates-check" class="btn">Check Templates</a>
                <a href="/status" class="btn">Server Status</a>
            </p>
        </div>
    </body>
    </html>
    """)

@app.get("/test", response_class=HTMLResponse)
async def test_template(request: Request):
    """Test the basic template rendering."""
    if not templates:
        return HTMLResponse("<h1>Error: Templates not configured</h1>")
    
    try:
        context = {
            "request": request,
            "title": "Test Template",
            "server": "Andikar Admin Test Server",
            "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "development"),
            "now": datetime.utcnow(),
            "context": {
                "test_var": "This is a test variable",
                "request_path": request.url.path,
                "template_dir": templates.directory if templates else "None"
            }
        }
        
        logger.info(f"Rendering test template with context: {context}")
        return templates.TemplateResponse("test.html", context)
    except Exception as e:
        logger.error(f"Error rendering test template: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return HTMLResponse(f"""
        <h1>Error rendering test template</h1>
        <p>The test template could not be rendered due to an error:</p>
        <pre style="background: #f8d7da; padding: 1rem; border-radius: 0.25rem;">{e}</pre>
        <h2>Traceback</h2>
        <pre style="background: #f8f9fa; padding: 1rem; border-radius: 0.25rem; overflow: auto;">{traceback.format_exc()}</pre>
        """)

@app.get("/test-simple", response_class=HTMLResponse)
async def test_simple():
    """Test with a simple HTML response for debugging."""
    try:
        # Check if templates directory exists
        templates_exists = os.path.exists("templates")
        templates_contents = os.listdir("templates") if templates_exists else []
        
        # Check if admin templates directory exists
        admin_templates_exists = os.path.exists("templates/admin")
        admin_templates_contents = os.listdir("templates/admin") if admin_templates_exists else []
        
        # Check if test.html exists
        test_html_exists = os.path.exists("templates/test.html")
        test_html_content = ""
        if test_html_exists:
            with open("templates/test.html", "r") as f:
                test_html_content = f.read()[:200] + "..." if len(f.read()) > 200 else f.read()
        
        # List all available directories
        available_dirs = os.listdir(".")
        
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Simple Template Test</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 1rem;
                }}
                .success {{
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                    padding: 1rem;
                    border-radius: 0.25rem;
                    margin-bottom: 1rem;
                }}
                .error {{
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                    padding: 1rem;
                    border-radius: 0.25rem;
                    margin-bottom: 1rem;
                }}
                pre {{
                    background-color: #f8f9fa;
                    padding: 1rem;
                    border-radius: 0.25rem;
                    overflow: auto;
                }}
            </style>
        </head>
        <body>
            <h1>Simple Template Test</h1>
            
            <div class="success">
                <p><strong>Success!</strong> This is a simple HTML response without using templates.</p>
            </div>
            
            <h2>Templates Directory</h2>
            <div class="{("success" if templates_exists else "error")}">
                <p>Templates directory exists: {templates_exists}</p>
                {(f"<p>Contents: {templates_contents}</p>" if templates_exists else "")}
            </div>
            
            <h2>Admin Templates</h2>
            <div class="{("success" if admin_templates_exists else "error")}">
                <p>Admin templates directory exists: {admin_templates_exists}</p>
                {(f"<p>Contents: {admin_templates_contents}</p>" if admin_templates_exists else "")}
            </div>
            
            <h2>Test Template</h2>
            <div class="{("success" if test_html_exists else "error")}">
                <p>test.html exists: {test_html_exists}</p>
                {(f"<p>Content preview:</p><pre>{test_html_content}</pre>" if test_html_exists else "")}
            </div>
            
            <h2>Available Directories</h2>
            <pre>{available_dirs}</pre>
            
            <p><a href="/">Back to Home</a></p>
        </body>
        </html>
        """)
    except Exception as e:
        import traceback
        return HTMLResponse(f"""
        <h1>Error in simple test</h1>
        <p>Error: {e}</p>
        <pre>{traceback.format_exc()}</pre>
        <p><a href="/">Back to Home</a></p>
        """)

@app.get("/admin", response_class=HTMLResponse)
async def admin_main(request: Request):
    """Main admin endpoint that redirects to the admin dashboard."""
    return await admin_dashboard(request)

@app.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Test the admin dashboard template."""
    if not templates:
        return HTMLResponse("<h1>Error: Templates not configured</h1>")
    
    try:
        # Create test stats
        stats = {
            "users": {
                "total": 125,
                "active": 98,
                "recent": [
                    {
                        "id": "user1",
                        "username": "john_doe",
                        "email": "john@example.com",
                        "plan_id": "pro",
                        "payment_status": "Paid",
                        "joined_date": datetime.utcnow() - timedelta(days=5)
                    },
                    {
                        "id": "user2",
                        "username": "jane_smith",
                        "email": "jane@example.com",
                        "plan_id": "basic",
                        "payment_status": "Paid",
                        "joined_date": datetime.utcnow() - timedelta(days=10)
                    },
                    {
                        "id": "user3",
                        "username": "bob_jackson",
                        "email": "bob@example.com",
                        "plan_id": "free",
                        "payment_status": "Pending",
                        "joined_date": datetime.utcnow() - timedelta(days=2)
                    }
                ]
            },
            "transactions": {
                "successful": 85,
                "pending": 12,
                "total": 97
            },
            "api": {
                "total_requests": 1250,
                "humanize_requests": 950,
                "detect_requests": 300
            }
        }
        
        # Create test chart data
        days = 30
        today = datetime.utcnow().date()
        start_date = today - timedelta(days=days-1)
        
        daily_users = []
        daily_api_usage = []
        
        import random
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Random user count
            user_count = random.randint(0, 5)
            
            daily_users.append({
                "date": date_str,
                "count": user_count
            })
            
            # Random API usage
            humanize_count = random.randint(10, 50)
            detect_count = random.randint(5, 20)
            
            daily_api_usage.append({
                "date": date_str,
                "humanize": humanize_count,
                "detect": detect_count
            })
        
        charts = {
            "daily_users": json.dumps(daily_users),
            "daily_api_usage": json.dumps(daily_api_usage)
        }
        
        # System status
        system = {
            "database": "healthy",
            "humanizer": "healthy",
            "detector": "not_configured",
            "mpesa": "healthy",
            "info": {
                "version": "1.0.2",
                "python_env": "production",
                "railway_project": "andikar-backend-api",
                "railway_service": "backend-api"
            }
        }
        
        logger.info("Rendering admin dashboard template")
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "title": "Admin Dashboard",
            "user": {"username": "admin"},
            "active_page": "dashboard",
            "stats": stats,
            "charts": charts,
            "system": system
        })
    except Exception as e:
        logger.error(f"Error rendering dashboard template: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return HTMLResponse(f"""
        <h1>Error rendering admin dashboard template</h1>
        <pre>{e}</pre>
        <h2>Traceback</h2>
        <pre>{traceback.format_exc()}</pre>
        """)

@app.get("/admin-users", response_class=HTMLResponse)
async def admin_users(request: Request):
    """Test the admin users template."""
    if not templates:
        return HTMLResponse("<h1>Error: Templates not configured</h1>")
    
    try:
        return templates.TemplateResponse("admin/users.html", {
            "request": request,
            "title": "User Management",
            "users": [
                {
                    "id": "user1",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "plan_id": "pro",
                    "payment_status": "Paid",
                    "words_used": 5000,
                    "joined_date": datetime.utcnow() - timedelta(days=30),
                    "is_active": True
                },
                {
                    "id": "user2",
                    "username": "jane_smith",
                    "email": "jane@example.com",
                    "plan_id": "basic",
                    "payment_status": "Paid",
                    "words_used": 2500,
                    "joined_date": datetime.utcnow() - timedelta(days=15),
                    "is_active": True
                },
                {
                    "id": "user3",
                    "username": "bob_jackson",
                    "email": "bob@example.com",
                    "plan_id": "free",
                    "payment_status": "Pending",
                    "words_used": 500,
                    "joined_date": datetime.utcnow() - timedelta(days=5),
                    "is_active": True
                }
            ],
            "page": 1,
            "total_pages": 1,
            "total_users": 3,
            "active_page": "users",
            "user": {"username": "admin"}
        })
    except Exception as e:
        logger.error(f"Error rendering users template: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return HTMLResponse(f"<h1>Error rendering template</h1><pre>{e}</pre>")

@app.get("/templates-check")
async def check_templates():
    """Check if templates are available and list their contents."""
    template_info = {}
    
    if os.path.exists("templates"):
        template_info["templates_dir_exists"] = True
        template_info["templates_contents"] = os.listdir("templates")
        
        if os.path.exists("templates/admin"):
            template_info["admin_dir_exists"] = True
            template_info["admin_contents"] = os.listdir("templates/admin")
            
            # Check for specific admin templates
            for template in ["base.html", "dashboard.html", "users.html"]:
                path = os.path.join("templates/admin", template)
                template_info[f"{template}_exists"] = os.path.exists(path)
                if os.path.exists(path):
                    with open(path, "r") as f:
                        template_info[f"{template}_size"] = len(f.read())
        else:
            template_info["admin_dir_exists"] = False
    else:
        template_info["templates_dir_exists"] = False
    
    return template_info

@app.get("/debug")
async def debug():
    """Provide debugging information about the server."""
    debug_info = {
        "python_version": sys.version,
        "current_directory": os.getcwd(),
        "directory_contents": os.listdir("."),
        "templates_configured": templates is not None
    }
    
    # Check template directory
    if os.path.exists("templates"):
        debug_info["templates_dir"] = {
            "exists": True,
            "contents": os.listdir("templates")
        }
        
        # Check admin templates
        if os.path.exists("templates/admin"):
            debug_info["admin_templates_dir"] = {
                "exists": True,
                "contents": os.listdir("templates/admin")
            }
            
            # Get sample of template content
            for template in ["base.html", "dashboard.html"]:
                path = os.path.join("templates/admin", template)
                if os.path.exists(path):
                    with open(path, "r") as f:
                        content = f.read()
                        debug_info[f"{template}_sample"] = content[:200] + "..." if len(content) > 200 else content
        else:
            debug_info["admin_templates_dir"] = {"exists": False}
    else:
        debug_info["templates_dir"] = {"exists": False}
    
    # Check static directory
    if os.path.exists("static"):
        debug_info["static_dir"] = {
            "exists": True,
            "contents": os.listdir("static")
        }
    else:
        debug_info["static_dir"] = {"exists": False}
    
    # Get environment variables (excluding sensitive ones)
    env_vars = {}
    for key, value in os.environ.items():
        if any(sensitive in key.lower() for sensitive in ['secret', 'password', 'token', 'key']):
            env_vars[key] = '********'
        else:
            env_vars[key] = value
    
    debug_info["environment_variables"] = env_vars
    
    return debug_info

@app.get("/status")
async def status():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Admin Test Server",
        "templates_configured": templates is not None,
        "admin_templates_available": os.path.exists("templates/admin"),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting server on port {port}")
    
    # Run the app
    uvicorn.run(app, host="0.0.0.0", port=port)
