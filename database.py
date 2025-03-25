from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
import logging
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

# Check for alternative PostgreSQL environment variables (Railway provides these)
if not DATABASE_URL:
    logger.warning("DATABASE_URL not found, checking for PostgreSQL environment variables...")
    pg_host = os.getenv("PGHOST")
    pg_database = os.getenv("PGDATABASE")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_port = os.getenv("PGPORT", "5432")
    
    if pg_host and pg_database and pg_user:
        logger.info("Found PostgreSQL environment variables, constructing DATABASE_URL")
        DATABASE_URL = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
    else:
        logger.warning("No PostgreSQL environment variables found, using SQLite as fallback")
        DATABASE_URL = "sqlite:///./app.db"

logger.info(f"Using database type: {DATABASE_URL.split(':')[0]}")

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

# Configure engine parameters based on database type
engine_kwargs = {
    "pool_pre_ping": True,  # Enable connection health checks
    "pool_recycle": 3600,   # Recycle connections after 1 hour
}

# Add special parameters for different database types
if DATABASE_URL.startswith("postgresql"):
    engine_kwargs["connect_args"] = {"connect_timeout": 10}  # Set connection timeout
elif DATABASE_URL.startswith("sqlite"):
    # Make sure path exists for SQLite
    db_path = urllib.parse.urlparse(DATABASE_URL).path.lstrip("/")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Create SQLAlchemy engine with connection pooling and retries
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds

def get_engine():
    """Create engine with connection retries"""
    retries = 0
    while retries < MAX_RETRIES:
        try:
            logger.info(f"Attempting to connect to database (attempt {retries + 1}/{MAX_RETRIES})")
            engine = create_engine(DATABASE_URL, **engine_kwargs)
            
            # Test the connection (for non-SQLite databases)
            if not DATABASE_URL.startswith("sqlite"):
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
                if DATABASE_URL.startswith("sqlite"):
                    # For SQLite, just create the engine without testing
                    logger.info("Using SQLite without connection test")
                    return create_engine(DATABASE_URL, **engine_kwargs)
                raise

# Create engine with retry logic
try:
    engine = get_engine()
except Exception as e:
    logger.critical(f"Failed to initialize database: {str(e)}")
    # Create a SQLite fallback engine for emergencies
    logger.warning("Creating SQLite fallback database")
    DATABASE_URL = "sqlite:///./fallback.db"
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
    engine = create_engine(DATABASE_URL, **engine_kwargs)

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
