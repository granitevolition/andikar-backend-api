import logging
import os
import threading
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dual_app")

# Create a minimal app to respond while the main app is loading
app = FastAPI()

# Flag to track if the main app is ready
is_main_app_ready = False

# Global variable to hold the main app once loaded
main_app = None

@app.get("/health")
async def health_check():
    """This endpoint always responds immediately, even during startup"""
    return {
        "status": "healthy",
        "main_app_ready": is_main_app_ready
    }

@app.get("/")
async def root():
    """Root endpoint that indicates status"""
    if is_main_app_ready:
        return {
            "status": "ready",
            "name": "Andikar Backend API",
            "version": "1.0.6"
        }
    else:
        return {
            "status": "starting",
            "message": "Andikar Backend API is starting up, please wait..."
        }

@app.middleware("http")
async def proxy_middleware(request: Request, call_next):
    """Middleware to forward requests to main app when it's ready"""
    # Always allow health checks and root endpoint
    if request.url.path in ["/health", "/"]:
        return await call_next(request)
    
    # If main app isn't ready, return a 503 Service Unavailable
    if not is_main_app_ready:
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Service is starting up, please try again shortly"
            }
        )
    
    # Forward to main app
    return await main_app(request.scope, request.receive, request.send)

def load_main_app():
    """Load the main app in a background thread"""
    global main_app, is_main_app_ready
    
    # Simulate startup time
    logger.info("Starting to load main application...")
    
    try:
        # Import the main app
        time.sleep(1)  # Brief pause to ensure minimal app is responding first
        import main
        
        # Store the reference to the main app
        main_app = main.app
        
        # Mark as ready
        is_main_app_ready = True
        logger.info("Main application loaded successfully")
    except Exception as e:
        logger.error(f"Error loading main application: {e}")

def run_app():
    """Run the FastAPI application with uvicorn"""
    # Start loading the main app in a background thread
    threading.Thread(target=load_main_app).start()
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8080))
    
    # Start uvicorn with the dual app
    uvicorn.run(
        "dual_app:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    run_app()
