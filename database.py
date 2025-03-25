import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("database")

# Get database URL from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL")

if DATABASE_PUBLIC_URL:
    logger.info(f"Found DATABASE_PUBLIC_URL: {DATABASE_PUBLIC_URL.replace('://', '://****@')}")
    used_url = DATABASE_PUBLIC_URL
    logger.info("Using DATABASE_PUBLIC_URL")
elif DATABASE_URL:
    logger.info(f"Found DATABASE_URL: {DATABASE_URL.replace('://', '://****@')}")
    used_url = DATABASE_URL
    logger.info("Using DATABASE_URL directly")
else:
    logger.warning("No DATABASE_URL or DATABASE_PUBLIC_URL found. Using SQLite as fallback.")
    used_url = "sqlite:///./andikar.db"

# Determine database type for proper configuration
if used_url.startswith("postgresql"):
    logger.info("Using database type: postgresql")
    # For PostgreSQL, use this configuration
    engine = create_engine(
        used_url, 
        pool_size=5, 
        max_overflow=10,
        pool_pre_ping=True
    )
else:
    # For SQLite or other databases
    logger.info(f"Using database type: {used_url.split(':')[0]}")
    engine = create_engine(
        used_url,
        connect_args={"check_same_thread": False} if used_url.startswith("sqlite") else {}
    )

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
