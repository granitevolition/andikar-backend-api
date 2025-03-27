import os
import logging
import time
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("andikar-database")

# Create base class for SQLAlchemy models
Base = declarative_base()

def get_database_url():
    """Get the database URL from environment variables."""
    # Priority 1: Use the direct DATABASE_URL if available
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Convert postgres:// to postgresql:// if needed
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        logger.info(f"Using DATABASE_URL from environment")
        return db_url

    # Priority 2: Construct from proxy variables
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("PGDATABASE", "railway")
    
    if proxy_domain and proxy_port and password:
        # Use quote_plus to properly encode the password
        encoded_password = quote_plus(password)
        db_url = f"postgresql://{user}:{encoded_password}@{proxy_domain}:{proxy_port}/{db}"
        logger.info(f"Using Railway TCP proxy connection: {proxy_domain}:{proxy_port}")
        return db_url
    
    # No PostgreSQL connection available
    return None

def create_db_engine(max_attempts=5, retry_interval=2):
    """Create database engine with retry logic."""
    database_url = get_database_url()
    
    if not database_url:
        logger.error("No PostgreSQL connection configuration found")
        logger.warning("⚠️ Creating SQLite fallback engine - FOR DEVELOPMENT ONLY")
        return create_engine("sqlite:///andikar.db")
    
    # Mask password in logs
    safe_url = database_url
    if os.getenv("PGPASSWORD"):
        safe_url = safe_url.replace(os.getenv("PGPASSWORD", ""), "*" * 8)
    if os.getenv("POSTGRES_PASSWORD"):
        safe_url = safe_url.replace(os.getenv("POSTGRES_PASSWORD", ""), "*" * 8)
    logger.info(f"Database URL: {safe_url}")
    
    # Try to connect to the database with retries
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Attempting to connect to database (attempt {attempt}/{max_attempts})...")
            engine = create_engine(
                database_url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800,
                connect_args={
                    "connect_timeout": 10,
                    "application_name": "andikar_backend_api"
                }
            )
            engine.connect().close()  # Test connection
            logger.info("✅ Database connection successful!")
            return engine
        except Exception as e:
            logger.warning(f"Database connection attempt {attempt} failed: {e}")
            if attempt < max_attempts:
                backoff = 2 ** (attempt - 1)
                logger.info(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
            else:
                logger.error(f"❌ All {max_attempts} database connection attempts failed")
                logger.error(f"Last connection error: {e}")
                logger.warning("⚠️ Creating SQLite fallback engine - FOR DEVELOPMENT ONLY")
                return create_engine("sqlite:///andikar.db")

# Create engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
