#!/usr/bin/env python3
"""
Minimal Status Server

This is an absolutely minimal FastAPI server that provides a /status endpoint
for Railway's health checks. It's designed to be as simple as possible to
avoid any potential issues.
"""

import os
from fastapi import FastAPI
import uvicorn

# Create a minimal FastAPI app
app = FastAPI()

@app.get("/status")
async def status():
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/health")
async def health():
    """More detailed health check endpoint."""
    return {
        "status": "healthy",
        "message": "Minimal status server is running"
    }

@app.get("/")
async def root():
    """Root endpoint for information."""
    return {
        "service": "Andikar API Status Server",
        "version": "1.0.0",
        "health_endpoint": "/status"
    }

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting minimal status server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
