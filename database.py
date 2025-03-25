from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/andikar")

# Print masked version of the DATABASE_URL for debugging
masked_url = DATABASE_URL
if "@" in masked_url:
    # Mask password in URL for logging
    parts = masked_url.split("@")
    auth_parts = parts[0].split(":")
    if len(auth_parts) > 2:
        masked_url = f"{auth_parts[0]}:****@{parts[1]}"
    
logger.info(f"Using database URL: {masked_url}")

# Adjust the URL if it's a Railway database URL (postgres:// -> postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info("Adjusted postgres:// to postgresql:// in database URL")

# Create SQLAlchemy engine with connection pooling and retries
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds

def get_engine():
    """Create engine with connection retries"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            logger.info(f"Attempting to connect to database (attempt {retries + 1}/{MAX_RETRIES})")
            engine = create_engine(
                DATABASE_URL, 
                pool_pre_ping=True,  # Enable connection health checks
                pool_recycle=3600,   # Recycle connections after 1 hour
                connect_args={"connect_timeout": 10}  # Set connection timeout
            )
            # Test the connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("Successfully connected to the database")
            return engine
        except Exception as e:
            retries += 1
            logger.error(f"Failed to connect to database: {str(e)}")
            if retries < MAX_RETRIES:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Max retries reached. Could not connect to the database.")
                raise

# Create engine with retry logic
try:
    engine = get_engine()
except Exception as e:
    logger.critical(f"Failed to initialize database: {str(e)}")
    # Still create the engine for the rest of the app, but it might not work
    engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
