from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import time
import logging
import urllib.parse
import socket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URLs from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL")

# Print available database URLs (masked)
if DATABASE_URL:
    masked_url = DATABASE_URL.replace(DATABASE_URL.split('@')[0].split(':')[-1], '****') if '@' in DATABASE_URL else DATABASE_URL
    logger.info(f"Found DATABASE_URL: {masked_url}")

if DATABASE_PUBLIC_URL:
    masked_url = DATABASE_PUBLIC_URL.replace(DATABASE_PUBLIC_URL.split('@')[0].split(':')[-1], '****') if '@' in DATABASE_PUBLIC_URL else DATABASE_PUBLIC_URL
    logger.info(f"Found DATABASE_PUBLIC_URL: {masked_url}")

# Function to check if a host is reachable
def is_host_reachable(host, port, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        s.close()
        return True
    except:
        return False

# Directly use the PostgreSQL URL provided by Railway
if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
    final_database_url = DATABASE_URL
    logger.info("Using DATABASE_URL directly")
elif DATABASE_PUBLIC_URL and DATABASE_PUBLIC_URL.startswith("postgresql"):
    final_database_url = DATABASE_PUBLIC_URL
    logger.info("Using DATABASE_PUBLIC_URL directly")
else:
    # Check for PostgreSQL environment variables
    pg_host = os.getenv("PGHOST")
    pg_database = os.getenv("PGDATABASE")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_port = os.getenv("PGPORT", "5432")
    
    if all([pg_host, pg_database, pg_user, pg_password]):
        final_database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        logger.info(f"Constructed DATABASE_URL from environment variables")
    else:
        # Use SQLite as last resort
        final_database_url = "sqlite:///./app.db"
        logger.warning("No PostgreSQL connection available, using SQLite as fallback")

# Adjust the URL if it's a Railway database URL (postgres:// -> postgresql://)
if final_database_url.startswith("postgres://"):
    final_database_url = final_database_url.replace("postgres://", "postgresql://", 1)
    logger.info("Adjusted postgres:// to postgresql:// in database URL")

logger.info(f"Using database type: {final_database_url.split(':')[0]}")

# Configure engine parameters based on database type
engine_kwargs = {
    "pool_pre_ping": True,  # Enable connection health checks
    "pool_recycle": 3600,   # Recycle connections after 1 hour
}

# Add special parameters for different database types
if final_database_url.startswith("postgresql"):
    engine_kwargs["connect_args"] = {"connect_timeout": 10}  # Set connection timeout
elif final_database_url.startswith("sqlite"):
    # Make sure path exists for SQLite
    db_path = urllib.parse.urlparse(final_database_url).path.lstrip("/")
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    engine_kwargs["connect_args"] = {"check_same_thread": False}

# Create SQLAlchemy engine
engine = create_engine(final_database_url, **engine_kwargs)

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
