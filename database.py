"""
Database connection utilities for Andikar Backend API.
Provides SQLAlchemy engine and session management.
"""
import os
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("andikar-database")

# Get database URL from environment or use SQLite as fallback
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL")

if DATABASE_URL and "postgres:" in DATABASE_URL:
    # Convert from postgres:// to postgresql:// if needed
    DATABASE_URL = DATABASE_URL.replace("postgres:", "postgresql:")

if DATABASE_PUBLIC_URL and "postgres:" in DATABASE_PUBLIC_URL:
    # Convert from postgres:// to postgresql:// if needed
    DATABASE_PUBLIC_URL = DATABASE_PUBLIC_URL.replace("postgres:", "postgresql:")

# Try DATABASE_URL (Railway internal), then DATABASE_PUBLIC_URL, then fallback to SQLite
if DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
    logger.info(f"Using DATABASE_URL: {DATABASE_URL.split('@')[0]}@...")
elif DATABASE_PUBLIC_URL:
    SQLALCHEMY_DATABASE_URL = DATABASE_PUBLIC_URL
    logger.info(f"Using DATABASE_PUBLIC_URL: {DATABASE_PUBLIC_URL.split('@')[0]}@...")
else:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./andikar.db"
    logger.info("Using SQLite database")

# Configure engine differently for SQLite vs PostgreSQL
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    # SQLite-specific configuration
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # PostgreSQL configuration
    for attempt in range(5):
        try:
            engine = create_engine(
                SQLALCHEMY_DATABASE_URL,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                echo=False
            )
            # Test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("Database connection successful")
            break
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt+1} failed: {str(e)}")
            if attempt < 4:
                backoff = 2 ** attempt
                logger.info(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            else:
                logger.error("All database connection attempts failed")
                engine = None

# Create session class
if 'engine' in locals() and engine is not None:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    # Dummy SessionLocal that will raise exceptions if used
    logger.warning("Creating dummy SessionLocal due to database connection failure")
    SessionLocal = None

# Create Base class for models
Base = declarative_base()

# Dependency to get a database session
def get_db():
    if SessionLocal is None:
        logger.error("Attempted to get database session but no connection available")
        yield None
        return
        
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
