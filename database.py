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

# Determine which database URL to use
final_database_url = None

# First try with DATABASE_URL (internal)
if DATABASE_URL:
    # Parse the URL to get host and port
    parsed = urllib.parse.urlparse(DATABASE_URL)
    if parsed.hostname:
        if is_host_reachable(parsed.hostname, parsed.port or 5432):
            logger.info(f"Internal database host {parsed.hostname} is reachable. Using DATABASE_URL.")
            final_database_url = DATABASE_URL
        else:
            logger.warning(f"Internal database host {parsed.hostname} is not reachable.")

# If internal URL doesn't work, try with public URL
if not final_database_url and DATABASE_PUBLIC_URL:
    # Parse the URL to get host and port
    parsed = urllib.parse.urlparse(DATABASE_PUBLIC_URL)
    if parsed.hostname:
        if is_host_reachable(parsed.hostname, parsed.port or 5432):
            logger.info(f"Public database host {parsed.hostname} is reachable. Using DATABASE_PUBLIC_URL.")
            final_database_url = DATABASE_PUBLIC_URL
        else:
            logger.warning(f"Public database host {parsed.hostname} is not reachable.")

# Check for alternative PostgreSQL environment variables if no URL is working
if not final_database_url:
    logger.warning("No database URL is reachable, checking for PostgreSQL environment variables...")
    pg_host = os.getenv("PGHOST")
    pg_database = os.getenv("PGDATABASE")
    pg_user = os.getenv("PGUSER")
    pg_password = os.getenv("PGPASSWORD")
    pg_port = os.getenv("PGPORT", "5432")
    
    if pg_host and pg_database and pg_user:
        logger.info(f"Found PostgreSQL environment variables, checking if host {pg_host} is reachable...")
        if is_host_reachable(pg_host, int(pg_port)):
            logger.info(f"PostgreSQL host {pg_host} is reachable. Constructing DATABASE_URL.")
            final_database_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        else:
            logger.warning(f"PostgreSQL host {pg_host} is not reachable.")
    else:
        logger.warning("No usable PostgreSQL environment variables found")

# If still no working URL, use SQLite as fallback
if not final_database_url:
    logger.warning("All database connection attempts failed, using SQLite as fallback")
    final_database_url = "sqlite:///./app.db"

DATABASE_URL = final_database_url
logger.info(f"Using database type: {DATABASE_URL.split(':')[0]}")

# Print masked version of the DATABASE_URL for debugging
masked_url = DATABASE_URL
if "@" in masked_url:
    # Mask password in URL for logging
    parts = masked_url.split("@")
    auth_parts = parts[0].split(":")
    if len(auth_parts) > 2:
        masked_url = f"{auth_parts[0]}:****@{parts[1]}"
    
logger.info(f"Final database URL: {masked_url}")

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
                    # Use text() to properly prepare SQL statements
                    conn.execute(text("SELECT 1"))
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
