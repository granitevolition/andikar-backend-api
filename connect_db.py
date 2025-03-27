import os
import logging
import psycopg2
from psycopg2.extras import DictCursor
from contextlib import contextmanager
from urllib.parse import quote_plus

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("andikar-database")

def get_connection_params():
    """Get database connection parameters from environment variables."""
    # Priority 1: Use direct DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Convert postgres:// to postgresql:// if needed
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        logger.info("Using DATABASE_URL environment variable")
        return db_url
    
    # Priority 2: Construct URL from proxy settings
    proxy_domain = os.getenv("RAILWAY_TCP_PROXY_DOMAIN")
    proxy_port = os.getenv("RAILWAY_TCP_PROXY_PORT")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("PGDATABASE", "railway")
    
    if proxy_domain and proxy_port and password:
        # Use quote_plus to properly encode the password
        encoded_password = quote_plus(password)
        db_url = f"postgresql://{user}:{encoded_password}@{proxy_domain}:{proxy_port}/{db}"
        logger.info(f"Using Railway TCP proxy connection")
        return db_url
    
    # Fallback to direct connection parameters
    return {
        "host": os.getenv("PGHOST", "localhost"),
        "port": os.getenv("PGPORT", 5432),
        "user": user,
        "password": password,
        "database": db,
        "connect_timeout": 10,
        "application_name": "andikar_backend_api"
    }

@contextmanager
def get_db_connection():
    """Get a database connection context manager."""
    connection = None
    params = get_connection_params()
    
    try:
        if isinstance(params, str):
            # Using connection string
            connection = psycopg2.connect(params)
        else:
            # Using connection parameters
            connection = psycopg2.connect(**params)
        
        connection.autocommit = True
        yield connection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if connection:
            connection.close()

@contextmanager
def get_db_cursor(cursor_factory=DictCursor):
    """Get a database cursor context manager."""
    with get_db_connection() as connection:
        cursor = connection.cursor(cursor_factory=cursor_factory)
        try:
            yield cursor
        finally:
            cursor.close()

def execute_query(query, params=None):
    """Execute a query and return all results."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchall()

def execute_single(query, params=None):
    """Execute a query and return a single result."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.fetchone()

def execute_and_commit(query, params=None):
    """Execute a query, commit, and return affected row count."""
    with get_db_cursor() as cursor:
        cursor.execute(query, params or ())
        return cursor.rowcount
