from logging.config import fileConfig
import os
import sys
import time
import logging
import socket
import urllib.parse
from sqlalchemy import engine_from_config, create_engine, text
from sqlalchemy import pool
from alembic import context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alembic.env")

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import models and database configuration
from models import Base

# Function to check if a host is reachable
def is_host_reachable(host, port, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
        s.close()
        return True
    except Exception as e:
        logger.warning(f"Host {host}:{port} is not reachable: {str(e)}")
        return False

# Get database URLs from environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_PUBLIC_URL = os.getenv("DATABASE_PUBLIC_URL")

# Determine which database URL to use
final_database_url = None

# First try with DATABASE_URL (internal)
if DATABASE_URL:
    # Parse the URL to get host and port
    parsed = urllib.parse.urlparse(DATABASE_URL)
    if parsed.hostname:
        if parsed.scheme.startswith('sqlite'):
            logger.info("Using SQLite database.")
            final_database_url = DATABASE_URL
        elif is_host_reachable(parsed.hostname, parsed.port or 5432):
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

# If still no working URL, use SQLite as fallback
if not final_database_url:
    logger.warning("All database connection attempts failed, using SQLite as fallback")
    final_database_url = "sqlite:///./app.db"

# Adjust the URL if it starts with postgres:// (SQLAlchemy wants postgresql://)
if final_database_url.startswith("postgres://"):
    final_database_url = final_database_url.replace("postgres://", "postgresql://", 1)

# This is the Alembic Config object
config = context.config

# Set the SQLAlchemy URL
logger.info(f"Setting database URL for migrations to: {final_database_url.split('@')[0].split(':')[0]}:****@{final_database_url.split('@')[1] if '@' in final_database_url else final_database_url}")
config.set_main_option("sqlalchemy.url", final_database_url)

# Interpret the config file for Python logging
fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Define retries for database connections
    MAX_RETRIES = 5
    retry_count = 0
    
    while retry_count < MAX_RETRIES:
        try:
            logger.info(f"Attempting to connect to database for migrations (attempt {retry_count + 1}/{MAX_RETRIES})")
            
            # Get the URL from config
            db_url = config.get_main_option("sqlalchemy.url")
            
            # Configure additional args based on database type
            connect_args = {}
            if db_url.startswith("postgresql"):
                connect_args = {"connect_timeout": 10}
            elif db_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
            
            # Create a custom engine with retry/reconnection settings
            connectable = create_engine(
                db_url,
                poolclass=pool.NullPool,
                connect_args=connect_args
            )
            
            # Test the connection before proceeding
            if not db_url.startswith("sqlite"):
                with connectable.connect() as test_conn:
                    # Use text() for SQL execution
                    test_conn.execute(text("SELECT 1"))
                    logger.info("Database connection successful")
            else:
                logger.info("Using SQLite database, skipping connection test")
            
            # Now use the connection for migrations
            with connectable.connect() as connection:
                context.configure(
                    connection=connection, 
                    target_metadata=target_metadata
                )

                with context.begin_transaction():
                    context.run_migrations()
            
            # If we get here, migrations were successful
            logger.info("Migrations executed successfully")
            break
            
        except Exception as e:
            retry_count += 1
            logger.error(f"Database connection failed: {str(e)}")
            
            if retry_count < MAX_RETRIES:
                wait_time = 2 ** retry_count  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error("Max retries reached. Could not establish database connection for migrations.")
                if db_url.startswith("sqlite"):
                    # For SQLite, we'll just proceed (it will create a new DB)
                    logger.warning("Using SQLite without verified connection")
                    connectable = create_engine(db_url, poolclass=pool.NullPool)
                    with connectable.connect() as connection:
                        context.configure(
                            connection=connection, 
                            target_metadata=target_metadata
                        )
                        with context.begin_transaction():
                            context.run_migrations()
                    break
                else:
                    # Try one last time with a SQLite fallback
                    logger.warning("Switching to SQLite fallback for migrations")
                    sqlite_url = "sqlite:///./fallback.db"
                    config.set_main_option("sqlalchemy.url", sqlite_url)
                    connectable = create_engine(sqlite_url, poolclass=pool.NullPool)
                    with connectable.connect() as connection:
                        context.configure(
                            connection=connection, 
                            target_metadata=target_metadata
                        )
                        with context.begin_transaction():
                            context.run_migrations()
                    break

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
