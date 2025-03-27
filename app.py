# Keep the entire file unchanged but modify the root endpoint to include admin test links

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if templates:
        try:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "title": PROJECT_NAME,
                "description": "Backend API Gateway for Andikar AI services",
                "version": PROJECT_VERSION,
                "status": "healthy",
                "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "production"),
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
    
    # If templates fail or aren't available, return a basic HTML response
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{PROJECT_NAME}</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 1rem;
                color: #333;
                line-height: 1.6;
            }}
            header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid #eaeaea;
            }}
            .status-indicator {{
                display: inline-block;
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background-color: #10b981;
                margin-right: 6px;
            }}
            section {{
                margin-bottom: 2rem;
            }}
            h1, h2, h3 {{
                margin-top: 0;
            }}
            ul {{
                padding-left: 20px;
            }}
            .card {{
                background: #f9fafb;
                border-radius: 8px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                border: 1px solid #e5e7eb;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 1rem;
                margin-bottom: 2rem;
            }}
            .badge {{
                display: inline-block;
                padding: 0.2rem 0.5rem;
                border-radius: 4px;
                font-size: 0.75rem;
                font-weight: 500;
                margin-right: 0.5rem;
                margin-bottom: 0.5rem;
            }}
            .badge-get {{
                background-color: #dbeafe;
                color: #1e40af;
            }}
            .badge-post {{
                background-color: #dcfce7;
                color: #166534;
            }}
            .badge-put {{
                background-color: #fef3c7;
                color: #92400e;
            }}
            footer {{
                margin-top: 3rem;
                padding-top: 1rem;
                border-top: 1px solid #eaeaea;
                text-align: center;
                font-size: 0.875rem;
                color: #6b7280;
            }}
            a {{
                color: #2563eb;
                text-decoration: none;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            code {{
                background-color: #f3f4f6;
                padding: 0.2rem 0.4rem;
                border-radius: 4px;
                font-size: 0.875rem;
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            }}
            .debug-box {{
                background-color: #fef3c7;
                border: 1px solid #f59e0b;
                border-radius: 8px;
                padding: 1rem;
                margin-bottom: 1.5rem;
            }}
        </style>
    </head>
    <body>
        <header>
            <div>
                <h1>{PROJECT_NAME}</h1>
                <p>Version {PROJECT_VERSION}</p>
            </div>
            <div>
                <span><span class="status-indicator"></span> System: Healthy</span>
            </div>
        </header>
        
        <div class="debug-box">
            <h3>Debug Links</h3>
            <p>These links are for testing and debugging purposes:</p>
            <ul>
                <li><a href="/test">/test</a> - Test page to verify template rendering</li>
                <li><a href="/admin-test">/admin-test</a> - Test admin dashboard without authentication</li>
                <li><a href="/admin">/admin</a> - Admin Dashboard (requires authentication)</li>
                <li><a href="/admin/database/seed?confirm=yes">/admin/database/seed</a> - Seed database with initial data (login with username: admin, password: admin123)</li>
            </ul>
        </div>
        
        <section>
            <h2>Quick Access</h2>
            <div class="grid">
                <a href="/" class="card">
                    <h3>Home Page</h3>
                    <p>Main index and dashboard</p>
                </a>
                <a href="/admin" class="card">
                    <h3>Admin Dashboard</h3>
                    <p>Administration interface</p>
                </a>
                <a href="/docs" class="card">
                    <h3>API Documentation</h3>
                    <p>Interactive API references</p>
                </a>
                <a href="/health" class="card">
                    <h3>System Health</h3>
                    <p>System status and health checks</p>
                </a>
            </div>
        </section>
        
        <section>
            <h2>Admin Area</h2>
            <ul>
                <li><a href="/admin">Dashboard</a> - Overview and statistics</li>
                <li><a href="/admin/users">User Management</a> - Manage users and permissions</li>
                <li><a href="/admin/transactions">Transaction Management</a> - View payment records</li>
                <li><a href="/admin/logs">API Logs</a> - Monitor API usage and errors</li>
                <li><a href="/admin/settings">System Settings</a> - Configure application settings</li>
            </ul>
        </section>
        
        <section>
            <h2>Documentation</h2>
            <ul>
                <li><a href="/docs">Swagger UI</a> - Interactive API documentation</li>
                <li><a href="/redoc">ReDoc</a> - Alternative API documentation</li>
                <li><a href="/openapi.json">OpenAPI Schema</a> - Raw OpenAPI JSON schema</li>
                <li><a href="/health">Health Status</a> - System health information</li>
            </ul>
        </section>
        
        <section>
            <h2>API Endpoints</h2>
            
            <h3>Authentication & User Management</h3>
            <div>
                <span class="badge badge-post">POST</span><a href="/token">/token</a> - Obtain authentication token
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/users/register">/users/register</a> - Register new user
            </div>
            <div>
                <span class="badge badge-get">GET</span><a href="/users/me">/users/me</a> - Get current user profile
            </div>
            <div>
                <span class="badge badge-put">PUT</span><a href="/users/me">/users/me</a> - Update user profile
            </div>
            
            <h3>Text Services</h3>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/humanize">/api/humanize</a> - Humanize text content
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/detect">/api/detect</a> - Detect AI-generated content
            </div>
            
            <h3>Payments</h3>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/payments/mpesa/initiate">/api/payments/mpesa/initiate</a> - Initiate M-Pesa payment
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/payments/mpesa/callback">/api/payments/mpesa/callback</a> - M-Pesa callback
            </div>
            <div>
                <span class="badge badge-post">POST</span><a href="/api/payments/simulate">/api/payments/simulate</a> - Simulate payment (testing)
            </div>
        </section>
        
        <section>
            <h2>System Information</h2>
            <div class="card">
                <div><strong>API Version:</strong> {PROJECT_VERSION}</div>
                <div><strong>Environment:</strong> {os.getenv("RAILWAY_ENVIRONMENT_NAME", "production")}</div>
                <div><strong>Status:</strong> <span class="status-indicator"></span> Healthy</div>
                <div><strong>Timestamp:</strong> {datetime.utcnow().isoformat()}</div>
            </div>
        </section>
        
        <footer>
            &copy; {datetime.utcnow().year} Andikar. All rights reserved.
        </footer>
    </body>
    </html>
    """)
