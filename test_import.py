#!/usr/bin/env python3
"""
Test script to diagnose import issues with app.py
"""

import os
import sys
import logging
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("test-import")

logger.info("Starting test of app.py import")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Files in current directory: {os.listdir('.')}")

# Test module imports
try:
    logger.info("Testing import of required modules...")
    import fastapi
    logger.info(f"✅ FastAPI version: {fastapi.__version__}")
    
    import uvicorn
    logger.info(f"✅ Uvicorn version: {uvicorn.__version__}")
    
    import jinja2
    logger.info(f"✅ Jinja2 version: {jinja2.__version__}")
    
    import sqlalchemy
    logger.info(f"✅ SQLAlchemy version: {sqlalchemy.__version__}")
    
    import httpx
    logger.info(f"✅ HTTPX version: {httpx.__version__}")
    
    import jose
    logger.info(f"✅ Python-jose version: {jose.__version__}")
    
    import passlib
    logger.info(f"✅ Passlib version: {passlib.__version__}")
    
    import pydantic
    logger.info(f"✅ Pydantic version: {pydantic.__version__}")
    
except Exception as e:
    logger.error(f"❌ Module import test failed: {e}")
    logger.error(traceback.format_exc())

# Test database.py import
try:
    logger.info("Testing import of database.py...")
    import database
    logger.info(f"✅ Database module imported successfully")
    logger.info(f"Database engine: {database.engine}")
    logger.info(f"Database get_db function: {database.get_db}")
except Exception as e:
    logger.error(f"❌ Database import test failed: {e}")
    logger.error(traceback.format_exc())

# Test models.py import
try:
    logger.info("Testing import of models.py...")
    import models
    logger.info(f"✅ Models module imported successfully")
    logger.info(f"Available models: {models.__all__}")
except Exception as e:
    logger.error(f"❌ Models import test failed: {e}")
    logger.error(traceback.format_exc())

# Test app.py import
try:
    logger.info("Testing import of app.py...")
    import app
    logger.info(f"✅ App module imported successfully")
    logger.info(f"App version: {app.PROJECT_VERSION}")
    logger.info(f"App name: {app.PROJECT_NAME}")
    
    # List all routes
    routes = [{"path": route.path, "name": route.name, "methods": route.methods if hasattr(route, 'methods') else None} 
              for route in app.app.routes]
    logger.info(f"Available routes: {routes}")
    
    # Check for admin routes
    admin_routes = [r for r in routes if '/admin' in r['path']]
    logger.info(f"Admin routes: {admin_routes}")
    
    # Check templates
    if hasattr(app, 'templates') and app.templates:
        logger.info(f"✅ Templates configured in app.py")
        logger.info(f"Templates directory: {app.templates.directory}")
    else:
        logger.error(f"❌ Templates not configured in app.py")
    
except Exception as e:
    logger.error(f"❌ App import test failed: {e}")
    logger.error(traceback.format_exc())

logger.info("Import test completed")
