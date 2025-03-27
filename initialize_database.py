"""
Database initialization script for Andikar Backend API.
Run this script to initialize and seed the PostgreSQL database on Railway.
"""
import os
import logging
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("database-init")

if __name__ == "__main__":
    logger.info("Starting database initialization...")
    
    # Import initialization functions from database.py
    try:
        from database import init_db, engine
        
        if engine is None:
            logger.error("Database engine initialization failed")
            sys.exit(1)
            
        logger.info("Engine created, initializing database...")
        
        # Initialize database with tables and seed data
        if init_db():
            logger.info("✅ Database initialization successful")
        else:
            logger.error("❌ Database initialization failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    
    # Also try the connect_db.py script as a backup option
    try:
        logger.info("Running connect_db.py as an additional check...")
        import connect_db
        connect_db.main()
    except Exception as e:
        logger.warning(f"connect_db.py execution failed: {str(e)}")
        
    logger.info("Database initialization complete")
